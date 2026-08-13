from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from typing import Dict, Iterable, Mapping, Optional


TOL = 1e-12


@dataclass
class LedgerSnapshot:
    label: str
    coefficients: Dict[str, float]


class CertificateLedger:
    """A symbolic linear certificate ledger.

    Coefficients are stored on canonical Phase-1 resources.  Exact linear
    identities can move any signed coefficient amount through a rewrite.
    A non-negative bundle B>=0 can be subtracted from a lower-bound
    certificate without invalidating the lower bound.
    """

    def __init__(self):
        self._c = defaultdict(float)
        self.history: list[LedgerSnapshot] = []

    def add(self, resource: str, coefficient: float) -> None:
        self._c[resource] += float(coefficient)
        self._clean(resource)

    def add_terms(self, terms: Mapping[str, float], scale: float = 1.0) -> None:
        for resource, coefficient in terms.items():
            self.add(resource, scale * coefficient)

    def coefficient(self, resource: str) -> float:
        return float(self._c.get(resource, 0.0))

    def drop_nonnegative_positive_term(self, resource: str,
                                       amount: Optional[float] = None) -> None:
        """Drop +amount*X using X>=0.

        This is legal only for positive coefficient mass in a lower-bound
        certificate.
        """
        available = self.coefficient(resource)
        if available <= TOL:
            raise ValueError(
                f"Cannot non-negatively drop {resource}: coefficient={available}"
            )
        if amount is None:
            amount = available
        if amount < -TOL or amount > available + TOL:
            raise ValueError(
                f"Invalid drop amount {amount} for {resource}; available={available}"
            )
        self.add(resource, -amount)

    def apply_identity(self, rule: Mapping, amount: float) -> None:
        """Apply amount * parent = amount * sum(children).

        `amount` is signed.  Example: if the ledger contains -S3 and the
        identity is S3=..., use amount=-1.
        """
        parent = rule["parent"]
        available = self.coefficient(parent)

        if abs(amount) <= TOL:
            return

        # The signed amount must be present in the parent coefficient.
        if available * amount <= 0 or abs(amount) > abs(available) + TOL:
            raise ValueError(
                f"Cannot apply {rule['name']} with amount={amount}: "
                f"parent {parent} has coefficient {available}"
            )

        self.add(parent, -amount)
        for child, multiplier in rule["children"].items():
            self.add(child, amount * float(multiplier))

    def bridge_exactly(self, source: str, target: str) -> None:
        c = self.coefficient(source)
        if abs(c) <= TOL:
            return
        self.add(source, -c)
        self.add(target, c)

    def subtract_nonnegative_bundle(self, rule: Mapping,
                                    amount: float = 1.0) -> None:
        """If B=sum b_i X_i >=0, replace E by E-amount*B.

        This produces a weaker but valid lower bound for amount>=0.
        """
        if amount < -TOL:
            raise ValueError("A nonnegative bundle may only be subtracted with amount>=0.")
        for resource, coefficient in rule["bundle"].items():
            self.add(resource, -amount * float(coefficient))

    def snapshot(self, label: str) -> None:
        self.history.append(
            LedgerSnapshot(label, dict(self.nonzero()))
        )

    def nonzero(self) -> Dict[str, float]:
        return {
            k: float(v)
            for k, v in self._c.items()
            if abs(v) > TOL
        }

    def _clean(self, resource: str) -> None:
        if abs(self._c[resource]) <= TOL:
            self._c.pop(resource, None)
