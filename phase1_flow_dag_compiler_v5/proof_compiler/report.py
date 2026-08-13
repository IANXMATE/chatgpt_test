from __future__ import annotations
from pathlib import Path
from collections import Counter, defaultdict
import json

from .stage2 import build_stage2_blueprint


def _dump_json(path, obj):
    Path(path).write_text(
        json.dumps(obj, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )


def write_all(out_dir, reference, domain, exploration, special_rewrites):
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)

    states = [s.to_dict() for s in exploration.states.values()]
    transitions = [t.to_dict() for t in exploration.transitions]
    roots = [r.to_dict() for r in exploration.roots]
    blueprint = build_stage2_blueprint(exploration, special_rewrites)

    manifest = {
        "schema": "goldbach-phase1-proof-compiler-v3",
        "reference_point": reference.as_dict(),
        "parameter_domain_linear_reachability": domain.as_strings(),
        "root_certificate": roots,
        "states": states,
        "transitions": transitions,
        "split_proposals": exploration.split_proposals,
        "collision_groups": exploration.collision_groups,
        "blocked_frontier": exploration.blocked_frontier,
        "depth_by_root": exploration.depth_by_root,
        "full_expand_expression": exploration.full_expand_expression,
        "special_rewrites": special_rewrites,
        "stage2_blueprint": blueprint,
        "source_audit": {
            "primary_source": "arXiv:2606.05224v2",
            "paper_version_date": "2026-08-08 (v2); manuscript date 2026-08-11",
            "g16_shape_warning": (
                "(4.29)/(4.34) render A_{p1 p2}, while "
                "(4.35)/(4.36) use A_{p1 p2 p3}; not auto-normalized."
            ),
        },
    }

    _dump_json(out / "phase1_manifest.json", manifest)
    _dump_json(out / "stage2_blueprint.json", blueprint)
    _dump_json(out / "special_rewrites.json", special_rewrites)
    _dump_json(out / "full_expand_expression.json",
               exploration.full_expand_expression)

    with (out / "states.jsonl").open("w", encoding="utf-8") as f:
        for x in states:
            f.write(json.dumps(x, ensure_ascii=False) + "\n")
    with (out / "transitions.jsonl").open("w", encoding="utf-8") as f:
        for x in transitions:
            f.write(json.dumps(x, ensure_ascii=False) + "\n")
    with (out / "split_proposals.jsonl").open("w", encoding="utf-8") as f:
        for x in exploration.split_proposals:
            f.write(json.dumps(x, ensure_ascii=False) + "\n")
    with (out / "blocked_frontier.jsonl").open("w", encoding="utf-8") as f:
        for x in exploration.blocked_frontier:
            f.write(json.dumps(x, ensure_ascii=False) + "\n")

    # Text summary.
    lines = [
        "PHASE-1 PROOF COMPILER V3",
        "="*88,
        "",
        "REFERENCE POINT",
    ]
    for k, v in reference.as_dict().items():
        lines.append(f"  {k:>10s} = {v:.12g}")
    lines += [
        "",
        "GLOBAL COUNTS",
        f"  canonical states              = {len(states)}",
        f"  exact Buchstab transitions    = {len(transitions)}",
        f"  candidate region splits       = {len(exploration.split_proposals)}",
        f"  canonical collision groups    = {len(exploration.collision_groups)}",
        f"  blocked/frontier records      = {len(exploration.blocked_frontier)}",
        f"  full-expand raw leaf terms    = "
        f"{exploration.full_expand_expression['raw_leaf_occurrence_count']}",
        f"  full-expand canonical leaves  = "
        f"{exploration.full_expand_expression['canonical_leaf_count_after_cancellation']}",
        f"  naive all-cut cell upper bound= "
        f"{exploration.full_expand_expression['naive_all_named_cuts_cell_upper_bound']}",
        "",
        "STAGE-2 VARIABLE BLUEPRINT",
    ]
    for k, v in blueprint["counts"].items():
        lines.append(f"  {k:>34s} = {v}")

    lines += ["", "DEPTH BY PAPER ROOT"]
    for name, d in exploration.depth_by_root.items():
        lines.append(
            f"  {name:>4s}: reachable={d['reachable_state_count']:3d}, "
            f"max-factor={d['max_factor_depth']:2d}, "
            f"max-rule-depth={d['max_rule_depth']:2d}"
        )

    lines += [
        "",
        "IMPORTANT",
        "  Max depth above is explored over the ENTIRE linear Proposition 4.3",
        "  parameter domain, not only alpha=4/53,beta=4/33,gamma=3/11.",
        "",
        "  Region splits are recorded as exact split proposals rather than",
        "  materializing their full Cartesian product. This preserves the full",
        "  Stage-2 search space without creating millions of redundant Phase-1",
        "  nodes. Stage 2 can introduce one binary variable per proposal.",
        "",
        "SOURCE AUDIT WARNING",
        "  arXiv v2 (4.29)/(4.34) displays A_{p1 p2}, whereas the closing",
        "  comparison (4.35)/(4.36) uses A_{p1 p2 p3}. The compiler records",
        "  this as a blocked source-shape ambiguity and never fixes it silently.",
    ]
    (out / "summary.txt").write_text("\n".join(lines)+"\n",
                                     encoding="utf-8")

    # Detailed Markdown.
    md = [
        "# Phase-1 proof-space exploration",
        "",
        "## What this file means",
        "",
        "This is the complete Stage-1 structural manifest. It does not optimize "
        "parameters and it does not invent analytic bounds. It enumerates all "
        "states reachable by the registered exact Buchstab grammar over the "
        "whole Proposition 4.3 linear parameter domain, then records every "
        "possible named region split and every known terminal estimator.",
        "",
        "## Root certificate",
        "",
        r"\[4D\ge 3G_1+G_2-4G_3-G_4-G_5+G_6+G_7"
        r"-2G_8-G_9-G_{10}-G_{11}-G_{12}+O(N^{1-\alpha}).\]",
        "",
        "## Depth map",
        "",
        "| root | reachable canonical states | max factor depth | rule depth |",
        "|---|---:|---:|---:|",
    ]
    for name, d in exploration.depth_by_root.items():
        md.append(
            f"| {name} | {d['reachable_state_count']} | "
            f"{d['max_factor_depth']} | {d['max_rule_depth']} |"
        )

    md += [
        "",
        "## Search-space counts",
        "",
        f"- canonical states: **{len(states)}**",
        f"- exact Buchstab transitions: **{len(transitions)}**",
        f"- candidate region splits: **{len(exploration.split_proposals)}**",
        f"- collision/cancellation groups: **{len(exploration.collision_groups)}**",
        f"- full-expand canonical leaves: "
        f"**{exploration.full_expand_expression['canonical_leaf_count_after_cancellation']}**",
        "",
        "## Collision groups",
        "",
    ]
    if not exploration.collision_groups:
        md.append("No nontrivial canonical collisions found.")
    for g in exploration.collision_groups:
        md.append(f"### `{g['state_id']}`")
        md.append(f"- aliases: `{g['paper_aliases']}`")
        md.append(f"- incoming contexts: `{len(g['incoming'])}`")
        md.append("")

    md += [
        "## Special paper rewrite",
        "",
        "The compiler retains equations (4.31)-(4.36) as an additional legal "
        "multi-state rewrite. It is not conflated with ordinary single-state "
        "Buchstab expansion.",
        "",
        "## Stage-2 contract",
        "",
        "Read `stage2_blueprint.json`. Every expandable state receives a "
        "STOP/EXPAND binary variable; every terminal estimator receives an "
        "estimator-choice binary; every meaningful named cut receives a "
        "region-split binary. Identical canonical states share one state ID, "
        "so coefficients must be aggregated before evaluating the final margin.",
        "",
        "## Safety boundary",
        "",
        "A structural path being present here does **not** imply that it has a "
        "useful certified upper/lower bound. Leaves tagged "
        "`high_dimensional_terminal_needs_certification` are exactly where "
        "Stage 2 or new number theory must supply one.",
    ]
    (out / "exploration_report.md").write_text(
        "\n".join(md)+"\n", encoding="utf-8"
    )

    return manifest
