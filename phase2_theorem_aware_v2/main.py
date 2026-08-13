#!/usr/bin/env python3
from __future__ import annotations

# ======================================================================
# Default mathematical input
# Target is Proposition 1 + (2 - DELTA).
# ======================================================================
DELTA = 0.15
# ======================================================================

import argparse
import json
import os
from pathlib import Path
import sys
import time

from goldbach_phase2.io import Phase1Artifacts
from goldbach_phase2.model import Phase2Model
from goldbach_phase2.paper_replay import PaperReplay
from goldbach_phase2.theorem_aware_evaluator import (
    Parameters,
    TheoremAwarePaperPathEvaluator,
)
from goldbach_phase2.random_search import RandomTheoremAwareSearch
from goldbach_phase2.storage import write_success_record, storage_dir_for_script


HERE = Path(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_MANIFEST = HERE / "data" / "phase1_manifest_v5.json"
DEFAULT_FLOW = HERE / "data" / "flow_blueprint.json"

SAMPLES_PER_BATCH = 64
BASE_SEED = 260605224
REQUIRED_MARGIN_4D = 1e-5

LOWDIM_ORDER = 40
HIGHDIM_ORDER = 10
SIEVE_STEP = 2e-5
BUCHSTAB_STEP = 2e-5
NUMERIC_PAD_PER_G = 2e-6


def make_parser():
    p = argparse.ArgumentParser(
        description=(
            "Theorem-aware Li-Liu Section-5 evaluator. "
            "Parameters -> guards -> automatic splits -> dynamic F/f/w -> G1..G12."
        )
    )
    p.add_argument("--delta", type=float, default=DELTA)
    p.add_argument("--alpha", type=float)
    p.add_argument("--beta", type=float)
    p.add_argument("--gamma", type=float)
    p.add_argument("--epsilon", type=float, default=1e-10)

    p.add_argument("--manifest", default=str(DEFAULT_MANIFEST))
    p.add_argument("--flow", default=str(DEFAULT_FLOW))

    p.add_argument("--start-batch", type=int, default=1)
    p.add_argument("--max-batches", type=int, default=0,
                   help="0 = continue until Ctrl+C")
    p.add_argument("--samples-per-batch", type=int, default=SAMPLES_PER_BATCH)

    p.add_argument("--show-trace", action="store_true")
    p.add_argument("--paper-point", action="store_true",
                   help="Evaluate exactly alpha=4/53,beta=4/33,gamma=3/11,a=1.9")
    return p


def paper_chain(model):
    replay = PaperReplay(model, allow_g16_paper_bridge=True)
    replay.run()
    return [
        {"label": x.label, "coefficients": x.coefficients}
        for x in replay.stages
    ]


def print_result(ev, show_trace=False):
    print("PARAMETERS")
    for k in ("delta", "a", "alpha", "beta", "gamma", "epsilon", "tau"):
        print(f"  {k:>7s} = {ev.parameters[k]:.15g}")
    print()

    hard = ev.theorem_trace["hard_failures"]
    print("THEOREM GUARDS")
    if hard:
        print(f"  FAIL ({len(hard)} hard failures)")
    else:
        print("  PASS")
    for g in ev.theorem_trace["guards"]:
        status = "PASS" if g["passed"] else ("FAIL" if g["hard"] else "WARN")
        print(f"  [{status:4s}] {g['name']}: {g['expression']}")
        if not g["passed"] and g.get("note"):
            print(f"         {g['note']}")
    print()

    if not ev.valid:
        print("RESULT: INVALID FOR CURRENT REGISTERED PAPER-PATH ESTIMATORS")
        return

    print("AUTOMATIC SPLITS")
    for s in ev.theorem_trace["splits"]:
        print(f"  {s['target']}: {s['boundary']}")
        print(f"      left : {s['left_rule']}")
        print(f"      right: {s['right_rule']}")
    print()

    print("DYNAMIC G1..G12")
    for i in range(1, 13):
        name = f"G{i}"
        print(
            f"  {name:>3s}: bound={ev.bounds[name]: .10f}  "
            f"coef={ev.per_G[name]['coefficient']:+.0f}  "
            f"contribution={ev.contributions[name]: .10f}"
        )
    print("  " + "-"*54)
    print(f"  4D margin = {ev.margin_4D:+.12e}")
    print(f"   D margin = {ev.margin_D:+.12e}")
    print(f"  status    = {ev.status}")
    print()

    if show_trace:
        print("FULL THEOREM APPLICATION TRACE")
        print(json.dumps(ev.theorem_trace, ensure_ascii=False, indent=2))


def main():
    args = make_parser().parse_args()
    artifacts = Phase1Artifacts.load(args.manifest, args.flow)
    model = Phase2Model(artifacts)
    chain = paper_chain(model)

    evaluator = TheoremAwarePaperPathEvaluator(
        lowdim_order=LOWDIM_ORDER,
        highdim_order=HIGHDIM_ORDER,
        sieve_step=SIEVE_STEP,
        buchstab_step=BUCHSTAB_STEP,
        numeric_pad_per_G=NUMERIC_PAD_PER_G,
    )

    if args.paper_point:
        p = Parameters(
            a=1.9, alpha=4/53, beta=4/33, gamma=3/11,
            epsilon=args.epsilon
        )
        ev = evaluator.evaluate(p)
        print("PHASE-2 THEOREM-AWARE EVALUATOR V2 — PAPER POINT")
        print("="*88)
        print_result(ev, args.show_trace)
        return 0 if ev.valid else 1

    supplied = [args.alpha is not None, args.beta is not None, args.gamma is not None]
    if any(supplied):
        if not all(supplied):
            raise SystemExit("Direct mode requires --alpha, --beta and --gamma together.")
        p = Parameters(
            a=2.0-args.delta,
            alpha=args.alpha,
            beta=args.beta,
            gamma=args.gamma,
            epsilon=args.epsilon,
        )
        ev = evaluator.evaluate(p)
        print("PHASE-2 THEOREM-AWARE EVALUATOR V2 — DIRECT MODE")
        print("="*88)
        print_result(ev, args.show_trace)
        return 0 if ev.valid else 2

    # Random-search mode.
    print("PHASE-2 THEOREM-AWARE RANDOM SEARCH V2")
    print("="*88)
    print(f"target            = 1 + {2.0-args.delta:.12g}")
    print(f"delta             = {args.delta:.12g}")
    print(f"samples/batch     = {args.samples_per_batch}")
    print(f"storage           = {storage_dir_for_script(__file__)}")
    print(f"highdim G11/G12 q = {HIGHDIM_ORDER}")
    print()

    search = RandomTheoremAwareSearch(
        evaluator=evaluator,
        delta=args.delta,
        epsilon=args.epsilon,
        samples_per_batch=args.samples_per_batch,
        base_seed=BASE_SEED,
        required_margin_4D=REQUIRED_MARGIN_4D,
    )

    batch = args.start_batch
    done = 0
    best_all = None

    try:
        while args.max_batches == 0 or done < args.max_batches:
            t0 = time.perf_counter()
            out = search.run_batch(batch)
            dt = time.perf_counter()-t0
            best = out["best"]
            hit = out["success"]
            if best is not None and (best_all is None or best.score() > best_all.score()):
                best_all = best

            btxt = "NONE" if best is None else f"{best.score():+.8e}"
            print(
                f"batch={batch:06d} valid={out['valid_count']:3d}/"
                f"{args.samples_per_batch} best4D={btxt} time={dt:.2f}s"
            )

            if hit is not None:
                path = write_success_record(
                    script_file=__file__,
                    delta=args.delta,
                    hit=hit,
                    manifest_path=args.manifest,
                    flow_path=args.flow,
                    evaluator_settings=evaluator.settings,
                    certificate_chain=chain,
                    required_margin_4D=REQUIRED_MARGIN_4D,
                )
                pp = hit.params
                print(
                    f"  >>> SUCCESS M4={hit.evaluation.margin_4D:+.10e} "
                    f"alpha={pp.alpha:.12g} beta={pp.beta:.12g} "
                    f"gamma={pp.gamma:.12g}"
                )
                print(f"      stored: {path}")

            batch += 1
            done += 1

    except KeyboardInterrupt:
        print("\nSTOPPED BY USER")
        if best_all is not None:
            pp = best_all.params
            print(f"best4D={best_all.score():+.10e}")
            print(
                f"alpha={pp.alpha:.12g}, beta={pp.beta:.12g}, "
                f"gamma={pp.gamma:.12g}, tau={pp.tau:.12g}"
            )
    return 0


if __name__ == "__main__":
    sys.exit(main())
