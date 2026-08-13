from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List

from .certificate import CertificateLedger
from .model import Phase2Model


@dataclass
class ReplayStage:
    label: str
    coefficients: Dict[str, float]


class PaperReplay:
    """Replay equations (4.19) -> (4.18) using Phase-1 generated rules."""

    def __init__(self, model: Phase2Model,
                 allow_g16_paper_bridge: bool = True):
        self.model = model
        self.allow_g16_paper_bridge = allow_g16_paper_bridge
        self.ledger = CertificateLedger()
        self.stages: List[ReplayStage] = []

    def _record(self, label: str):
        named = {
            self.model.paper_name(r): c
            for r, c in self.ledger.nonzero().items()
        }
        self.stages.append(ReplayStage(label, named))

    def run(self) -> Dict[str, float]:
        L = self.ledger

        # (4.19) + (4.20), raw paper addition (not normalized source mixing).
        L.add_terms(self.model.source("P4_2_alpha_one_third")["terms"], 1.0)
        L.add_terms(self.model.source("P4_2_beta_gamma")["terms"], 1.0)
        self._record("(4.19)+(4.20), before dropping S6(beta,gamma)")

        # The paper drops +S6(beta,gamma) by non-negativity in (4.21).
        L.drop_nonnegative_positive_term("S6_beta_gamma")
        self._record("(4.21)")

        # Paper uses (4.22) for one of the two G2 terms.
        L.apply_identity(
            self.model.rewrite("paper_G2_to_G1_G13_G6_G14"),
            amount=+1.0,
        )
        self._record("(4.24): expand one G2")

        # Substitute the entire -S3(beta,gamma).
        L.apply_identity(
            self.model.rewrite("paper_S3_to_G5_G13_G7_G15"),
            amount=-1.0,
        )
        self._record("(4.27): expand -S3; G13 cancels canonically")

        # Substitute the entire -S5(beta,gamma).
        L.apply_identity(
            self.model.rewrite("paper_S5_to_G10_G16"),
            amount=-1.0,
        )
        self._record("(4.30): expand -S5")

        # Phase 1 deliberately keeps the arXiv-v2 G16 literal shape separate
        # from the shape used in the final (4.35)-(4.36) coverage.
        if self.allow_g16_paper_bridge:
            L.bridge_exactly(
                "G16_literal",
                self.model.alias("G16_expected_3factor_shape"),
            )
            self._record("paper G16 closure interpretation (source-shape warning)")
        else:
            raise RuntimeError(
                "Strict-source replay stops at G16: Phase 1 records the "
                "(4.29)/(4.34) vs (4.35)/(4.36) sequence-shape mismatch. "
                "Use allow_g16_paper_bridge=True to reproduce the paper's "
                "stated closure while retaining the warning."
            )

        # (4.31)-(4.36):
        # B = S6-G14-G15-G16+G11+G12 >= 0.
        # Current certificate contains S6-G14-G15-G16, so subtract B.
        L.subtract_nonnegative_bundle(
            self.model.bundle("paper_closure_4_31_4_36"),
            amount=1.0,
        )
        self._record("(4.18): drop nonnegative closure bundle")

        return dict(L.nonzero())
