#!/usr/bin/env python3
"""
Hook: PostToolUse Write|Edit|MultiEdit
Tracks cumulative edit metrics per session and emits SIMPLIFY_TRIGGERED when
thresholds are breached. Thresholds can be customized via .ck.json:

{
  "simplify": {
    "threshold": {
      "enabled": true,
      "totalLoc": 400,
      "fileCount": 8,
      "singleFileLoc": 200,
      "sourceExtensions": [".ts", ".tsx", ".js", ".jsx", ".py"]
    }
  }
}
"""

import json
import os
import sys
from pathlib import Path


def find_repo_root(cwd: str) -> Path | None:
    for parent in [Path(cwd)] + list(Path(cwd).parents):
        if (parent / ".git").exists():
            return parent
    return None


def load_threshold_config(root: Path) -> dict:
    ck = root / ".ck.json"
    if ck.exists():
        try:
            return json.loads(ck.read_text(encoding="utf-8")).get("simplify", {}).get("threshold", {})
        except Exception:
            pass
    return {}


def state_file(root: Path, session_id: str) -> Path:
    d = root / ".claude" / "session-data"
    d.mkdir(parents=True, exist_ok=True)
    return d / f"simplify-tracker-{session_id}.json"


def load_state(path: Path) -> dict:
    if path.exists():
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {"files": {}, "total_loc": 0, "triggered": False}


def emit_context(message: str) -> None:
    print(
        json.dumps(
            {
                "hookSpecificOutput": {
                    "hookEventName": "PostToolUse",
                    "additionalContext": message,
                }
            }
        )
    )


def main() -> None:
    try:
        data = json.load(sys.stdin)
    except Exception:
        return

    if data.get("agent_id"):
        return

    session_id = data.get("session_id") or os.environ.get("CLAUDE_SESSION_ID", "default")
    cwd = data.get("cwd", os.getcwd())
    root = find_repo_root(cwd)
    if not root:
        return

    cfg = load_threshold_config(root)
    if not cfg.get("enabled", True):
        return

    threshold_total = cfg.get("totalLoc", 400)
    threshold_files = cfg.get("fileCount", 8)
    threshold_single = cfg.get("singleFileLoc", 200)

    sp = state_file(root, session_id)
    state = load_state(sp)
    if state.get("triggered"):
        return

    tool_input = data.get("tool_input", {})
    file_path = tool_input.get("file_path") or ""
    if not file_path:
        return

    source_extensions = set(cfg.get("sourceExtensions", []))
    if source_extensions and Path(file_path).suffix.lower() not in source_extensions:
        return

    content = tool_input.get("content") or tool_input.get("new_string") or ""
    lines = len(content.splitlines()) if content else 0

    state["files"][file_path] = state["files"].get(file_path, 0) + lines
    state["total_loc"] = sum(state["files"].values())
    sp.write_text(json.dumps(state), encoding="utf-8")

    breached = []
    if state["total_loc"] >= threshold_total:
        breached.append(f"total LOC {state['total_loc']} >= {threshold_total}")
    if len(state["files"]) >= threshold_files:
        breached.append(f"files edited {len(state['files'])} >= {threshold_files}")
    max_loc = max(state["files"].values(), default=0)
    if max_loc >= threshold_single:
        worst = max(state["files"], key=state["files"].get)
        breached.append(f"single-file {max_loc} >= {threshold_single} ({Path(worst).name})")

    if not breached:
        return

    state["triggered"] = True
    sp.write_text(json.dumps(state), encoding="utf-8")
    emit_context(
        "SIMPLIFY_TRIGGERED: Edit thresholds breached — "
        + "; ".join(breached)
        + ". Consider simplifying implementation and reducing scope before continuing."
    )


if __name__ == "__main__":
    try:
        main()
    except Exception:
        pass
