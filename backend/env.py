import os
from pathlib import Path
from typing import Optional


PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_ENV_PATH = PROJECT_ROOT / ".env"


def load_project_env(env_path: Optional[Path] = None, override: bool = False) -> bool:
    """
    Load project-local environment variables from .env.

    Returns True when a file was found and loaded. Existing process environment
    values win by default so shell-provided secrets override local defaults.
    """
    path = env_path or DEFAULT_ENV_PATH
    if not path.exists():
        return False

    try:
        from dotenv import load_dotenv
    except ImportError:
        _load_env_fallback(path, override=override)
        return True

    load_dotenv(dotenv_path=path, override=override)
    return True


def _load_env_fallback(path: Path, override: bool = False) -> None:
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue

        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if not key:
            continue
        if override or key not in os.environ:
            os.environ[key] = value
