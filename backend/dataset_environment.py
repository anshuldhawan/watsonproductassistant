import json
from pathlib import Path
from typing import Any, Dict, Optional


PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_MANIFEST_PATH = PROJECT_ROOT / "dataset-manifest.json"


class DatasetEnvironmentError(RuntimeError):
    """Raised when Gemini mode cannot resolve a valid baked data environment."""


def load_dataset_manifest(path: Optional[Path] = None) -> Dict[str, Any]:
    manifest_path = path or DEFAULT_MANIFEST_PATH
    try:
        return json.loads(manifest_path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise DatasetEnvironmentError(f"Dataset manifest not found: {manifest_path}") from exc
    except json.JSONDecodeError as exc:
        raise DatasetEnvironmentError(f"Dataset manifest is not valid JSON: {manifest_path}") from exc


def get_baked_environment_id(path: Optional[Path] = None) -> str:
    manifest = load_dataset_manifest(path)
    environment_id = str(manifest.get("environment_id") or "").strip()
    status = str(manifest.get("environment_status") or "").strip().lower()

    if not environment_id:
        raise DatasetEnvironmentError("dataset-manifest.json is missing environment_id.")
    if environment_id.startswith("local-"):
        raise DatasetEnvironmentError(
            "dataset-manifest.json still points at a local placeholder environment_id. "
            "Run scripts/bake_gemini_environment.py to create a real Gemini baked environment."
        )
    if status != "baked":
        raise DatasetEnvironmentError(
            "dataset-manifest.json must set environment_status to 'baked' before Gemini analyst runs."
        )

    return environment_id


def resolve_analysis_environment(config: Optional[Dict[str, Any]] = None) -> str:
    config = config or {}
    explicit_environment = config.get("environment")
    if explicit_environment:
        return str(explicit_environment)
    return get_baked_environment_id()
