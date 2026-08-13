#!/usr/bin/env python3
from __future__ import annotations

# ======================================================================
# Only mathematical target you normally need to edit:
# target = 1 + (2 - DELTA)
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
from goldbach_phase2.theorem_aware_evaluator import (
    Parameters,
    TheoremAwarePaperPathEvaluator,
)
from goldbach_phase2.flow140 import Flow140Model
from goldbach_phase2.flow140_search import RandomFlow140Search
from goldbach_phase2.storage_flow140 import (
    storage_dir_for_script,
    write_flow140_success,
)


HERE = Path(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_MANIFEST = HERE / "data" / "phase1_manifest_v5.json"
DEFAULT_FLOW = HERE / "data" / "flow_blueprint.json"

PARAMETER_SAMPLES_PER_BATCH = 12
FLOW_TRIALS_PER_PARAMETER = 16
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
            "Random search over theorem-aware alpha,beta,gamma AND all 140 "
            "Phase-1 rewrite preferences. Every scored flow satisfies exact "
            "signed conservation with unresolved=0."
        )
    )
    p.add_argument("--delta", type=float, default=DELTA)
    p.add_argument("--epsilon", type=float, default=1e-10)

    p.add_argument("--manifest", default=str(DEFAULT_MANIFEST))
    p.add_argument("--flow", default=str(DEFAULT_FLOW))

    p.add_argument("--start-batch", type=int, default=1)
    p.add_argument("--max-batches", type=int, default=0,
                   help="0 = run until Ctrl+C")
    p.add_argument("--parameter-samples", type=int,
                   default=PARAMETER_SAMPLES_PER_BATCH)
    p.add_argument("--flow-trials", type=int,
                   default=FLOW_TRIALS_PER_PARAMETER)

    p.add_argument("--paper-point", action="store_true",
                   help="Use a=1.9, alpha=4/53,beta=4/33,gamma=3/11.")
    p.add_argument("--exact-flow", action="store_true",
                   help=(
                       "At the selected paper/direct point, solve the pure "
                       "linear margin optimum instead of random preference."
                   ))
    p.add_argument("--diagnose-140", action="store_true",
                   help=(
                       "LP-check all 140 rewrites and print which can be "
                       "nonzero with current theorem registry + unresolved=0."
                   ))
    p.add_argument("--show-certificate", action="store_true")
    return p


def build(args):
    artifacts = Phase1Artifacts.load(args.manifest, args.flow)
    evaluator = TheoremAwarePaperPathEvaluator(
        lowdim_order=LOWDIM_ORDER,
        highdim_order=HIGHDIM_ORDER,
        sieve_step=SIEVE_STEP,
        buchstab_step=BUCHSTAB_STEP,
        numeric_pad_per_G=NUMERIC_PAD_PER_G,
    )
    flow_model = Flow140Model(
        artifacts.flow,
        allow_g16_paper_bridge=True,
        strict_unresolved=True,
    )
    return artifacts, evaluator, flow_model


def print_flow_solution(sol, title="FLOW RESULT"):
    print(title)
    print("-"*88)
    if not sol.success:
        print("  FAIL:", sol.message)
        return

    print(f"  4D-equivalent margin = {sol.margin_4D_equivalent:+.12e}")
    print(f"  D margin             = {sol.margin_D:+.12e}")
    print(f"  active rewrites      = {sol.active_rewrite_count}/140")
    print(f"  max unresolved       = {sol.max_unresolved:.3e}")
    print(f"  conservation residual= {sol.max_conservation_residual:.3e}")
    print("  source weights:")
    for k, v in sol.source_weights.items():
        print(f"    {k} = {v:.12g}")
    print("  effective 4D certificate:")
    print(
        "   ",
        " ".join(
            f"{sol.effective_G_coefficients_4D[f'G{i}']:+.6g}*G{i}"
            for i in range(1, 13)
            if abs(sol.effective_G_coefficients_4D[f'G{i}']) > 1e-10
        )
    )
    print()


def main():
    args = make_parser().parse_args()
    artifacts, evaluator, flow_model = build(args)

    print("PHASE-2 140-REWRITE RANDOM FLOW SEARCH V3")
    print("="*88)
    print(f"target                       = 1 + {2.0-args.delta:.12g}")
    print(f"delta                        = {args.delta:.12g}")
    print(f"declared rewrite dimensions  = {len(flow_model.rewrite_names)}")
    print(f"full flow variables           = {len(flow_model.original_names)} + 2 G16 bridges")
    print(f"conservation equalities       = {flow_model.A_eq.shape[0]}")
    print(f"strict unresolved             = 0")
    print(f"storage                       = {storage_dir_for_script(__file__)}")
    print()

    # This diagnosis is structural and parameter-independent inside the
    # current Proposition-4.3 regime.
    reachable, forced_zero = flow_model.certifiably_reachable_rewrites()
    print("CURRENT CERTIFIED 140-DIMENSION COVERAGE")
    print("-"*88)
    print(f"  rewrites that can be nonzero = {len(reachable)}/140")
    print(f"  forced zero by current theorem registry + unresolved=0 = {len(forced_zero)}/140")
    if reachable:
        for name, mx in reachable.items():
            print(f"    {name}: feasible max {mx:.12g}")
    print()

    if args.diagnose_140:
        print("FORCED-ZERO REWRITES")
        for name in forced_zero:
            print(" ", name)
        return 0

    if args.paper_point or args.exact_flow:
        p = Parameters(
            a=1.9 if args.paper_point else 2.0-args.delta,
            alpha=4/53,
            beta=4/33,
            gamma=3/11,
            epsilon=args.epsilon,
        )
        tev = evaluator.evaluate(p)
        if not tev.valid:
            print("Paper/direct theorem point invalid:")
            print(json.dumps(
                tev.theorem_trace["hard_failures"],
                ensure_ascii=False, indent=2
            ))
            return 2

        if args.exact_flow:
            sol = flow_model.solve(tev)
            print_flow_solution(sol, "EXACT LP FLOW OPTIMUM")
            return 0 if sol.success else 3

        # Paper point + randomized 140 preferences.
        rng = __import__("numpy").random.default_rng(BASE_SEED)
        best = None
        for trial in range(args.flow_trials):
            pref = rng.normal(size=140)
            temp = RandomFlow140Search.TEMPERATURES[
                trial % len(RandomFlow140Search.TEMPERATURES)
            ]
            sol = flow_model.solve(
                tev,
                preference_vector=pref,
                preference_temperature=temp,
            )
            if sol.success and (
                best is None
                or sol.margin_4D_equivalent > best.margin_4D_equivalent
            ):
                best = sol
        if best is None:
            print("No feasible randomized flow.")
            return 3
        print_flow_solution(best, "BEST RANDOMIZED PAPER-POINT FLOW")
        return 0

    search = RandomFlow140Search(
        evaluator=evaluator,
        flow_model=flow_model,
        delta=args.delta,
        epsilon=args.epsilon,
        parameter_samples_per_batch=args.parameter_samples,
        flow_trials_per_parameter=args.flow_trials,
        base_seed=BASE_SEED,
        required_margin_4D=REQUIRED_MARGIN_4D,
    )

    batch = int(args.start_batch)
    completed = 0
    global_best = None

    print("SEARCH STARTED — Ctrl+C stops cleanly.")
    print("-"*88)

    try:
        while args.max_batches == 0 or completed < args.max_batches:
            t0 = time.perf_counter()
            out = search.run_batch(batch)
            dt = time.perf_counter()-t0

            best = out["best"]
            success = out["success"]

            if best is not None and (
                global_best is None or best.score() > global_best.score()
            ):
                global_best = best

            best_text = "NONE" if best is None else f"{best.score():+.8e}"
            active_text = (
                "-"
                if best is None
                else f"{best.flow_solution.active_rewrite_count:3d}"
            )

            print(
                f"batch={batch:06d} "
                f"param_valid={out['theorem_valid_parameter_samples']:3d}/"
                f"{args.parameter_samples} "
                f"flow_feasible={out['feasible_flow_trials']:4d}/"
                f"{out['flow_trials']:4d} "
                f"best4D={best_text} "
                f"active={active_text}/140 "
                f"time={dt:.2f}s"
            )

            if success is not None:
                path = write_flow140_success(
                    script_file=__file__,
                    delta=args.delta,
                    hit=success,
                    manifest_path=args.manifest,
                    flow_path=args.flow,
                    evaluator_settings=evaluator.settings,
                    reachable_rewrite_count=len(reachable),
                    required_margin_4D=REQUIRED_MARGIN_4D,
                )
                pp = success.params
                ss = success.flow_solution
                print(
                    f"  >>> SUCCESS M4={ss.margin_4D_equivalent:+.10e} "
                    f"active={ss.active_rewrite_count}/140"
                )
                print(
                    f"      alpha={pp.alpha:.12g} "
                    f"beta={pp.beta:.12g} gamma={pp.gamma:.12g} "
                    f"tau={pp.tau:.12g}"
                )
                print(f"      stored: {path}")

                if args.show_certificate:
                    print(
                        "      cert:",
                        ss.effective_G_coefficients_4D
                    )

            batch += 1
            completed += 1

    except KeyboardInterrupt:
        print("\nSTOPPED BY USER")
        if global_best is not None:
            ss = global_best.flow_solution
            pp = global_best.params
            print(f"best4D={ss.margin_4D_equivalent:+.12e}")
            print(f"active rewrites={ss.active_rewrite_count}/140")
            print(
                f"alpha={pp.alpha:.12g}, beta={pp.beta:.12g}, "
                f"gamma={pp.gamma:.12g}, tau={pp.tau:.12g}"
            )
            print("effective certificate:")
            print(ss.effective_G_coefficients_4D)

    return 0


if __name__ == "__main__":
    sys.exit(main())
