from __future__ import annotations
from itertools import combinations


def _support(bundle_rule):
    return set(bundle_rule["bundle"].keys())


def classify_pair(a, b):
    A, B = _support(a), _support(b)
    inter = A & B
    if not inter:
        return "DISJOINT", inter
    if A <= B or B <= A:
        return "LAMINAR_NESTED", inter
    return "CROSSING", inter


def analyze_bundle_conflicts(bundle_rules):
    pairs = []
    crossing = []
    laminar = []
    disjoint = []

    for a, b in combinations(bundle_rules, 2):
        cls, inter = classify_pair(a, b)
        rec = {
            "a": a["name"],
            "b": b["name"],
            "classification": cls,
            "intersection_resources": sorted(inter),
        }
        pairs.append(rec)
        if cls == "CROSSING":
            crossing.append(rec)
        elif cls == "LAMINAR_NESTED":
            laminar.append(rec)
        else:
            disjoint.append(rec)

    return {
        "pairwise": pairs,
        "crossing_pairs": crossing,
        "laminar_pairs": laminar,
        "disjoint_pairs": disjoint,
        "crossing_count": len(crossing),
        "recommendation": (
            "DISJOINT/LAMINAR bundle families can usually be handled by "
            "resource-flow DP/LP. CROSSING families form the genuine global "
            "set-packing/MILP core."
        ),
    }
