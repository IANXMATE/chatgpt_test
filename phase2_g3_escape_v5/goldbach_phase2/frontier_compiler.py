from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple
import math

import numpy as np
from scipy.optimize import linprog

from .polytope import RegionPolytope
from .special_functions import EULER_GAMMA
from .flow140 import Flow140Model


@dataclass
class CompiledTerminal:
    resource: str
    unresolved_variable: str
    family: str
    upper_bound: float
    factor_count: int
    theorem_guard: str
    theorem_source: str
    phase1_oracles: List[str]
    numerical_diagnostics: dict
    state_summary: dict

    def to_dict(self):
        return {
            "resource": self.resource,
            "unresolved_variable": self.unresolved_variable,
            "family": self.family,
            "upper_bound": self.upper_bound,
            "factor_count": self.factor_count,
            "theorem_guard": self.theorem_guard,
            "theorem_source": self.theorem_source,
            "phase1_oracles": list(self.phase1_oracles),
            "numerical_diagnostics": dict(self.numerical_diagnostics),
            "state_summary": dict(self.state_summary),
        }


@dataclass
class RejectedCandidate:
    resource: str
    family: str
    reason: str
    factor_count: int
    phase1_oracles: List[str]

    def to_dict(self):
        return {
            "resource": self.resource,
            "family": self.family,
            "reason": self.reason,
            "factor_count": self.factor_count,
            "phase1_oracles": list(self.phase1_oracles),
        }


@dataclass
class CompileResult:
    terminals: Dict[str, CompiledTerminal]
    rejected: List[RejectedCandidate]
    empty_states: List[str]
    candidate_count: int

    def to_dict(self):
        return {
            "candidate_count": self.candidate_count,
            "compiled_count": len(self.terminals),
            "terminals": {
                k: v.to_dict() for k, v in self.terminals.items()
            },
            "rejected": [x.to_dict() for x in self.rejected],
            "empty_states": list(self.empty_states),
        }


class FrontierTheoremCompiler:
    """Compile Phase-1 NEG unresolved states into legal terminal upper sinks.

    Current V4 families:

    A) GENERIC_LINEAR_SIEVE_UPPER
       Phase-1 oracle: linear_sieve_candidate
       State shape: P(N), fixed threshold z=N^rho.
       Guard on the WHOLE state region:
            (1/2 - sum u_i)/rho >= 2
       Then Lemma 2.5 upper sieve gives the dynamic F integral.

    B) GENERIC_SWITCHED_BUCHSTAB_UPPER
       Phase-1 oracle: buchstab_or_switching_upper_candidate
       State shape: P(N*p1), threshold p_j.
       Guard on the WHOLE state region:
            (1 - sum u_i)/u_j >= 1
       The terminal density is the parameterized Section-5.4 switched
       Buchstab integrand.  u1=1/10 is handled pointwise, using the
       Lemma-3.5 coefficient below the boundary and Lemma-3.1 above it.

    IMPORTANT:
    - We compile only states whose entire region satisfies the theorem guard.
    - Mixed regions are rejected in V4 rather than silently clipping them.
    - Numerical quadrature is candidate-level (Sobol + positive pad), not
      interval certified.
    """

    def __init__(
        self,
        manifest: dict,
        flow_blueprint: dict,
        sieve_functions,
        buchstab_function,
        max_factor_count: int = 6,
        qmc_power: int = 16,
        qmc_scrambles: int = 2,
        qmc_relative_pad: float = 0.03,
        qmc_absolute_pad: float = 1e-7,
    ):
        self.manifest = manifest
        self.flow = flow_blueprint
        self.sieve = sieve_functions
        self.buchstab = buchstab_function
        self.max_factor_count = int(max_factor_count)
        self.qmc_power = int(qmc_power)
        self.qmc_scrambles = int(qmc_scrambles)
        self.qmc_relative_pad = float(qmc_relative_pad)
        self.qmc_absolute_pad = float(qmc_absolute_pad)

        self.states = {
            s["state_id"]: s for s in manifest["structural_states"]
        }

        self.neg_unresolved = {}
        for v in self.flow["flow_variables"]:
            if v["kind"] != "UNRESOLVED_FRONTIER":
                continue
            md = v["metadata"]
            if md.get("sign") == "NEG":
                self.neg_unresolved[md["resource"]] = v["name"]

    @staticmethod
    def parameter_dict(p):
        return {
            "alpha": float(p.alpha),
            "beta": float(p.beta),
            "gamma": float(p.gamma),
            "tau": float(p.tau),
        }

    def _state_summary(self, s):
        return {
            "factor_count": s["factor_count"],
            "sieve_set": s["sieve_set"],
            "threshold": s["threshold"],
            "anchor": s.get("anchor"),
            "sequence_kind": s["sequence_kind"],
            "region": s["region"],
            "paper_aliases": s.get("paper_aliases", []),
        }

    def _linear_candidate(self, resource, s, p, poly):
        threshold = s["threshold"]
        if (
            "linear_sieve_candidate" not in s["analytic_oracles"]
            or s["sieve_set"] != "P(N)"
            or threshold["kind"] != "fixed"
        ):
            return None

        rho_name = threshold["value"]
        if rho_name not in ("alpha", "beta", "tau"):
            return RejectedCandidate(
                resource, "GENERIC_LINEAR_SIEVE_UPPER",
                f"unsupported fixed threshold {rho_name}",
                s["factor_count"], s["analytic_oracles"],
            )

        rho = float(getattr(p, rho_name))
        n = s["factor_count"]

        _, max_sum = poly.extrema([1.0] * n) if n else (0.0, 0.0)
        s_min = (0.5 - max_sum) / rho

        if s_min < 2.0 - 1e-10:
            return RejectedCandidate(
                resource, "GENERIC_LINEAR_SIEVE_UPPER",
                f"mixed/invalid Lemma-2.5 region: min sieve parameter s={s_min:.12g}<2",
                n, s["analytic_oracles"],
            )

        pref = 2.0 * math.exp(-EULER_GAMMA) / rho

        if n == 0:
            raw = pref * float(self.sieve.F(0.5 / rho))
            upper = raw * (1.0 + self.qmc_relative_pad) + self.qmc_absolute_pad
            diag = {
                "raw": raw,
                "s_min": s_min,
                "qmc": None,
            }
        else:
            def integrand(x):
                sums = np.sum(x, axis=1)
                ss = (0.5 - sums) / rho
                return pref * self.sieve.F(ss) / np.prod(x, axis=1)

            qres = poly.qmc_integral(
                integrand,
                power=self.qmc_power,
                scrambles=self.qmc_scrambles,
                seed=260600000 + int(resource[-6:], 16) % 1000000
                     if resource.startswith("S_") else 260600001,
                relative_pad=self.qmc_relative_pad,
                absolute_pad=self.qmc_absolute_pad,
            )
            upper = qres.estimate
            diag = {
                "s_min": s_min,
                "qmc": qres.to_dict(),
            }

        return CompiledTerminal(
            resource=resource,
            unresolved_variable=self.neg_unresolved[resource],
            family="GENERIC_LINEAR_SIEVE_UPPER",
            upper_bound=float(upper),
            factor_count=n,
            theorem_guard="whole region satisfies (1/2-sum u)/rho >= 2",
            theorem_source=(
                "Li-Liu 2026 Lemma 2.5, parameterized well-factorable "
                "linear-sieve upper bound; Phase-1 oracle linear_sieve_candidate"
            ),
            phase1_oracles=list(s["analytic_oracles"]),
            numerical_diagnostics=diag,
            state_summary=self._state_summary(s),
        )

    def _buchstab_candidate(self, resource, s, p, poly):
        threshold = s["threshold"]
        if (
            "buchstab_or_switching_upper_candidate" not in s["analytic_oracles"]
            or s["sieve_set"] != "P(N*p1)"
            or threshold["kind"] != "factor"
        ):
            return None

        n = s["factor_count"]
        if n <= 0:
            return RejectedCandidate(
                resource, "GENERIC_SWITCHED_BUCHSTAB_UPPER",
                "factor threshold with zero factors",
                n, s["analytic_oracles"],
            )

        j = int(threshold["value"]) - 1
        if not 0 <= j < n:
            return RejectedCandidate(
                resource, "GENERIC_SWITCHED_BUCHSTAB_UPPER",
                f"threshold factor index {j+1} outside factor count {n}",
                n, s["analytic_oracles"],
            )

        # arg=(1-sum u)/u_j >=1 <=> sum u + u_j <=1.
        coeff = np.ones(n)
        coeff[j] += 1.0
        _, max_sum_plus = poly.extrema(coeff)
        arg_guard = 1.0 - max_sum_plus

        if arg_guard < -1e-10:
            return RejectedCandidate(
                resource, "GENERIC_SWITCHED_BUCHSTAB_UPPER",
                (
                    "mixed Buchstab domain: region contains "
                    f"(1-sum u)/u_{j+1}<1; linear guard residual={arg_guard:.12g}"
                ),
                n, s["analytic_oracles"],
            )

        def integrand(x):
            sums = np.sum(x, axis=1)
            uj = x[:, j]
            arg = (1.0 - sums) / uj
            # Numerical tolerance at the linear guard boundary.
            arg = np.maximum(arg, 1.0)
            omega = self.buchstab.w(arg)

            denominator = np.prod(x, axis=1) * uj
            u1 = x[:, 0]

            # Section 5.4 theorem-induced distribution split.
            distribution = np.where(
                u1 < 0.1,
                (36.0 / 5.0) / (1.0 - u1),
                8.0,
            )
            return distribution * omega / denominator

        qres = poly.qmc_integral(
            integrand,
            power=self.qmc_power,
            scrambles=self.qmc_scrambles,
            seed=261100000 + int(resource[-6:], 16) % 1000000
                 if resource.startswith("S_") else 261100001,
            relative_pad=self.qmc_relative_pad,
            absolute_pad=self.qmc_absolute_pad,
        )

        return CompiledTerminal(
            resource=resource,
            unresolved_variable=self.neg_unresolved[resource],
            family="GENERIC_SWITCHED_BUCHSTAB_UPPER",
            upper_bound=float(qres.estimate),
            factor_count=n,
            theorem_guard=(
                f"whole region satisfies (1-sum u)/u_{j+1} >= 1; "
                "u1=1/10 split evaluated pointwise"
            ),
            theorem_source=(
                "Li-Liu 2026 Section 5.4 + Lemmas 3.1/3.5, generalized "
                "to Phase-1 states explicitly marked "
                "buchstab_or_switching_upper_candidate"
            ),
            phase1_oracles=list(s["analytic_oracles"]),
            numerical_diagnostics={
                "threshold_factor": j + 1,
                "linear_guard_residual_1_minus_max_sum_plus_uj": arg_guard,
                "qmc": qres.to_dict(),
            },
            state_summary=self._state_summary(s),
        )

    def compile(self, p) -> CompileResult:
        params = self.parameter_dict(p)
        terminals = {}
        rejected = []
        empty = []
        candidate_count = 0

        for resource, unresolved_var in sorted(self.neg_unresolved.items()):
            s = self.states.get(resource)
            if s is None:
                continue

            ors = set(s["analytic_oracles"])
            is_candidate = (
                (
                    "linear_sieve_candidate" in ors
                    and s["sieve_set"] == "P(N)"
                    and s["threshold"]["kind"] == "fixed"
                )
                or (
                    "buchstab_or_switching_upper_candidate" in ors
                    and s["sieve_set"] == "P(N*p1)"
                    and s["threshold"]["kind"] == "factor"
                )
            )
            if not is_candidate:
                continue

            candidate_count += 1

            if s["factor_count"] > self.max_factor_count:
                rejected.append(RejectedCandidate(
                    resource=resource,
                    family="DIMENSION_LIMIT",
                    reason=(
                        f"factor_count={s['factor_count']} exceeds "
                        f"V4 max_factor_count={self.max_factor_count}"
                    ),
                    factor_count=s["factor_count"],
                    phase1_oracles=s["analytic_oracles"],
                ))
                continue

            poly = RegionPolytope(s, params)
            if not poly.feasible():
                empty.append(resource)
                continue

            result = self._linear_candidate(resource, s, p, poly)
            if result is None:
                result = self._buchstab_candidate(resource, s, p, poly)

            if isinstance(result, CompiledTerminal):
                terminals[resource] = result
            elif isinstance(result, RejectedCandidate):
                rejected.append(result)

        return CompileResult(
            terminals=terminals,
            rejected=rejected,
            empty_states=empty,
            candidate_count=candidate_count,
        )

    # ------------------------------------------------------------------
    # Structural blocker analysis (parameter-independent)
    # ------------------------------------------------------------------
    def blocker_ranking(self, top_n: int = 30):
        strict = Flow140Model(
            self.flow,
            allow_g16_paper_bridge=True,
            strict_unresolved=True,
        )
        relaxed = Flow140Model(
            self.flow,
            allow_g16_paper_bridge=True,
            strict_unresolved=False,
        )

        reachable, forced = strict.certifiably_reachable_rewrites()

        unresolved_vars = [
            v for v in self.flow["flow_variables"]
            if v["kind"] == "UNRESOLVED_FRONTIER"
        ]
        unresolved_indices = [
            relaxed.index[v["name"]] for v in unresolved_vars
        ]

        counts = Counter()
        examples = {}

        for rw in forced:
            c = np.zeros(relaxed.n)
            c[relaxed.index[rw]] = -1.0
            r1 = linprog(
                c,
                A_eq=relaxed.A_eq,
                b_eq=relaxed.b_eq,
                bounds=relaxed.bounds,
                method="highs",
            )
            if not r1.success:
                continue
            max_rw = float(r1.x[relaxed.index[rw]])
            if max_rw <= 1e-10:
                continue

            # Among near-maximal uses of this rewrite, minimize total
            # unresolved mass.  Positive entries are the first practical
            # blockers for this route.
            A_ub = np.zeros((1, relaxed.n))
            A_ub[0, relaxed.index[rw]] = -1.0
            b_ub = np.array([-0.999 * max_rw])

            c2 = np.zeros(relaxed.n)
            c2[unresolved_indices] = 1.0
            r2 = linprog(
                c2,
                A_ub=A_ub,
                b_ub=b_ub,
                A_eq=relaxed.A_eq,
                b_eq=relaxed.b_eq,
                bounds=relaxed.bounds,
                method="highs",
            )
            x = r2.x if r2.success else r1.x

            for v in unresolved_vars:
                value = float(x[relaxed.index[v["name"]]])
                if value > 1e-9:
                    counts[v["name"]] += 1
                    examples.setdefault(v["name"], []).append(rw)

        ranking = []
        for unresolved_name, count in counts.most_common(top_n):
            resource = unresolved_name.split("__", 2)[2]
            state = self.states.get(resource)
            ranking.append({
                "unresolved_variable": unresolved_name,
                "resource": resource,
                "blocked_rewrite_count": count,
                "example_rewrites": examples[unresolved_name][:8],
                "state": self._state_summary(state) if state else None,
                "analytic_oracles": (
                    list(state["analytic_oracles"]) if state else []
                ),
            })
        return {
            "base_reachable_rewrites": len(reachable),
            "base_forced_zero_rewrites": len(forced),
            "ranking": ranking,
        }
