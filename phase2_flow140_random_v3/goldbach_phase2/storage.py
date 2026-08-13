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
    out = Path(os.path.join(script_dir, "storage"))
    out.mkdir(parents=True, exist_ok=True)
    return out


def write_success_record(
    script_file: str,
    delta: float,
    hit,
    manifest_path: str,
    flow_path: str,
    evaluator_settings,
    certificate_chain,
    required_margin_4D: float,
):
    out = storage_dir_for_script(script_file)
    stem = f"delta_{safe_delta(delta)}_batch_{hit.batch_index:06d}"
    path = out / f"{stem}.txt"
    repeat = 1
    while path.exists():
        path = out / f"{stem}_repeat_{repeat:03d}.txt"
        repeat += 1

    ev = hit.evaluation
    record = {
        "schema": "goldbach-phase2-theorem-aware-hit-v2",
        "status": ev.status,
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
            "batch_seed": hit.batch_seed,
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
        "evaluator_settings": dict(evaluator_settings),
        "theorem_trace": ev.theorem_trace,
        "per_G": ev.per_G,
        "bounds": ev.bounds,
        "contributions": ev.contributions,
        "margin": {
            "margin_4D": ev.margin_4D,
            "margin_D": ev.margin_D,
        },
        "certificate": {
            "coefficient_vector": {
                "G1": 3, "G2": 1, "G3": -4, "G4": -1, "G5": -1,
                "G6": 1, "G7": 1, "G8": -2, "G9": -1, "G10": -1,
                "G11": -1, "G12": -1,
            },
            "paper_replay_chain": certificate_chain,
        },
    }

    with path.open("w", encoding="utf-8") as f:
        f.write("# Goldbach Phase-2 theorem-aware random-search record\n")
        f.write("# Numerical candidate only; theorem guards/splits are recorded, but integrals are not interval-certified.\n")
        json.dump(record, f, ensure_ascii=False, indent=2)
        f.write("\n")
    return path
