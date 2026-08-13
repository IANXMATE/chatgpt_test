from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Mapping


@dataclass(frozen=True)
class BoundRecord:
    name: str
    value: float
    direction: str
    source: str


class PaperSection5Bounds:
    """Published rounded constants used verbatim in equation (5.51).

    These constants validate that the Phase-2 certificate plumbing reproduces
    the paper's final arithmetic.  They are not yet an independent numerical
    re-integration of every Section-5 integral.
    """

    RECORDS = {
        "G1": BoundRecord("G1", 14.87710, "lower", "(5.11)-(5.12)"),
        "G2": BoundRecord("G2", 9.11587, "lower", "(5.15)"),
        "G3": BoundRecord("G3", 0.84289, "upper", "(5.40)"),
        "G4": BoundRecord("G4", 23.60636, "upper", "(5.24)"),
        "G5": BoundRecord("G5", 19.51976, "upper", "(5.26)-(5.28)"),
        "G6": BoundRecord("G6", 1.63357, "lower", "(5.29)-(5.30)"),
        "G7": BoundRecord("G7", 3.79029, "lower", "(5.31)-(5.32)"),
        "G8": BoundRecord("G8", 0.60962, "upper", "(5.42)"),
        "G9": BoundRecord("G9", 5.27231, "upper", "(5.44)"),
        "G10": BoundRecord("G10", 5.40996, "upper", "(5.47)"),
        "G11": BoundRecord("G11", 0.10191, "upper", "(5.48)"),
        "G12": BoundRecord("G12", 0.66821, "upper", "(5.50)"),
    }

    @classmethod
    def records(cls) -> Dict[str, BoundRecord]:
        return dict(cls.RECORDS)

    @classmethod
    def evaluate_certificate(cls, paper_coefficients: Mapping[str, float]):
        contributions = {}
        total = 0.0

        for name, coefficient in paper_coefficients.items():
            if name not in cls.RECORDS:
                raise KeyError(f"No published Section-5 bound registered for {name}")
            record = cls.RECORDS[name]

            # In a lower-bound certificate, positive coefficients require
            # lower bounds and negative coefficients require upper bounds.
            expected = "lower" if coefficient > 0 else "upper"
            if record.direction != expected:
                raise ValueError(
                    f"Sign/bound mismatch for {name}: coefficient={coefficient}, "
                    f"need {expected}, registered {record.direction}"
                )

            contribution = float(coefficient) * record.value
            contributions[name] = contribution
            total += contribution

        return total, contributions
