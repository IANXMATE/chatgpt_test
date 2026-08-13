from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import hashlib
import json
import os
import sys


def sha256_file(path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024*1024), b""):
            h.update(chunk)
    return h.hexdigest()


def safe_delta(delta: float) -> str:
    return f"{delta:.8f}".rstrip("0").rstrip(".").replace(".", "p")


def storage_dir_for_script(script_file: str) -> Path:
    script_dir = os.path.dirname(os.path.abspath(script_file))
    p = Path(os.path.join(script_dir, "storage"))
    p.mkdir(parents=True, exist_ok=True)
    return p


def write_flow140_success(
    script_file: str,
    delta: float,
    hit,
    manifest_path: str,
    flow_path: str,
    evaluator_settings,
    reachable_rewrite_count: int,
    required_margin_4D: float,
):
    out = storage_dir_for_script(script_file)
    stem = (
        f"delta_{safe_delta(delta)}"
        f"_batch_{hit.batch_index:06d}"
        f"_sample_{hit.sample_index:04d}"
        f"_flow_{hit.flow_trial_index:04d}"
    )
    path = out / f"{stem}.txt"
    repeat = 1
    while path.exists():
        path = out / f"{stem}_repeat_{repeat:03d}.txt"
        repeat += 1

    tev = hit.theorem_eval
    sol = hit.flow_solution

    record = {
        "schema": "goldbach-phase2-flow140-random-hit-v3",
        "status": (
            "NUMERICAL_CANDIDATE_THEOREM_GUARDED_FLOW_CONSERVING_"
            "UNRESOLVED_ZERO_NOT_INTERVAL_CERTIFIED"
        ),
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "target": {
            "delta": delta,
            "a": 2.0-delta,
            "form": "1 + (2-delta)",
            "required_margin_4D": required_margin_4D,
        },
        "reproducibility": {
            "batch_index": hit.batch_index,
            "sample_index": hit.sample_index,
            "flow_trial_index": hit.flow_trial_index,
            "parameter_seed": hit.parameter_seed,
            "flow_seed": hit.flow_seed,
            "python": sys.version,
            "argv": list(sys.argv),
            "manifest_path": os.path.abspath(manifest_path),
            "manifest_sha256": sha256_file(manifest_path),
            "flow_path": os.path.abspath(flow_path),
            "flow_sha256": sha256_file(flow_path),
            "script_path": os.path.abspath(script_file),
            "script_sha256": sha256_file(script_file),
        },
        "parameters": tev.parameters,
        "theorem_trace": tev.theorem_trace,
        "dynamic_G_bounds": tev.bounds,
        "per_G": tev.per_G,
        "evaluator_settings": dict(evaluator_settings),
        "flow_search": {
            "requested_rewrite_dimensions": 140,
            "currently_certifiably_reachable_rewrites": reachable_rewrite_count,
            "preference_temperature": sol.preference_temperature,
            "random_140_preference_vector": sol.preference_vector,
            "actual_140_rewrite_allocations": sol.rewrite_allocations,
            "active_rewrite_count_in_solution": sol.active_rewrite_count,
            "source_weights": sol.source_weights,
            "nonzero_terminal_allocations": sol.terminal_allocations,
            "nonzero_cancellation_allocations": sol.cancellation_allocations,
            "bundle_allocations": sol.bundle_allocations,
            "g16_bridge_allocations": sol.bridge_allocations,
            "effective_G_coefficients_4D": sol.effective_G_coefficients_4D,
            "max_conservation_residual": sol.max_conservation_residual,
            "max_unresolved": sol.max_unresolved,
        },
        "margin": {
            "normalized_flow_lhs": "2D because source weights sum to 1",
            "margin_2D": sol.objective_margin_2D,
            "margin_4D_equivalent": sol.margin_4D_equivalent,
            "margin_D": sol.margin_D,
        },
        "source_audit_warning": (
            "G16 literal/three-factor bridge is enabled to match the paper's "
            "intended closure; arXiv-v2 source-shape discrepancy remains."
        ),
    }

    with path.open("w", encoding="utf-8") as f:
        f.write("# Goldbach Phase-2 140-rewrite randomized-flow success record\n")
        f.write("# The 140 random coordinates are rewrite preferences; the stored actual allocations are the conservation-feasible projection.\n")
        f.write("# unresolved is forced to zero. Numerical integration is not interval-certified.\n")
        json.dump(record, f, ensure_ascii=False, indent=2)
        f.write("\n")
    return path
