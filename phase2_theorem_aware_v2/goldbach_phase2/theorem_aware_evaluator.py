from __future__ import annotations

from dataclasses import dataclass, asdict
import math
from typing import Any, Dict, List, Tuple

import numpy as np

from .special_functions import (
    EULER_GAMMA,
    LinearSieveFunctions,
    BuchstabFunction,
)
from .theorem_registry import (
    GuardCheck, SplitRecord, TheoremTrace, THEOREM_SOURCES,
)


EXP_MINUS_GAMMA = math.exp(-EULER_GAMMA)


@dataclass(frozen=True)
class Parameters:
    a: float
    alpha: float
    beta: float
    gamma: float
    epsilon: float = 1e-10

    @property
    def tau(self) -> float:
        return (self.a - 1.0)/self.a - self.epsilon

    @property
    def delta(self) -> float:
        return 2.0 - self.a

    def to_dict(self):
        d = asdict(self)
        d["tau"] = self.tau
        d["delta"] = self.delta
        return d


@dataclass
class EvaluationResult:
    valid: bool
    parameters: Dict[str, float]
    bounds: Dict[str, float]
    contributions: Dict[str, float]
    margin_4D: float
    margin_D: float
    theorem_trace: Dict[str, Any]
    per_G: Dict[str, Any]
    status: str

    def to_dict(self):
        return {
            "valid": self.valid,
            "parameters": self.parameters,
            "bounds": self.bounds,
            "contributions": self.contributions,
            "margin_4D": self.margin_4D,
            "margin_D": self.margin_D,
            "theorem_trace": self.theorem_trace,
            "per_G": self.per_G,
            "status": self.status,
        }


class GaussLegendre:
    def __init__(self, order: int):
        self.order = int(order)
        self.x, self.w = np.polynomial.legendre.leggauss(self.order)

    def nodes_weights(self, a: float, b: float):
        if b <= a:
            return np.empty(0), np.empty(0)
        h = 0.5*(b-a)
        m = 0.5*(a+b)
        return m + h*self.x, h*self.w

    def integrate1(self, f, a, b):
        x, w = self.nodes_weights(a, b)
        if x.size == 0:
            return 0.0
        return float(np.sum(w*np.asarray(f(x), dtype=float)))

    def integrate2(self, f, a, b, lo2, hi2):
        x1, w1 = self.nodes_weights(a, b)
        total = 0.0
        for u, wu in zip(x1, w1):
            lo, hi = float(lo2(u)), float(hi2(u))
            x2, w2 = self.nodes_weights(lo, hi)
            if x2.size:
                total += float(wu*np.sum(w2*np.asarray(f(u, x2), dtype=float)))
        return total


class TheoremAwarePaperPathEvaluator:
    """Theorem-aware dynamic evaluator for the Li-Liu 12-term architecture.

    Pipeline:
        parameters
          -> Proposition 4.3 guards
          -> estimator-specific guards
          -> theorem-induced splits
          -> dynamic F/f/w
          -> G1..G12
          -> 12-term margin.

    This is still a numerical candidate evaluator, not interval arithmetic.
    """

    COEFF = {
        "G1": +3.0, "G2": +1.0, "G3": -4.0,
        "G4": -1.0, "G5": -1.0, "G6": +1.0,
        "G7": +1.0, "G8": -2.0, "G9": -1.0,
        "G10": -1.0, "G11": -1.0, "G12": -1.0,
    }

    def __init__(
        self,
        lowdim_order: int = 40,
        highdim_order: int = 10,
        sieve_step: float = 2e-5,
        buchstab_step: float = 2e-5,
        numeric_pad_per_G: float = 2e-6,
    ):
        self.q = GaussLegendre(lowdim_order)
        self.q4 = GaussLegendre(highdim_order)
        self.sieve = LinearSieveFunctions(step=sieve_step, s_max=10.0)
        self.buchstab = BuchstabFunction(step=buchstab_step, u_max=40.0)
        self.numeric_pad_per_G = float(numeric_pad_per_G)
        self.settings = {
            "lowdim_gauss_order": lowdim_order,
            "highdim_gauss_order": highdim_order,
            "linear_sieve_grid_step": sieve_step,
            "buchstab_grid_step": buchstab_step,
            "numeric_pad_per_G": numeric_pad_per_G,
            "status": "NUMERICAL_CANDIDATE_THEOREM_GUARDED_NOT_INTERVAL_CERTIFIED",
        }

    # ------------------------------------------------------------------
    # Guard layer
    # ------------------------------------------------------------------
    def build_trace(self, p: Parameters) -> TheoremTrace:
        tr = TheoremTrace()
        eps = p.epsilon
        middle = (1.0 - 3.0*p.beta)/3.0

        def g(name, passed, expr, *, value=None, threshold=None,
              theorem="", source="", hard=True, note=""):
            tr.add_guard(GuardCheck(
                name=name, passed=bool(passed), expression=expr,
                value=value, threshold=threshold, theorem=theorem,
                source=source, hard=hard, note=note,
            ))

        # Proposition 4.3.
        g("P43_a", 1.5+3*eps < p.a < 2.0,
          "1.5+3ε < a < 2",
          value=p.a, theorem="Proposition 4.3",
          source=THEOREM_SOURCES["PROP43"])
        g("P43_alpha_beta", 1/18 < p.alpha < p.beta,
          "1/18 < alpha < beta",
          theorem="Proposition 4.3", source=THEOREM_SOURCES["PROP43"])
        g("P43_beta_middle", p.beta < middle,
          "beta < (1-3 beta)/3",
          value=p.beta, threshold=middle,
          theorem="Proposition 4.3", source=THEOREM_SOURCES["PROP43"])
        g("P43_middle_gamma", middle < p.gamma < 1/3,
          "(1-3 beta)/3 < gamma < 1/3",
          value=p.gamma, theorem="Proposition 4.3",
          source=THEOREM_SOURCES["PROP43"])
        g("P43_tau", 1/3 < p.tau,
          "1/3 < tau=(a-1)/a-epsilon",
          value=p.tau, threshold=1/3,
          theorem="Proposition 4.3", source=THEOREM_SOURCES["PROP43"])

        # G1/G2: z <= Q^(1/2), Q~N^(1/2), automatically true in P4.3
        # for alpha,beta<1/4. Keep it explicit in the trace.
        g("G1_linear_sieve", p.alpha < 1/4,
          "alpha < 1/4  (asymptotic form of z=N^alpha <= Q^(1/2), Q~N^(1/2))",
          value=p.alpha, threshold=1/4,
          theorem="Lemma 2.5", source=THEOREM_SOURCES["LINEAR_WF"])
        g("G2_linear_sieve", p.beta < 1/4,
          "beta < 1/4",
          value=p.beta, threshold=1/4,
          theorem="Lemma 2.5", source=THEOREM_SOURCES["LINEAR_WF"])

        # G4 reaches u=1/3.  Lemma 2.5 requires
        # alpha < (1/2-u)/2 uniformly, hence alpha<1/12.
        g("G4_uniform_upper_sieve", p.alpha < 1/12,
          "alpha < 1/12  (uniform s=(1/2-u)/alpha > 2 for u<=1/3)",
          value=p.alpha, threshold=1/12,
          theorem="Lemma 2.5 upper bound",
          source=THEOREM_SOURCES["LINEAR_WF"],
          note="No alternative upper estimator is registered outside this guard.")

        # G5 ends at gamma; record its own guard too.
        g("G5_uniform_upper_sieve", 2*p.alpha + p.gamma < 1/2,
          "2 alpha + gamma < 1/2",
          value=2*p.alpha+p.gamma, threshold=1/2,
          theorem="Lemma 2.5 upper bound",
          source=THEOREM_SOURCES["LINEAR_WF"])

        # G8 structural switching step: paper uses gamma=3/11>1/4.
        g("G8_single_remaining_prime", p.gamma > 1/4,
          "gamma > 1/4",
          value=p.gamma, threshold=1/4,
          theorem="Section 5.3 switching structure",
          source=THEOREM_SOURCES["SEC53"],
          note="Ensures the unsieved remainder cannot have two prime factors.")

        # G11/G12 only require Buchstab argument >=1; do NOT impose >=3.
        g11_min = (1.0 - 4.0*p.beta)/p.beta
        g12_min = (1.0 - 3.0*p.beta - p.gamma)/p.beta
        g("G11_buchstab_domain", g11_min > 1.0,
          "(1-4 beta)/beta > 1",
          value=g11_min, threshold=1.0,
          theorem="Lemma 2.1 Buchstab domain",
          source=THEOREM_SOURCES["BUCHSTAB"])
        g("G12_buchstab_domain", g12_min > 1.0,
          "(1-3 beta-gamma)/beta > 1",
          value=g12_min, threshold=1.0,
          theorem="Lemma 2.1 Buchstab domain",
          source=THEOREM_SOURCES["BUCHSTAB"],
          note="Arguments below 3 are legal; w is evaluated dynamically.")

        # Theorem-induced splits.
        tr.add_split(SplitRecord(
            target="G6,G7",
            variable="u+v",
            boundary="u+v = 1/2 - 2 alpha",
            left_rule="Lemma 2.5 lower sieve with dynamic f(s)",
            right_rule="trivial lower bound S>=0",
            source="Li-Liu Section 5.2; f(s)=0 for s<=2",
            note="Lossless for the lower-bound certificate.",
        ))
        tr.add_split(SplitRecord(
            target="G9",
            variable="u=t1",
            boundary="u = 1/10",
            left_rule="Lemma 3.5, coefficient 36/5 and extra 1/(1-u)",
            right_rule="Lemma 3.1, coefficient 8",
            source=THEOREM_SOURCES["DIST_SMALL"],
            note="This is a genuine theorem applicability boundary.",
        ))
        tr.add_split(SplitRecord(
            target="G11,G12",
            variable="t1",
            boundary="t1 = 1/10",
            left_rule="Lemma 3.5 switched distribution factor 36/5",
            right_rule="Lemma 3.1 switched distribution factor 8",
            source="Li-Liu Section 5.4",
        ))

        return tr

    def _pref_alpha(self, p):
        return 2.0*EXP_MINUS_GAMMA/p.alpha

    # ------------------------------------------------------------------
    # G1..G10
    # ------------------------------------------------------------------
    def G1(self, p, tr):
        s = 0.5/p.alpha
        v = self._pref_alpha(p)*self.sieve.f(s)
        tr.add_application(target="G1", theorem="Lemma 2.5 lower",
                           source=THEOREM_SOURCES["LINEAR_WF"],
                           detail=f"s=1/(2alpha)={s:.12g}")
        return v, {"s": s}

    def G2(self, p, tr):
        s = 0.5/p.beta
        v = 2.0*EXP_MINUS_GAMMA/p.beta*self.sieve.f(s)
        tr.add_application(target="G2", theorem="Lemma 2.5 lower",
                           source=THEOREM_SOURCES["LINEAR_WF"],
                           detail=f"s=1/(2beta)={s:.12g}")
        return v, {"s": s}

    def G3(self, p, tr):
        # Section 5.3 formula with the Proposition-4.3 lower endpoint tau
        # left symbolic instead of substituting 9/19.
        v = 8.0*math.log((1.0-p.tau)/p.tau)
        tr.add_application(
            target="G3",
            theorem="Section 5.3 switching upper bound",
            source=THEOREM_SOURCES["SEC53"],
            detail="8 * integral_tau^(1/2) du/[u(1-u)]",
        )
        return v, {"tau": p.tau}

    def G4(self, p, tr):
        v = self._pref_alpha(p)*self.q.integrate1(
            lambda u: self.sieve.F((0.5-u)/p.alpha)/u,
            p.alpha, 1/3,
        )
        tr.add_application(target="G4", theorem="Lemma 2.5 upper",
                           source=THEOREM_SOURCES["LINEAR_WF"],
                           detail="u in [alpha,1/3], dynamic F((1/2-u)/alpha)")
        return v, {}

    def G5(self, p, tr):
        v = self._pref_alpha(p)*self.q.integrate1(
            lambda u: self.sieve.F((0.5-u)/p.alpha)/u,
            p.alpha, p.gamma,
        )
        tr.add_application(target="G5", theorem="Lemma 2.5 upper",
                           source=THEOREM_SOURCES["LINEAR_WF"],
                           detail="u in [alpha,gamma], dynamic F")
        return v, {}

    def G6(self, p, tr):
        cutoff = 0.5 - 2.0*p.alpha
        eligible_measure_proxy = 0.0

        def hi2(u):
            return min(p.beta, cutoff-u)

        def lo2(u):
            return u

        # Only the region s>=2 is sent through the lower sieve.
        u_hi = min(p.beta, cutoff/2.0)
        if u_hi <= p.alpha:
            return 0.0, {"eligible_u_range": None, "cutoff_u_plus_v": cutoff}

        val = self.q.integrate2(
            lambda u, v: self.sieve.f((0.5-u-v)/p.alpha)/(u*v),
            p.alpha, u_hi, lo2, hi2,
        )
        out = self._pref_alpha(p)*val
        tr.add_application(
            target="G6",
            theorem="Lemma 2.5 lower + trivial S>=0 outside",
            source=THEOREM_SOURCES["LINEAR_WF"],
            detail=f"auto-split at u+v={cutoff:.12g}",
        )
        return out, {
            "cutoff_u_plus_v": cutoff,
            "eligible_u_range": [p.alpha, u_hi],
            "outside_rule": "0 lower bound",
        }

    def G7(self, p, tr):
        cutoff = 0.5 - 2.0*p.alpha

        def lo2(u):
            return p.beta

        def hi2(u):
            return min(p.gamma, cutoff-u)

        u_hi = min(p.beta, cutoff-p.beta)
        if u_hi <= p.alpha:
            return 0.0, {"eligible_u_range": None, "cutoff_u_plus_v": cutoff}

        val = self.q.integrate2(
            lambda u, v: self.sieve.f((0.5-u-v)/p.alpha)/(u*v),
            p.alpha, u_hi, lo2, hi2,
        )
        out = self._pref_alpha(p)*val
        tr.add_application(
            target="G7",
            theorem="Lemma 2.5 lower + trivial S>=0 outside",
            source=THEOREM_SOURCES["LINEAR_WF"],
            detail=f"auto-split at u+v={cutoff:.12g}",
        )
        return out, {
            "cutoff_u_plus_v": cutoff,
            "eligible_u_range": [p.alpha, u_hi],
            "outside_rule": "0 lower bound",
        }

    def G8(self, p, tr):
        v = 8.0*self.q.integrate1(
            lambda u: np.log(1.0/u - 2.0)/(u*(1.0-u)),
            p.gamma, 1/3,
        )
        tr.add_application(target="G8", theorem="Section 5.3 switching upper",
                           source=THEOREM_SOURCES["SEC53"],
                           detail="gamma-parametrized version of (5.39)-(5.41)")
        return v, {"gamma": p.gamma}

    def G9(self, p, tr):
        left_hi = min(0.1, 1/3)
        total = 0.0
        pieces = []

        if p.alpha < left_hi:
            part = (36.0/5.0)*self.q.integrate2(
                lambda u, v: 1.0/(u*v*(1.0-u-v)*(1.0-u)),
                p.alpha, left_hi,
                lambda u: 1/3,
                lambda u: (1.0-u)/2.0,
            )
            total += part
            pieces.append({"range": [p.alpha, left_hi],
                           "rule": "Lemma 3.5", "value": part})

        right_lo = max(p.alpha, 0.1)
        if right_lo < 1/3:
            part = 8.0*self.q.integrate2(
                lambda u, v: 1.0/(u*v*(1.0-u-v)),
                right_lo, 1/3,
                lambda u: 1/3,
                lambda u: (1.0-u)/2.0,
            )
            total += part
            pieces.append({"range": [right_lo, 1/3],
                           "rule": "Lemma 3.1", "value": part})

        tr.add_application(target="G9", theorem="Lemma 3.5 / Lemma 3.1 split",
                           source=THEOREM_SOURCES["DIST_SMALL"],
                           detail="automatic split at u=1/10")
        return total, {"pieces": pieces}

    def G10(self, p, tr):
        v = 8.0*self.q.integrate2(
            lambda u, x: 1.0/(u*x*(1.0-u-x)),
            p.beta, p.gamma,
            lambda u: p.gamma,
            lambda u: (1.0-u)/2.0,
        )
        tr.add_application(target="G10", theorem="Section 5.3 switching upper",
                           source=THEOREM_SOURCES["SEC53"],
                           detail="sqrt-remaining sieve removes a second large factor")
        return v, {}

    # ------------------------------------------------------------------
    # Dynamic four-dimensional Buchstab integrals G11/G12
    # ------------------------------------------------------------------
    def _g11_piece(self, p, a, b, small):
        if b <= a:
            return 0.0, {"range": [a, b], "empty": True}
        q = self.q4
        t1s, w1s = q.nodes_weights(a, b)
        total = 0.0
        arg_min_seen = float("inf")
        arg_max_seen = 0.0

        for t1, w1 in zip(t1s, w1s):
            t2s, w2s = q.nodes_weights(t1, p.beta)
            for t2, w2 in zip(t2s, w2s):
                t3s, w3s = q.nodes_weights(t2, p.beta)
                for t3, w3 in zip(t3s, w3s):
                    t4s, w4s = q.nodes_weights(t3, p.beta)
                    if not t4s.size:
                        continue
                    arg = (1.0-t1-t2-t3-t4s)/t2
                    arg_min_seen = min(arg_min_seen, float(np.min(arg)))
                    arg_max_seen = max(arg_max_seen, float(np.max(arg)))
                    omega = self.buchstab.w(arg)
                    vals = omega/t4s
                    inner4 = float(np.sum(w4s*vals))
                    denom1 = t1*(1.0-t1) if small else t1
                    total += (
                        w1*w2*w3
                        * inner4
                        / (denom1*t2*t2*t3)
                    )
        factor = 36.0/5.0 if small else 8.0
        return factor*total, {
            "range": [a, b],
            "factor": factor,
            "buchstab_argument_seen": [arg_min_seen, arg_max_seen],
        }

    def G11(self, p, tr):
        split = 0.1
        v1, d1 = self._g11_piece(
            p, p.alpha, min(split, p.beta), True
        ) if p.alpha < min(split, p.beta) else (0.0, {"empty": True})
        lo = max(split, p.alpha)
        v2, d2 = self._g11_piece(
            p, lo, p.beta, False
        ) if lo < p.beta else (0.0, {"empty": True})
        tr.add_application(
            target="G11",
            theorem="Buchstab function + theorem split at t1=1/10",
            source=THEOREM_SOURCES["SEC54"],
            detail="Directly evaluates w((1-t1-t2-t3-t4)/t2); no constant omega cap.",
        )
        return v1+v2, {"small_t1": d1, "large_t1": d2}

    def _g12_piece(self, p, a, b, small):
        if b <= a:
            return 0.0, {"range": [a, b], "empty": True}
        q = self.q4
        t1s, w1s = q.nodes_weights(a, b)
        total = 0.0
        arg_min_seen = float("inf")
        arg_max_seen = 0.0

        for t1, w1 in zip(t1s, w1s):
            t2s, w2s = q.nodes_weights(t1, p.beta)
            for t2, w2 in zip(t2s, w2s):
                t3s, w3s = q.nodes_weights(t2, p.beta)
                for t3, w3 in zip(t3s, w3s):
                    t4s, w4s = q.nodes_weights(p.beta, p.gamma)
                    if not t4s.size:
                        continue
                    arg = (1.0-t1-t2-t3-t4s)/t2
                    arg_min_seen = min(arg_min_seen, float(np.min(arg)))
                    arg_max_seen = max(arg_max_seen, float(np.max(arg)))
                    omega = self.buchstab.w(arg)
                    inner4 = float(np.sum(w4s*(omega/t4s)))
                    denom1 = t1*(1.0-t1) if small else t1
                    total += (
                        w1*w2*w3
                        * inner4
                        / (denom1*t2*t2*t3)
                    )
        factor = 36.0/5.0 if small else 8.0
        return factor*total, {
            "range": [a, b],
            "factor": factor,
            "buchstab_argument_seen": [arg_min_seen, arg_max_seen],
        }

    def G12(self, p, tr):
        split = 0.1
        v1, d1 = self._g12_piece(
            p, p.alpha, min(split, p.beta), True
        ) if p.alpha < min(split, p.beta) else (0.0, {"empty": True})
        lo = max(split, p.alpha)
        v2, d2 = self._g12_piece(
            p, lo, p.beta, False
        ) if lo < p.beta else (0.0, {"empty": True})
        tr.add_application(
            target="G12",
            theorem="Buchstab function + theorem split at t1=1/10",
            source=THEOREM_SOURCES["SEC54"],
            detail="Direct dynamic w; values below u=3 remain legal.",
        )
        return v1+v2, {"small_t1": d1, "large_t1": d2}

    # ------------------------------------------------------------------
    # Full evaluation
    # ------------------------------------------------------------------
    def evaluate(self, p: Parameters) -> EvaluationResult:
        tr = self.build_trace(p)
        if not tr.passed:
            return EvaluationResult(
                valid=False,
                parameters=p.to_dict(),
                bounds={},
                contributions={},
                margin_4D=float("-inf"),
                margin_D=float("-inf"),
                theorem_trace=tr.to_dict(),
                per_G={},
                status=self.settings["status"],
            )

        funcs = [
            self.G1, self.G2, self.G3, self.G4, self.G5, self.G6,
            self.G7, self.G8, self.G9, self.G10, self.G11, self.G12,
        ]
        raw = {}
        per_G = {}
        try:
            for i, fn in enumerate(funcs, start=1):
                value, diag = fn(p, tr)
                raw[f"G{i}"] = float(value)
                per_G[f"G{i}"] = diag
        except (ValueError, FloatingPointError) as exc:
            tr.add_guard(GuardCheck(
                name="runtime_special_function_domain",
                passed=False,
                expression="all dynamic F/f/w arguments inside registered domains",
                theorem="numerical evaluator",
                source="runtime",
                hard=True,
                note=str(exc),
            ))
            return EvaluationResult(
                valid=False,
                parameters=p.to_dict(),
                bounds={},
                contributions={},
                margin_4D=float("-inf"),
                margin_D=float("-inf"),
                theorem_trace=tr.to_dict(),
                per_G=per_G,
                status=self.settings["status"],
            )

        # Conservative numerical screening pad only.
        bounds = {}
        for name, value in raw.items():
            if self.COEFF[name] > 0:
                bounds[name] = value - self.numeric_pad_per_G
            else:
                bounds[name] = value + self.numeric_pad_per_G

        contributions = {
            name: self.COEFF[name]*bounds[name]
            for name in self.COEFF
        }
        m4 = float(sum(contributions.values()))

        for name in per_G:
            per_G[name]["raw_unpadded_bound"] = raw[name]
            per_G[name]["padded_bound"] = bounds[name]
            per_G[name]["coefficient"] = self.COEFF[name]
            per_G[name]["contribution"] = contributions[name]

        return EvaluationResult(
            valid=True,
            parameters=p.to_dict(),
            bounds=bounds,
            contributions=contributions,
            margin_4D=m4,
            margin_D=m4/4.0,
            theorem_trace=tr.to_dict(),
            per_G=per_G,
            status=self.settings["status"],
        )
