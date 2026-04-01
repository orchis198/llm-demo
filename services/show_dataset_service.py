from __future__ import annotations

import json
from pathlib import Path
from typing import Any


class ShowDatasetService:
    def __init__(self, base_dir: str) -> None:
        self.base_dir = Path(base_dir)

    def load_manifest(self, scenario_name: str = "show") -> dict[str, Any]:
        manifest_path = self.base_dir / "data" / "show" / "manifests" / f"{scenario_name}_manifest.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        return manifest

    def resolve_path(self, relative_path: str) -> str:
        return str((self.base_dir / relative_path).resolve())

    def load_text(self, relative_path: str) -> str:
        return Path(self.resolve_path(relative_path)).read_text(encoding="utf-8")
