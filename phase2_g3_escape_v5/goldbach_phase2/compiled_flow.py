from __future__ import annotations

from typing import Dict

import numpy as np

from .flow140 import Flow140Model


class CompiledFlow140Model(Flow140Model):
    """Flow140 with selected NEG unresolved sinks promoted to theorem terminals."""

    def __init__(
        self,
        flow_blueprint,
        compiled_terminals: Dict[str, object],
        allow_g16_paper_bridge: bool = True,
    ):
        super().__init__(
            flow_blueprint,
            allow_g16_paper_bridge=allow_g16_paper_bridge,
            strict_unresolved=True,
        )
        self.compiled_terminals = dict(compiled_terminals)

        # The Phase-1 diagnostic variable already sits on the correct NEG
        # conservation output.  Promotion simply reopens that variable and
        # gives it a certified/theorem-matched upper-bound objective cost.
        b = list(self.bounds)
        for resource, terminal in self.compiled_terminals.items():
            name = terminal.unresolved_variable
            b[self.index[name]] = (0.0, None)
        self.bounds = b

    def terminal_margin_vector(self, theorem_eval):
        c = super().terminal_margin_vector(theorem_eval)
        for resource, terminal in self.compiled_terminals.items():
            # NEG resource with upper bound U contributes -U per coefficient.
            c[self.index[terminal.unresolved_variable]] = -float(
                terminal.upper_bound
            )
        return c

    def solve(self, theorem_eval, preference_vector=None,
              preference_temperature=0.0):
        sol = super().solve(
            theorem_eval,
            preference_vector=preference_vector,
            preference_temperature=preference_temperature,
        )
        if not sol.success or sol.x is None:
            return sol

        compiled_names = {
            t.unresolved_variable for t in self.compiled_terminals.values()
        }

        # Reinterpret promoted diagnostics as theorem terminals.
        compiled_alloc = {}
        for resource, terminal in self.compiled_terminals.items():
            val = float(sol.x[self.index[terminal.unresolved_variable]])
            if abs(val) > 1e-12:
                compiled_alloc[resource] = {
                    "allocation": val,
                    "upper_bound": terminal.upper_bound,
                    "contribution_to_2D_margin": -val * terminal.upper_bound,
                    "family": terminal.family,
                }

        genuine_unresolved = []
        for v in self.original_variables:
            if v["kind"] != "UNRESOLVED_FRONTIER":
                continue
            if v["name"] in compiled_names:
                continue
            genuine_unresolved.append(float(sol.x[self.index[v["name"]]]))

        sol.max_unresolved = (
            max(genuine_unresolved) if genuine_unresolved else 0.0
        )
        sol.compiled_terminal_allocations = compiled_alloc
        sol.compiled_terminal_count = len(self.compiled_terminals)
        return sol
