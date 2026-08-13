from __future__ import annotations
import sympy as sp
from typing import Dict, List, Tuple

from .params import alpha, beta, gamma, tau
from .region import Region, u
from .state import Anchor, RootOccurrence, State, Threshold
from .oracles import ROOT_ORACLES


def _ordered(*idxs):
    out = []
    for a, b in zip(idxs[:-1], idxs[1:]):
        out.append(u(a) - u(b))  # ui <= uj
    return out


def _state(k, inequalities, sieve_set, threshold, anchor,
           alias, source, notes=None):
    all_ineq = list(inequalities)
    if k > 0:
        all_ineq.append(sum(u(i) for i in range(1, k+1)) - 1)
    s = State(
        factor_count=k,
        region=Region(k, tuple(sp.expand(x) for x in all_ineq),
                      source=source),
        sieve_set=sieve_set,
        threshold=threshold,
        anchor=anchor,
        analytic_oracles=list(ROOT_ORACLES.get(alias, [])),
        source_tags=[source],
        notes=list(notes or []),
        paper_aliases=[alias],
    )
    return s


def build_root_certificate():
    roots: Dict[str, State] = {}

    roots["G1"] = _state(
        0, [], "P(N)", Threshold("fixed", "alpha"), None,
        "G1", "(4.18)"
    )
    roots["G2"] = _state(
        0, [], "P(N)", Threshold("fixed", "beta"),
        Anchor("fixed", "alpha"),
        "G2", "(4.18),(4.22)"
    )
    roots["G3"] = _state(
        1, [tau-u(1), u(1)-sp.Rational(1,2)],
        "P(N)", Threshold("factor", "1"), Anchor("fixed", "tau"),
        "G3", "(4.18)"
    )
    roots["G4"] = _state(
        1, [alpha-u(1), u(1)-sp.Rational(1,3)],
        "P(N)", Threshold("fixed", "alpha"), None,
        "G4", "(4.18)"
    )
    roots["G5"] = _state(
        1, [alpha-u(1), u(1)-gamma],
        "P(N)", Threshold("fixed", "alpha"), None,
        "G5", "(4.18)"
    )
    roots["G6"] = _state(
        2, [alpha-u(1), u(1)-u(2), u(2)-beta],
        "P(N)", Threshold("fixed", "alpha"), None,
        "G6", "(4.18)"
    )
    roots["G7"] = _state(
        2, [alpha-u(1), u(1)-beta, beta-u(2), u(2)-gamma],
        "P(N)", Threshold("fixed", "alpha"), None,
        "G7", "(4.18)"
    )
    roots["G8"] = _state(
        2, [gamma-u(1), u(1)-u(2),
            u(1)+2*u(2)-1],
        "P(N*p1)", Threshold("factor", "2"), Anchor("factor", "1"),
        "G8", "(4.18)"
    )
    roots["G9"] = _state(
        2, [alpha-u(1), u(1)-sp.Rational(1,3),
            sp.Rational(1,3)-u(2),
            u(1)+2*u(2)-1],
        "P(N*p1)", Threshold("factor", "2"), Anchor("factor", "1"),
        "G9", "(4.18)"
    )
    roots["G10"] = _state(
        2, [beta-u(1), u(1)-gamma,
            gamma-u(2), u(1)+2*u(2)-1],
        "P(N*p1)", Threshold("sqrt_remaining", "1"),
        Anchor("factor", "2"),
        "G10", "(4.18)"
    )
    roots["G11"] = _state(
        4, [alpha-u(1), u(1)-u(2), u(2)-u(3),
            u(3)-u(4), u(4)-beta],
        "P(N*p1)", Threshold("factor", "2"), Anchor("factor", "1"),
        "G11", "(4.18),(5.4)"
    )
    roots["G12"] = _state(
        4, [alpha-u(1), u(1)-u(2), u(2)-u(3),
            u(3)-beta, beta-u(4), u(4)-gamma],
        "P(N*p1)", Threshold("factor", "2"), Anchor("factor", "1"),
        "G12", "(4.18),(5.4)"
    )

    coeff = {
        "G1": 3.0, "G2": 1.0, "G3": -4.0, "G4": -1.0,
        "G5": -1.0, "G6": 1.0, "G7": 1.0, "G8": -2.0,
        "G9": -1.0, "G10": -1.0, "G11": -1.0, "G12": -1.0,
    }
    occurrences = [
        RootOccurrence(name, roots[name].state_id, coeff[name], "(4.18)")
        for name in coeff
    ]
    return roots, occurrences


def build_special_rewrites():
    """Multi-state/certificate rewrites from (4.31)-(4.36).

    These do not replace the generic Buchstab state transitions. They are
    additional legal transformations Stage 2 may choose when the required
    states/coefficient pattern is present.
    """
    return [
        {
            "rewrite_id": "paper_closure_4_31_4_36",
            "type": "multi_state_domination",
            "source": "(4.31)-(4.36)",
            "guards": [
                "beta + gamma > 1/3",
                "1/18 < alpha < beta < (1-3*beta)/3 < gamma < 1/3 < tau",
            ],
            "input_pattern": {
                "description": "G14 + G15 + G16 - G11 - G12",
            },
            "resource": "S6(alpha,1/3)",
            "output_relation": (
                "S6(alpha,1/3) >= G14+G15+G16-G11-G12"
            ),
            "subrules": [
                {
                    "source": "(4.32)",
                    "relation": "G14-G11 -> three-factor positive region",
                },
                {
                    "source": "(4.33)",
                    "relation": "G15-G12 -> three-factor positive region",
                },
                {
                    "source": "(4.34)",
                    "relation": "G16 upper majorant",
                    "warning": (
                        "arXiv v2 displays A_{p1 p2} here; the final "
                        "(4.36) comparison uses A_{p1 p2 p3}."
                    ),
                },
                {
                    "source": "(4.35)",
                    "relation": "S6 exact four-cell region split",
                },
                {
                    "source": "(4.36)",
                    "relation": "region inclusion under beta+gamma>1/3",
                },
            ],
            "proof_status": "paper_exact_except_source_shape_warning",
        }
    ]
