#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path
import sys

from goldbach_phase2.io import Phase1Artifacts
from goldbach_phase2.model import Phase2Model
from goldbach_phase2.replay_validator import validate_paper_replay


HERE = Path(__file__).resolve().parent


def parser():
    p = argparse.ArgumentParser(
        description=(
            "Replay the Li-Liu 1+1.9 paper path through the Phase-1 "
            "flow/DAG structure and verify Proposition 4.3 + equation (5.51)."
        )
    )
    p.add_argument(
        "--manifest",
        default=str(HERE / "data" / "phase1_manifest_v5.json"),
    )
    p.add_argument(
        "--flow",
        default=str(HERE / "data" / "flow_blueprint.json"),
    )
    p.add_argument(
        "--strict-g16",
        action="store_true",
        help=(
            "Do not bridge the arXiv-v2 G16 sequence-shape mismatch. "
            "This intentionally stops the replay before the final closure."
        ),
    )
    p.add_argument(
        "--show-stages",
        action="store_true",
        help="Print every intermediate certificate ledger."
    )
    return p


def fmt_terms(d):
    def key(item):
        name = item[0]
        if name.startswith("G") and name[1:].isdigit():
            return (0, int(name[1:]))
        return (1, name)
    parts = []
    for name, coeff in sorted(d.items(), key=key):
        parts.append(f"{coeff:+g}*{name}")
    return " ".join(parts)


def main():
    args = parser().parse_args()

    artifacts = Phase1Artifacts.load(args.manifest, args.flow)
    model = Phase2Model(artifacts)

    try:
        report, replay, contributions = validate_paper_replay(
            model,
            allow_g16_paper_bridge=not args.strict_g16,
        )
    except RuntimeError as exc:
        print("PAPER REPLAY STOPPED")
        print("=" * 88)
        print(str(exc))
        print()
        print(
            "This is expected in --strict-g16 mode because Phase 1 "
            "deliberately refuses to identify the two displayed G16 shapes."
        )
        return 2

    p = model.reference_parameters

    print("PHASE-2 PAPER REPLAY")
    print("=" * 88)
    print("Inputs")
    print(f"  manifest = {Path(args.manifest).resolve()}")
    print(f"  flow     = {Path(args.flow).resolve()}")
    print()
    print("Reference parameters")
    print(f"  a       = {p.a}")
    print(f"  alpha   = {p.alpha:.15g}")
    print(f"  beta    = {p.beta:.15g}")
    print(f"  gamma   = {p.gamma:.15g}")
    print(f"  epsilon = {p.epsilon:.3g}")
    print(f"  tau     = {p.tau:.15g}")
    print()

    print("Validation")
    print(
        f"  [{'PASS' if report.parameter_constraints_pass else 'FAIL'}] "
        "Proposition 4.3 parameter constraints"
    )
    print(
        f"  [{'PASS' if report.structure_pass else 'FAIL'}] "
        "Phase-1 flow/rewrite structure reproduces the 12-term certificate"
    )
    print(
        f"  [{'PASS' if report.arithmetic_pass else 'FAIL'}] "
        "Section-5 rounded bounds reproduce equation (5.51)"
    )
    print(
        f"  [{'PASS' if report.theorem_threshold_pass else 'FAIL'}] "
        "D_{1,1.9} coefficient exceeds the theorem's 0.0004 threshold"
    )
    print()

    final_named = replay.stages[-1].coefficients
    print("Replayed Proposition 4.3 coefficient vector")
    print(" ", fmt_terms(final_named))
    print()

    print("Equation (5.51) contributions")
    order = [f"G{i}" for i in range(1, 13)]
    for name in order:
        if name in contributions:
            print(f"  {name:>3s}: {contributions[name]: .8f}")
    print("  " + "-" * 28)
    print(f"  4D margin = {report.margin_4D:.12f}")
    print(f"   D margin = {report.margin_D:.12f}")
    print(f"  theorem threshold = {report.paper_threshold_D:.7f}")
    print()

    if report.g16_warning:
        print("SOURCE-AUDIT WARNING")
        print(
            "  Replay used the paper's intended G16 closure bridge. "
            "Phase 1 records that arXiv v2 displays A_{p1p2} in "
            "(4.29)/(4.34) but A_{p1p2p3} in (4.35)/(4.36)."
        )
        print(
            "  Therefore PASS means: the Phase-2 model reproduces the "
            "paper's stated proof path and arithmetic; it is not an "
            "independent resolution of that source-shape discrepancy."
        )
        print()

    if args.show_stages:
        print("Intermediate certificate stages")
        print("-" * 88)
        for stage in replay.stages:
            print(stage.label)
            print(" ", fmt_terms(stage.coefficients))
            print()

    if report.messages:
        print("Diagnostics")
        for msg in report.messages:
            print("  *", msg)
        print()

    if report.passed:
        print("RESULT: PASS")
        print(
            "The uploaded Phase-1 structure reproduces the paper's "
            "Proposition 4.3 certificate and the published 0.00172 "
            "four-D margin (hence 0.00043 for D > 0.0004)."
        )
        return 0

    print("RESULT: FAIL")
    return 1


if __name__ == "__main__":
    sys.exit(main())
