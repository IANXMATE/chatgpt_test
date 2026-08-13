from __future__ import annotations

from dataclasses import dataclass, asdict, field
from typing import Any, Dict, Iterable, List, Optional


@dataclass(frozen=True)
class GuardCheck:
    name: str
    passed: bool
    expression: str
    value: Optional[float] = None
    threshold: Optional[float] = None
    theorem: str = ""
    source: str = ""
    hard: bool = True
    note: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class SplitRecord:
    target: str
    variable: str
    boundary: str
    left_rule: str
    right_rule: str
    source: str
    note: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class TheoremTrace:
    guards: List[GuardCheck] = field(default_factory=list)
    splits: List[SplitRecord] = field(default_factory=list)
    applications: List[Dict[str, Any]] = field(default_factory=list)

    def add_guard(self, guard: GuardCheck) -> None:
        self.guards.append(guard)

    def add_split(self, split: SplitRecord) -> None:
        self.splits.append(split)

    def add_application(self, *, target: str, theorem: str,
                        source: str, detail: str) -> None:
        self.applications.append({
            "target": target,
            "theorem": theorem,
            "source": source,
            "detail": detail,
        })

    @property
    def hard_failures(self) -> List[GuardCheck]:
        return [g for g in self.guards if g.hard and not g.passed]

    @property
    def passed(self) -> bool:
        return not self.hard_failures

    def to_dict(self) -> Dict[str, Any]:
        return {
            "passed": self.passed,
            "hard_failures": [g.to_dict() for g in self.hard_failures],
            "guards": [g.to_dict() for g in self.guards],
            "splits": [s.to_dict() for s in self.splits],
            "applications": list(self.applications),
        }


# Human-readable source registry.  These are source labels rather than URLs
# because the saved record should remain stable if websites move.
THEOREM_SOURCES = {
    "PROP43": "Li-Liu 2026, Proposition 4.3, equations (4.18)-(4.18 definitions)",
    "LINEAR_WF": "Li-Liu 2026, Lemma 2.5 (Rosser-Iwaniec well-factorable linear sieve)",
    "SIEVE_FUNCS": "Li-Liu 2026, Lemma 2.2 (linear-sieve F,f)",
    "BUCHSTAB": "Li-Liu 2026, Lemma 2.1 (Buchstab function)",
    "DIST_GENERAL": "Li-Liu 2026, Lemma 3.1 (weighted Bombieri-Vinogradov / Pan-Ding)",
    "DIST_SMALL": "Li-Liu 2026, Lemma 3.5; adapted by Wu for Goldbach, valid nu<=1/10",
    "SEC53": "Li-Liu 2026, Section 5.3, equations (5.33)-(5.46)",
    "SEC54": "Li-Liu 2026, Section 5.4, equations (5.47)-(5.50)",
}
