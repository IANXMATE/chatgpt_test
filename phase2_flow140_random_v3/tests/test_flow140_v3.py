import json
from pathlib import Path
import numpy as np

from goldbach_phase2.io import Phase1Artifacts
from goldbach_phase2.theorem_aware_evaluator import (
    Parameters, TheoremAwarePaperPathEvaluator,
)
from goldbach_phase2.flow140 import Flow140Model


ROOT = Path(__file__).resolve().parents[1]


def setup():
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
    model = Flow140Model(
        artifacts.flow,
        allow_g16_paper_bridge=True,
        strict_unresolved=True,
    )
    return evaluator, model


def test_exactly_140_rewrites():
    _, model = setup()
    assert len(model.rewrite_names) == 140


def test_paper_point_full_flow_is_feasible_and_positive():
    evaluator, model = setup()
    tev = evaluator.evaluate(Parameters(
        a=1.9, alpha=4/53, beta=4/33, gamma=3/11
    ))
    assert tev.valid
    sol = model.solve(tev)
    assert sol.success
    assert sol.max_unresolved < 1e-12
    assert sol.max_conservation_residual < 1e-8
    assert sol.margin_4D_equivalent > 0

    # At the current theorem registry, the exact LP can recover the paper
    # normalized certificate at the paper point.
    expected = {
        "G1": 3, "G2": 1, "G3": -4, "G4": -1, "G5": -1, "G6": 1,
        "G7": 1, "G8": -2, "G9": -1, "G10": -1, "G11": -1, "G12": -1,
    }
    for g, v in expected.items():
        assert abs(sol.effective_G_coefficients_4D[g] - v) < 1e-7


def test_random_140_preference_projects_to_feasible_flow():
    evaluator, model = setup()
    tev = evaluator.evaluate(Parameters(
        a=1.9, alpha=4/53, beta=4/33, gamma=3/11
    ))
    rng = np.random.default_rng(123)
    pref = rng.normal(size=140)
    sol = model.solve(
        tev,
        preference_vector=pref,
        preference_temperature=10.0,
    )
    assert sol.success
    assert len(sol.preference_vector) == 140
    assert len(sol.rewrite_allocations) == 140
    assert sol.max_unresolved < 1e-12
    assert sol.max_conservation_residual < 1e-8


def test_current_registry_has_only_six_rewrites_reachable():
    _, model = setup()
    reachable, forced_zero = model.certifiably_reachable_rewrites()
    assert len(reachable) == 6
    assert len(forced_zero) == 134
