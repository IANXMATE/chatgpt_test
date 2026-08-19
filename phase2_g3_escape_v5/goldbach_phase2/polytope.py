from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Sequence, Tuple
import math

import numpy as np
import sympy as sp
from scipy.optimize import linprog
from scipy.stats import qmc


@dataclass
class QMCResult:
    estimate: float
    raw_estimates: List[float]
    accepted: List[int]
    total: int
    acceptance_rates: List[float]
    relative_pad: float
    absolute_pad: float

    def to_dict(self):
        return {
            "estimate": self.estimate,
            "raw_estimates": list(self.raw_estimates),
            "accepted": list(self.accepted),
            "total_per_scramble": self.total,
            "acceptance_rates": list(self.acceptance_rates),
            "relative_pad": self.relative_pad,
            "absolute_pad": self.absolute_pad,
        }


class RegionPolytope:
    """Linear region from a Phase-1 canonical state's inequalities.

    All Phase-1 structural regions are linear in the u_i and in
    alpha,beta,gamma,tau.  At a fixed parameter point this becomes A u <= b.
    """

    PARAM_NAMES = ("alpha", "beta", "gamma", "tau")

    def __init__(self, state: dict, params: Dict[str, float]):
        self.state = state
        self.var_names = list(state["region"]["variables"])
        self.n = len(self.var_names)
        self.params = dict(params)

        u_syms = [sp.Symbol(v, real=True) for v in self.var_names]
        locals_map = {v.name: v for v in u_syms}
        p_syms = {name: sp.Symbol(name, real=True) for name in self.PARAM_NAMES}
        locals_map.update(p_syms)

        substitutions = {
            p_syms[name]: float(self.params[name])
            for name in self.PARAM_NAMES
            if name in self.params
        }

        rows = []
        rhs = []

        for raw in state["region"]["inequalities"]:
            lhs = raw.split("<=", 1)[0].strip()
            expr = sp.expand(sp.sympify(lhs, locals=locals_map).subs(substitutions))
            coeff = [float(expr.coeff(u)) for u in u_syms]
            const = float(expr.subs({u: 0 for u in u_syms}))
            rows.append(coeff)
            rhs.append(-const)

        if self.n == 0:
            # Zero-dimensional canonical state: there are no u-variables.
            # Keep one scalar feasibility condition per inequality, but the
            # coefficient matrix must have shape (m, 0).
            self.A = np.zeros((len(rows), 0), dtype=float)
        else:
            self.A = np.asarray(rows, dtype=float).reshape((len(rows), self.n))
        self.b = np.asarray(rhs, dtype=float)

        self._feasible = None
        self._box = None

    def feasible(self) -> bool:
        if self._feasible is not None:
            return self._feasible
        if self.n == 0:
            self._feasible = bool(np.all(self.b >= -1e-12))
            return self._feasible

        res = linprog(
            np.zeros(self.n),
            A_ub=self.A if len(self.A) else None,
            b_ub=self.b if len(self.b) else None,
            bounds=[(0.0, None)] * self.n,
            method="highs",
        )
        self._feasible = bool(res.success)
        return self._feasible

    def extrema(self, coefficients: Sequence[float]) -> Tuple[float, float]:
        if len(coefficients) != self.n:
            raise ValueError("coefficient length mismatch")
        if self.n == 0:
            return 0.0, 0.0
        if not self.feasible():
            raise ValueError("infeasible region")

        c = np.asarray(coefficients, dtype=float)
        common = dict(
            A_ub=self.A if len(self.A) else None,
            b_ub=self.b if len(self.b) else None,
            bounds=[(0.0, None)] * self.n,
            method="highs",
        )
        rmin = linprog(c, **common)
        rmax = linprog(-c, **common)
        if not (rmin.success and rmax.success):
            raise RuntimeError("LP extrema failed")
        return float(rmin.fun), float(-rmax.fun)

    def bounding_box(self):
        if self._box is not None:
            return self._box
        if self.n == 0:
            self._box = (np.empty(0), np.empty(0))
            return self._box
        if not self.feasible():
            raise ValueError("infeasible region")

        lo = np.empty(self.n)
        hi = np.empty(self.n)
        for i in range(self.n):
            c = np.zeros(self.n)
            c[i] = 1.0
            lo[i], hi[i] = self.extrema(c)
        self._box = (lo, hi)
        return self._box

    def contains(self, x: np.ndarray, tol: float = 1e-12):
        if self.n == 0:
            return np.ones(len(x), dtype=bool)
        if not len(self.A):
            return np.ones(len(x), dtype=bool)
        return np.all(x @ self.A.T <= self.b + tol, axis=1)


    def qmc_integral(
        self,
        integrand,
        power: int = 16,
        scrambles: int = 2,
        seed: int = 20260813,
        relative_pad: float = 0.03,
        absolute_pad: float = 1e-7,
        min_accepted: int = 32,
        max_extra_power: int = 5,
    ) -> QMCResult:
        """Candidate numerical integral over the polytope.

        Thin canonical regions are common after repeated Buchstab expansion.
        If the requested Sobol resolution hits too few points, V4
        automatically doubles resolution (power -> power+1) up to
        `max_extra_power` times.  This is a numerical-resolution adjustment,
        not a theorem relaxation.

        The returned value is the maximum of independent scrambled-Sobol
        estimates with a positive screening pad.  It is NOT interval-certified.
        """
        if self.n == 0:
            value = float(integrand(np.empty((1, 0)))[0])
            estimate = max(0.0, value) * (1.0 + relative_pad) + absolute_pad
            return QMCResult(
                estimate=estimate,
                raw_estimates=[value],
                accepted=[1],
                total=1,
                acceptance_rates=[1.0],
                relative_pad=relative_pad,
                absolute_pad=absolute_pad,
            )

        lo, hi = self.bounding_box()
        widths = hi - lo
        if np.any(widths < -1e-14):
            raise ValueError("invalid bounding box")
        box_volume = float(np.prod(np.maximum(widths, 0.0)))

        last_raw = None
        last_counts = None
        last_rates = None
        last_total = None

        for current_power in range(
            int(power), int(power) + int(max_extra_power) + 1
        ):
            total = 2 ** current_power
            raw = []
            accepted_counts = []
            rates = []

            for s in range(int(scrambles)):
                engine = qmc.Sobol(
                    d=self.n,
                    scramble=True,
                    seed=int(seed) + 7919*s + 104729*current_power,
                )
                y = engine.random_base2(current_power)
                x = lo + widths * y
                mask = self.contains(x)
                accepted = int(np.sum(mask))
                accepted_counts.append(accepted)
                rates.append(accepted / total)

                if accepted < min_accepted:
                    raw.append(float("nan"))
                    continue

                vals = np.asarray(integrand(x[mask]), dtype=float)
                if np.any(~np.isfinite(vals)):
                    raw.append(float("nan"))
                    continue
                raw.append(float(box_volume * np.sum(vals) / total))

            last_raw = raw
            last_counts = accepted_counts
            last_rates = rates
            last_total = total

            # Require every scramble to have enough accepted samples so the
            # max-over-scrambles screening pad has actual meaning.
            finite = [x for x in raw if math.isfinite(x)]
            if len(finite) == int(scrambles):
                padded = max(finite) * (1.0 + relative_pad) + absolute_pad
                return QMCResult(
                    estimate=float(padded),
                    raw_estimates=raw,
                    accepted=accepted_counts,
                    total=total,
                    acceptance_rates=rates,
                    relative_pad=relative_pad,
                    absolute_pad=absolute_pad,
                )

        raise RuntimeError(
            "QMC region remained too thin after adaptive refinement: "
            f"accepted={last_counts}, total={last_total}, "
            f"start_power={power}, max_extra_power={max_extra_power}"
        )

