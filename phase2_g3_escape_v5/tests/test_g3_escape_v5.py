from pathlib import Path

from goldbach_phase2.io import Phase1Artifacts
from goldbach_phase2.theorem_aware_evaluator import (
    Parameters,
    TheoremAwarePaperPathEvaluator,
)
from goldbach_phase2.frontier_compiler import FrontierTheoremCompiler
from goldbach_phase2.g3_escape import G3EscapeAnalyzer


ROOT = Path(__file__).resolve().parents[1]


def setup(qmc_power=11):
    artifacts = Phase1Artifacts.load(
        ROOT / "data" / "phase1_manifest_v5.json",
        ROOT / "data" / "flow_blueprint.json",
    )
    evaluator = TheoremAwarePaperPathEvaluator(
        lowdim_order=24,
        highdim_order=8,
        sieve_step=5e-5,
        buchstab_step=5e-5,
        numeric_pad_per_G=0.0,
    )
    compiler = FrontierTheoremCompiler(
        manifest=artifacts.manifest,
        flow_blueprint=artifacts.flow,
        sieve_functions=evaluator.sieve,
        buchstab_function=evaluator.buchstab,
        max_factor_count=6,
        qmc_power=qmc_power,
        qmc_scrambles=1,
        qmc_relative_pad=0.05,
        qmc_absolute_pad=1e-7,
    )
    analyzer = G3EscapeAnalyzer(
        artifacts.manifest,
        artifacts.flow,
    )
    return artifacts, evaluator, compiler, analyzer


def test_g3_exact_route_is_discovered():
    artifacts, evaluator, compiler, analyzer = setup()
    s = analyzer.structure
    assert s.state_id == artifacts.flow["alias_map"]["G3"]
    assert len(s.correction_states) == 1
    assert s.neg_rewrite.startswith("x_rewrite__NEG__")


def test_without_direct_g3_paper_point_is_infeasible_under_current_registry():
    artifacts, evaluator, compiler, analyzer = setup()
    p = Parameters(a=1.9, alpha=4/53, beta=4/33, gamma=3/11)
    tev = evaluator.evaluate(p)
    cres = compiler.compile(p)

    strict = analyzer.strict_without_direct_g3(tev, cres.terminals)
    assert not strict.success


def test_first_blocker_is_the_g3_base_state():
    artifacts, evaluator, compiler, analyzer = setup()
    p = Parameters(a=1.9, alpha=4/53, beta=4/33, gamma=3/11)
    tev = evaluator.evaluate(p)
    cres = compiler.compile(p)

    relaxed, blockers = analyzer.first_blockers(tev, cres.terminals)
    assert relaxed.success
    assert blockers
    assert blockers[0]["resource"] == analyzer.structure.base_state
    assert blockers[0]["flow"] > 0


def test_hypothetical_zero_base_upper_closes_paper_point():
    artifacts, evaluator, compiler, analyzer = setup()
    p = Parameters(a=1.9, alpha=4/53, beta=4/33, gamma=3/11)
    tev = evaluator.evaluate(p)
    cres = compiler.compile(p)

    sol = analyzer.solve_with_hypothetical_base(
        tev, cres.terminals, 0.0, disable_direct_g3=True
    )
    assert sol.success
    assert sol.margin_4D > 0
    assert sol.direct_g3_terminal_flow < 1e-12
    assert sol.g3_rewrite_flow > 0


def test_critical_upper_exists_at_paper_point():
    artifacts, evaluator, compiler, analyzer = setup()
    p = Parameters(a=1.9, alpha=4/53, beta=4/33, gamma=3/11)
    tev = evaluator.evaluate(p)
    cres = compiler.compile(p)

    crit = analyzer.critical_base_upper(
        tev, cres.terminals, target_margin_4D=0.0, upper_search_cap=3.0
    )
    assert crit.feasible_with_zero_bound
    assert crit.critical_upper is not None
    assert crit.critical_upper > 0
