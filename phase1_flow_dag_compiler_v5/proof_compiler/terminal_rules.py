from __future__ import annotations
from dataclasses import dataclass, asdict
from typing import Dict, List, Optional


@dataclass(frozen=True)
class TerminalRule:
    name: str
    resources: List[str]
    allowed_sign: str  # POS | NEG | BOTH
    bound_direction: str  # lower | upper | exact | trivial
    source: str
    certified: bool
    guard: List[str]
    notes: List[str]

    def to_dict(self):
        return asdict(self)


def build_terminal_rules() -> List[TerminalRule]:
    rules = [
        TerminalRule(
            "paper_lower_G1_G2", ["G1", "G2"], "POS", "lower",
            "Section 5.1; Lemma 2.5", True, [],
            ["Positive coefficient states need lower bounds."],
        ),
        TerminalRule(
            "paper_upper_G3", ["G3"], "NEG", "upper",
            "Section 5.3", True, [],
            ["Switching/distribution estimate is used as an upper bound."],
        ),
        TerminalRule(
            "paper_upper_G4_G5", ["G4", "G5"], "NEG", "upper",
            "Section 5.2", True, [],
            [],
        ),
        TerminalRule(
            "paper_lower_G6_G7", ["G6", "G7"], "POS", "lower",
            "Section 5.2", True, [],
            [],
        ),
        TerminalRule(
            "paper_upper_G8_G9_G10", ["G8", "G9", "G10"], "NEG", "upper",
            "Section 5.3", True, [],
            [
                "Switching principle only supplies upper bounds; therefore "
                "these are sign-specific terminal rules."
            ],
        ),
        TerminalRule(
            "paper_upper_G11_G12", ["G11", "G12"], "NEG", "upper",
            "Section 5.4", True, [],
            ["Buchstab-function based terminal evaluation."],
        ),
        TerminalRule(
            "trivial_nonnegative_lower",
            ["*"], "POS", "trivial",
            "non-negativity of sieve counts", True, [],
            [
                "X>=0. For a positive term in a lower-bound certificate this "
                "is always legal but may discard all precision."
            ],
        ),
    ]
    return rules


def terminal_rules_for(resource: str, sign: str):
    out = []
    for r in build_terminal_rules():
        if r.allowed_sign not in {sign, "BOTH"}:
            continue
        if "*" in r.resources or resource in r.resources:
            out.append(r)
    return out
