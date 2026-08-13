from __future__ import annotations
from collections import defaultdict
import sympy as sp

from .params import alpha, beta, gamma, tau
from .region import u


def _canon_zero(expr):
    e = sp.factor(sp.expand(sp.sympify(expr)))
    # Hyperplane e=0 and -e=0 are identical.
    s1 = sp.srepr(e)
    s2 = sp.srepr(-e)
    return min(s1, s2)


def build_boundary_templates():
    """Boundaries are generated from theorem applicability, not from a generic
    list of preferred cut points.
    """
    return [
        {
            "name": "Lemma3_5_small_nu",
            "source": "Lemma 3.5",
            "match": "P(N*p1) switching/distribution states",
            "conditions": [
                {
                    "expr": u(1) - sp.Rational(1,10),
                    "meaning": "u1 <= 1/10",
                }
            ],
        },
        {
            "name": "theta_nu_piecewise_distribution",
            "source": "Section 3 piecewise distribution level",
            "match": "states whose distribution level depends on nu=u1",
            "conditions": [
                {"expr": u(1)-sp.Rational(1,15), "meaning": "u1 <= 1/15"},
                {"expr": u(1)-sp.Rational(1,10), "meaning": "u1 <= 1/10"},
                {"expr": u(1)-sp.Rational(3,14), "meaning": "u1 <= 3/14"},
                {"expr": u(1)-sp.Rational(1,4), "meaning": "u1 <= 1/4"},
                {"expr": u(1)-sp.Rational(2,7), "meaning": "u1 <= 2/7"},
                {"expr": u(1)-sp.Rational(2,5), "meaning": "u1 <= 2/5"},
                {"expr": u(1)-sp.Rational(1,2), "meaning": "u1 <= 1/2"},
            ],
        },
        {
            "name": "buchstab_omega_3_5",
            "source": "Lemma 2.1 / Section 5.4",
            "match": "four-or-more-factor Buchstab terminal states",
            "conditions": [
                {
                    "expr_template": "sum_u + (7/2)*u2 - 1",
                    "meaning": "(1-sum(ui))/u2 >= 3.5",
                }
            ],
        },
        {
            "name": "buchstab_omega_3_16",
            "source": "(5.49)",
            "match": "four-or-more-factor Buchstab terminal states",
            "conditions": [
                {
                    "expr_template": "sum_u + (79/25)*u2 - 1",
                    "meaning": "(1-sum(ui))/u2 >= 3.16",
                }
            ],
        },
        {
            "name": "buchstab_omega_3",
            "source": "(5.49)",
            "match": "four-or-more-factor Buchstab terminal states",
            "conditions": [
                {
                    "expr_template": "sum_u + 3*u2 - 1",
                    "meaning": "(1-sum(ui))/u2 >= 3",
                }
            ],
        },
    ]


def generate_lazy_boundaries(states):
    out = []
    seen = set()

    for sid, s in states.items():
        # Distribution-level boundaries.
        if s.factor_count >= 1:
            for tpl in build_boundary_templates()[:2]:
                # Restrict Lemma 3.5 to P(N*p1)-type states.
                if tpl["name"] == "Lemma3_5_small_nu" and s.sieve_set != "P(N*p1)":
                    continue
                for cond in tpl["conditions"]:
                    expr = cond["expr"]
                    key = (sid, _canon_zero(expr), tpl["name"])
                    if key in seen:
                        continue
                    seen.add(key)
                    out.append({
                        "state_id": sid,
                        "paper_aliases": list(s.paper_aliases),
                        "theorem": tpl["name"],
                        "source": tpl["source"],
                        "boundary_expr_zero": str(sp.expand(expr)) + " = 0",
                        "condition_side": cond["meaning"],
                        "activation": "LAZY_ONLY_IF_THEOREM_IS_CONSIDERED",
                    })

        # Buchstab argument boundaries.
        if (
            s.factor_count >= 4
            and s.sieve_set == "P(N*p1)"
            and s.threshold.kind == "factor"
        ):
            sum_u = sum(u(i) for i in range(1, s.factor_count+1))
            for tpl, c in [
                (build_boundary_templates()[2], sp.Rational(7,2)),
                (build_boundary_templates()[3], sp.Rational(79,25)),
                (build_boundary_templates()[4], sp.Integer(3)),
            ]:
                expr = sum_u + c*u(2) - 1
                key = (sid, _canon_zero(expr), tpl["name"])
                if key in seen:
                    continue
                seen.add(key)
                out.append({
                    "state_id": sid,
                    "paper_aliases": list(s.paper_aliases),
                    "theorem": tpl["name"],
                    "source": tpl["source"],
                    "boundary_expr_zero": str(sp.expand(expr)) + " = 0",
                    "condition_side": tpl["conditions"][0]["meaning"],
                    "activation": "LAZY_ONLY_IF_THEOREM_IS_CONSIDERED",
                })

    return out
