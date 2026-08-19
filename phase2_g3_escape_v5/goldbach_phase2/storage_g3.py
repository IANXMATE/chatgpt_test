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
    out = Path(os.path.dirname(os.path.abspath(script_file))) / "storage"
    out.mkdir(parents=True, exist_ok=True)
    return out


def write_g3_target_record(
    script_file,
    delta,
    hit,
    manifest_path,
    flow_path,
    analyzer,
):
    out = storage_dir_for_script(script_file)
    stem = (
        f"g3_target_delta_{safe_delta(delta)}"
        f"_batch_{hit.batch_index:06d}"
        f"_sample_{hit.sample_index:04d}"
    )
    path = out / f"{stem}.txt"
    repeat = 1
    while path.exists():
        path = out / f"{stem}_repeat_{repeat:03d}.txt"
        repeat += 1

    ev = hit.theorem_eval
    record = {
        "schema": "goldbach-phase2-g3-escape-target-v5",
        "status": (
            "THEOREM_DESIGN_TARGET_NOT_A_PROOF_"
            "CRITICAL_G3_BASE_UPPER_IS_HYPOTHETICAL"
        ),
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "target": {
            "delta": delta,
            "a": 2-delta,
            "form": "1 + (2-delta)",
        },
        "reproducibility": {
            "batch_index": hit.batch_index,
            "sample_index": hit.sample_index,
            "seed": hit.seed,
            "python": sys.version,
            "argv": list(sys.argv),
            "manifest_sha256": sha256_file(manifest_path),
            "flow_sha256": sha256_file(flow_path),
            "script_sha256": sha256_file(script_file),
        },
        "parameters": ev.parameters,
        "g3_structure": analyzer.structure.to_dict(),
        "paper_G_bounds": ev.bounds,
        "theorem_trace": ev.theorem_trace,
        "frontier_compiler": hit.compile_result.to_dict(),
        "baseline": hit.baseline.to_dict(),
        "critical_hypothetical_G3_base_upper": hit.critical.to_dict(),
        "warning": (
            "critical_upper is not a proved estimate. It is the largest "
            "normalized upper constant U such that, IF the exact G3 Buchstab "
            "base state could be proved <= U*C(N)N/log^2N, the complete flow "
            "certificate would attain the requested margin while the paper's "
            "direct G3 upper terminal is disabled."
        ),
    }

    with path.open("w", encoding="utf-8") as f:
        f.write("# G3 Escape V5 theorem-design target\n")
        json.dump(record, f, ensure_ascii=False, indent=2)
        f.write("\n")
    return path
