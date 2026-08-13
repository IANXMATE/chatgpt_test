from __future__ import annotations
from collections import defaultdict


def build_stage2_blueprint(exploration, special_rewrites):
    outgoing = defaultdict(list)
    for t in exploration.transitions:
        outgoing[t.parent].append(t)

    expand_vars = []
    estimator_vars = []
    split_vars = []

    for sid, s in exploration.states.items():
        if sid in outgoing:
            expand_vars.append({
                "name": f"z_expand__{sid}",
                "type": "binary",
                "state_id": sid,
                "meaning": "1=use registered expansion, 0=STOP at this state",
            })
        for oracle in s.analytic_oracles:
            estimator_vars.append({
                "name": f"z_oracle__{sid}__{oracle}",
                "type": "binary",
                "state_id": sid,
                "oracle": oracle,
                "meaning": "Activate this terminal estimator if STOP is chosen.",
            })

    for p in exploration.split_proposals:
        split_vars.append({
            "name": "z_" + p["proposal_id"].replace(":", "__"),
            "type": "binary",
            **p,
        })

    continuous = [
        {"name": "a", "type": "continuous", "bounds": [1.5, 2.0]},
        {"name": "alpha", "type": "continuous"},
        {"name": "beta", "type": "continuous"},
        {"name": "gamma", "type": "continuous"},
        {"name": "epsilon", "type": "continuous", "lower": 0.0},
        {
            "name": "tau", "type": "derived",
            "definition": "(a-1)/a - epsilon"
        },
    ]

    return {
        "continuous_variables": continuous,
        "expand_binary_variables": expand_vars,
        "estimator_binary_variables": estimator_vars,
        "split_binary_variables": split_vars,
        "special_rewrite_choices": special_rewrites,
        "counts": {
            "continuous": len(continuous),
            "expand_binary": len(expand_vars),
            "estimator_binary": len(estimator_vars),
            "split_binary": len(split_vars),
            "special_rewrite": len(special_rewrites),
            "total_declared_before_auxiliaries": (
                len(continuous)+len(expand_vars)+
                len(estimator_vars)+len(split_vars)+len(special_rewrites)
            ),
        },
        "constraints_to_generate": [
            "Proposition 4.3 parameter-domain constraints",
            "tau=(a-1)/a-epsilon",
            "one STOP/EXPAND logic constraint per expandable state",
            "expansion child activation constraints",
            "one-of-N estimator constraint when STOP is active",
            "optional region split disjunctions",
            "canonical coefficient aggregation over identical state IDs",
            "registered special multi-state rewrites",
            "final certified margin >= delta > 0",
        ],
    }
