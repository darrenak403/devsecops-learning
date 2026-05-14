#!/usr/bin/env python3
"""
PreCompact Hook — save state before context compaction.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "lib"))
from utils import (
    append_file, ensure_dir, find_files,
    get_datetime_string, get_sessions_dir, get_time_string, log,
)


def main() -> None:
    sessions_dir = get_sessions_dir()
    ensure_dir(sessions_dir)

    timestamp = get_datetime_string()
    append_file(sessions_dir / "compaction-log.txt", f"[{timestamp}] Context compaction triggered\n")

    active = find_files(sessions_dir, "*-session.tmp")
    if active:
        time_str = get_time_string()
        append_file(
            active[0]["path"],
            f"\n---\n**[Compaction occurred at {time_str}]** - Context was summarized\n",
        )

    log("[PreCompact] State saved before compaction")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        log(f"[PreCompact] Error: {e}")
