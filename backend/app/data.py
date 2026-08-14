from __future__ import annotations

import json
import os
from functools import lru_cache
from pathlib import Path


def _resolve_data_dir() -> Path:
    if os.environ.get("DATA_DIR"):
        return Path(os.environ["DATA_DIR"])
    here = Path(__file__).resolve()
    for candidate in (here.parents[1] / "data", here.parents[2] / "data"):
        if (candidate / "dispatchers.json").exists():
            return candidate
    return here.parents[2] / "data"


DATA_DIR = _resolve_data_dir()


def _read(name: str):
    path = DATA_DIR / name
    if not path.exists():
        raise FileNotFoundError(
            f"Missing {path}. Run: python scripts/generate_data.py"
        )
    return json.loads(path.read_text(encoding="utf-8"))


@lru_cache(maxsize=1)
def dispatchers() -> list[dict]:
    return _read("dispatchers.json")


@lru_cache(maxsize=1)
def loads() -> list[dict]:
    return _read("loads.json")


@lru_cache(maxsize=1)
def events() -> list[dict]:
    return _read("events.json")


def dispatcher_map() -> dict[str, dict]:
    return {d["id"]: d for d in dispatchers()}
