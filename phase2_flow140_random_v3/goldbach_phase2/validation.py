from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List


@dataclass
class ReplayReport:
    parameter_constraints_pass: bool
    structure_pass: bool
    arithmetic_pass: bool
    theorem_threshold_pass: bool
    g16_warning: bool
    coefficient_differences: Dict[str, float]
    margin_4D: float
    margin_D: float
    paper_threshold_D: float
    messages: List[str] = field(default_factory=list)

    @property
    def passed(self) -> bool:
        return (
            self.parameter_constraints_pass
            and self.structure_pass
            and self.arithmetic_pass
            and self.theorem_threshold_pass
        )
