from __future__ import annotations

from typing import Dict

from .model import Phase2Model
from .paper_bounds import PaperSection5Bounds
from .paper_replay import PaperReplay
from .validation import ReplayReport


TOL = 1e-10


def validate_paper_replay(model: Phase2Model,
                          allow_g16_paper_bridge: bool = True) -> ReplayReport:
    failures = model.check_reference_parameter_constraints()
    parameter_ok = not failures

    replay = PaperReplay(
        model,
        allow_g16_paper_bridge=allow_g16_paper_bridge
    )
    actual = replay.run()
    expected = model.expected_prop43_coefficients()

    keys = set(actual) | set(expected)
    differences = {
        model.paper_name(k): actual.get(k, 0.0) - expected.get(k, 0.0)
        for k in sorted(keys)
        if abs(actual.get(k, 0.0) - expected.get(k, 0.0)) > TOL
    }
    structure_ok = not differences

    # Convert final canonical IDs back to G1..G12 names.
    paper_coeffs = {}
    for resource, coefficient in actual.items():
        name = model.paper_name(resource)
        if name.startswith("G") and name[1:].isdigit():
            idx = int(name[1:])
            if 1 <= idx <= 12:
                paper_coeffs[name] = coefficient

    margin_4D, contributions = PaperSection5Bounds.evaluate_certificate(
        paper_coeffs
    )
    margin_D = margin_4D / 4.0

    arithmetic_ok = abs(margin_4D - 0.00172) <= 5e-10
    threshold = 0.0004
    theorem_threshold_ok = margin_D > threshold

    messages = []
    if failures:
        messages.append("Reference parameter failures: " + ", ".join(failures))
    if differences:
        messages.append(
            "Final coefficient vector differs from Phase-1 Proposition 4.3 target."
        )
    if not arithmetic_ok:
        messages.append(
            f"Equation (5.51) mismatch: got {margin_4D:.12g}, expected 0.00172."
        )

    return ReplayReport(
        parameter_constraints_pass=parameter_ok,
        structure_pass=structure_ok,
        arithmetic_pass=arithmetic_ok,
        theorem_threshold_pass=theorem_threshold_ok,
        g16_warning=allow_g16_paper_bridge,
        coefficient_differences=differences,
        margin_4D=margin_4D,
        margin_D=margin_D,
        paper_threshold_D=threshold,
        messages=messages,
    ), replay, contributions
