#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'USAGE'
Usage:
  scripts/run_bake_gemini_environment.sh

Required:
  GEMINI_API_KEY must be set in your environment.

Options:
  --source-mode <mode>
                    Source mode: local (default) or repo.
  --repo <url>       Git repo Gemini should clone in repo mode.
                    Can also be set with GENERATOR_REPO_URL.
  --sha <ref>        Commit SHA, branch, or tag to checkout in repo mode.
                    Can also be set with GENERATOR_SHA.
  --python <path>    Python 3.10+ executable to use. Default: python3.10,
                    then python3.
  --no-update        Run bake verification but do not update dataset-manifest.json.
  -h, --help         Show this help.

Example:
  export GEMINI_API_KEY="..."
  scripts/run_bake_gemini_environment.sh
USAGE
}

REPO="${GENERATOR_REPO_URL:-}"
SHA="${GENERATOR_SHA:-}"
SOURCE_MODE="${GEMINI_BAKE_SOURCE_MODE:-local}"
PYTHON_BIN="${PYTHON_BIN:-}"
NO_UPDATE=""

if [[ -f ".env" ]]; then
  set -a
  # shellcheck disable=SC1091
  source ".env"
  set +a
  REPO="${GENERATOR_REPO_URL:-$REPO}"
  SHA="${GENERATOR_SHA:-$SHA}"
  SOURCE_MODE="${GEMINI_BAKE_SOURCE_MODE:-$SOURCE_MODE}"
  PYTHON_BIN="${PYTHON_BIN:-$PYTHON_BIN}"
fi

while [[ $# -gt 0 ]]; do
  case "$1" in
    --source-mode)
      SOURCE_MODE="${2:-}"
      shift 2
      ;;
    --repo)
      REPO="${2:-}"
      shift 2
      ;;
    --sha)
      SHA="${2:-}"
      shift 2
      ;;
    --python)
      PYTHON_BIN="${2:-}"
      shift 2
      ;;
    --no-update)
      NO_UPDATE="--no-update"
      shift
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "Unknown argument: $1" >&2
      usage >&2
      exit 2
      ;;
  esac
done

if [[ -z "${GEMINI_API_KEY:-}" ]]; then
  echo "GEMINI_API_KEY is required." >&2
  exit 1
fi

if [[ "$SOURCE_MODE" != "local" && "$SOURCE_MODE" != "repo" ]]; then
  echo "--source-mode must be 'local' or 'repo'." >&2
  exit 1
fi

if [[ "$SOURCE_MODE" == "repo" ]]; then
  if [[ -z "$REPO" ]]; then
    echo "--repo or GENERATOR_REPO_URL is required when --source-mode=repo." >&2
    exit 1
  fi

  if [[ -z "$SHA" ]]; then
    echo "--sha or GENERATOR_SHA is required when --source-mode=repo." >&2
    exit 1
  fi
fi

if [[ -z "$PYTHON_BIN" ]]; then
  if command -v python3.10 >/dev/null 2>&1; then
    PYTHON_BIN="python3.10"
  elif command -v python3 >/dev/null 2>&1; then
    PYTHON_BIN="python3"
  else
    echo "No Python executable found. Install Python 3.10+." >&2
    exit 1
  fi
fi

"$PYTHON_BIN" - <<'PY'
import sys
if sys.version_info < (3, 10):
    raise SystemExit("Python 3.10+ is required for google-genai>=1.55.0.")
PY

ARGS=(scripts/bake_gemini_environment.py --source-mode "$SOURCE_MODE")

if [[ "$SOURCE_MODE" == "repo" ]]; then
  ARGS+=(--generator-repo "$REPO" --generator-sha "$SHA")
fi

if [[ -n "$NO_UPDATE" ]]; then
  ARGS+=(--no-update)
fi

exec "$PYTHON_BIN" "${ARGS[@]}"
