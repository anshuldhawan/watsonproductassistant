#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'USAGE'
Usage:
  scripts/run_gemini_demo_bake.sh [--python <path>] [--no-update]

Required:
  GEMINI_API_KEY must be set in .env or the process environment.

Options:
  --python <path>    Python 3.10+ executable to use.
  --no-update        Run verification but do not update demo-dataset-manifest.json.
  -h, --help         Show this help.
USAGE
}

PYTHON_BIN="${PYTHON_BIN:-}"
NO_UPDATE=""

if [[ -f ".env" ]]; then
  set -a
  # shellcheck disable=SC1091
  source ".env"
  set +a
  PYTHON_BIN="${PYTHON_BIN:-$PYTHON_BIN}"
fi

while [[ $# -gt 0 ]]; do
  case "$1" in
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

if [[ -z "$PYTHON_BIN" ]]; then
  if [[ -x ".venv-gemini/bin/python" ]]; then
    PYTHON_BIN=".venv-gemini/bin/python"
  elif command -v python3.10 >/dev/null 2>&1; then
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

ARGS=(scripts/bake_gemini_demo_environment.py)
if [[ -n "$NO_UPDATE" ]]; then
  ARGS+=(--no-update)
fi

exec "$PYTHON_BIN" "${ARGS[@]}"
