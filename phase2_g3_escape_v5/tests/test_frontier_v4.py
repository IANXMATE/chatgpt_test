from pathlib import Path

from goldbach_phase2.io import Phase1Artifacts
from goldbach_phase2.theorem_aware_evaluator import (
    Parameters,
    TheoremAwarePaperPathEvaluator,
)
from goldbach_phase2.flow140 import Flow140Model
from goldbach_phase2.frontier_compiler import FrontierTheoremCompiler
from goldbach_phase2.compiled_flow import CompiledFlow140Model
from goldbach_phase2.polytope import RegionPolytope


ROOT = Path(__file__).resolve().parents[1]


def setup(qmc_power=13):
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
        qmc_scrambles=2,
        qmc_relative_pad=0.05,
        qmc_absolute_pad=1e-7,
    )
    p = Parameters(
        a=1.9, alpha=4/53, beta=4/33, gamma=3/11
    )
    return artifacts, evaluator, compiler, p


def test_generic_linear_reproduces_G4_scale():
    artifacts, evaluator, compiler, p = setup()
    states = {
        s["state_id"]: s for s in artifacts.manifest["structural_states"]
    }
    s = states[artifacts.flow["alias_map"]["G4"]]
    poly = RegionPolytope(s, compiler.parameter_dict(p))

    # Call the same generic integrand machinery on G4 directly.
    # G4 is not itself unresolved, so temporarily provide the expected key.
    compiler.neg_unresolved[s["state_id"]] = "dummy"
    t = compiler._linear_candidate(s["state_id"], s, p, poly)
    assert t is not None
    assert 22.0 < t.upper_bound < 26.0


def test_generic_buchstab_reproduces_G11_scale():
    artifacts, evaluator, compiler, p = setup(qmc_power=15)
    states = {
        s["state_id"]: s for s in artifacts.manifest["structural_states"]
    }
    s = states[artifacts.flow["alias_map"]["G11"]]
    poly = RegionPolytope(s, compiler.parameter_dict(p))

    compiler.neg_unresolved[s["state_id"]] = "dummy"
    t = compiler._buchstab_candidate(s["state_id"], s, p, poly)
    assert t is not None
    # Dedicated dynamic G11 is about 0.1019. QMC + positive pad should remain
    # in the same scale and above the raw dedicated value.
    assert 0.09 < t.upper_bound < 0.14


def test_paper_point_coverage_improves_6_to_15():
    artifacts, evaluator, compiler, p = setup(qmc_power=13)
    tev = evaluator.evaluate(p)
    assert tev.valid

    base = Flow140Model(
        artifacts.flow,
        allow_g16_paper_bridge=True,
        strict_unresolved=True,
    )
    r0, _ = base.certifiably_reachable_rewrites()
    assert len(r0) == 6

    cres = compiler.compile(p)
    compiled = CompiledFlow140Model(
        artifacts.flow,
        cres.terminals,
        allow_g16_paper_bridge=True,
    )
    r1, _ = compiled.certifiably_reachable_rewrites()
    assert len(r1) == 15
    assert len(cres.terminals) >= 15


def test_compiled_flow_remains_conserving_and_positive_at_paper_point():
    artifacts, evaluator, compiler, p = setup(qmc_power=13)
    tev = evaluator.evaluate(p)
    cres = compiler.compile(p)
    model = CompiledFlow140Model(
        artifacts.flow,
        cres.terminals,
        allow_g16_paper_bridge=True,
    )
    sol = model.solve(tev)
    assert sol.success
    assert sol.max_unresolved < 1e-12
    assert sol.max_conservation_residual < 1e-8
    assert sol.margin_4D_equivalent > 0
