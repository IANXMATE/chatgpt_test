#!/usr/bin/env python3
from __future__ import annotations
import argparse
from pathlib import Path

from proof_compiler.params import (
    ReferencePoint, ParameterDomain, parse_number
)
from proof_compiler.paper import build_root_certificate
from proof_compiler.explorer import ProofSpaceExplorer
from proof_compiler.v5_report import write_v5


def parser():
    p = argparse.ArgumentParser(
        description=(
            "Phase-1 compiler that compresses the weighted-sieve proof space "
            "into canonical signed resource flow + AND/OR hypergraph structure."
        )
    )
    p.add_argument("--a", default="1.9")
    p.add_argument("--alpha", default="4/53")
    p.add_argument("--beta", default="4/33")
    p.add_argument("--gamma", default="3/11")
    p.add_argument("--epsilon", default="1e-10")
    p.add_argument("--strict-margin", default="1e-9")
    p.add_argument("--max-states", type=int, default=200000)
    p.add_argument("--max-factor-depth", type=int, default=None)
    p.add_argument("--out", default="phase1_flow_output")
    return p


def main():
    args = parser().parse_args()

    ref = ReferencePoint(
        a=parse_number(args.a),
        alpha=parse_number(args.alpha),
        beta=parse_number(args.beta),
        gamma=parse_number(args.gamma),
        epsilon=parse_number(args.epsilon),
    )
    domain = ParameterDomain(
        strict_margin=parse_number(args.strict_margin)
    )

    root_states, roots = build_root_certificate()
    structural = ProofSpaceExplorer(
        parameter_domain=domain,
        max_states=args.max_states,
        max_factor_depth=args.max_factor_depth,
    ).explore(root_states, roots)

    write_v5(args.out, ref, domain, structural)

    summary = Path(args.out) / "summary.txt"
    print(summary.read_text(encoding="utf-8"))
    print(f"Detailed outputs written to: {Path(args.out).resolve()}")


if __name__ == "__main__":
    main()
