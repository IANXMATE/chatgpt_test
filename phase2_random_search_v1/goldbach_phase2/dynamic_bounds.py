from __future__ import annotations

from dataclasses import dataclass, asdict
from functools import lru_cache
import math
from typing import Dict, List, Tuple

import numpy as np
from scipy.integrate import quad


EULER_GAMMA = 0.577215664901532860606512090082402431
EXP_MINUS_GAMMA = math.exp(-EULER_GAMMA)


@dataclass(frozen=True)
class DynamicParameters:
    a: float
    alpha: float
    beta: float
    gamma: float
    epsilon: float = 1e-10

    @property
    def tau(self) -> float:
        return (self.a - 1.0) / self.a - self.epsilon

    def to_dict(self):
        d = asdict(self)
        d["tau"] = self.tau
        return d


@dataclass
class DynamicEvaluation:
    valid: bool
    failure_reasons: List[str]
    bounds: Dict[str, float]
    contributions: Dict[str, float]
    margin_4D: float
    margin_D: float
    diagnostics: Dict

    def to_dict(self):
        return {
            "valid": self.valid,
            "failure_reasons": list(self.failure_reasons),
            "bounds": dict(self.bounds),
            "contributions": dict(self.contributions),
            "margin_4D": self.margin_4D,
            "margin_D": self.margin_D,
            "diagnostics": dict(self.diagnostics),
        }


class LinearSieveTable:
    """Numerical method-of-steps table for the classical linear-sieve F,f.

    Differential-delay equations:
      (sF(s))' = f(s-1), s>3,
      (sf(s))' = F(s-1), s>2,
    with F(s)=2e^gamma/s on [1,3] and f(s)=0 on [1,2].

    This is used only for numerical candidate discovery.  The storage record
    explicitly marks the result as not interval-certified.
    """

    def __init__(self, step: float = 2e-5, s_max: float = 10.0):
        inv = round(1.0 / step)
        if abs(inv * step - 1.0) > 1e-12:
            raise ValueError("step must divide 1 exactly enough for method-of-steps")
        self.step = float(step)
        self.inv = int(inv)
        self.s_max = float(s_max)

        self.s = np.arange(1.0, s_max + step * 0.5, step, dtype=float)
        n = len(self.s)
        A = np.zeros(n, dtype=float)  # s F(s)
        B = np.zeros(n, dtype=float)  # s f(s)

        twoeg = 2.0 * math.exp(EULER_GAMMA)

        i3 = self._index(3.0)
        A[:i3 + 1] = twoeg

        # B=0 through s=2.
        # Integrate one unit at a time; delayed values are already known.
        max_integer = int(math.floor(s_max))
        for k in range(2, max_integer + 1):
            lo = float(k)
            hi = min(float(k + 1), s_max)
            if hi <= lo:
                continue
            i0 = self._index(lo)
            i1 = self._index(hi)
            idx = np.arange(i0, i1 + 1)
            delayed = idx - self.inv

            # B'(s) = F(s-1), valid for s>2.
            Fdel = A[delayed] / self.s[delayed]
            increments = 0.5 * self.step * (Fdel[:-1] + Fdel[1:])
            B[idx[1:]] = B[i0] + np.cumsum(increments)

            # A'(s) = f(s-1), valid for s>3.
            if lo >= 3.0:
                fdel = B[delayed] / self.s[delayed]
                incrementsA = 0.5 * self.step * (fdel[:-1] + fdel[1:])
                A[idx[1:]] = A[i0] + np.cumsum(incrementsA)

        self.Fv = A / self.s
        self.fv = B / self.s

    def _index(self, x: float) -> int:
        return int(round((x - 1.0) / self.step))

    def F(self, x):
        arr = np.asarray(x, dtype=float)
        out = np.empty_like(arr)

        # Standard safe extension used in the paper: F(s) is already extremely
        # close to 1 for s>=7.  For candidate search we interpolate our table
        # all the way to s_max instead of freezing at F(7).
        if np.any(arr < 1.0) or np.any(arr > self.s_max):
            raise ValueError(f"F(s) requested outside [1,{self.s_max}]")
        out[...] = np.interp(arr, self.s, self.Fv)
        return float(out) if out.ndim == 0 else out

    def f(self, x):
        arr = np.asarray(x, dtype=float)
        if np.any(arr < 0.0) or np.any(arr > self.s_max):
            raise ValueError(f"f(s) requested outside [0,{self.s_max}]")
        out = np.zeros_like(arr)
        mask = arr >= 1.0
        out[mask] = np.interp(arr[mask], self.s, self.fv)
        return float(out) if out.ndim == 0 else out


class GaussLegendre:
    def __init__(self, order: int = 40):
        self.order = int(order)
        self.x, self.w = np.polynomial.legendre.leggauss(self.order)

    def nodes_weights(self, a: float, b: float):
        if b <= a:
            return np.empty(0), np.empty(0)
        half = 0.5 * (b - a)
        mid = 0.5 * (a + b)
        return mid + half * self.x, half * self.w

    def integrate1(self, func, a: float, b: float) -> float:
        x, w = self.nodes_weights(a, b)
        if x.size == 0:
            return 0.0
        y = np.asarray(func(x), dtype=float)
        return float(np.sum(w * y))

    def integrate2_variable(self, func, a: float, b: float, lo2, hi2) -> float:
        us, wu = self.nodes_weights(a, b)
        if us.size == 0:
            return 0.0
        total = 0.0
        for u, weight_u in zip(us, wu):
            v0 = float(lo2(u))
            v1 = float(hi2(u))
            vs, wv = self.nodes_weights(v0, v1)
            if vs.size == 0:
                continue
            vals = np.asarray(func(u, vs), dtype=float)
            total += float(weight_u * np.sum(wv * vals))
        return total


@lru_cache(maxsize=2048)
def buchstab_w_3_to_4(u_rounded: float) -> float:
    u = float(u_rounded)
    if not (3.0 <= u <= 4.0):
        raise ValueError("This helper is only for 3<=u<=4")
    val, _ = quad(
        lambda t: math.log(t - 1.0) / t,
        2.0, u - 1.0,
        epsabs=1e-13, epsrel=1e-13, limit=100,
    )
    return (1.0 + math.log(u - 1.0) + val) / u


def omega_upper_from_lower_argument(lower_arg: float,
                                    numeric_pad: float = 5e-9) -> float:
    """Paper-supported upper envelope for Buchstab w on [lower_arg, infinity).

    Lemma 2.1 gives w(u)<=0.561522 for u>=3.5.
    Section 5.4 proves the shape on (3,3.5): w decreases then increases before
    3.5. Therefore for L in [3,3.5], max_{u>=L} w(u) is bounded by
    max(w(L), 0.561522).  We add a small floating-point search pad.
    """
    if lower_arg < 3.0:
        raise ValueError(
            f"Buchstab argument lower bound {lower_arg:.12g} < 3; "
            "current numerical evaluator has no registered safe envelope."
        )
    if lower_arg >= 3.5:
        return 0.561522
    L = round(float(lower_arg), 12)
    return max(buchstab_w_3_to_4(L), 0.561522) + numeric_pad


class PaperPathDynamicEvaluator:
    """Parameter-dependent numerical evaluator for the paper's 12-term path.

    It generalizes the displayed Section-5 formulas by replacing
    4/53 -> alpha, 4/33 -> beta, 3/11 -> gamma, 9/19-eps -> tau.

    Scope:
      * same Proposition 4.3 twelve-term architecture,
      * same Section-5 estimator families,
      * floating-point numerical candidate discovery,
      * NOT interval-certified.
    """

    COEFF = {
        "G1": +3.0, "G2": +1.0, "G3": -4.0,
        "G4": -1.0, "G5": -1.0, "G6": +1.0,
        "G7": +1.0, "G8": -2.0, "G9": -1.0,
        "G10": -1.0, "G11": -1.0, "G12": -1.0,
    }

    def __init__(self, quadrature_order: int = 40,
                 sieve_step: float = 2e-5,
                 numeric_bound_pad: float = 2e-6):
        self.q = GaussLegendre(quadrature_order)
        self.sieve = LinearSieveTable(step=sieve_step, s_max=10.0)
        self.numeric_bound_pad = float(numeric_bound_pad)
        self.settings = {
            "quadrature": "Gauss-Legendre fixed order",
            "quadrature_order": quadrature_order,
            "linear_sieve_method": "method-of-steps delay differential equations",
            "linear_sieve_grid_step": sieve_step,
            "numeric_bound_pad_per_G": numeric_bound_pad,
            "certification_level": "NUMERICAL_CANDIDATE_NOT_INTERVAL_CERTIFIED",
        }

    def validate_parameters(self, p: DynamicParameters) -> List[str]:
        f = []
        if not (1.5 + 3*p.epsilon < p.a < 2.0):
            f.append("1.5+3epsilon < a < 2")
        if not (1/18 < p.alpha < p.beta):
            f.append("1/18 < alpha < beta")
        middle = 1/3 - p.beta
        if not (p.beta < middle < p.gamma < 1/3):
            f.append("beta < 1/3-beta < gamma < 1/3")
        if not (1/3 < p.tau < 1/2):
            f.append("1/3 < tau < 1/2")

        # Current Section-5 G4 upper-bound implementation needs s>=2 across
        # u<=1/3, equivalently alpha<=1/12.
        if p.alpha > 1/12 + 1e-14:
            f.append("paper-path G4 estimator requires alpha <= 1/12")

        # Section 5.3 uses gamma>1/4 to force the unsieved remaining factor
        # in G8 to be a single prime.
        if p.gamma <= 1/4:
            f.append("paper-path G8 switching estimator requires gamma > 1/4")

        # G11/G12 current terminal evaluator uses the Section-5.4 Buchstab
        # envelope only for argument >=3.
        g11_min = (1.0 - 4.0 * p.beta) / p.beta
        g12_min = (1.0 - 3.0 * p.beta - p.gamma) / p.beta
        if g11_min < 3.0:
            f.append("G11 Buchstab argument lower bound must be >=3")
        if g12_min < 3.0:
            f.append("G12 Buchstab argument lower bound must be >=3")
        return f

    def _pref(self, alpha):
        return 2.0 * EXP_MINUS_GAMMA / alpha

    def g1(self, p):
        s = 0.5 / p.alpha
        return self._pref(p.alpha) * self.sieve.f(s)

    def g2(self, p):
        s = 0.5 / p.beta
        return 2.0 * EXP_MINUS_GAMMA / p.beta * self.sieve.f(s)

    def g3(self, p):
        return 8.0 * math.log((1.0 - p.tau) / p.tau)

    def g4(self, p):
        pref = self._pref(p.alpha)
        return pref * self.q.integrate1(
            lambda u: self.sieve.F((0.5-u)/p.alpha) / u,
            p.alpha, 1/3
        )

    def g5(self, p):
        pref = self._pref(p.alpha)
        return pref * self.q.integrate1(
            lambda u: self.sieve.F((0.5-u)/p.alpha) / u,
            p.alpha, p.gamma
        )

    def g6(self, p):
        pref = self._pref(p.alpha)
        val = self.q.integrate2_variable(
            lambda u, v: self.sieve.f((0.5-u-v)/p.alpha) / (u*v),
            p.alpha, p.beta,
            lambda u: u,
            lambda u: p.beta,
        )
        return pref * val

    def g7(self, p):
        pref = self._pref(p.alpha)
        val = self.q.integrate2_variable(
            lambda u, v: self.sieve.f((0.5-u-v)/p.alpha) / (u*v),
            p.alpha, p.beta,
            lambda u: p.beta,
            lambda u: p.gamma,
        )
        return pref * val

    def g8(self, p):
        return 8.0 * self.q.integrate1(
            lambda u: np.log(1.0/u - 2.0) / (u*(1.0-u)),
            p.gamma, 1/3,
        )

    def g9(self, p):
        split = 0.1
        ans = 0.0
        small_hi = min(split, 1/3)
        if p.alpha < small_hi:
            ans += (36.0/5.0) * self.q.integrate2_variable(
                lambda u, v: 1.0 / (
                    u*v*(1.0-u-v)*(1.0-u)
                ),
                p.alpha, small_hi,
                lambda u: 1/3,
                lambda u: (1.0-u)/2.0,
            )
        large_lo = max(p.alpha, split)
        if large_lo < 1/3:
            ans += 8.0 * self.q.integrate2_variable(
                lambda u, v: 1.0 / (u*v*(1.0-u-v)),
                large_lo, 1/3,
                lambda u: 1/3,
                lambda u: (1.0-u)/2.0,
            )
        return ans

    def g10(self, p):
        return 8.0 * self.q.integrate2_variable(
            lambda u, v: 1.0 / (u*v*(1.0-u-v)),
            p.beta, p.gamma,
            lambda u: p.gamma,
            lambda u: (1.0-u)/2.0,
        )

    def _g11_piece(self, p, t1_lo, t1_hi, small):
        if t1_hi <= t1_lo:
            return 0.0, None
        # Minimum omega argument over t2,t3,t4 <= beta.
        t1_max = t1_hi
        lower_arg = (1.0 - t1_max - 3.0*p.beta) / p.beta
        omega = omega_upper_from_lower_argument(lower_arg)
        outer_factor = 36.0/5.0 if small else 8.0

        def inner(t1, t2):
            return 0.5 * np.log(p.beta/t2)**2 / (t2**2)

        integral = self.q.integrate2_variable(
            lambda t1, t2: (
                inner(t1, t2) /
                (t1*(1.0-t1) if small else t1)
            ),
            t1_lo, t1_hi,
            lambda t1: t1,
            lambda t1: p.beta,
        )
        return outer_factor * omega * integral, {
            "t1_range": [t1_lo, t1_hi],
            "omega_argument_lower": lower_arg,
            "omega_upper": omega,
        }

    def g11(self, p):
        small_hi = min(0.1, p.beta)
        x1, d1 = self._g11_piece(
            p, p.alpha, small_hi, True
        ) if p.alpha < small_hi else (0.0, None)
        large_lo = max(0.1, p.alpha)
        x2, d2 = self._g11_piece(
            p, large_lo, p.beta, False
        ) if large_lo < p.beta else (0.0, None)
        return x1+x2, {"small": d1, "large": d2}

    def _g12_piece(self, p, t1_lo, t1_hi, small):
        if t1_hi <= t1_lo:
            return 0.0, None
        t1_max = t1_hi
        lower_arg = (
            1.0 - t1_max - 2.0*p.beta - p.gamma
        ) / p.beta
        omega = omega_upper_from_lower_argument(lower_arg)
        outer_factor = 36.0/5.0 if small else 8.0
        loggb = math.log(p.gamma/p.beta)

        integral = self.q.integrate2_variable(
            lambda t1, t2: (
                (np.log(p.beta/t2) * loggb / (t2**2))
                / (t1*(1.0-t1) if small else t1)
            ),
            t1_lo, t1_hi,
            lambda t1: t1,
            lambda t1: p.beta,
        )
        return outer_factor * omega * integral, {
            "t1_range": [t1_lo, t1_hi],
            "omega_argument_lower": lower_arg,
            "omega_upper": omega,
        }

    def g12(self, p):
        small_hi = min(0.1, p.beta)
        x1, d1 = self._g12_piece(
            p, p.alpha, small_hi, True
        ) if p.alpha < small_hi else (0.0, None)
        large_lo = max(0.1, p.alpha)
        x2, d2 = self._g12_piece(
            p, large_lo, p.beta, False
        ) if large_lo < p.beta else (0.0, None)
        return x1+x2, {"small": d1, "large": d2}

    def evaluate(self, p: DynamicParameters) -> DynamicEvaluation:
        failures = self.validate_parameters(p)
        if failures:
            return DynamicEvaluation(
                valid=False, failure_reasons=failures,
                bounds={}, contributions={},
                margin_4D=float("-inf"), margin_D=float("-inf"),
                diagnostics={"settings": self.settings},
            )

        try:
            g11, d11 = self.g11(p)
            g12, d12 = self.g12(p)
            raw = {
                "G1": self.g1(p),
                "G2": self.g2(p),
                "G3": self.g3(p),
                "G4": self.g4(p),
                "G5": self.g5(p),
                "G6": self.g6(p),
                "G7": self.g7(p),
                "G8": self.g8(p),
                "G9": self.g9(p),
                "G10": self.g10(p),
                "G11": g11,
                "G12": g12,
            }
        except (ValueError, FloatingPointError) as exc:
            return DynamicEvaluation(
                valid=False, failure_reasons=[str(exc)],
                bounds={}, contributions={},
                margin_4D=float("-inf"), margin_D=float("-inf"),
                diagnostics={"settings": self.settings},
            )

        # Conservative numerical pad for candidate screening:
        # lower bounds are reduced; upper bounds are increased.
        bounds = {}
        for name, value in raw.items():
            if self.COEFF[name] > 0:
                bounds[name] = value - self.numeric_bound_pad
            else:
                bounds[name] = value + self.numeric_bound_pad

        contributions = {
            name: self.COEFF[name] * bounds[name]
            for name in self.COEFF
        }
        m4 = float(sum(contributions.values()))

        return DynamicEvaluation(
            valid=True,
            failure_reasons=[],
            bounds=bounds,
            contributions=contributions,
            margin_4D=m4,
            margin_D=m4/4.0,
            diagnostics={
                "settings": self.settings,
                "raw_unpadded_bounds": raw,
                "G11_buchstab": d11,
                "G12_buchstab": d12,
            },
        )
