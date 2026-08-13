from __future__ import annotations
from collections import defaultdict


def analyze_unique_rewrite_chains(states, transitions):
    """Identify the Buchstab continuation spine.

    Each transition normally has:
      - a same-depth/base child;
      - a deeper correction child.
    Repeated continuation is therefore a linear-depth flow spine, not a
    binary proof-tree enumeration.
    """
    trans_by_parent = {t.parent: t for t in transitions}
    continuation = {}

    for t in transitions:
        parent_k = states[t.parent].factor_count
        deeper = [
            child for child, mult in t.children
            if states[child].factor_count > parent_k
        ]
        if len(deeper) == 1:
            continuation[t.parent] = deeper[0]

    starts = []
    incoming_cont = set(continuation.values())
    for p in continuation:
        if p not in incoming_cont:
            starts.append(p)

    chains = []
    covered = set()
    for start in starts:
        cur = start
        nodes = [cur]
        while cur in continuation and continuation[cur] not in nodes:
            cur = continuation[cur]
            nodes.append(cur)
        for n in nodes:
            covered.add(n)
        chains.append({
            "start": start,
            "nodes": nodes,
            "length_nodes": len(nodes),
            "max_factor_depth": max(states[n].factor_count for n in nodes),
            "paper_aliases": sorted({
                a for n in nodes for a in states[n].paper_aliases
            }),
            "solver_recommendation": (
                "Use one continuous through-flow per level with conservation; "
                "do not enumerate STOP/EXPAND bitstrings."
            ),
        })

    return {
        "chains": sorted(chains, key=lambda x: -x["length_nodes"]),
        "continuation_edge_count": len(continuation),
        "covered_state_count": len(covered),
    }
