from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict
import json


@dataclass(frozen=True)
class Phase1Artifacts:
    manifest: Dict[str, Any]
    flow: Dict[str, Any]
    manifest_path: Path
    flow_path: Path

    @classmethod
    def load(cls, manifest_path, flow_path) -> "Phase1Artifacts":
        manifest_path = Path(manifest_path)
        flow_path = Path(flow_path)

        with manifest_path.open("r", encoding="utf-8") as f:
            manifest = json.load(f)
        with flow_path.open("r", encoding="utf-8") as f:
            flow = json.load(f)

        if manifest.get("schema") != "goldbach-phase1-flow-dag-v5":
            raise ValueError(
                "Expected Phase-1 schema goldbach-phase1-flow-dag-v5, "
                f"got {manifest.get('schema')!r}"
            )

        for key in (
            "alias_map", "sources", "linear_rewrite_rules",
            "bundle_rules", "conservation_equations",
        ):
            if key not in flow:
                raise ValueError(f"flow_blueprint is missing required key: {key}")

        return cls(
            manifest=manifest,
            flow=flow,
            manifest_path=manifest_path,
            flow_path=flow_path,
        )
