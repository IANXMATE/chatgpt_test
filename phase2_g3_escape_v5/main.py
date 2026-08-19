#!/usr/bin/env python3
from __future__ import annotations

# ======================================================================
# Research target.  0.10 = 1+1.9, 0.106 = 1+1.894, 0.11 = 1+1.89.
# ======================================================================
DELTA = 0.11
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
from goldbach_phase2.frontier_compiler import FrontierTheoremCompiler
from goldbach_phase2.g3_escape import G3EscapeAnalyzer
from goldbach_phase2.g3_search import RandomG3TargetSearch
from goldbach_phase2.storage_g3 import (
    storage_dir_for_script,
    write_g3_target_record,
)


HERE = Path(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_MANIFEST = HERE / "data" / "phase1_manifest_v5.json"
DEFAULT_FLOW = HERE / "data" / "flow_blueprint.json"

LOWDIM_ORDER = 40
HIGHDIM_ORDER = 10
SIEVE_STEP = 2e-5
BUCHSTAB_STEP = 2e-5
NUMERIC_PAD_PER_G = 2e-6

MAX_FACTOR_COUNT = 6
QMC_POWER = 14
QMC_SCRAMBLES = 2
QMC_RELATIVE_PAD = 0.03
QMC_ABSOLUTE_PAD = 1e-7

SAMPLES_PER_BATCH = 24
BASE_SEED = 260605224


def parser():
    p = argparse.ArgumentParser(
        description=(
            "G3 Escape Analyzer V5. It disables the paper G3 terminal, "
            "forces the exact Phase-1 G3 Buchstab route, identifies the "
            "first blocker, and searches the critical hypothetical upper "
            "constant required for that blocker."
        )
    )
    p.add_argument("--delta", type=float, default=DELTA)
    p.add_argument("--epsilon", type=float, default=1e-10)
    p.add_argument("--manifest", default=str(DEFAULT_MANIFEST))
    p.add_argument("--flow", default=str(DEFAULT_FLOW))

    p.add_argument("--paper-point", action="store_true")
    p.add_argument("--alpha", type=float)
    p.add_argument("--beta", type=float)
    p.add_argument("--gamma", type=float)

    p.add_argument("--report", action="store_true")
    p.add_argument("--pareto", action="store_true")
    p.add_argument("--hypothetical-base-upper", type=float)

    p.add_argument("--target-margin-4d", type=float, default=0.0)
    p.add_argument("--upper-cap", type=float, default=5.0)

    p.add_argument("--search", action="store_true")
    p.add_argument("--start-batch", type=int, default=1)
    p.add_argument("--max-batches", type=int, default=0)
    p.add_argument("--samples-per-batch", type=int, default=SAMPLES_PER_BATCH)

    p.add_argument("--qmc-power", type=int, default=QMC_POWER)
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
    compiler = FrontierTheoremCompiler(
        manifest=artifacts.manifest,
        flow_blueprint=artifacts.flow,
        sieve_functions=evaluator.sieve,
        buchstab_function=evaluator.buchstab,
        max_factor_count=MAX_FACTOR_COUNT,
        qmc_power=args.qmc_power,
        qmc_scrambles=QMC_SCRAMBLES,
        qmc_relative_pad=QMC_RELATIVE_PAD,
        qmc_absolute_pad=QMC_ABSOLUTE_PAD,
    )
    analyzer = G3EscapeAnalyzer(
        artifacts.manifest,
        artifacts.flow,
    )
    return artifacts, evaluator, compiler, analyzer


def fixed_params(args):
    if args.paper_point:
        return Parameters(
            a=1.9,
            alpha=4/53,
            beta=4/33,
            gamma=3/11,
            epsilon=args.epsilon,
        )
    supplied = [
        args.alpha is not None,
        args.beta is not None,
        args.gamma is not None,
    ]
    if any(supplied):
        if not all(supplied):
            raise SystemExit("--alpha --beta --gamma must be supplied together")
        return Parameters(
            a=2-args.delta,
            alpha=args.alpha,
            beta=args.beta,
            gamma=args.gamma,
            epsilon=args.epsilon,
        )
    return None


def print_structure(analyzer):
    s = analyzer.structure
    print("G3 EXACT STRUCTURAL ROUTE")
    print("-"*92)
    print(f"  G3 state             = {s.state_id}")
    print(f"  direct paper upper   = {s.direct_upper_terminal}")
    print(f"  NEG rewrite          = {s.neg_rewrite}")
    print(f"  base child           = {s.base_state}")
    print(f"  correction children  = {s.correction_states}")
    print(f"  NEG base blocker var = {s.base_unresolved_variable}")
    print()
    print("  exact identity:")
    print("      G3 = BASE - CORRECTION")
    print("     -G3 = -BASE + CORRECTION")
    print("  therefore positive CORRECTION may be discarded; BASE is the first")
    print("  upper-bound theorem target.")
    print()


def run_report(p, evaluator, compiler, analyzer, args):
    tev = evaluator.evaluate(p)
    if not tev.valid:
        print("INVALID PARAMETERS")
        print(json.dumps(
            tev.theorem_trace["hard_failures"],
            ensure_ascii=False, indent=2
        ))
        return 2

    cres = compiler.compile(p)

    print("PARAMETERS")
    print(
        f"  delta={p.delta:.12g} a={p.a:.12g} "
        f"alpha={p.alpha:.12g} beta={p.beta:.12g} "
        f"gamma={p.gamma:.12g} tau={p.tau:.12g}"
    )
    print()
    print_structure(analyzer)

    base = analyzer.baseline(tev, cres.terminals)
    print("BASELINE — PAPER G3 TERMINAL ALLOWED")
    print("-"*92)
    print(f"  margin4D          = {base.margin_4D:+.12e}")
    print(f"  direct G3 coeff   = {base.direct_g3_coefficient_4D:+.8g}")
    print(f"  G3 rewrite flow   = {base.g3_rewrite_flow:.8g}")
    print()

    strict = analyzer.strict_without_direct_g3(
        tev, cres.terminals
    )
    print("STRICT ESCAPE — PAPER G3 TERMINAL DISABLED")
    print("-"*92)
    print(f"  feasible = {strict.success}")
    if strict.success:
        print(f"  margin4D = {strict.margin_4D:+.12e}")
    else:
        print(f"  solver   = {strict.message}")
    print()

    relaxed, blockers = analyzer.first_blockers(
        tev, cres.terminals
    )
    print("FIRST BLOCKER ANALYSIS")
    print("-"*92)
    if not relaxed.success:
        print("  relaxed diagnostic flow is infeasible:", relaxed.message)
    elif not blockers:
        print("  no genuine unresolved blocker was required.")
    else:
        for i, row in enumerate(blockers[:20], 1):
            s = row["state"]
            print(
                f"  {i:2d}. flow={row['flow']:.8g} "
                f"resource={row['resource']}"
            )
            if s:
                print(
                    f"      factors={s['factor_count']} "
                    f"sieve_set={s['sieve_set']} "
                    f"threshold={s['threshold']} "
                    f"oracles={s['analytic_oracles']}"
                )
                print(
                    f"      region={s['region']['inequalities']}"
                )
    print()

    crit = analyzer.critical_base_upper(
        tev,
        cres.terminals,
        target_margin_4D=args.target_margin_4d,
        upper_search_cap=args.upper_cap,
    )
    print("HYPOTHETICAL G3-BASE THEOREM TARGET")
    print("-"*92)
    print(f"  target margin4D            = {args.target_margin_4d:+.8g}")
    print(f"  direct paper G3 bound      = {crit.baseline_direct_g3_bound:.12g}")
    if crit.critical_upper is None:
        print("  critical base upper        = NONE")
        print(f"  reason                     = {crit.note}")
    else:
        print(f"  critical base upper Ucrit  = {crit.critical_upper:.12g}")
        print(
            f"  Ucrit / direct-G3-bound    = "
            f"{crit.ratio_to_direct_g3_bound:.8g}"
        )
        print(f"  margin4D at U=0            = {crit.margin_at_zero:+.12e}")
        print(f"  margin4D near Ucrit        = {crit.margin_at_critical:+.12e}")
        print()
        print(
            "  INTERPRETATION: if one could rigorously prove\n"
            "      BASE <= U * C(N)N/log^2 N\n"
            f"  with U <= {crit.critical_upper:.12g}, then this exact G3 escape\n"
            "  route would meet the requested margin. V5 does NOT prove such\n"
            "  a bound; it only computes the theorem target."
        )
    print()

    if args.hypothetical_base_upper is not None:
        sol = analyzer.solve_with_hypothetical_base(
            tev,
            cres.terminals,
            args.hypothetical_base_upper,
            disable_direct_g3=True,
        )
        print("USER-SUPPLIED HYPOTHETICAL BASE UPPER")
        print("-"*92)
        print(f"  U={args.hypothetical_base_upper:.12g}")
        print(f"  feasible={sol.success}")
        if sol.success:
            print(f"  margin4D={sol.margin_4D:+.12e}")
            print(f"  G3 rewrite flow={sol.g3_rewrite_flow:.8g}")
        print()

    if args.pareto:
        hyp = args.hypothetical_base_upper
        rows = analyzer.direct_g3_pareto(
            tev,
            cres.terminals,
            fractions=(1.0, .95, .9, .8, .6, .4, .2, 0.0),
            hypothetical_base_upper=hyp,
        )
        print("DIRECT-G3 EXPOSURE PARETO")
        print("-"*92)
        if hyp is None:
            print("  no hypothetical base terminal supplied; reductions may be infeasible.")
        else:
            print(f"  hypothetical base upper U={hyp:.8g}")
        print("  fraction   feasible      coeff(G3)4D       margin4D      rewrite_flow")
        for r in rows:
            print(
                f"  {r['fraction']:8.2f}   "
                f"{str(r['success']):>8s}   "
                f"{str(None if r['direct_g3_coefficient_4D'] is None else round(r['direct_g3_coefficient_4D'],8)):>15s}   "
                f"{('None' if r['margin_4D'] is None else format(r['margin_4D'], '+.8e')):>13s}   "
                f"{str(None if r['g3_rewrite_flow'] is None else round(r['g3_rewrite_flow'],8)):>12s}"
            )
        print()

    return 0


def main():
    args = parser().parse_args()
    artifacts, evaluator, compiler, analyzer = build(args)

    print("PHASE-2 G3 ESCAPE ANALYZER V5")
    print("="*92)
    print(f"target                     = 1 + {2-args.delta:.12g}")
    print(f"delta                      = {args.delta:.12g}")
    print(f"search objective           = maximize critical hypothetical G3-base upper")
    print(f"storage                    = {storage_dir_for_script(__file__)}")
    print()

    p = fixed_params(args)
    if p is not None or args.report or args.pareto:
        if p is None:
            # For a report without explicit alpha,beta,gamma, use the paper
            # alpha,beta,gamma but the requested delta.
            p = Parameters(
                a=2-args.delta,
                alpha=4/53,
                beta=4/33,
                gamma=3/11,
                epsilon=args.epsilon,
            )
        return run_report(p, evaluator, compiler, analyzer, args)

    # Default action is the useful search; --search is accepted for clarity.
    search = RandomG3TargetSearch(
        evaluator=evaluator,
        compiler=compiler,
        analyzer=analyzer,
        delta=args.delta,
        epsilon=args.epsilon,
        samples_per_batch=args.samples_per_batch,
        base_seed=BASE_SEED,
        target_margin_4D=args.target_margin_4d,
        upper_cap=args.upper_cap,
    )

    batch = args.start_batch
    done = 0
    global_best = None

    print("SEARCH STARTED — Ctrl+C stops cleanly.")
    print("-"*92)
    try:
        while args.max_batches == 0 or done < args.max_batches:
            t0 = time.perf_counter()
            out = search.run_batch(batch)
            dt = time.perf_counter() - t0

            best = out["best"]
            if best is not None and (
                global_best is None or best.score() > global_best.score()
            ):
                global_best = best

            if best is None or best.critical.critical_upper is None:
                print(
                    f"batch={batch:06d} valid={out['valid']:3d}/"
                    f"{args.samples_per_batch} zero_escape="
                    f"{out['escape_feasible_at_zero']:3d} "
                    f"best_Ucrit=NONE time={dt:.2f}s"
                )
            else:
                p = best.params
                c = best.critical
                print(
                    f"batch={batch:06d} valid={out['valid']:3d}/"
                    f"{args.samples_per_batch} zero_escape="
                    f"{out['escape_feasible_at_zero']:3d} "
                    f"best_Ucrit={c.critical_upper:.9f} "
                    f"ratio={c.ratio_to_direct_g3_bound:.6f} "
                    f"baseline4D={best.baseline.margin_4D:+.5e} "
                    f"time={dt:.2f}s"
                )
                print(
                    f"    alpha={p.alpha:.12g} beta={p.beta:.12g} "
                    f"gamma={p.gamma:.12g} tau={p.tau:.12g}"
                )

                path = write_g3_target_record(
                    script_file=__file__,
                    delta=args.delta,
                    hit=best,
                    manifest_path=args.manifest,
                    flow_path=args.flow,
                    analyzer=analyzer,
                )
                print(f"    stored: {path}")

            batch += 1
            done += 1

    except KeyboardInterrupt:
        print("\nSTOPPED BY USER")
        if global_best is not None and global_best.critical.critical_upper is not None:
            p = global_best.params
            c = global_best.critical
            print(f"best Ucrit={c.critical_upper:.12g}")
            print(f"ratio to direct G3 bound={c.ratio_to_direct_g3_bound:.8g}")
            print(
                f"alpha={p.alpha:.12g}, beta={p.beta:.12g}, "
                f"gamma={p.gamma:.12g}, tau={p.tau:.12g}"
            )
    return 0


if __name__ == "__main__":
    sys.exit(main())
