#!/usr/bin/env python3
"""
UserPromptSubmit hook — injects active plan context into each prompt.

Scans the plans/ directory for in-progress plan.md files and outputs
a brief reminder so Claude knows which plan is active and what phase
is next. Also detects cross-plan dependencies.

Cross-platform (Windows, macOS, Linux).
"""

import json
import os
import re
import sys
from pathlib import Path

PLANS_DIR = "plans"
STATUS_ACTIVE = "🟡"
STATUS_COMPLETE = "✅"
MAX_ACTIVE_PLANS = 3


def find_active_plans(root: Path) -> list[dict]:
    """Return active (in-progress) plans sorted by modification time, newest first."""
    plans_root = root / PLANS_DIR
    if not plans_root.exists():
        return []

    active = []
    for plan_dir in sorted(plans_root.iterdir()):
        if not plan_dir.is_dir():
            continue
        plan_file = plan_dir / "plan.md"
        if not plan_file.exists():
            continue

        content = plan_file.read_text(encoding="utf-8", errors="replace")

        # Skip completed plans
        if STATUS_COMPLETE in content:
            continue
        # Only include active/in-progress plans
        if STATUS_ACTIVE not in content:
            continue

        plan_info = parse_plan(plan_file, content)
        if plan_info:
            active.append(plan_info)

    # Sort newest-first by mtime
    active.sort(key=lambda p: p["mtime"], reverse=True)
    return active[:MAX_ACTIVE_PLANS]


def parse_plan(plan_file: Path, content: str) -> dict | None:
    """Extract key fields from a plan.md file."""
    name_match = re.search(r"^#\s+Plan:\s+(.+)$", content, re.MULTILINE)
    mode_match = re.search(r"^Mode:\s+(.+)$", content, re.MULTILINE)

    name = name_match.group(1).strip() if name_match else plan_file.parent.name
    mode = mode_match.group(1).strip() if mode_match else "Unknown"

    # Find next incomplete phase
    phases = re.findall(r"- \[([ x])\] Phase \d+: (.+)", content)
    next_phase = None
    completed_count = 0
    total_count = len(phases)
    for done, phase_name in phases:
        if done == "x":
            completed_count += 1
        elif next_phase is None:
            next_phase = phase_name.split("—")[0].strip()

    return {
        "name": name,
        "mode": mode,
        "path": str(plan_file),
        "next_phase": next_phase,
        "progress": f"{completed_count}/{total_count}",
        "mtime": plan_file.stat().st_mtime,
    }


def build_context(active_plans: list[dict]) -> str:
    if not active_plans:
        return ""

    lines = ["Active plan context:"]
    for plan in active_plans:
        next_info = f"next → {plan['next_phase']}" if plan["next_phase"] else "all phases complete"
        lines.append(
            f"  [{plan['mode']}] {plan['name']} ({plan['progress']} phases) — {next_info}"
        )
        lines.append(f"  Plan file: {plan['path']}")

    return "\n".join(lines)


def main():
    # Read the hook input (UserPromptSubmit payload from stdin)
    try:
        payload = json.loads(sys.stdin.read())
    except (json.JSONDecodeError, EOFError):
        payload = {}

    root = Path(os.getcwd())
    active_plans = find_active_plans(root)
    context = build_context(active_plans)

    if not context:
        # Nothing to inject — exit cleanly
        sys.exit(0)

    output = json.dumps({"hookSpecificOutput": {"additionalContext": context}})
    sys.stdout.write(output)
    sys.stdout.flush()


if __name__ == "__main__":
    main()
