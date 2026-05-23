#!/usr/bin/env python3
"""
Create a verified Gemini baked environment for the Spotify dataset.

This script runs one Gemini Managed Agent interaction that writes the local
dataset generator source into the remote environment, regenerates data/ there,
runs verification, and stores the returned environment id in dataset-manifest.json.
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
MANIFEST_PATH = PROJECT_ROOT / "dataset-manifest.json"
DEFAULT_AGENT = "antigravity-preview-05-2026"
INLINE_SOURCE_REPO = "inline-local-source"
SOURCE_FILES = (
    "scripts/generate_data.py",
    "scripts/verify_data.py",
    "requirements.txt",
)

sys.path.insert(0, str(PROJECT_ROOT))

from backend.env import load_project_env  # noqa: E402

load_project_env()


def require_python_310() -> None:
    if sys.version_info < (3, 10):
        raise RuntimeError("Gemini Interactions API support requires Python 3.10+.")


def load_manifest(path: Path = MANIFEST_PATH) -> Dict[str, Any]:
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


def build_bake_prompt(
    *,
    source_bundle: Dict[str, str],
    generator_source_hash: str,
    expected_schema_hash: str,
    seed: int,
) -> str:
    encoded_bundle = encode_source_bundle(source_bundle)
    bundle_json = json.dumps(encoded_bundle, indent=2, sort_keys=True)
    return f"""
Create a verified Lighthouse Spotify dataset from scratch in this remote Gemini
environment. Do not clone any repository. Use the embedded local source bundle
below as the source of truth.

SOURCE_BUNDLE_BASE64_JSON:
```json
{bundle_json}
```

Steps:
1. Create the scripts/ directory.
2. Decode SOURCE_BUNDLE_BASE64_JSON and write each file exactly to its relative path.
3. Install Python dependencies from requirements.txt.
4. Run python scripts/generate_data.py. It must use seed {seed}.
5. Confirm the dataset exists at data/catalog/*.parquet and data/play_events/date=*/part_0.parquet.
6. Run python scripts/verify_data.py.
7. Print the full verification output and the exact lines:
   EXPECTED_SCHEMA_HASH={expected_schema_hash}
   GENERATOR_SOURCE_HASH={generator_source_hash}

Success criteria:
- scripts/verify_data.py completes successfully.
- The computed schema hash equals {expected_schema_hash}.
- The generated data/ directory remains on disk in this remote environment.
- Leave the verified data/ directory on disk in this environment.
""".strip()


def build_legacy_repo_bake_prompt(
    *,
    generator_repo: str,
    generator_ref: str,
    expected_schema_hash: str,
    seed: int,
) -> str:
    return f"""
Clone this repository: {generator_repo}
Checkout this exact ref: {generator_ref}

Create a verified Lighthouse Spotify dataset in the current working directory.

Steps:
1. Install Python dependencies from requirements.txt.
2. Run scripts/generate_data.py. It must use seed {seed}.
3. Confirm the dataset exists at data/catalog/*.parquet and data/play_events/date=*/part_0.parquet.
4. Run scripts/verify_data.py.
5. Print the full verification output and the exact line:
   EXPECTED_SCHEMA_HASH={expected_schema_hash}

Success criteria:
- scripts/verify_data.py completes successfully.
- The computed schema hash equals {expected_schema_hash}.
- Leave the verified data/ directory on disk in this environment.
""".strip()


def create_interaction(api_key: str, agent: str, prompt: str) -> Any:
    try:
        from google import genai
    except ImportError as exc:
        raise RuntimeError("Install google-genai>=1.55.0 in Python 3.10+ to bake the environment.") from exc

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


def read_output_text(response: Any) -> str:
    output_text = getattr(response, "output_text", None)
    if output_text:
        return str(output_text)

    text_parts = []
    for step in getattr(response, "steps", []) or []:
        for name in ("text", "output_text"):
            value = getattr(step, name, None)
            if value:
                text_parts.append(str(value))
    return "\n".join(text_parts)


def validate_bake_result(output_text: str, expected_schema_hash: str, environment_id: Optional[str]) -> None:
    if not environment_id:
        raise RuntimeError("Gemini bake interaction did not return an environment_id.")
    if expected_schema_hash not in output_text:
        raise RuntimeError(
            "Gemini bake output did not contain the expected schema hash. "
            "Refusing to update dataset-manifest.json."
        )


def update_manifest(
    manifest: Dict[str, Any],
    *,
    environment_id: str,
    generator_repo: str,
    generator_sha: str,
    interaction_id: Optional[str],
    generator_source_hash: Optional[str] = None,
) -> Dict[str, Any]:
    updated = dict(manifest)
    updated.update(
        {
            "environment_id": environment_id,
            "environment_status": "baked",
            "generator_repo": generator_repo,
            "generator_sha": generator_sha,
            "baked_interaction_id": interaction_id,
            "baked_at": datetime.datetime.now(datetime.timezone.utc)
            .replace(microsecond=0)
            .isoformat()
            .replace("+00:00", "Z"),
        }
    )
    if generator_source_hash:
        updated["generator_source_hash"] = generator_source_hash
    return updated


def write_manifest(manifest: Dict[str, Any], path: Path = MANIFEST_PATH) -> None:
    path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Bake and verify the Gemini dataset environment.")
    parser.add_argument("--source-mode", choices=("local", "repo"), default=os.getenv("GEMINI_BAKE_SOURCE_MODE", "local"))
    parser.add_argument("--generator-repo", default=os.getenv("GENERATOR_REPO_URL"))
    parser.add_argument("--generator-sha", default=os.getenv("GENERATOR_SHA"))
    parser.add_argument("--agent", default=os.getenv("GEMINI_BAKE_AGENT", DEFAULT_AGENT))
    parser.add_argument("--manifest", type=Path, default=MANIFEST_PATH)
    parser.add_argument("--no-update", action="store_true", help="Run the bake but do not update the manifest.")
    return parser.parse_args()


def main() -> int:
    require_python_310()
    args = parse_args()

    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY is required.")

    manifest = load_manifest(args.manifest)
    expected_schema_hash = str(manifest["schema_hash"])
    seed = int(manifest.get("seed", 42))

    generator_source_hash = None
    if args.source_mode == "local":
        source_bundle = read_source_bundle()
        generator_source_hash = compute_source_hash(source_bundle)
        prompt = build_bake_prompt(
            source_bundle=source_bundle,
            generator_source_hash=generator_source_hash,
            expected_schema_hash=expected_schema_hash,
            seed=seed,
        )
        generator_repo = INLINE_SOURCE_REPO
        generator_sha = generator_source_hash
    else:
        if not args.generator_repo:
            raise RuntimeError("Provide --generator-repo or GENERATOR_REPO_URL when --source-mode=repo.")
        if not args.generator_sha:
            raise RuntimeError("Provide --generator-sha or GENERATOR_SHA when --source-mode=repo.")
        prompt = build_legacy_repo_bake_prompt(
            generator_repo=args.generator_repo,
            generator_ref=args.generator_sha,
            expected_schema_hash=expected_schema_hash,
            seed=seed,
        )
        generator_repo = args.generator_repo
        generator_sha = args.generator_sha

    response = create_interaction(api_key=api_key, agent=args.agent, prompt=prompt)

    interaction_id = read_attr(response, "id", "name")
    environment_id = read_environment_id(response)
    output_text = read_output_text(response)
    validate_bake_result(output_text, expected_schema_hash, environment_id)

    print(f"Interaction id: {interaction_id}")
    print(f"Environment id: {environment_id}")

    if not args.no_update:
        updated = update_manifest(
            manifest,
            environment_id=environment_id,
            generator_repo=generator_repo,
            generator_sha=generator_sha,
            interaction_id=interaction_id,
            generator_source_hash=generator_source_hash,
        )
        write_manifest(updated, args.manifest)
        print(f"Updated manifest: {args.manifest}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
