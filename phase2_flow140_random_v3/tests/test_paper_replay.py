from pathlib import Path

from goldbach_phase2.io import Phase1Artifacts
from goldbach_phase2.model import Phase2Model
from goldbach_phase2.replay_validator import validate_paper_replay


ROOT = Path(__file__).resolve().parents[1]


def test_paper_replay_passes():
    artifacts = Phase1Artifacts.load(
        ROOT / "data" / "phase1_manifest_v5.json",
        ROOT / "data" / "flow_blueprint.json",
    )
    model = Phase2Model(artifacts)
    report, replay, contributions = validate_paper_replay(model)
    assert report.passed
    assert abs(report.margin_4D - 0.00172) < 1e-10
    assert abs(report.margin_D - 0.00043) < 1e-10
    assert not report.coefficient_differences


def test_strict_g16_stops():
    artifacts = Phase1Artifacts.load(
        ROOT / "data" / "phase1_manifest_v5.json",
        ROOT / "data" / "flow_blueprint.json",
    )
    model = Phase2Model(artifacts)
    try:
        validate_paper_replay(model, allow_g16_paper_bridge=False)
    except RuntimeError:
        return
    raise AssertionError("strict G16 replay should stop")
