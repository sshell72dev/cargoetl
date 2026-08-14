from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent.parent.parent / "data"


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
