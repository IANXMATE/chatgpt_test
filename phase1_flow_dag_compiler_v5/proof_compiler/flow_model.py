from __future__ import annotations
from dataclasses import dataclass, asdict
from collections import defaultdict, deque
from typing import Dict, List, Tuple, Optional

from .paper_flow import (
    build_source_certificates, build_macro_rewrites, build_bundle_rules
)
from .terminal_rules import terminal_rules_for


def signed(resource: str, sign: str) -> str:
    return f"{sign}::{resource}"


def flip(sign: str) -> str:
    return "NEG" if sign == "POS" else "POS"


@dataclass
class FlowVariable:
    name: str
    kind: str
    domain: str
    lower: float
    upper: Optional[float]
    meaning: str
    metadata: dict

    def to_dict(self):
        return asdict(self)


def build_alias_map(states):
    out = {}
    for sid, s in states.items():
        for alias in s.paper_aliases:
            out[alias] = sid
    return out


def structural_rewrite_rules(states, transitions):
    """Convert exact Buchstab transitions to resource rewrites on canonical
    state IDs.  These are AND-hyperedges: using one unit of the parent rewrite
    generates every child with its signed multiplier.
    """
    rules = []
    for i, tr in enumerate(transitions):
        children = {}
        for child_sid, mult in tr.children:
            children[child_sid] = float(mult)
        rules.append({
            "name": f"structural_{i:04d}",
            "parent": tr.parent,
            "children": children,
            "source": tr.source,
            "proof_status": tr.proof_status,
            "type": "LINEAR_INHERITABLE_AND",
        })
    return rules


def macro_rules_with_aliases(alias_map):
    rules = []
    for r in build_macro_rewrites():
        # Keep paper names as resources if no canonical structural state exists.
        parent = alias_map.get(r.parent, r.parent)
        children = {
            alias_map.get(name, name): coeff
            for name, coeff in r.children.items()
        }
        rules.append({
            "name": r.name,
            "parent": parent,
            "children": children,
            "source": r.source,
            "proof_status": r.exactness,
            "type": "LINEAR_INHERITABLE_AND_MACRO",
            "notes": r.notes,
        })
    return rules


def source_terms_with_aliases(alias_map):
    sources = []
    for s in build_source_certificates():
        terms = {
            alias_map.get(name, name): coeff
            for name, coeff in s.terms.items()
        }
        sources.append({
            "name": s.name,
            "lhs_scale": s.lhs_scale,
            "terms": terms,
            "source": s.source,
            "guard": s.guard,
            "notes": s.notes,
        })
    return sources


def bundle_rules_with_aliases(alias_map):
    out = []
    for r in build_bundle_rules():
        out.append({
            "name": r.name,
            "bundle": {
                alias_map.get(name, name): coeff
                for name, coeff in r.bundle.items()
            },
            "source": r.source,
            "guard": r.guard,
            "verification_status": r.verification_status,
            "notes": r.notes,
            "type": "MULTI_RESOURCE_NONNEGATIVE_ELIMINATION",
        })
    return out


def build_flow_blueprint(states, transitions):
    alias_map = build_alias_map(states)
    srules = structural_rewrite_rules(states, transitions)
    mrules = macro_rules_with_aliases(alias_map)
    all_unary_rules = srules + mrules
    sources = source_terms_with_aliases(alias_map)
    bundles = bundle_rules_with_aliases(alias_map)

    resources = set(states.keys())
    # Include abstract paper resources not present in the structural graph.
    for s in sources:
        resources.update(s["terms"].keys())
    for r in all_unary_rules:
        resources.add(r["parent"])
        resources.update(r["children"].keys())
    for b in bundles:
        resources.update(b["bundle"].keys())

    outgoing = defaultdict(list)
    incoming = defaultdict(list)

    variables = []
    equations = defaultdict(lambda: {"in": [], "out": []})
    guards = []

    # 1) Continuous mixture of the two valid source certificates.
    # Normalize lambda_A + lambda_B = 1. Because both have lhs scale 2,
    # this yields a normalized valid 2D lower-bound certificate.
    for s in sources:
        lam = f"lambda_source__{s['name']}"
        variables.append(FlowVariable(
            lam, "SOURCE_MIX_WEIGHT", "continuous", 0.0, 1.0,
            "Nonnegative mixing weight for a valid source inequality.",
            {"source": s["source"], "guard": s["guard"]},
        ))
        for resource, coeff in s["terms"].items():
            sign = "POS" if coeff > 0 else "NEG"
            node = signed(resource, sign)
            equations[node]["in"].append({
                "expr": f"{abs(coeff)}*{lam}",
                "kind": "source_supply",
                "source_certificate": s["name"],
            })
    source_normalization = {
        "equation": " + ".join(
            f"lambda_source__{s['name']}" for s in sources
        ) + " = 1",
        "meaning": (
            "Continuous convex mixing of the two Proposition 4.2 instances. "
            "The paper's addition corresponds to equal normalized weights."
        ),
    }

    # 2) Linear inheritable rewrites.  No binary variable is needed.
    # A coefficient mass may split continuously among STOP and any valid
    # linear identity rewrites.
    for r in all_unary_rules:
        parent = r["parent"]
        for sign in ("POS", "NEG"):
            x = f"x_rewrite__{sign}__{r['name']}"
            variables.append(FlowVariable(
                x, "REWRITE_ALLOCATION", "continuous", 0.0, None,
                "Amount of signed coefficient mass using this linear identity.",
                {
                    "parent": parent,
                    "sign": sign,
                    "rule": r["name"],
                    "type": r["type"],
                },
            ))
            pnode = signed(parent, sign)
            equations[pnode]["out"].append({
                "expr": x, "kind": "rewrite_use", "rule": r["name"]
            })

            for child, mult in r["children"].items():
                child_sign = sign if mult > 0 else flip(sign)
                cnode = signed(child, child_sign)
                equations[cnode]["in"].append({
                    "expr": f"{abs(mult)}*{x}",
                    "kind": "rewrite_output",
                    "rule": r["name"],
                    "from": pnode,
                })

    # 3) Exact cancellation between positive and negative copies of the same
    # canonical resource. This is a local continuous operation, not a branch.
    for resource in sorted(resources):
        c = f"x_cancel__{resource}"
        variables.append(FlowVariable(
            c, "EXACT_CANCELLATION", "continuous", 0.0, None,
            "Equal positive and negative coefficient mass cancelled exactly.",
            {"resource": resource},
        ))
        equations[signed(resource, "POS")]["out"].append({
            "expr": c, "kind": "exact_cancellation"
        })
        equations[signed(resource, "NEG")]["out"].append({
            "expr": c, "kind": "exact_cancellation"
        })

    # 4) Terminal estimation / trivial drop.  Rules are sign-aware.
    # For certified paper aliases we can attach known directions.
    reverse_alias = defaultdict(list)
    for alias, sid in alias_map.items():
        reverse_alias[sid].append(alias)

    for resource in sorted(resources):
        aliases = reverse_alias.get(resource, [])
        names_for_terminal = aliases or [resource]

        for sign in ("POS", "NEG"):
            attached = []
            for name in names_for_terminal:
                for rule in terminal_rules_for(name, sign):
                    key = (rule.name, sign)
                    if key in attached:
                        continue
                    attached.append(key)
                    x = f"x_terminal__{sign}__{resource}__{rule.name}"
                    variables.append(FlowVariable(
                        x, "TERMINAL_ALLOCATION", "continuous", 0.0, None,
                        "Coefficient mass stopped and certified by this estimator.",
                        {
                            "resource": resource,
                            "paper_names": names_for_terminal,
                            "sign": sign,
                            "rule": rule.to_dict(),
                        },
                    ))
                    equations[signed(resource, sign)]["out"].append({
                        "expr": x,
                        "kind": "terminal",
                        "terminal_rule": rule.name,
                        "bound_direction": rule.bound_direction,
                    })

            # If no certified terminal exists, create an unresolved sink only
            # for diagnostics. Stage 2 must not use it in a proof.
            if not attached:
                x = f"x_unresolved__{sign}__{resource}"
                variables.append(FlowVariable(
                    x, "UNRESOLVED_FRONTIER", "continuous", 0.0, None,
                    "Diagnostic only; must be forced to zero in a certified solve.",
                    {"resource": resource, "sign": sign},
                ))
                equations[signed(resource, sign)]["out"].append({
                    "expr": x, "kind": "UNRESOLVED_FRONTIER"
                })

    # 5) Multi-resource nonnegative bundle eliminations.
    # These are the only operations here that jointly consume several state
    # pools.  They are the source of genuine resource-overlap complexity.
    for b in bundles:
        y = f"y_bundle__{b['name']}"
        variables.append(FlowVariable(
            y, "BUNDLE_USE", "continuous", 0.0, None,
            "Amount of a certified nonnegative signed bundle removed.",
            {
                "bundle": b["bundle"],
                "guard": b["guard"],
                "verification_status": b["verification_status"],
            },
        ))
        for resource, coeff in b["bundle"].items():
            sign = "POS" if coeff > 0 else "NEG"
            equations[signed(resource, sign)]["out"].append({
                "expr": f"{abs(coeff)}*{y}",
                "kind": "bundle_consumption",
                "bundle_rule": b["name"],
            })
        guards.append({
            "variable": y,
            "guard": b["guard"],
            "verification_status": b["verification_status"],
        })

    # Conservation equations.
    conservation = []
    for node, io in sorted(equations.items()):
        inflow = " + ".join(x["expr"] for x in io["in"]) or "0"
        outflow = " + ".join(x["expr"] for x in io["out"]) or "0"
        conservation.append({
            "signed_node": node,
            "equation": f"{inflow} = {outflow}",
            "in_terms": io["in"],
            "out_terms": io["out"],
        })

    return {
        "alias_map": alias_map,
        "sources": sources,
        "source_normalization": source_normalization,
        "linear_rewrite_rules": all_unary_rules,
        "bundle_rules": bundles,
        "resources": sorted(resources),
        "flow_variables": [v.to_dict() for v in variables],
        "conservation_equations": conservation,
        "guarded_variables": guards,
        "model_principle": {
            "linear_rewrites": (
                "Continuous coefficient flow; no integer/binary expansion count."
            ),
            "and_semantics": (
                "Using x units of a rewrite creates all children with the listed "
                "signed multipliers."
            ),
            "or_semantics": (
                "Alternative linear rewrites/terminal estimators share the same "
                "resource conservation equation, so coefficient mass may be "
                "allocated among them without enumerating proof paths."
            ),
            "cancellation": (
                "Positive and negative copies of the same canonical state share "
                "an exact continuous cancellation variable."
            ),
            "combinatorial_core": (
                "Only guarded regime choices and crossing multi-resource bundle "
                "operations need genuine disjunctive/MILP treatment."
            ),
        },
    }
