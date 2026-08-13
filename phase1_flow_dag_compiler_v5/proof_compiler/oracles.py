from __future__ import annotations
from typing import List
from .state import State


ROOT_ORACLES = {
    "G1": ["paper_linear_sieve_lower_G1"],
    "G2": ["paper_linear_sieve_lower_G2"],
    "G3": ["paper_switching_upper_G3"],
    "G4": ["paper_linear_sieve_upper_G4"],
    "G5": ["paper_linear_sieve_upper_G5"],
    "G6": ["paper_linear_sieve_lower_G6"],
    "G7": ["paper_linear_sieve_lower_G7"],
    "G8": ["paper_switching_upper_G8"],
    "G9": ["paper_piecewise_upper_G9"],
    "G10": ["paper_switching_upper_G10"],
    "G11": ["paper_buchstab_upper_G11"],
    "G12": ["paper_buchstab_upper_G12"],
}


def infer_oracles(state: State) -> List[str]:
    out = set(state.analytic_oracles)
    out.add("trivial_nonnegative_lower")

    if state.threshold.kind == "fixed":
        out.add("linear_sieve_candidate")

    if state.sieve_set == "P(N*p1)" and \
       state.threshold.kind in {"factor", "sqrt_remaining"}:
        out.add("buchstab_or_switching_upper_candidate")

    if state.factor_count >= 4 and \
       state.sieve_set == "P(N*p1)":
        out.add("buchstab_function_terminal_candidate")

    if state.factor_count >= 5:
        out.add("high_dimensional_terminal_needs_certification")

    return sorted(out)
