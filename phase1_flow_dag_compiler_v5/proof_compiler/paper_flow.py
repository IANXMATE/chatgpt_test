from __future__ import annotations
from dataclasses import dataclass, asdict
from typing import Dict, List, Optional


@dataclass(frozen=True)
class SourceCertificate:
    name: str
    lhs_scale: float
    terms: Dict[str, float]
    source: str
    guard: List[str]
    notes: List[str]

    def to_dict(self):
        return asdict(self)


@dataclass(frozen=True)
class LinearMacroRewrite:
    name: str
    parent: str
    children: Dict[str, float]
    source: str
    exactness: str
    notes: List[str]

    def to_dict(self):
        return asdict(self)


@dataclass(frozen=True)
class NonnegativeBundleRule:
    """If sum_i coeff_i * X_i >= 0, that signed bundle may be removed
    from a lower-bound certificate without invalidating it.
    """
    name: str
    bundle: Dict[str, float]
    source: str
    guard: List[str]
    verification_status: str
    notes: List[str]

    def to_dict(self):
        return asdict(self)


def build_source_certificates() -> List[SourceCertificate]:
    # We start before Proposition 4.3 is fully nested.  This preserves the
    # authors' actual structural choice of adding (4.19) and (4.20).
    #
    # S4(1/3)=0 has already been eliminated exactly in source_A.
    return [
        SourceCertificate(
            name="P4_2_alpha_one_third",
            lhs_scale=2.0,
            terms={
                "G1": +2.0,
                "G3": -2.0,
                "G4": -1.0,
                "G9": -1.0,
                "S6_alpha_1_3": +1.0,
            },
            source="(4.19)",
            guard=[
                "1/18 < alpha < 1/3",
                "1/3 < tau",
            ],
            notes=[
                "This is Proposition 4.2 at (kappa,sigma)=(alpha,1/3).",
                "S4(1/3)=0 is removed exactly.",
            ],
        ),
        SourceCertificate(
            name="P4_2_beta_gamma",
            lhs_scale=2.0,
            terms={
                "G2": +2.0,
                "G3": -2.0,
                "S3_beta_gamma": -1.0,
                "G8": -2.0,
                "S5_beta_gamma": -1.0,
                "S6_beta_gamma": +1.0,
            },
            source="(4.20)",
            guard=[
                "alpha < beta < gamma < 1/3",
                "1/3 < tau",
            ],
            notes=[
                "This is Proposition 4.2 at (kappa,sigma)=(beta,gamma).",
                "The paper later drops S6(beta,gamma) by non-negativity.",
            ],
        ),
    ]


def build_macro_rewrites() -> List[LinearMacroRewrite]:
    return [
        LinearMacroRewrite(
            name="paper_G2_to_G1_G13_G6_G14",
            parent="G2",
            children={
                "G1": +1.0,
                "G13": -1.0,
                "G6": +1.0,
                "G14": -1.0,
            },
            source="(4.22)-(4.23)",
            exactness="identity_up_to_admissible_error",
            notes=[
                "The paper applies this identity to one of the two G2 copies.",
                "In the flow model, any nonnegative fraction of the G2 coefficient "
                "may legally use the same linear identity.",
            ],
        ),
        LinearMacroRewrite(
            name="paper_S3_to_G5_G13_G7_G15",
            parent="S3_beta_gamma",
            children={
                "G5": +1.0,
                "G13": -1.0,
                "G7": -1.0,
                "G15": +1.0,
            },
            source="(4.25)-(4.26)",
            exactness="identity_up_to_admissible_error",
            notes=[
                "When substituted with coefficient -1, the G13 contribution "
                "has the opposite sign to the one from the G2 rewrite and can cancel.",
            ],
        ),
        LinearMacroRewrite(
            name="paper_S5_to_G10_G16",
            parent="S5_beta_gamma",
            children={
                "G10": +1.0,
                "G16_literal": +1.0,
            },
            source="(4.28)-(4.29)",
            exactness="identity_up_to_admissible_error",
            notes=[
                "G16_literal preserves the arXiv v2 sequence shape A_{p1 p2}.",
                "The later closure uses a three-factor shape; this is audited separately.",
            ],
        ),
    ]


def build_bundle_rules() -> List[NonnegativeBundleRule]:
    return [
        NonnegativeBundleRule(
            name="paper_closure_4_31_4_36",
            # Paper claims:
            # S6 >= G14+G15+G16-G11-G12
            # equivalently S6-G14-G15-G16+G11+G12 >= 0.
            bundle={
                "S6_alpha_1_3": +1.0,
                "G14": -1.0,
                "G15": -1.0,
                "G16_expected_3factor_shape": -1.0,
                "G11": +1.0,
                "G12": +1.0,
            },
            source="(4.31)-(4.36)",
            guard=["beta + gamma > 1/3"],
            verification_status="PAPER_CLAIM_WITH_SOURCE_SHAPE_WARNING",
            notes=[
                "This is a multi-resource nonnegative bundle, not a unary rewrite.",
                "It is exactly the kind of operation that can create resource conflicts.",
                "arXiv v2 renders G16 in (4.29)/(4.34) with A_{p1 p2}, while "
                "(4.35)/(4.36) close with A_{p1 p2 p3}.",
            ],
        )
    ]


def build_reference_final_certificate():
    return {
        "lhs_scale": 4.0,
        "source": "(4.18)",
        "terms": {
            "G1": +3.0, "G2": +1.0, "G3": -4.0,
            "G4": -1.0, "G5": -1.0, "G6": +1.0,
            "G7": +1.0, "G8": -2.0, "G9": -1.0,
            "G10": -1.0, "G11": -1.0, "G12": -1.0,
        },
        "role": "regression target; not an independent optimization source",
    }


def build_verification_bridges():
    return [
        {
            "name": "G16_literal_to_expected_three_factor_shape",
            "from": "G16_literal",
            "to": "G16_expected_3factor_shape",
            "relation": "identity_if_source_typo_is_confirmed",
            "enabled_by_default": False,
            "source_issue": "(4.29)/(4.34) vs (4.35)/(4.36)",
            "notes": [
                "This bridge is intentionally disabled.",
                "Enable only after checking the source/PDF/erratum and confirming "
                "that the A_{p1p2} / A_{p1p2p3} mismatch is typographical."
            ],
        }
    ]
