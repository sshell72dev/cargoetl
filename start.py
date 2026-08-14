"""Start API + Next.js from the repo root."""

from __future__ import annotations

import os
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent
BACKEND = ROOT / "backend"
FRONTEND = ROOT / "frontend"


def main() -> None:
    env = os.environ.copy()
    env.setdefault("PYTHONPATH", str(BACKEND))
    api = subprocess.Popen(
        [
            sys.executable,
            "-m",
            "uvicorn",
            "app.main:app",
            "--app-dir",
            str(BACKEND),
            "--reload",
            "--host",
            "127.0.0.1",
            "--port",
            "8000",
        ],
        cwd=str(BACKEND),
        env=env,
    )
    time.sleep(0.8)
    next_js = FRONTEND / "node_modules" / "next" / "dist" / "bin" / "next"
    web = subprocess.Popen(
        ["node", str(next_js), "dev", "--port", "3000"],
        cwd=str(FRONTEND),
        env=env,
    )
    print("API  http://127.0.0.1:8000/api/health")
    print("UI   http://127.0.0.1:3000")
    try:
        web.wait()
    finally:
        api.terminate()
        web.terminate()


if __name__ == "__main__":
    main()
