from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import hashlib
import json
import os
import sys


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024*1024), b""):
            h.update(chunk)
    return h.hexdigest()


def safe_delta(delta):
    return f"{delta:.8f}".rstrip("0").rstrip(".").replace(".", "p")


def storage_dir_for_script(script_file):
    script_dir = os.path.dirname(os.path.abspath(script_file))
    out = Path(os.path.join(script_dir, "storage"))
    out.mkdir(parents=True, exist_ok=True)
    return out


def write_frontier_success(
    script_file,
    delta,
    hit,
    manifest_path,
    flow_path,
    evaluator_settings,
    compiler_settings,
    required_margin_4D,
):
    out = storage_dir_for_script(script_file)
    stem = (
        f"delta_{safe_delta(delta)}"
        f"_batch_{hit.batch_index:06d}"
        f"_sample_{hit.sample_index:04d}"
    )
    path = out / f"{stem}.txt"
    repeat = 1
    while path.exists():
        path = out / f"{stem}_repeat_{repeat:03d}.txt"
        repeat += 1

    ev = hit.theorem_eval
    sol = hit.flow_solution
    cres = hit.compile_result

    record = {
        "schema": "goldbach-phase2-frontier-compiler-hit-v4",
        "status": (
            "NUMERICAL_CANDIDATE_THEOREM_GUARDED_FRONTIER_COMPILED_"
            "FLOW_CONSERVING_NOT_INTERVAL_CERTIFIED"
        ),
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "target": {
            "delta": delta,
            "a": 2-delta,
            "form": "1 + (2-delta)",
            "required_margin_4D": required_margin_4D,
        },
        "reproducibility": {
            "batch_index": hit.batch_index,
            "sample_index": hit.sample_index,
            "parameter_seed": hit.parameter_seed,
            "python": sys.version,
            "argv": list(sys.argv),
            "manifest_path": os.path.abspath(manifest_path),
            "manifest_sha256": sha256_file(manifest_path),
            "flow_path": os.path.abspath(flow_path),
            "flow_sha256": sha256_file(flow_path),
            "script_path": os.path.abspath(script_file),
            "script_sha256": sha256_file(script_file),
        },
        "parameters": ev.parameters,
        "paper_terminal_evaluator": {
            "settings": evaluator_settings,
            "theorem_trace": ev.theorem_trace,
            "G_bounds": ev.bounds,
            "per_G": ev.per_G,
        },
        "frontier_compiler": {
            "settings": compiler_settings,
            "compiled_count": len(cres.terminals),
            "reachable_rewrite_count": hit.reachable_rewrite_count,
            "compile_result": cres.to_dict(),
        },
        "flow_solution": {
            "margin_2D": sol.objective_margin_2D,
            "margin_4D_equivalent": sol.margin_4D_equivalent,
            "margin_D": sol.margin_D,
            "active_rewrites": sol.active_rewrite_count,
            "rewrite_allocations": sol.rewrite_allocations,
            "source_weights": sol.source_weights,
            "paper_terminal_allocations": sol.terminal_allocations,
            "compiled_terminal_allocations": getattr(
                sol, "compiled_terminal_allocations", {}
            ),
            "cancellations": sol.cancellation_allocations,
            "bundles": sol.bundle_allocations,
            "g16_bridges": sol.bridge_allocations,
            "effective_paper_G_coefficients_4D": sol.effective_G_coefficients_4D,
            "max_genuine_unresolved": sol.max_unresolved,
            "max_conservation_residual": sol.max_conservation_residual,
        },
        "warnings": [
            "QMC values are screening estimates with positive pads, not interval bounds.",
            "Generic switched-Buchstab terminals are derived from the Phase-1 "
            "buchstab_or_switching_upper_candidate oracle and the Li-Liu "
            "Section-5.4 density pattern; each successful new exponent still "
            "requires source-level and interval certification.",
            "The G16 source-shape bridge remains enabled exactly as in V3.",
        ],
    }

    with path.open("w", encoding="utf-8") as f:
        f.write("# Goldbach Phase-2 Frontier Theorem Compiler V4 success record\n")
        f.write("# Full JSON follows. This is a numerical candidate, not a published proof certificate.\n")
        json.dump(record, f, ensure_ascii=False, indent=2)
        f.write("\n")

    return path
