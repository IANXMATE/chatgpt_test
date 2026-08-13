from __future__ import annotations
from dataclasses import dataclass
from typing import Dict, Iterable, List, Optional, Sequence, Tuple
import hashlib
import numpy as np
import sympy as sp
from scipy.optimize import linprog

from .params import PARAM_SYMBOLS, ParameterDomain


def u(i: int) -> sp.Symbol:
    return sp.Symbol(f"u{i}", real=True)


def canonical_expr(expr: sp.Expr) -> str:
    expr = sp.cancel(sp.expand(sp.sympify(expr)))
    return sp.srepr(expr)


@dataclass(frozen=True)
class Region:
    factor_count: int
    inequalities: Tuple[sp.Expr, ...]  # each <= 0
    guards: Tuple[str, ...] = ()
    source: str = ""

    @property
    def variables(self) -> Tuple[sp.Symbol, ...]:
        return tuple(u(i) for i in range(1, self.factor_count + 1))

    @property
    def canonical_inequalities(self) -> Tuple[str, ...]:
        return tuple(sorted(canonical_expr(x) for x in self.inequalities))

    @property
    def key(self) -> Tuple:
        return (
            self.factor_count,
            self.canonical_inequalities,
            tuple(sorted(self.guards)),
        )

    @property
    def short_hash(self) -> str:
        return hashlib.sha1(repr(self.key).encode()).hexdigest()[:12]

    def add(self, *exprs: sp.Expr, guard: Optional[str] = None,
            source: Optional[str] = None) -> "Region":
        guards = self.guards + ((guard,) if guard else ())
        return Region(
            self.factor_count,
            self.inequalities + tuple(sp.expand(sp.sympify(x)) for x in exprs),
            guards,
            source or self.source,
        )

    def with_factor_count(self, k: int, inequalities: Sequence[sp.Expr],
                          source: Optional[str] = None) -> "Region":
        return Region(
            k,
            tuple(sp.expand(sp.sympify(x)) for x in inequalities),
            self.guards,
            source or self.source,
        )

    def substitute_factor_map(self, mapping: Dict[sp.Symbol, sp.Symbol],
                              new_factor_count: int) -> "Region":
        exprs = [sp.expand(x.xreplace(mapping)) for x in self.inequalities]
        return Region(
            new_factor_count,
            tuple(exprs),
            self.guards,
            self.source,
        )

    def to_dict(self):
        return {
            "factor_count": self.factor_count,
            "variables": [str(x) for x in self.variables],
            "inequalities": [str(sp.expand(x)) + " <= 0"
                             for x in self.inequalities],
            "guards": list(self.guards),
            "source": self.source,
            "canonical_key": repr(self.key),
        }


class LinearRegionOracle:
    """LP feasibility/bounds over factor variables + proposition parameters."""

    def __init__(self, parameter_domain: ParameterDomain):
        self.domain = parameter_domain
        self._feas_cache = {}

    def _matrix(self, region: Region,
                extra: Sequence[sp.Expr] = ()):
        vars_ = list(region.variables) + list(PARAM_SYMBOLS)
        exprs = list(self.domain.inequalities()) + \
                list(region.inequalities) + list(extra)

        A, b = [], []
        for ex in exprs:
            ex = sp.expand(ex)
            row = [float(ex.coeff(v)) for v in vars_]
            const = float(ex.subs({v: 0 for v in vars_}))
            # ex <= 0  -> coeff*x <= -const
            A.append(row)
            b.append(-const)
        return vars_, np.asarray(A, dtype=float), np.asarray(b, dtype=float)

    def feasible(self, region: Region,
                 extra: Sequence[sp.Expr] = ()) -> bool:
        key = (region.key, tuple(sorted(canonical_expr(x) for x in extra)))
        if key in self._feas_cache:
            return self._feas_cache[key]
        vars_, A, b = self._matrix(region, extra)
        res = linprog(
            np.zeros(len(vars_)),
            A_ub=A, b_ub=b,
            bounds=[(None, None)] * len(vars_),
            method="highs",
            options={"primal_feasibility_tolerance": 1e-9,
                     "dual_feasibility_tolerance": 1e-9},
        )
        ans = bool(res.success)
        self._feas_cache[key] = ans
        return ans

    def optimize_expr(self, region: Region, expr: sp.Expr,
                      maximize=False,
                      extra: Sequence[sp.Expr] = ()):
        vars_, A, b = self._matrix(region, extra)
        expr = sp.expand(expr)
        c = np.array([float(expr.coeff(v)) for v in vars_], dtype=float)
        const = float(expr.subs({v: 0 for v in vars_}))
        if maximize:
            c = -c
        res = linprog(
            c, A_ub=A, b_ub=b,
            bounds=[(None, None)] * len(vars_),
            method="highs",
            options={"primal_feasibility_tolerance": 1e-9,
                     "dual_feasibility_tolerance": 1e-9},
        )
        if not res.success:
            return None
        val = float(res.fun)
        if maximize:
            val = -val
        return val + const

    def factor_bounds(self, region: Region):
        out = {}
        for x in region.variables:
            lo = self.optimize_expr(region, x, maximize=False)
            hi = self.optimize_expr(region, x, maximize=True)
            out[str(x)] = {"min": lo, "max": hi}
        return out

    def meaningful_split(self, region: Region, var: sp.Symbol,
                         cut: sp.Expr) -> bool:
        # Require both strict-ish sides to be feasible somewhere in the
        # full parameter domain. Tiny slack prevents boundary-only splits.
        e = sp.Float(self.domain.strict_margin)
        left = var - cut + e       # var < cut
        right = cut - var + e      # var > cut
        return self.feasible(region, [left]) and \
               self.feasible(region, [right])

    def subset_at_domain(self, small: Region, large: Region,
                         tol: float = 1e-9):
        """Try proving small subset large over the linear parameter domain.

        Every inequality f<=0 of `large` is maximized over `small`.
        If all maxima <= tol, the inclusion is LP-certified.
        """
        if small.factor_count != large.factor_count:
            return False, []
        witnesses = []
        for ex in large.inequalities:
            mx = self.optimize_expr(small, ex, maximize=True)
            if mx is None or mx > tol:
                return False, witnesses + [{"expr": str(ex), "max": mx}]
            witnesses.append({"expr": str(ex), "max": mx})
        return True, witnesses
