from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple

import numpy as np
from scipy.optimize import linprog


@dataclass
class FlowSolution:
    success: bool
    message: str
    objective_margin_2D: float
    margin_4D_equivalent: float
    margin_D: float
    x: Optional[np.ndarray]
    rewrite_allocations: Dict[str, float]
    source_weights: Dict[str, float]
    terminal_allocations: Dict[str, float]
    cancellation_allocations: Dict[str, float]
    bundle_allocations: Dict[str, float]
    bridge_allocations: Dict[str, float]
    effective_G_coefficients_4D: Dict[str, float]
    max_conservation_residual: float
    max_unresolved: float
    active_rewrite_count: int
    preference_vector: Dict[str, float]
    preference_temperature: float

    def to_dict(self):
        return {
            "success": self.success,
            "message": self.message,
            "objective_margin_2D": self.objective_margin_2D,
            "margin_4D_equivalent": self.margin_4D_equivalent,
            "margin_D": self.margin_D,
            "rewrite_allocations": self.rewrite_allocations,
            "source_weights": self.source_weights,
            "terminal_allocations": self.terminal_allocations,
            "cancellation_allocations": self.cancellation_allocations,
            "bundle_allocations": self.bundle_allocations,
            "bridge_allocations": self.bridge_allocations,
            "effective_G_coefficients_4D": self.effective_G_coefficients_4D,
            "max_conservation_residual": self.max_conservation_residual,
            "max_unresolved": self.max_unresolved,
            "active_rewrite_count": self.active_rewrite_count,
            "preference_vector": self.preference_vector,
            "preference_temperature": self.preference_temperature,
        }


class Flow140Model:
    """Full Phase-1 flow model with all 140 rewrite allocation variables.

    Important:
      * 140 rewrite variables are NOT independent box variables.
      * They live inside the 576-variable signed-resource flow model.
      * Every scored solution satisfies resource conservation.
      * every UNRESOLVED_FRONTIER variable is fixed to zero.
      * positive trivial terminal sinks are allowed and score zero.
      * nontrivial terminal scores use theorem-aware G1..G12 bounds.

    The Phase-1 V5 bundle incidence has a direction bug for G11/G12.
    The mathematical bundle
        S6 - G14 - G15 - G16 + G11 + G12 >= 0
    is used by replacing
        S6-G14-G15-G16 >= -G11-G12.
    Hence a bundle use CONSUMES POS S6 / NEG G14 / NEG G15 / NEG G16
    and CREATES NEG G11 / NEG G12.
    V5 conservation instead put the bundle on POS G11/POS G12 output.
    We patch that incidence here and regression-test it.
    """

    BRIDGE_POS = "bridge__POS__G16_literal_to_expected"
    BRIDGE_NEG = "bridge__NEG__G16_literal_to_expected"

    def __init__(
        self,
        flow_blueprint: Mapping[str, Any],
        allow_g16_paper_bridge: bool = True,
        strict_unresolved: bool = True,
    ):
        self.flow = flow_blueprint
        self.allow_g16_paper_bridge = bool(allow_g16_paper_bridge)
        self.strict_unresolved = bool(strict_unresolved)

        self.original_variables = list(self.flow["flow_variables"])
        self.original_names = [v["name"] for v in self.original_variables]
        self.rewrite_names = [
            v["name"] for v in self.original_variables
            if v["kind"] == "REWRITE_ALLOCATION"
        ]
        if len(self.rewrite_names) != 140:
            raise ValueError(
                f"Expected exactly 140 rewrite allocations, got {len(self.rewrite_names)}"
            )

        self.var_names = self.original_names + [self.BRIDGE_POS, self.BRIDGE_NEG]
        self.index = {name: i for i, name in enumerate(self.var_names)}
        self.n = len(self.var_names)

        self._conservation_row_by_signed_node = {
            e["signed_node"]: i
            for i, e in enumerate(self.flow["conservation_equations"])
        }

        self.A_eq, self.b_eq = self._build_equalities()
        self.bounds = self._build_bounds()

    @staticmethod
    def _parse_expr(expr: str) -> Tuple[float, str]:
        expr = expr.strip()
        if "*" in expr:
            c, name = expr.split("*", 1)
            return float(c), name
        return 1.0, expr

    def _build_equalities(self):
        rows = []
        rhs = []

        for eq in self.flow["conservation_equations"]:
            row = np.zeros(self.n, dtype=float)
            for term in eq["in_terms"]:
                c, name = self._parse_expr(term["expr"])
                row[self.index[name]] += c
            for term in eq["out_terms"]:
                c, name = self._parse_expr(term["expr"])
                row[self.index[name]] -= c
            rows.append(row)
            rhs.append(0.0)

        # --------------------------------------------------------------
        # Correct the V5 bundle incidence for G11/G12.
        # --------------------------------------------------------------
        bundle_name = "y_bundle__paper_closure_4_31_4_36"
        if bundle_name in self.index:
            j_bundle = self.index[bundle_name]
            for alias in ("G11", "G12"):
                sid = self.flow["alias_map"][alias]
                pos_row = self._conservation_row_by_signed_node[f"POS::{sid}"]
                neg_row = self._conservation_row_by_signed_node[f"NEG::{sid}"]

                # V5: -bundle in POS output. Remove it.
                if abs(rows[pos_row][j_bundle]) > 1e-12:
                    rows[pos_row][j_bundle] = 0.0

                # Correct: +bundle is an input creating NEG G11/G12.
                if abs(rows[neg_row][j_bundle]) < 1e-12:
                    rows[neg_row][j_bundle] += 1.0

        # --------------------------------------------------------------
        # Optional explicit G16 source-shape bridge.
        # This keeps the existing source warning visible; it is not silently
        # treated as independently verified.
        # --------------------------------------------------------------
        literal = "G16_literal"
        expected = self.flow["alias_map"]["G16_expected_3factor_shape"]
        for sign, bridge_name in (
            ("POS", self.BRIDGE_POS),
            ("NEG", self.BRIDGE_NEG),
        ):
            j = self.index[bridge_name]
            r_from = self._conservation_row_by_signed_node[f"{sign}::{literal}"]
            r_to = self._conservation_row_by_signed_node[f"{sign}::{expected}"]
            rows[r_from][j] -= 1.0  # consume literal
            rows[r_to][j] += 1.0    # create expected-shape state

        # Source normalization.  Each source inequality has LHS scale 2D,
        # hence lambda_A+lambda_B=1 makes the flow objective a 2D margin.
        row = np.zeros(self.n, dtype=float)
        row[self.index["lambda_source__P4_2_alpha_one_third"]] = 1.0
        row[self.index["lambda_source__P4_2_beta_gamma"]] = 1.0
        rows.append(row)
        rhs.append(1.0)

        return np.asarray(rows, dtype=float), np.asarray(rhs, dtype=float)

    def _build_bounds(self):
        bounds = []
        for v in self.original_variables:
            lo = float(v.get("lower", 0.0) or 0.0)
            hi = v.get("upper", None)

            if self.strict_unresolved and v["kind"] == "UNRESOLVED_FRONTIER":
                hi = 0.0

            bounds.append((lo, hi))

        bridge_hi = None if self.allow_g16_paper_bridge else 0.0
        bounds.extend([(0.0, bridge_hi), (0.0, bridge_hi)])
        return bounds

    # ------------------------------------------------------------------
    # Terminal objective
    # ------------------------------------------------------------------
    def terminal_margin_vector(self, theorem_eval) -> np.ndarray:
        c = np.zeros(self.n, dtype=float)

        for v in self.original_variables:
            if v["kind"] != "TERMINAL_ALLOCATION":
                continue

            md = v["metadata"]
            rule = md["rule"]["name"]
            if rule == "trivial_nonnegative_lower":
                continue

            paper_names = md.get("paper_names", [])
            if len(paper_names) != 1:
                raise ValueError(
                    f"Expected exactly one paper alias for terminal {v['name']}"
                )
            g = paper_names[0]
            if g not in theorem_eval.bounds:
                raise ValueError(
                    f"Theorem-aware evaluator did not provide {g} "
                    f"needed by terminal {v['name']}"
                )

            value = float(theorem_eval.bounds[g])
            sign = md["sign"]
            c[self.index[v["name"]]] = value if sign == "POS" else -value

        return c

    def effective_G_coefficients_4D(self, x: np.ndarray) -> Dict[str, float]:
        out = {f"G{i}": 0.0 for i in range(1, 13)}

        for v in self.original_variables:
            if v["kind"] != "TERMINAL_ALLOCATION":
                continue
            md = v["metadata"]
            if md["rule"]["name"] == "trivial_nonnegative_lower":
                continue
            g = md["paper_names"][0]
            sign = 1.0 if md["sign"] == "POS" else -1.0
            # Source normalization has LHS=2D. Multiply by 2 to report the
            # certificate in the paper-comparable 4D normalization.
            out[g] += 2.0 * sign * float(x[self.index[v["name"]]])
        return out

    def solve(
        self,
        theorem_eval,
        preference_vector: Optional[Sequence[float]] = None,
        preference_temperature: float = 0.0,
    ) -> FlowSolution:
        margin = self.terminal_margin_vector(theorem_eval)

        if preference_vector is None:
            preference = np.zeros(len(self.rewrite_names), dtype=float)
        else:
            preference = np.asarray(preference_vector, dtype=float)
            if preference.shape != (len(self.rewrite_names),):
                raise ValueError(
                    f"preference_vector must have shape ({len(self.rewrite_names)},)"
                )

        # Randomized architecture objective:
        # maximize true 2D margin + T/140 * sum(z_j * rewrite_j).
        objective = margin.copy()
        if preference_temperature != 0.0:
            scale = float(preference_temperature) / len(self.rewrite_names)
            for name, z in zip(self.rewrite_names, preference):
                objective[self.index[name]] += scale * float(z)

        res = linprog(
            -objective,
            A_eq=self.A_eq,
            b_eq=self.b_eq,
            bounds=self.bounds,
            method="highs",
        )

        if not res.success:
            return FlowSolution(
                success=False,
                message=res.message,
                objective_margin_2D=float("-inf"),
                margin_4D_equivalent=float("-inf"),
                margin_D=float("-inf"),
                x=None,
                rewrite_allocations={},
                source_weights={},
                terminal_allocations={},
                cancellation_allocations={},
                bundle_allocations={},
                bridge_allocations={},
                effective_G_coefficients_4D={},
                max_conservation_residual=float("inf"),
                max_unresolved=float("inf"),
                active_rewrite_count=0,
                preference_vector={
                    n: float(z) for n, z in zip(self.rewrite_names, preference)
                },
                preference_temperature=float(preference_temperature),
            )

        x = np.asarray(res.x, dtype=float)
        true_margin_2D = float(margin @ x)
        margin_4D = 2.0 * true_margin_2D
        margin_D = true_margin_2D / 2.0

        def collect(kind: str):
            return {
                v["name"]: float(x[self.index[v["name"]]])
                for v in self.original_variables
                if v["kind"] == kind and abs(x[self.index[v["name"]]]) > 1e-12
            }

        all_rewrites = {
            name: float(x[self.index[name]])
            for name in self.rewrite_names
        }
        active = sum(abs(v) > 1e-10 for v in all_rewrites.values())

        unresolved_vals = [
            float(x[self.index[v["name"]]])
            for v in self.original_variables
            if v["kind"] == "UNRESOLVED_FRONTIER"
        ]

        residual = self.A_eq @ x - self.b_eq

        return FlowSolution(
            success=True,
            message=res.message,
            objective_margin_2D=true_margin_2D,
            margin_4D_equivalent=margin_4D,
            margin_D=margin_D,
            x=x,
            rewrite_allocations=all_rewrites,
            source_weights=collect("SOURCE_MIX_WEIGHT"),
            terminal_allocations=collect("TERMINAL_ALLOCATION"),
            cancellation_allocations=collect("EXACT_CANCELLATION"),
            bundle_allocations=collect("BUNDLE_USE"),
            bridge_allocations={
                self.BRIDGE_POS: float(x[self.index[self.BRIDGE_POS]]),
                self.BRIDGE_NEG: float(x[self.index[self.BRIDGE_NEG]]),
            },
            effective_G_coefficients_4D=self.effective_G_coefficients_4D(x),
            max_conservation_residual=float(np.max(np.abs(residual))),
            max_unresolved=float(max(unresolved_vals) if unresolved_vals else 0.0),
            active_rewrite_count=active,
            preference_vector={
                n: float(z) for n, z in zip(self.rewrite_names, preference)
            },
            preference_temperature=float(preference_temperature),
        )

    # ------------------------------------------------------------------
    # Structural diagnostics: which of the 140 rewrites can EVER be nonzero
    # under the current registry + unresolved=0?
    # ------------------------------------------------------------------
    def certifiably_reachable_rewrites(self, tol: float = 1e-9):
        reachable = {}
        zero_forced = []

        for name in self.rewrite_names:
            c = np.zeros(self.n, dtype=float)
            c[self.index[name]] = -1.0  # maximize this variable
            res = linprog(
                c,
                A_eq=self.A_eq,
                b_eq=self.b_eq,
                bounds=self.bounds,
                method="highs",
            )
            mx = float(res.x[self.index[name]]) if res.success else 0.0
            if mx > tol:
                reachable[name] = mx
            else:
                zero_forced.append(name)

        return reachable, zero_forced
