#!/usr/bin/env python3
"""
Continuous Learning v2 — Observation Hook (cross-platform Python)
Replaces observe.sh / PowerShell wrapper on Windows.

Usage: python observe.py [pre|post]
  pre  = PreToolUse event
  post = PostToolUse event (default)

Reads Claude Code hook JSON from stdin, writes an observation record
to {project_root}/.claude/projects/homunculus/projects/{id}/observations.jsonl
"""

import sys
import json
import os
import re
import hashlib
import subprocess
from pathlib import Path
from datetime import datetime, timezone

HOOK_PHASE = sys.argv[1] if len(sys.argv) > 1 else "post"
MAX_STDIN = 1024 * 1024
MAX_FIELD = 5000
MAX_FILE_MB = 10
SIGNAL_EVERY_N = int(os.environ.get("ECC_OBSERVER_SIGNAL_EVERY_N", "20"))

_SECRET_RE = re.compile(
    r"(?i)(api[_-]?key|token|secret|password|authorization|credentials?|auth)"
    r"""(["'\s:=]+)([A-Za-z]+\s+)?([A-Za-z0-9_\-/.+=]{8,})"""
)


def scrub(val) -> str:
    return _SECRET_RE.sub(
        lambda m: m.group(1) + m.group(2) + (m.group(3) or "") + "[REDACTED]",
        str(val),
    )


def _git_toplevel(cwd: str) -> str | None:
    try:
        r = subprocess.run(
            ["git", "-C", cwd, "rev-parse", "--show-toplevel"],
            capture_output=True, text=True, timeout=5,
        )
        return r.stdout.strip() if r.returncode == 0 else None
    except Exception:
        return None


def homunculus_dir(cwd: str) -> Path:
    """
    Resolution order:
    1. CLV2_HOMUNCULUS_DIR env var (explicit override)
    2. {git_repo_root}/.claude/projects/homunculus (project-local default)
    3. ~/.claude/homunculus (global fallback)
    """
    if env := os.environ.get("CLV2_HOMUNCULUS_DIR"):
        return Path(env)
    top = _git_toplevel(cwd)
    if top:
        return Path(top) / ".claude" / "projects" / "homunculus"
    return Path.home() / ".claude" / "homunculus"


def project_context(cwd: str, hom: Path) -> tuple[str, str, Path]:
    """Returns (project_id, project_name, project_dir)."""
    top = _git_toplevel(cwd)
    if not top:
        return "global", "global", hom

    project_name = Path(top).name

    # Prefer git remote URL for stable hash across machines
    try:
        r = subprocess.run(
            ["git", "-C", cwd, "remote", "get-url", "origin"],
            capture_output=True, text=True, timeout=5,
        )
        hash_src = r.stdout.strip() if r.returncode == 0 else top
    except Exception:
        hash_src = top

    # Strip embedded credentials (https://token@github.com → https://github.com)
    hash_src = re.sub(r"://[^@]+@", "://", hash_src)
    project_id = hashlib.sha256(hash_src.encode()).hexdigest()[:12]

    project_dir = hom / "projects" / project_id
    project_dir.mkdir(parents=True, exist_ok=True)

    return project_id, project_name, project_dir


def should_skip(data: dict) -> bool:
    """Skip non-human / automated sessions."""
    entrypoint = os.environ.get("CLAUDE_CODE_ENTRYPOINT", "cli")
    if entrypoint not in ("cli", "sdk-ts"):
        return True
    if os.environ.get("ECC_HOOK_PROFILE", "standard") == "minimal":
        return True
    if os.environ.get("ECC_SKIP_OBSERVE", "0") == "1":
        return True
    if data.get("agent_id"):
        return True
    cwd = data.get("cwd", "")
    skip_patterns = os.environ.get(
        "ECC_OBSERVE_SKIP_PATHS", "observer-sessions,.claude-mem"
    ).split(",")
    return any(p.strip() and p.strip() in cwd for p in skip_patterns)


def archive_if_large(obs_file: Path, project_dir: Path) -> None:
    if not obs_file.exists():
        return
    if obs_file.stat().st_size / (1024 * 1024) >= MAX_FILE_MB:
        archive = project_dir / "observations.archive"
        archive.mkdir(exist_ok=True)
        ts = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
        obs_file.rename(archive / f"observations-{ts}.jsonl")


def maybe_signal_observer(project_dir: Path, hom: Path) -> None:
    """Throttled SIGUSR1 to observer process — Unix only."""
    if sys.platform == "win32":
        return
    counter_file = project_dir / ".observer-signal-counter"
    try:
        count = int(counter_file.read_text().strip()) + 1 if counter_file.exists() else 1
        counter_file.write_text(str(0 if count >= SIGNAL_EVERY_N else count))
        if count < SIGNAL_EVERY_N:
            return
        import signal as _signal
        seen: set[int] = set()
        for pf in [project_dir / ".observer.pid", hom / ".observer.pid"]:
            if not pf.exists():
                continue
            try:
                pid = int(pf.read_text().strip())
                if pid > 1 and pid not in seen:
                    os.kill(pid, _signal.SIGUSR1)
                    seen.add(pid)
            except Exception:
                pass
    except Exception:
        pass


def main() -> None:
    raw = sys.stdin.buffer.read(MAX_STDIN)
    if not raw:
        return

    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return

    if should_skip(data):
        return

    cwd = data.get("cwd", os.getcwd())
    hom = homunculus_dir(cwd)

    # Respect disabled flag
    if (hom / "disabled").exists():
        return

    project_id, project_name, project_dir = project_context(cwd, hom)
    obs_file = project_dir / "observations.jsonl"
    archive_if_large(obs_file, project_dir)

    event = "tool_start" if HOOK_PHASE == "pre" else "tool_complete"
    tool_name = data.get("tool_name", data.get("tool", "unknown"))
    tool_input = data.get("tool_input", data.get("input", {}))
    tool_output = data.get("tool_response") or data.get("tool_output", data.get("output", ""))

    input_str = (json.dumps(tool_input) if isinstance(tool_input, dict) else str(tool_input))[:MAX_FIELD]
    output_str = (json.dumps(tool_output) if isinstance(tool_output, dict) else str(tool_output))[:MAX_FIELD]

    observation: dict = {
        "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "event": event,
        "tool": tool_name,
        "session": data.get("session_id", "unknown"),
        "project_id": project_id,
        "project_name": project_name,
    }
    if event == "tool_start":
        observation["input"] = scrub(input_str)
    else:
        observation["output"] = scrub(output_str)

    with obs_file.open("a", encoding="utf-8") as f:
        f.write(json.dumps(observation) + "\n")

    maybe_signal_observer(project_dir, hom)


if __name__ == "__main__":
    try:
        main()
    except Exception:
        pass  # Never block Claude on hook errors
