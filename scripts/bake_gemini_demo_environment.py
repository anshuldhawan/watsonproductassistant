#!/usr/bin/env python3
"""
Create a small Gemini demo environment using real Managed Agents.

The script embeds tiny demo dataset scripts, asks Gemini to generate data/ in a
remote sandbox, verifies it, and writes demo-dataset-manifest.json.
"""

import argparse
import base64
import datetime
import hashlib
import json
import os
import sys
from pathlib import Path
from typing import Any, Dict, Optional


PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEMO_MANIFEST_PATH = PROJECT_ROOT / "demo-dataset-manifest.json"
LAST_OUTPUT_PATH = PROJECT_ROOT / "bake_gemini_demo_last_output.txt"
DEFAULT_AGENT = "antigravity-preview-05-2026"
INLINE_DEMO_SOURCE = "inline-demo-source"
SOURCE_FILES = (
    "scripts/generate_demo_data.py",
    "scripts/verify_demo_data.py",
    "requirements.txt",
)

sys.path.insert(0, str(PROJECT_ROOT))

from backend.env import load_project_env  # noqa: E402

load_project_env()


def require_python_310() -> None:
    if sys.version_info < (3, 10):
        raise RuntimeError("Gemini Interactions API support requires Python 3.10+.")


def load_manifest(path: Path = DEMO_MANIFEST_PATH) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def read_source_bundle(project_root: Path = PROJECT_ROOT) -> Dict[str, str]:
    return {
        relative_path: (project_root / relative_path).read_text(encoding="utf-8")
        for relative_path in SOURCE_FILES
    }


def compute_source_hash(source_bundle: Dict[str, str]) -> str:
    digest = hashlib.sha256()
    for relative_path in sorted(source_bundle):
        digest.update(relative_path.encode("utf-8"))
        digest.update(b"\0")
        digest.update(source_bundle[relative_path].encode("utf-8"))
        digest.update(b"\0")
    return digest.hexdigest()


def encode_source_bundle(source_bundle: Dict[str, str]) -> Dict[str, str]:
    return {
        relative_path: base64.b64encode(content.encode("utf-8")).decode("ascii")
        for relative_path, content in source_bundle.items()
    }


def build_demo_bake_prompt(source_bundle: Dict[str, str], source_hash: str) -> str:
    bundle_json = json.dumps(encode_source_bundle(source_bundle), indent=2, sort_keys=True)
    return f"""
Create a small fake Spotify product-analytics demo dataset from scratch in this
remote Gemini environment. This is for a live product demo, so keep the verified
data/ directory on disk for later analyst-agent interactions.

Decode and write these local source files exactly:

SOURCE_BUNDLE_BASE64_JSON:
```json
{bundle_json}
```

Steps:
1. Create the scripts/ directory.
2. Decode SOURCE_BUNDLE_BASE64_JSON and write each file to its relative path.
3. Install dependencies from requirements.txt.
4. Run python scripts/generate_demo_data.py.
5. Run python scripts/verify_demo_data.py.
6. Print the exact lines:
   DEMO_VERIFICATION_PASSED
   DEMO_GENERATOR_SOURCE_HASH={source_hash}

The dataset must be available at data/catalog/*.parquet and
data/play_events/date=*/part_0.parquet after you finish.
""".strip()


def create_interaction(api_key: str, agent: str, prompt: str) -> Any:
    try:
        from google import genai
    except ImportError as exc:
        raise RuntimeError("Install google-genai>=1.55.0 in Python 3.10+ to bake the demo environment.") from exc

    client = genai.Client(api_key=api_key)
    return client.interactions.create(
        agent=agent,
        input=prompt,
        environment="remote",
    )


def read_attr(obj: Any, *names: str) -> Optional[str]:
    for name in names:
        value = getattr(obj, name, None)
        if value:
            return str(value)
    return None


def read_environment_id(response: Any) -> Optional[str]:
    environment_id = read_attr(response, "environment_id")
    if environment_id:
        return environment_id
    environment = getattr(response, "environment", None)
    if environment is not None:
        return read_attr(environment, "id", "name")
    return None


def collect_text_parts(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        return [value]
    if isinstance(value, dict):
        parts: list[str] = []
        for key, nested in value.items():
            if key in {"text", "output_text"} and isinstance(nested, str):
                parts.append(nested)
            else:
                parts.extend(collect_text_parts(nested))
        return parts
    if isinstance(value, (list, tuple)):
        parts: list[str] = []
        for item in value:
            parts.extend(collect_text_parts(item))
        return parts

    parts: list[str] = []
    for attr in ("text", "output_text", "content", "parts", "steps", "model_output"):
        if hasattr(value, attr):
            parts.extend(collect_text_parts(getattr(value, attr)))
    if hasattr(value, "model_dump"):
        try:
            parts.extend(collect_text_parts(value.model_dump()))
        except Exception:
            pass
    return parts


def read_output_text(response: Any) -> str:
    output_text = getattr(response, "output_text", None)
    if output_text:
        return str(output_text)
    parts = collect_text_parts(response)
    return "\n".join(parts) if parts else str(response)


def validate_demo_bake_result(output_text: str, source_hash: str, environment_id: Optional[str]) -> None:
    if not environment_id:
        raise RuntimeError("Gemini demo bake did not return an environment_id.")
    if "DEMO_VERIFICATION_PASSED" not in output_text or source_hash not in output_text:
        raise RuntimeError("Gemini demo bake output did not include verification success markers.")


def update_demo_manifest(
    manifest: Dict[str, Any],
    *,
    environment_id: str,
    source_hash: str,
    interaction_id: Optional[str],
) -> Dict[str, Any]:
    updated = dict(manifest)
    updated.update(
        {
            "dataset_profile": "demo",
            "environment_id": environment_id,
            "environment_status": "demo-baked",
            "generator_repo": INLINE_DEMO_SOURCE,
            "generator_sha": source_hash,
            "generator_source_hash": source_hash,
            "baked_interaction_id": interaction_id,
            "baked_at": datetime.datetime.now(datetime.timezone.utc)
            .replace(microsecond=0)
            .isoformat()
            .replace("+00:00", "Z"),
        }
    )
    return updated


def write_manifest(manifest: Dict[str, Any], path: Path = DEMO_MANIFEST_PATH) -> None:
    path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")


def write_last_output(output_text: str, path: Path = LAST_OUTPUT_PATH) -> None:
    path.write_text(output_text or "<empty Gemini output>", encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Bake a small Gemini demo dataset environment.")
    parser.add_argument("--agent", default=os.getenv("GEMINI_DEMO_AGENT_ID", DEFAULT_AGENT))
    parser.add_argument("--manifest", type=Path, default=DEMO_MANIFEST_PATH)
    parser.add_argument("--no-update", action="store_true")
    return parser.parse_args()


def main() -> int:
    require_python_310()
    args = parse_args()
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY is required.")

    source_bundle = read_source_bundle()
    source_hash = compute_source_hash(source_bundle)
    prompt = build_demo_bake_prompt(source_bundle, source_hash)
    response = create_interaction(api_key=api_key, agent=args.agent, prompt=prompt)

    interaction_id = read_attr(response, "id", "name")
    environment_id = read_environment_id(response)
    output_text = read_output_text(response)
    write_last_output(output_text)
    validate_demo_bake_result(output_text, source_hash, environment_id)

    print(f"Demo interaction id: {interaction_id}")
    print(f"Demo environment id: {environment_id}")

    if not args.no_update:
        manifest = load_manifest(args.manifest)
        updated = update_demo_manifest(
            manifest,
            environment_id=environment_id,
            source_hash=source_hash,
            interaction_id=interaction_id,
        )
        write_manifest(updated, args.manifest)
        print(f"Updated demo manifest: {args.manifest}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
