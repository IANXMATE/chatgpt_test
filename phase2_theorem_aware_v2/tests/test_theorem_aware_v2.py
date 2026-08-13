from pathlib import Path

from goldbach_phase2.theorem_aware_evaluator import (
    Parameters, TheoremAwarePaperPathEvaluator,
)


def evaluator():
    return TheoremAwarePaperPathEvaluator(
        lowdim_order=28,
        highdim_order=8,
        sieve_step=5e-5,
        buchstab_step=5e-5,
        numeric_pad_per_G=0.0,
    )


def test_paper_point_is_valid_and_close():
    ev = evaluator().evaluate(Parameters(
        a=1.9, alpha=4/53, beta=4/33, gamma=3/11
    ))
    assert ev.valid
    assert abs(ev.per_G["G2"]["raw_unpadded_bound"] - 9.11587) < 5e-3
    assert abs(ev.per_G["G3"]["raw_unpadded_bound"] - 0.84289) < 5e-4
    assert abs(ev.per_G["G9"]["raw_unpadded_bound"] - 5.27231) < 5e-3
    assert 0.09 < ev.per_G["G11"]["raw_unpadded_bound"] < 0.12
    assert 0.64 < ev.per_G["G12"]["raw_unpadded_bound"] < 0.70


def test_g4_guard_rejects_alpha_above_one_twelfth():
    ev = evaluator().evaluate(Parameters(
        a=1.9, alpha=0.09, beta=0.12, gamma=0.28
    ))
    assert not ev.valid
    names = {g["name"] for g in ev.theorem_trace["hard_failures"]}
    assert "G4_uniform_upper_sieve" in names


def test_buchstab_below_three_is_not_rejected():
    # Legal Proposition-4.3 / current estimator point with G12 minimum
    # Buchstab argument below 3 but above 1.
    p = Parameters(a=1.9, alpha=0.08, beta=0.15, gamma=0.26)
    ev = evaluator().evaluate(p)
    assert ev.valid
    g12_guard = [
        g for g in ev.theorem_trace["guards"]
        if g["name"] == "G12_buchstab_domain"
    ][0]
    assert 1.0 < g12_guard["value"] < 3.0
