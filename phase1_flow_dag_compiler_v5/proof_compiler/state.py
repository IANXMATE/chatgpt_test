from __future__ import annotations
from dataclasses import dataclass, field, asdict
from typing import List, Optional, Tuple
import hashlib
import sympy as sp

from .region import Region


@dataclass(frozen=True)
class Threshold:
    kind: str  # fixed | factor | sqrt_remaining
    value: str

    def key(self):
        return (self.kind, self.value)

    def to_dict(self):
        return {"kind": self.kind, "value": self.value}


@dataclass(frozen=True)
class Anchor:
    kind: str  # fixed | factor
    value: str

    def key(self):
        return (self.kind, self.value)

    def to_dict(self):
        return {"kind": self.kind, "value": self.value}


@dataclass
class State:
    factor_count: int
    region: Region
    sieve_set: str
    threshold: Threshold
    anchor: Optional[Anchor]
    sequence_kind: str = "A_product"
    analytic_oracles: List[str] = field(default_factory=list)
    source_tags: List[str] = field(default_factory=list)
    notes: List[str] = field(default_factory=list)
    paper_aliases: List[str] = field(default_factory=list)

    @property
    def canonical_key(self):
        return (
            self.factor_count,
            self.region.key,
            self.sieve_set,
            self.threshold.key(),
            self.anchor.key() if self.anchor else None,
            self.sequence_kind,
        )

    @property
    def state_id(self):
        h = hashlib.sha1(repr(self.canonical_key).encode()).hexdigest()[:14]
        return f"S_{h}"

    @property
    def expandable(self):
        return self.anchor is not None

    def to_dict(self):
        return {
            "state_id": self.state_id,
            "factor_count": self.factor_count,
            "region": self.region.to_dict(),
            "sieve_set": self.sieve_set,
            "threshold": self.threshold.to_dict(),
            "anchor": self.anchor.to_dict() if self.anchor else None,
            "sequence_kind": self.sequence_kind,
            "analytic_oracles": sorted(set(self.analytic_oracles)),
            "source_tags": sorted(set(self.source_tags)),
            "notes": self.notes,
            "paper_aliases": sorted(set(self.paper_aliases)),
            "expandable": self.expandable,
            "canonical_key": repr(self.canonical_key),
        }


@dataclass
class Transition:
    parent: str
    children: List[Tuple[str, float]]
    rule: str
    relation: str
    proof_status: str
    source: str
    notes: List[str] = field(default_factory=list)

    def to_dict(self):
        return {
            "parent": self.parent,
            "children": [
                {"state_id": sid, "multiplier": mult}
                for sid, mult in self.children
            ],
            "rule": self.rule,
            "relation": self.relation,
            "proof_status": self.proof_status,
            "source": self.source,
            "notes": self.notes,
        }


@dataclass
class RootOccurrence:
    name: str
    state_id: str
    coefficient: float
    source: str

    def to_dict(self):
        return asdict(self)
