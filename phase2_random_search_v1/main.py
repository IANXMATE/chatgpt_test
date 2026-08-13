#!/usr/bin/env python3
from __future__ import annotations

# ======================================================================
# ONLY REQUIRED USER INPUT
# ======================================================================
# Proposition target: 1 + (2 - DELTA)
#
# Examples:
#   DELTA = 0.10  -> 1 + 1.90
#   DELTA = 0.105 -> 1 + 1.895
#
DELTA = 0.1
# ======================================================================

import argparse
import os
from pathlib import Path
import signal
import sys
import time

from goldbach_phase2.io import Phase1Artifacts
from goldbach_phase2.model import Phase2Model
from goldbach_phase2.paper_replay import PaperReplay
from goldbach_phase2.dynamic_bounds import (
    DynamicParameters,
    PaperPathDynamicEvaluator,
)
from goldbach_phase2.random_search import RandomPaperPathSearch
from goldbach_phase2.storage import write_success_record, storage_dir_for_script


# Search defaults.  DELTA is the only mathematically required input.
SAMPLES_PER_BATCH = 256
BASE_SEED = 260605224

# Any fixed positive asymptotic coefficient is enough for candidate discovery.
# We require a small positive safety distance from zero to reduce pure
# floating-point edge hits.  This is 4D's normalized coefficient.
REQUIRED_MARGIN_4D = 1.0e-5

# Numerical search resolution.
QUADRATURE_ORDER = 40
LINEAR_SIEVE_GRID_STEP = 2.0e-5
NUMERIC_BOUND_PAD_PER_G = 2.0e-6

# 0 means run until Ctrl+C.
MAX_BATCHES = 1000

HERE = Path(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_MANIFEST = HERE / "data" / "phase1_manifest_v5.json"
DEFAULT_FLOW = HERE / "data" / "flow_blueprint.json"


def parser():
    p = argparse.ArgumentParser(
        description=(
            "Randomly search paper-path parameters for Proposition "
            "1+(2-delta). Successful numerical candidates are stored next "
            "to this script under storage/."
        )
    )
    p.add_argument(
        "--delta", type=float, default=DELTA,
        help="Target delta in 1+(2-delta). This is the only required input."
    )
    p.add_argument(
        "--manifest", default=str(DEFAULT_MANIFEST),
        help="Phase-1 manifest; defaults to packaged data."
    )
    p.add_argument(
        "--flow", default=str(DEFAULT_FLOW),
        help="Phase-1 flow blueprint; defaults to packaged data."
    )
    p.add_argument(
        "--start-batch", type=int, default=1,
        help="Start batch index; useful for deterministic resume."
    )
    p.add_argument(
        "--max-batches", type=int, default=MAX_BATCHES,
        help="0 = run until Ctrl+C."
    )
    return p


def get_paper_chain(model):
    replay = PaperReplay(model, allow_g16_paper_bridge=True)
    replay.run()
    return [
        {
            "label": stage.label,
            "coefficients": stage.coefficients,
        }
        for stage in replay.stages
    ]


def print_reference_calibration(evaluator):
    p = DynamicParameters(
        a=1.9,
        alpha=4/53,
        beta=4/33,
        gamma=3/11,
        epsilon=1e-10,
    )
    ev = evaluator.evaluate(p)

    print("REFERENCE CALIBRATION (dynamic numerical evaluator)")
    print("-" * 88)
    if not ev.valid:
        print("  FAILED:", "; ".join(ev.failure_reasons))
        return

    published = {
        "G1": 14.87710, "G2": 9.11587, "G3": 0.84289,
        "G4": 23.60636, "G5": 19.51976, "G6": 1.63357,
        "G7": 3.79029, "G8": 0.60962, "G9": 5.27231,
        "G10": 5.40996, "G11": 0.10191, "G12": 0.66821,
    }
    raw = ev.diagnostics["raw_unpadded_bounds"]
    for name in [f"G{i}" for i in range(1, 13)]:
        print(
            f"  {name:>3s}: dynamic={raw[name]:.8f} "
            f"paper-rounded={published[name]:.8f} "
            f"diff={raw[name]-published[name]:+.3e}"
        )
    print(f"  padded dynamic 4D margin = {ev.margin_4D:.10f}")
    print()


def main():
    args = parser().parse_args()
    delta = float(args.delta)
    a = 2.0 - delta

    artifacts = Phase1Artifacts.load(args.manifest, args.flow)
    model = Phase2Model(artifacts)
    certificate_chain = get_paper_chain(model)

    print("PHASE-2 RANDOM PAPER-PATH SEARCH V1")
    print("=" * 88)
    print(f"target          : 1 + {a:.12g}")
    print(f"delta           : {delta:.12g}")
    print(f"samples/batch   : {SAMPLES_PER_BATCH}")
    print(f"required 4D M   : {REQUIRED_MARGIN_4D:.3g}")
    print(f"base seed       : {BASE_SEED}")
    print(f"script dir      : {HERE}")
    print(f"storage dir     : {storage_dir_for_script(__file__)}")
    print()

    evaluator = PaperPathDynamicEvaluator(
        quadrature_order=QUADRATURE_ORDER,
        sieve_step=LINEAR_SIEVE_GRID_STEP,
        numeric_bound_pad=NUMERIC_BOUND_PAD_PER_G,
    )

    # A startup self-calibration against the paper point catches broken
    # numerical plumbing before the random loop starts.
    print_reference_calibration(evaluator)

    search = RandomPaperPathSearch(
        evaluator=evaluator,
        delta=delta,
        samples_per_batch=SAMPLES_PER_BATCH,
        base_seed=BASE_SEED,
        required_margin_4D=REQUIRED_MARGIN_4D,
    )

    batch = int(args.start_batch)
    completed = 0
    global_best = None

    print("SEARCH STARTED — Ctrl+C stops cleanly.")
    print("-" * 88)

    try:
        while args.max_batches == 0 or completed < args.max_batches:
            t0 = time.perf_counter()
            result = search.run_batch(batch)
            elapsed = time.perf_counter() - t0

            best = result["best"]
            success = result["success"]

            if best is not None and (
                global_best is None or best.score() > global_best.score()
            ):
                global_best = best

            best_text = (
                f"{best.evaluation.margin_4D:+.8e}"
                if best is not None else "NO_VALID_SAMPLE"
            )
            print(
                f"batch={batch:06d} "
                f"valid={result['valid_count']:3d}/{SAMPLES_PER_BATCH} "
                f"best4D={best_text} "
                f"time={elapsed:.2f}s"
            )

            if success is not None:
                path = write_success_record(
                    script_file=__file__,
                    delta=delta,
                    hit=success,
                    manifest_path=args.manifest,
                    flow_path=args.flow,
                    evaluator_settings=evaluator.settings,
                    certificate_chain=certificate_chain,
                    required_margin_4D=REQUIRED_MARGIN_4D,
                )
                p = success.params
                print(
                    "  >>> SUCCESS "
                    f"M4={success.evaluation.margin_4D:+.10e} "
                    f"MD={success.evaluation.margin_D:+.10e}"
                )
                print(
                    "      "
                    f"alpha={p.alpha:.12g} "
                    f"beta={p.beta:.12g} "
                    f"gamma={p.gamma:.12g} "
                    f"tau={p.tau:.12g}"
                )
                print(f"      stored: {path}")

            batch += 1
            completed += 1

    except KeyboardInterrupt:
        print()
        print("STOPPED BY USER")
        if global_best is not None:
            p = global_best.params
            print(
                f"best observed 4D margin = "
                f"{global_best.evaluation.margin_4D:+.10e}"
            )
            print(
                f"alpha={p.alpha:.12g}, beta={p.beta:.12g}, "
                f"gamma={p.gamma:.12g}, tau={p.tau:.12g}"
            )
        return 0

    return 0


if __name__ == "__main__":
    sys.exit(main())
