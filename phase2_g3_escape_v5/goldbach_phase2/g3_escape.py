from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple
import copy
import math

import numpy as np
from scipy.optimize import linprog

from .compiled_flow import CompiledFlow140Model
from .frontier_compiler import CompiledTerminal


@dataclass
class G3Structure:
    state_id: str
    direct_upper_terminal: str
    neg_rewrite: str
    base_state: str
    correction_states: List[str]
    base_unresolved_variable: str

    def to_dict(self):
        return {
            "state_id": self.state_id,
            "direct_upper_terminal": self.direct_upper_terminal,
            "neg_rewrite": self.neg_rewrite,
            "base_state": self.base_state,
            "correction_states": list(self.correction_states),
            "base_unresolved_variable": self.base_unresolved_variable,
        }


@dataclass
class EscapeSolve:
    success: bool
    message: str
    margin_2D: float
    margin_4D: float
    margin_D: float
    direct_g3_terminal_flow: float
    direct_g3_coefficient_4D: float
    g3_rewrite_flow: float
    source_weights: Dict[str, float]
    active_rewrites: int
    max_conservation_residual: float
    genuine_unresolved: Dict[str, float]
    compiled_terminal_uses: Dict[str, dict]
    hypothetical_base_upper: Optional[float] = None
    x: Optional[np.ndarray] = None

    def to_dict(self):
        return {
            "success": self.success,
            "message": self.message,
            "margin_2D": self.margin_2D,
            "margin_4D": self.margin_4D,
            "margin_D": self.margin_D,
            "direct_g3_terminal_flow": self.direct_g3_terminal_flow,
            "direct_g3_coefficient_4D": self.direct_g3_coefficient_4D,
            "g3_rewrite_flow": self.g3_rewrite_flow,
            "source_weights": self.source_weights,
            "active_rewrites": self.active_rewrites,
            "max_conservation_residual": self.max_conservation_residual,
            "genuine_unresolved": self.genuine_unresolved,
            "compiled_terminal_uses": self.compiled_terminal_uses,
            "hypothetical_base_upper": self.hypothetical_base_upper,
        }


@dataclass
class CriticalBoundResult:
    feasible_with_zero_bound: bool
    critical_upper: Optional[float]
    lower_bracket: Optional[float]
    upper_bracket: Optional[float]
    iterations: int
    margin_at_zero: Optional[float]
    margin_at_critical: Optional[float]
    baseline_direct_g3_bound: float
    ratio_to_direct_g3_bound: Optional[float]
    note: str

    def to_dict(self):
        return {
            "feasible_with_zero_bound": self.feasible_with_zero_bound,
            "critical_upper": self.critical_upper,
            "lower_bracket": self.lower_bracket,
            "upper_bracket": self.upper_bracket,
            "iterations": self.iterations,
            "margin_at_zero": self.margin_at_zero,
            "margin_at_critical": self.margin_at_critical,
            "baseline_direct_g3_bound": self.baseline_direct_g3_bound,
            "ratio_to_direct_g3_bound": self.ratio_to_direct_g3_bound,
            "note": self.note,
        }


class G3EscapeAnalyzer:
    """Targeted exact-flow analysis of the Phase-1 G3 Buchstab escape route.

    Phase-1 contains an exact transition

        G3 = BASE - CORRECTION,

    so in the lower-bound certificate

        -G3 = -BASE + CORRECTION.

    CORRECTION is positive and may always be discarded with the trivial
    lower bound 0.  The sole first blocker is therefore a NEG BASE state.

    V5 does NOT claim a theorem for BASE.  Instead it treats an upper bound

        BASE <= U * C(N)N/log^2 N

    as a symbolic/hypothetical theorem and solves for the largest U for which
    the complete proof would still have positive margin.

    That critical U is a theorem-design target, not a proved bound.
    """

    def __init__(self, manifest: dict, flow_blueprint: dict):
        self.manifest = manifest
        self.flow = flow_blueprint
        self.states = {s["state_id"]: s for s in manifest["structural_states"]}
        self.structure = self._discover_structure()

    def _discover_structure(self) -> G3Structure:
        g3 = self.flow["alias_map"]["G3"]

        direct = None
        neg_rewrite = None
        base_unresolved = None

        for v in self.flow["flow_variables"]:
            md = v.get("metadata", {})
            if (
                v["kind"] == "TERMINAL_ALLOCATION"
                and md.get("paper_names") == ["G3"]
                and md.get("sign") == "NEG"
                and md.get("rule", {}).get("bound_direction") == "upper"
            ):
                direct = v["name"]

            if (
                v["kind"] == "REWRITE_ALLOCATION"
                and md.get("parent") == g3
                and md.get("sign") == "NEG"
            ):
                neg_rewrite = v["name"]

        # Find the exact structural transition whose parent is G3.
        transition = None
        for t in self.manifest["structural_transitions"]:
            if t["parent"] == g3:
                transition = t
                break
        if transition is None:
            raise ValueError("Phase-1 manifest has no structural transition from G3")

        plus_children = [
            c["state_id"] for c in transition["children"]
            if float(c["multiplier"]) > 0
        ]
        minus_children = [
            c["state_id"] for c in transition["children"]
            if float(c["multiplier"]) < 0
        ]
        if len(plus_children) != 1:
            raise ValueError(
                "Expected G3 Buchstab expansion to have one +BASE child"
            )
        base = plus_children[0]

        # In a NEG parent expansion, the +BASE child becomes NEG.
        for v in self.flow["flow_variables"]:
            md = v.get("metadata", {})
            if (
                v["kind"] == "UNRESOLVED_FRONTIER"
                and md.get("resource") == base
                and md.get("sign") == "NEG"
            ):
                base_unresolved = v["name"]
                break

        if not all([direct, neg_rewrite, base_unresolved]):
            raise ValueError(
                "Could not discover complete G3 escape structure "
                f"(direct={direct}, rewrite={neg_rewrite}, base_unresolved={base_unresolved})"
            )

        return G3Structure(
            state_id=g3,
            direct_upper_terminal=direct,
            neg_rewrite=neg_rewrite,
            base_state=base,
            correction_states=minus_children,
            base_unresolved_variable=base_unresolved,
        )

    def _make_model(self, flow, compiled_terminals, hypothetical_upper=None):
        terminals = dict(compiled_terminals)

        if hypothetical_upper is not None:
            base_state = self.states[self.structure.base_state]
            terminals[self.structure.base_state] = CompiledTerminal(
                resource=self.structure.base_state,
                unresolved_variable=self.structure.base_unresolved_variable,
                family="HYPOTHETICAL_G3_BASE_UPPER",
                upper_bound=float(hypothetical_upper),
                factor_count=int(base_state["factor_count"]),
                theorem_guard="NOT PROVED: symbolic G3-base theorem target",
                theorem_source=(
                    "Hypothetical terminal used only for sensitivity/search. "
                    "No theorem is asserted by V5."
                ),
                phase1_oracles=list(base_state["analytic_oracles"]),
                numerical_diagnostics={
                    "status": "SYMBOLIC_THEOREM_TARGET_ONLY",
                },
                state_summary={
                    "factor_count": base_state["factor_count"],
                    "sieve_set": base_state["sieve_set"],
                    "threshold": base_state["threshold"],
                    "anchor": base_state.get("anchor"),
                    "region": base_state["region"],
                },
            )

        return CompiledFlow140Model(
            flow,
            terminals,
            allow_g16_paper_bridge=True,
        )

    def _solve_lp(
        self,
        model,
        theorem_eval,
        *,
        disable_direct_g3=False,
        max_direct_g3_flow=None,
        force_g3_rewrite_min=None,
        relax_genuine_unresolved=False,
        minimize_unresolved=False,
        hypothetical_upper=None,
    ) -> EscapeSolve:
        margin = model.terminal_margin_vector(theorem_eval)
        bounds = list(model.bounds)

        if disable_direct_g3:
            bounds[model.index[self.structure.direct_upper_terminal]] = (0.0, 0.0)
        elif max_direct_g3_flow is not None:
            bounds[model.index[self.structure.direct_upper_terminal]] = (
                0.0, float(max_direct_g3_flow)
            )

        if force_g3_rewrite_min is not None:
            j = model.index[self.structure.neg_rewrite]
            old_lo, old_hi = bounds[j]
            lo = max(float(force_g3_rewrite_min), float(old_lo or 0.0))
            bounds[j] = (lo, old_hi)

        compiled_names = {
            t.unresolved_variable for t in model.compiled_terminals.values()
        }
        genuine_unresolved_vars = []
        if relax_genuine_unresolved:
            for v in model.original_variables:
                if v["kind"] != "UNRESOLVED_FRONTIER":
                    continue
                if v["name"] in compiled_names:
                    continue
                genuine_unresolved_vars.append(v)
                bounds[model.index[v["name"]]] = (0.0, None)

        if minimize_unresolved:
            objective = np.zeros(model.n, dtype=float)
            for v in genuine_unresolved_vars:
                objective[model.index[v["name"]]] = 1.0
            # Tie-break weakly toward better true margin.
            objective -= 1e-8 * margin
        else:
            objective = -margin

        res = linprog(
            objective,
            A_eq=model.A_eq,
            b_eq=model.b_eq,
            bounds=bounds,
            method="highs",
        )

        if not res.success:
            return EscapeSolve(
                success=False,
                message=res.message,
                margin_2D=float("-inf"),
                margin_4D=float("-inf"),
                margin_D=float("-inf"),
                direct_g3_terminal_flow=float("nan"),
                direct_g3_coefficient_4D=float("nan"),
                g3_rewrite_flow=float("nan"),
                source_weights={},
                active_rewrites=0,
                max_conservation_residual=float("inf"),
                genuine_unresolved={},
                compiled_terminal_uses={},
                hypothetical_base_upper=hypothetical_upper,
                x=None,
            )

        x = np.asarray(res.x, dtype=float)
        true_margin_2d = float(margin @ x)

        direct_flow = float(
            x[model.index[self.structure.direct_upper_terminal]]
        )
        rewrite_flow = float(
            x[model.index[self.structure.neg_rewrite]]
        )

        source_weights = {}
        active_rewrites = 0
        genuine = {}
        compiled_uses = {}

        for v in model.original_variables:
            val = float(x[model.index[v["name"]]])
            if v["kind"] == "SOURCE_MIX_WEIGHT" and abs(val) > 1e-12:
                source_weights[v["name"]] = val
            elif v["kind"] == "REWRITE_ALLOCATION" and abs(val) > 1e-10:
                active_rewrites += 1
            elif (
                v["kind"] == "UNRESOLVED_FRONTIER"
                and v["name"] not in compiled_names
                and val > 1e-10
            ):
                genuine[v["name"]] = val

        for resource, terminal in model.compiled_terminals.items():
            val = float(x[model.index[terminal.unresolved_variable]])
            if val > 1e-10:
                compiled_uses[resource] = {
                    "flow": val,
                    "upper_bound": float(terminal.upper_bound),
                    "family": terminal.family,
                    "contribution_2D": -val * float(terminal.upper_bound),
                }

        residual = model.A_eq @ x - model.b_eq

        return EscapeSolve(
            success=True,
            message=res.message,
            margin_2D=true_margin_2d,
            margin_4D=2.0 * true_margin_2d,
            margin_D=true_margin_2d / 2.0,
            direct_g3_terminal_flow=direct_flow,
            # 4D normalization = 2 * 2D flow; NEG sign:
            direct_g3_coefficient_4D=-2.0 * direct_flow,
            g3_rewrite_flow=rewrite_flow,
            source_weights=source_weights,
            active_rewrites=active_rewrites,
            max_conservation_residual=float(np.max(np.abs(residual))),
            genuine_unresolved=genuine,
            compiled_terminal_uses=compiled_uses,
            hypothetical_base_upper=hypothetical_upper,
            x=x,
        )

    def baseline(self, theorem_eval, compiled_terminals):
        model = self._make_model(
            self.flow, compiled_terminals, hypothetical_upper=None
        )
        return self._solve_lp(model, theorem_eval)

    def strict_without_direct_g3(self, theorem_eval, compiled_terminals):
        model = self._make_model(
            self.flow, compiled_terminals, hypothetical_upper=None
        )
        return self._solve_lp(
            model, theorem_eval, disable_direct_g3=True
        )

    def first_blockers(self, theorem_eval, compiled_terminals):
        """Disable direct G3, relax only genuine unresolved, minimize their sum."""
        model = self._make_model(
            self.flow, compiled_terminals, hypothetical_upper=None
        )
        sol = self._solve_lp(
            model,
            theorem_eval,
            disable_direct_g3=True,
            relax_genuine_unresolved=True,
            minimize_unresolved=True,
        )
        if not sol.success:
            return sol, []

        rows = []
        for name, flow in sorted(
            sol.genuine_unresolved.items(),
            key=lambda kv: -kv[1]
        ):
            # unresolved variable naming: x_unresolved__SIGN__STATE
            resource = name.split("__", 2)[2]
            state = self.states.get(resource)
            rows.append({
                "unresolved_variable": name,
                "resource": resource,
                "flow": flow,
                "state": state,
            })
        return sol, rows

    def solve_with_hypothetical_base(
        self,
        theorem_eval,
        compiled_terminals,
        upper: float,
        disable_direct_g3: bool = True,
    ):
        model = self._make_model(
            self.flow, compiled_terminals, hypothetical_upper=float(upper)
        )
        return self._solve_lp(
            model,
            theorem_eval,
            disable_direct_g3=disable_direct_g3,
            hypothetical_upper=float(upper),
        )

    def critical_base_upper(
        self,
        theorem_eval,
        compiled_terminals,
        target_margin_4D: float = 0.0,
        upper_search_cap: float = 20.0,
        tolerance: float = 1e-7,
        max_iter: int = 80,
    ) -> CriticalBoundResult:
        """Largest hypothetical BASE upper constant compatible with target margin."""

        g3_bound = float(theorem_eval.bounds["G3"])

        z = self.solve_with_hypothetical_base(
            theorem_eval, compiled_terminals, 0.0, disable_direct_g3=True
        )
        if not z.success or z.margin_4D < target_margin_4D:
            return CriticalBoundResult(
                feasible_with_zero_bound=False,
                critical_upper=None,
                lower_bracket=None,
                upper_bracket=None,
                iterations=0,
                margin_at_zero=(z.margin_4D if z.success else None),
                margin_at_critical=None,
                baseline_direct_g3_bound=g3_bound,
                ratio_to_direct_g3_bound=None,
                note=(
                    "Even a hypothetical zero-cost G3-base terminal cannot "
                    "reach the requested margin; another blocker or the "
                    "structural architecture itself is limiting."
                ),
            )

        lo = 0.0
        hi = max(g3_bound, 1.0)

        # Expand upper bracket until margin falls below target.
        while hi < upper_search_cap:
            s = self.solve_with_hypothetical_base(
                theorem_eval, compiled_terminals, hi, disable_direct_g3=True
            )
            if (not s.success) or s.margin_4D < target_margin_4D:
                break
            lo = hi
            hi *= 2.0

        if hi >= upper_search_cap:
            hi = upper_search_cap
            s = self.solve_with_hypothetical_base(
                theorem_eval, compiled_terminals, hi, disable_direct_g3=True
            )
            if s.success and s.margin_4D >= target_margin_4D:
                return CriticalBoundResult(
                    feasible_with_zero_bound=True,
                    critical_upper=hi,
                    lower_bracket=hi,
                    upper_bracket=None,
                    iterations=0,
                    margin_at_zero=z.margin_4D,
                    margin_at_critical=s.margin_4D,
                    baseline_direct_g3_bound=g3_bound,
                    ratio_to_direct_g3_bound=hi / g3_bound,
                    note=(
                        "Critical upper exceeds search cap; increase "
                        "--upper-cap if needed."
                    ),
                )

        last_good = z
        iterations = 0
        while iterations < max_iter and hi - lo > tolerance:
            mid = 0.5 * (lo + hi)
            s = self.solve_with_hypothetical_base(
                theorem_eval, compiled_terminals, mid, disable_direct_g3=True
            )
            if s.success and s.margin_4D >= target_margin_4D:
                lo = mid
                last_good = s
            else:
                hi = mid
            iterations += 1

        critical = lo
        return CriticalBoundResult(
            feasible_with_zero_bound=True,
            critical_upper=critical,
            lower_bracket=lo,
            upper_bracket=hi,
            iterations=iterations,
            margin_at_zero=z.margin_4D,
            margin_at_critical=last_good.margin_4D,
            baseline_direct_g3_bound=g3_bound,
            ratio_to_direct_g3_bound=critical / g3_bound,
            note=(
                "This is a hypothetical theorem target only. A proof that "
                "the G3-base state has upper constant <= critical_upper is "
                "still required."
            ),
        )

    def direct_g3_pareto(
        self,
        theorem_eval,
        compiled_terminals,
        fractions=(1.0, 0.9, 0.75, 0.5, 0.25, 0.0),
        hypothetical_base_upper=None,
    ):
        model = self._make_model(
            self.flow,
            compiled_terminals,
            hypothetical_upper=hypothetical_base_upper,
        )
        baseline = self._solve_lp(model, theorem_eval)
        if not baseline.success:
            return []

        baseline_flow = baseline.direct_g3_terminal_flow
        rows = []
        for f in fractions:
            sol = self._solve_lp(
                model,
                theorem_eval,
                max_direct_g3_flow=float(f) * baseline_flow,
                hypothetical_upper=hypothetical_base_upper,
            )
            rows.append({
                "fraction": float(f),
                "max_direct_g3_flow": float(f) * baseline_flow,
                "success": sol.success,
                "margin_4D": sol.margin_4D if sol.success else None,
                "direct_g3_coefficient_4D": (
                    sol.direct_g3_coefficient_4D if sol.success else None
                ),
                "g3_rewrite_flow": (
                    sol.g3_rewrite_flow if sol.success else None
                ),
            })
        return rows
