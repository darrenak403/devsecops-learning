from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run Alembic migrations")
    parser.add_argument(
        "revision",
        nargs="?",
        default="head",
        help="Alembic target revision (default: head)",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    project_root = Path(__file__).resolve().parent

    command = [sys.executable, "-m", "alembic", "upgrade", args.revision]
    result = subprocess.run(command, cwd=project_root)
    return result.returncode


if __name__ == "__main__":
    raise SystemExit(main())