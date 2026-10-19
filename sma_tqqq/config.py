"""Reads settings from the environment, with an optional .env file at the project root."""

import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def _load_env_file():
    path = ROOT / ".env"
    if not path.exists():
        return
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value


_load_env_file()


def host():
    return os.environ.get("SMA_TQQQ_HOST", "127.0.0.1")


def port():
    return int(os.environ.get("SMA_TQQQ_PORT", "8742"))


def history_ttl_seconds():
    return int(os.environ.get("SMA_TQQQ_HISTORY_TTL_MINUTES", "30")) * 60


def quote_ttl_seconds():
    return int(os.environ.get("SMA_TQQQ_QUOTE_TTL_SECONDS", "120"))


def data_dir():
    return Path(os.environ.get("SMA_TQQQ_DATA_DIR", str(ROOT / "data")))
