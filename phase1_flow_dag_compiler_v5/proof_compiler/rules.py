from __future__ import annotations
from typing import Dict, List, Tuple
import sympy as sp

from .params import alpha, beta, gamma, tau
from .region import Region, u
from .state import Anchor, State, Threshold, Transition
from .oracles import infer_oracles


FIXED_EXPR = {
    "alpha": alpha,
    "beta": beta,
    "gamma": gamma,
    "tau": tau,
    "1/3": sp.Rational(1,3),
    "1/10": sp.Rational(1,10),
}


def _fixed_expr(name: str):
    if name in FIXED_EXPR:
        return FIXED_EXPR[name]
    return sp.sympify(name)


def _threshold_expr(state: State, mapped_old: Dict[sp.Symbol, sp.Symbol]):
    t = state.threshold
    if t.kind == "fixed":
        return _fixed_expr(t.value)
    if t.kind == "factor":
        old = u(int(t.value))
        return mapped_old[old]
    raise ValueError("sqrt_remaining has no linear threshold expression")


def _anchor_expr_and_index(state: State,
                           mapped_old: Dict[sp.Symbol, sp.Symbol]):
    a = state.anchor
    if a.kind == "fixed":
        return _fixed_expr(a.value), None
    old = u(int(a.value))
    new_sym = mapped_old[old]
    return new_sym, int(str(new_sym)[1:])


def _insertion_position(state: State) -> int:
    """0-based insertion position among ordered factor variables."""
    if state.threshold.kind == "factor":
        return int(state.threshold.value) - 1
    if state.threshold.kind == "sqrt_remaining":
        return state.factor_count
    if state.threshold.kind == "fixed":
        # Root G2: first newly exposed prime.
        return state.factor_count
    raise ValueError(state.threshold.kind)


def buchstab_expand(state: State, feasible_oracle):
    """Exact one-step Buchstab expansion.

    parent = base(anchor threshold) - correction(new prime factor).

    Factor variables are canonically renamed after inserting the new exposed
    prime into its ordered position.
    """
    if not state.expandable:
        return None

    k = state.factor_count
    pos = _insertion_position(state)  # 0..k

    # Old ui -> new uj after insertion.
    mapping = {}
    for i in range(1, k+1):
        new_i = i if (i-1) < pos else i+1
        mapping[u(i)] = u(new_i)

    q = u(pos+1)
    # Map old constraints, but discard the old product-sum <= 1 constraint:
    # after a new exposed prime is inserted, the new total-product constraint
    # strictly dominates the old one. Keeping both prevents canonical merging
    # with paper terms such as G6.
    old_product = (sum(u(i) for i in range(1, k+1)) - 1) if k else None
    mapped_exprs = []
    for ex in state.region.inequalities:
        if old_product is not None and sp.simplify(ex - old_product) == 0:
            continue
        mapped_exprs.append(sp.expand(ex.xreplace(mapping)))
    new_region = Region(
        k+1, tuple(mapped_exprs), state.region.guards, state.region.source
    )
    exprs = list(new_region.inequalities)

    # Anchor lower bound q >= anchor.
    anchor_expr, anchor_new_idx = _anchor_expr_and_index(state, mapping)

    # If the anchor is fixed and the old threshold is a factor, an old
    # constraint anchor<=threshold becomes redundant once we add
    # anchor<=q<=threshold. Remove that exact redundant inequality.
    if state.anchor.kind == "fixed" and state.threshold.kind == "factor":
        mapped_thr = mapping[u(int(state.threshold.value))]
        redundant = sp.expand(anchor_expr - mapped_thr)
        exprs = [ex for ex in exprs if sp.simplify(ex-redundant) != 0]

    exprs.append(anchor_expr - q)

    # q <= old threshold.
    if state.threshold.kind in {"fixed", "factor"}:
        high = _threshold_expr(state, mapping)
        exprs.append(q - high)
    elif state.threshold.kind == "sqrt_remaining":
        # q <= sqrt(N / product(old fixed factors))
        # exponent form: 2q + sum(old factors) <= 1.
        old_sum = sum(mapping[u(i)] for i in range(1, k+1))
        exprs.append(2*q + old_sum - 1)
    else:
        raise ValueError(state.threshold.kind)

    # Any fixed product of exposed prime factors divides an element <= N,
    # hence the exponent sum is <= 1. This constraint is what makes the
    # Buchstab factor-depth recursion genuinely finite.
    exprs.append(sum(u(i) for i in range(1, k+2)) - 1)

    corr_region = Region(
        k+1, tuple(sp.expand(x) for x in exprs),
        state.region.guards,
        source=f"Buchstab correction from {state.state_id}",
    )

    # Base: same region, lower threshold = anchor, no further lower anchor
    # registered in this grammar.
    if state.anchor.kind == "fixed":
        base_threshold = Threshold("fixed", state.anchor.value)
    else:
        # Anchor factor index after insertion is not relevant to base, because
        # base has the old factor count. Use old anchor index.
        base_threshold = Threshold("factor", state.anchor.value)

    base = State(
        factor_count=k,
        region=state.region,
        sieve_set=state.sieve_set,
        threshold=base_threshold,
        anchor=None,
        analytic_oracles=infer_oracles(state),
        source_tags=state.source_tags + ["Buchstab base"],
        notes=state.notes + ["STOP child of exact Buchstab identity."],
        paper_aliases=[],
    )

    # Correction threshold is the newly exposed q.
    # Anchor after insertion:
    if state.anchor.kind == "fixed":
        corr_anchor = state.anchor
    else:
        corr_anchor = Anchor("factor", str(anchor_new_idx))

    corr = State(
        factor_count=k+1,
        region=corr_region,
        sieve_set=state.sieve_set,
        threshold=Threshold("factor", str(pos+1)),
        anchor=corr_anchor,
        analytic_oracles=[],
        source_tags=state.source_tags + ["Buchstab correction"],
        notes=state.notes + [
            "Exact correction child; coefficient multiplier is -1."
        ],
        paper_aliases=[],
    )
    corr.analytic_oracles = infer_oracles(corr)

    if not feasible_oracle.feasible(corr.region):
        corr = None

    children = [(base, +1.0)]
    if corr is not None:
        children.append((corr, -1.0))

    transition = Transition(
        parent=state.state_id,
        children=[(c.state_id, m) for c, m in children],
        rule="BUCHSTAB_EXPAND",
        relation="parent = base - correction",
        proof_status="identity_exact",
        source="Buchstab identity; paper repeatedly uses it in (4.16),(4.22),(4.32),(4.33)",
        notes=[
            "Reachability is checked over the full linear Proposition 4.3 parameter domain.",
            "No analytic upper/lower estimate is assumed by this transition."
        ],
    )
    return children, transition
