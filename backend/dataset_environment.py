import json
import os
from pathlib import Path
from typing import Any, Dict, Optional


PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_MANIFEST_PATH = PROJECT_ROOT / "dataset-manifest.json"
DEMO_MANIFEST_PATH = PROJECT_ROOT / "demo-dataset-manifest.json"


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


def get_dataset_profile(config: Optional[Dict[str, Any]] = None) -> str:
    config = config or {}
    profile = str(config.get("dataset_profile") or os.getenv("GEMINI_DATASET_PROFILE") or "full").strip().lower()
    if profile not in {"full", "demo"}:
        raise DatasetEnvironmentError("GEMINI_DATASET_PROFILE must be either 'full' or 'demo'.")
    return profile


def manifest_path_for_profile(profile: str) -> Path:
    return DEMO_MANIFEST_PATH if profile == "demo" else DEFAULT_MANIFEST_PATH


def get_baked_environment_id(path: Optional[Path] = None, profile: Optional[str] = None) -> str:
    resolved_profile = profile or ("demo" if path == DEMO_MANIFEST_PATH else "full")
    manifest = load_dataset_manifest(path or manifest_path_for_profile(resolved_profile))
    environment_id = str(manifest.get("environment_id") or "").strip()
    status = str(manifest.get("environment_status") or "").strip().lower()
    expected_status = "demo-baked" if resolved_profile == "demo" else "baked"
    manifest_name = "demo-dataset-manifest.json" if resolved_profile == "demo" else "dataset-manifest.json"

    if not environment_id:
        raise DatasetEnvironmentError(f"{manifest_name} is missing environment_id.")
    if environment_id.startswith("local-"):
        raise DatasetEnvironmentError(
            f"{manifest_name} still points at a local placeholder environment_id. "
            "Run the Gemini demo/full bake script to create a real Gemini environment."
        )
    if status != expected_status:
        raise DatasetEnvironmentError(
            f"{manifest_name} must set environment_status to '{expected_status}' before Gemini analyst runs."
        )

    return environment_id


def resolve_analysis_environment(config: Optional[Dict[str, Any]] = None) -> str:
    config = config or {}
    explicit_environment = config.get("environment")
    if explicit_environment:
        return str(explicit_environment)
    profile = get_dataset_profile(config)
    return get_baked_environment_id(profile=profile)
