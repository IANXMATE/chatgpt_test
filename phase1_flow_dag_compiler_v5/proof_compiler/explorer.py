from __future__ import annotations
from collections import defaultdict, deque
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple
import sympy as sp

from .params import ParameterDomain, ReferencePoint, alpha, beta, gamma, tau
from .region import LinearRegionOracle, Region, u
from .state import RootOccurrence, State, Transition
from .rules import buchstab_expand
from .oracles import infer_oracles


SPLIT_CUTS = [
    ("alpha", alpha),
    ("1/10", sp.Rational(1,10)),
    ("beta", beta),
    ("gamma", gamma),
    ("1/3", sp.Rational(1,3)),
    ("tau", tau),
]


@dataclass
class Exploration:
    states: Dict[str, State]
    transitions: List[Transition]
    roots: List[RootOccurrence]
    split_proposals: List[dict]
    collision_groups: List[dict]
    blocked_frontier: List[dict]
    depth_by_root: Dict[str, dict]
    full_expand_expression: dict


class ProofSpaceExplorer:
    def __init__(self, parameter_domain: ParameterDomain,
                 max_states: int = 200000,
                 max_factor_depth: Optional[int] = None):
        self.domain = parameter_domain
        self.lp = LinearRegionOracle(parameter_domain)
        self.max_states = max_states
        self.max_factor_depth = max_factor_depth

    def explore(self, root_states: Dict[str, State],
                roots: List[RootOccurrence]) -> Exploration:
        states: Dict[str, State] = {}
        transitions: List[Transition] = []
        incoming = defaultdict(list)
        aliases = defaultdict(set)
        blocked = []

        def add_state(s: State):
            sid = s.state_id
            if sid in states:
                old = states[sid]
                old.paper_aliases = sorted(
                    set(old.paper_aliases) | set(s.paper_aliases)
                )
                old.source_tags = sorted(
                    set(old.source_tags) | set(s.source_tags)
                )
                old.analytic_oracles = sorted(
                    set(old.analytic_oracles) | set(s.analytic_oracles)
                )
                return states[sid]
            if len(states) >= self.max_states:
                raise RuntimeError(
                    f"State cap {self.max_states} reached. "
                    "Increase --max-states."
                )
            s.analytic_oracles = infer_oracles(s)
            states[sid] = s
            return s

        q = deque()
        for name, s in root_states.items():
            s = add_state(s)
            aliases[s.state_id].add(name)
            if s.expandable:
                q.append(s.state_id)

        seen_expand = set()
        while q:
            sid = q.popleft()
            if sid in seen_expand:
                continue
            seen_expand.add(sid)
            s = states[sid]

            if self.max_factor_depth is not None and \
               s.factor_count >= self.max_factor_depth:
                blocked.append({
                    "state_id": sid,
                    "reason": "USER_MAX_FACTOR_DEPTH",
                    "factor_count": s.factor_count,
                })
                continue

            result = buchstab_expand(s, self.lp)
            if result is None:
                blocked.append({
                    "state_id": sid,
                    "reason": "NO_REGISTERED_EXPANSION_RULE",
                    "factor_count": s.factor_count,
                })
                continue

            children, tr = result
            actual_children = []
            for c, mult in children:
                c = add_state(c)
                incoming[c.state_id].append({
                    "parent": sid,
                    "multiplier": mult,
                    "rule": tr.rule,
                })
                actual_children.append((c.state_id, mult))
                if c.expandable and c.factor_count > s.factor_count:
                    q.append(c.state_id)

            tr.children = actual_children
            transitions.append(tr)

            # If correction child is absent, the next correction region is
            # infeasible everywhere in the admissible parameter domain.
            if len(actual_children) == 1:
                blocked.append({
                    "state_id": sid,
                    "reason": "CORRECTION_INFEASIBLE_OVER_PARAMETER_DOMAIN",
                    "factor_count": s.factor_count,
                })

        # Attach paper names to important states rediscovered mechanically.
        # This is annotation only and does not change the proof graph.
        tr_by_parent = {t.parent: t for t in transitions}

        def correction_child(sid):
            t = tr_by_parent.get(sid)
            if not t:
                return None
            for child, mult in t.children:
                if mult < 0:
                    return child
            return None

        def base_child(sid):
            t = tr_by_parent.get(sid)
            if not t:
                return None
            for child, mult in t.children:
                if mult > 0:
                    return child
            return None

        root_id = {r.name: r.state_id for r in roots}
        c1 = correction_child(root_id.get("G2"))
        if c1:
            b1 = base_child(c1)
            if b1:
                states[b1].paper_aliases = sorted(
                    set(states[b1].paper_aliases) | {"G13"}
                )
            c2 = correction_child(c1)
            if c2:
                b2 = base_child(c2)
                if b2:
                    states[b2].paper_aliases = sorted(
                        set(states[b2].paper_aliases) | {"G6"}
                    )
                c3 = correction_child(c2)
                if c3:
                    states[c3].paper_aliases = sorted(
                        set(states[c3].paper_aliases) | {"G14"}
                    )
        g10c = correction_child(root_id.get("G10"))
        if g10c:
            states[g10c].paper_aliases = sorted(
                set(states[g10c].paper_aliases) |
                {"G16_expected_3factor_shape"}
            )

        # Generate every named split hyperplane as a Stage-2 proposal.
        # We intentionally do NOT solve two additional LPs per proposal here:
        # that is thousands of redundant feasibility solves and can be checked
        # cheaply after Stage 2 fixes/boxes the continuous parameters. Keeping
        # all proposals is conservative: it cannot remove a useful branch.
        split_proposals = []
        for sid, s in states.items():
            for var in s.region.variables:
                for label, cut in SPLIT_CUTS:
                    split_proposals.append({
                        "proposal_id": f"split:{sid}:{var}:{label}",
                        "state_id": sid,
                        "variable": str(var),
                        "cut_label": label,
                        "cut_expr": str(cut),
                        "left_constraint": f"{var} <= {cut}",
                        "right_constraint": f"{var} >= {cut}",
                        "proof_status": "exact_partition_candidate",
                        "feasibility_status": "stage2_recheck_required",
                        "stage2_type": "binary_region_split",
                    })

        # Collision groups: states reachable from multiple contexts or known
        # by multiple paper aliases.
        collision_groups = []
        for sid, s in states.items():
            parents = incoming.get(sid, [])
            labels = sorted(set(s.paper_aliases) | aliases.get(sid, set()))
            is_root_and_reached = bool(parents) and bool(labels)
            if len(parents) > 1 or len(labels) > 1 or is_root_and_reached:
                collision_groups.append({
                    "state_id": sid,
                    "paper_aliases": labels,
                    "incoming": parents,
                    "meaning": (
                        "Canonical identical state; coefficient contributions "
                        "must be merged in Stage 2 and may cancel."
                    ),
                })

        # Root depth reachability via graph traversal.
        adjacency = defaultdict(list)
        for tr in transitions:
            for child, mult in tr.children:
                adjacency[tr.parent].append((child, mult))

        depth_by_root = {}
        for r in roots:
            dq = deque([(r.state_id, 0)])
            seen = {}
            max_factor = 0
            max_rule_depth = 0
            reachable = set()
            while dq:
                x, d = dq.popleft()
                if x in seen and seen[x] <= d:
                    continue
                seen[x] = d
                reachable.add(x)
                max_rule_depth = max(max_rule_depth, d)
                max_factor = max(max_factor, states[x].factor_count)
                for y, _ in adjacency.get(x, []):
                    dq.append((y, d+1))
            depth_by_root[r.name] = {
                "root_state_id": r.state_id,
                "reachable_state_count": len(reachable),
                "max_factor_depth": max_factor,
                "max_rule_depth": max_rule_depth,
            }

        # Full-expand expression: always choose EXPAND whenever available,
        # until the correction disappears. This is a diagnostic, not an
        # optimizer decision.
        def expand_expr(sid, coeff, memo_stack=None):
            memo_stack = memo_stack or set()
            if sid in memo_stack:
                raise RuntimeError("Cycle detected in expansion graph.")
            trs = [t for t in transitions if t.parent == sid]
            if not trs:
                return {sid: coeff}
            t = trs[0]
            out = defaultdict(float)
            stack2 = set(memo_stack)
            stack2.add(sid)
            for child, mult in t.children:
                for leaf, val in expand_expr(
                    child, coeff*mult, stack2
                ).items():
                    out[leaf] += val
            return dict(out)

        total = defaultdict(float)
        raw_root_expansions = {}
        for r in roots:
            ex = expand_expr(r.state_id, r.coefficient)
            raw_root_expansions[r.name] = ex
            for sid, c in ex.items():
                total[sid] += c

        total = {sid: c for sid, c in total.items() if abs(c) > 1e-12}
        full_expand_expression = {
            "per_root": raw_root_expansions,
            "canonical_leaf_coefficients": total,
            "canonical_leaf_count_after_cancellation": len(total),
            "raw_leaf_occurrence_count": sum(
                len(x) for x in raw_root_expansions.values()
            ),
            "naive_all_named_cuts_cell_upper_bound": sum(
                (len(SPLIT_CUTS)+1) ** s.factor_count
                for s in states.values()
            ),
            "note_on_cell_upper_bound": (
                "Pure Cartesian upper bound before ordering/feasibility; "
                "Stage 2 should use binary split disjunctions instead."
            ),
        }

        return Exploration(
            states=states,
            transitions=transitions,
            roots=roots,
            split_proposals=split_proposals,
            collision_groups=collision_groups,
            blocked_frontier=blocked,
            depth_by_root=depth_by_root,
            full_expand_expression=full_expand_expression,
        )
