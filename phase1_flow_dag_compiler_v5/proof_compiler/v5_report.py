from __future__ import annotations
from pathlib import Path
import json

from .flow_model import build_flow_blueprint
from .chain_analysis import analyze_unique_rewrite_chains
from .conflict_analysis import analyze_bundle_conflicts
from .lazy_boundaries import generate_lazy_boundaries
from .paper_flow import build_reference_final_certificate, build_verification_bridges
from .regime_model import build_regime_templates


def dump(path, obj):
    Path(path).write_text(
        json.dumps(obj, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )


def write_v5(out_dir, reference, domain, exploration):
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)

    flow = build_flow_blueprint(
        exploration.states, exploration.transitions
    )
    chains = analyze_unique_rewrite_chains(
        exploration.states, exploration.transitions
    )
    conflicts = analyze_bundle_conflicts(flow["bundle_rules"])
    boundaries = generate_lazy_boundaries(exploration.states)
    regimes = build_regime_templates()

    # Count true combinatorial variables conservatively.
    source_mix_cont = sum(
        1 for v in flow["flow_variables"]
        if v["kind"] == "SOURCE_MIX_WEIGHT"
    )
    rewrite_cont = sum(
        1 for v in flow["flow_variables"]
        if v["kind"] == "REWRITE_ALLOCATION"
    )
    terminal_cont = sum(
        1 for v in flow["flow_variables"]
        if v["kind"] == "TERMINAL_ALLOCATION"
    )
    cancel_cont = sum(
        1 for v in flow["flow_variables"]
        if v["kind"] == "EXACT_CANCELLATION"
    )
    bundle_cont = sum(
        1 for v in flow["flow_variables"]
        if v["kind"] == "BUNDLE_USE"
    )
    unresolved = sum(
        1 for v in flow["flow_variables"]
        if v["kind"] == "UNRESOLVED_FRONTIER"
    )
    regime_binary = sum(
        1 for key, x in regimes.items()
        if x.get("discrete_regime_binary_needed")
        and "outside_current" not in key.lower()
        and key == "current_unconditional_1p9"
    )

    stats = {
        "canonical_structural_states": len(exploration.states),
        "exact_structural_transitions": len(exploration.transitions),
        "continuous_source_mix_variables": source_mix_cont,
        "continuous_rewrite_allocations": rewrite_cont,
        "continuous_terminal_allocations": terminal_cont,
        "continuous_cancellation_variables": cancel_cont,
        "continuous_bundle_usage_variables": bundle_cont,
        "diagnostic_unresolved_frontier_variables": unresolved,
        "lazy_theorem_boundaries": len(boundaries),
        "crossing_multi_resource_conflicts": conflicts["crossing_count"],
        "active_regime_binary_variables_current_1p9": regime_binary,
        "key_conclusion": (
            "Most proof-structure choices are continuous resource-flow "
            "allocations, not binary path choices."
        ),
    }

    manifest = {
        "schema": "goldbach-phase1-flow-dag-v5",
        "reference_point": reference.as_dict(),
        "parameter_domain": domain.as_strings(),
        "structural_states": [
            s.to_dict() for s in exploration.states.values()
        ],
        "structural_transitions": [
            t.to_dict() for t in exploration.transitions
        ],
        "depth_by_root": exploration.depth_by_root,
        "flow_blueprint": flow,
        "chain_analysis": chains,
        "bundle_conflict_analysis": conflicts,
        "lazy_theorem_boundaries": boundaries,
        "regime_templates": regimes,
        "reference_final_certificate": build_reference_final_certificate(),
        "disabled_verification_bridges": build_verification_bridges(),
        "stats": stats,
        "certification_policy": {
            "unresolved_frontier": "must equal 0 in a certified Stage-2 solve",
            "g16_source_shape_warning": (
                "paper_closure_4_31_4_36 cannot be treated as machine-certified "
                "until the G16 A_{p1p2} / A_{p1p2p3} source mismatch is resolved."
            ),
            "switching_sign_policy": (
                "switching-based terminal estimators are upper-bound only and "
                "therefore attach to NEG signed resources in a lower-bound certificate."
            ),
        },
    }

    dump(out / "phase1_manifest_v5.json", manifest)
    dump(out / "flow_blueprint.json", flow)
    dump(out / "chain_analysis.json", chains)
    dump(out / "bundle_conflicts.json", conflicts)
    dump(out / "lazy_boundaries.json", boundaries)
    dump(out / "regime_templates.json", regimes)

    # Human-readable equations and summary.
    with (out / "flow_conservation.txt").open("w", encoding="utf-8") as f:
        f.write("SOURCE NORMALIZATION\n")
        f.write(flow["source_normalization"]["equation"] + "\n\n")
        f.write("SIGNED RESOURCE CONSERVATION\n")
        f.write("="*100 + "\n")
        for eq in flow["conservation_equations"]:
            f.write(f"{eq['signed_node']}: {eq['equation']}\n")

    lines = [
        "PHASE-1 FLOW / AND-OR-DAG COMPILER V5",
        "="*96,
        "",
        "WHY THIS VERSION IS DIFFERENT",
        "  Linear identities are represented as continuous coefficient flow.",
        "  They do NOT create one binary variable per proof-path decision.",
        "  Exact canonical cancellation is also a continuous local operation.",
        "  Only true regime disjunctions or crossing multi-resource rewrites",
        "  form the combinatorial/MILP core.",
        "",
        "STRUCTURAL GRAPH",
        f"  canonical states                  = {len(exploration.states)}",
        f"  exact Buchstab transitions        = {len(exploration.transitions)}",
        f"  continuation chains               = {len(chains['chains'])}",
        f"  lazy theorem boundaries           = {len(boundaries)}",
        "",
        "FLOW VARIABLES",
        f"  source mixture                    = {source_mix_cont}",
        f"  rewrite allocations               = {rewrite_cont}",
        f"  terminal allocations              = {terminal_cont}",
        f"  exact cancellation                = {cancel_cont}",
        f"  bundle usage                      = {bundle_cont}",
        f"  unresolved diagnostic             = {unresolved}",
        "",
        "TRUE COMBINATORIAL CORE",
        f"  crossing bundle conflicts         = {conflicts['crossing_count']}",
        f"  active 1.9 regime binaries        = {regime_binary}",
        "",
        "PAPER-DRIVEN DESIGN FACTS",
        "  * (4.19) and (4.20) are valid lower-bound certificates. Their",
        "    nonnegative mixture is modeled continuously; the paper used their sum.",
        "  * The paper expands one of two G2 copies. V5 generalizes that to a",
        "    continuous allocation of the G2 coefficient through the identity.",
        "  * Switching is upper-bound only, so sign determines terminal eligibility.",
        "  * S6 positive lower-bound weakness is represented as proof pressure:",
        "    either take the trivial X>=0 sink or use a legal structural bundle.",
        "  * theorem-induced split boundaries are lazy; they are materialized only",
        "    when a theorem whose applicability changes across the region is used.",
        "",
        "STRICT CERTIFICATION WARNING",
        "  The paper's G16 sequence shape changes between (4.29)/(4.34) and",
        "  (4.35)/(4.36). The corresponding multi-resource closure remains",
        "  flagged for source verification instead of being silently accepted.",
    ]
    (out / "summary.txt").write_text(
        "\n".join(lines) + "\n", encoding="utf-8"
    )

    return manifest
