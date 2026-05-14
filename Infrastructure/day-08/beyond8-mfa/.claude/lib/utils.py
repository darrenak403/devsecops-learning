#!/usr/bin/env python3
"""Shared utilities for Claude Code Python hooks."""
import fnmatch
import hashlib
import os
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path

SESSION_DATA_DIR = "session-data"
WINDOWS_RESERVED = {
    "CON", "PRN", "AUX", "NUL",
    "COM1", "COM2", "COM3", "COM4", "COM5", "COM6", "COM7", "COM8", "COM9",
    "LPT1", "LPT2", "LPT3", "LPT4", "LPT5", "LPT6", "LPT7", "LPT8", "LPT9",
}


def get_home_dir() -> Path:
    explicit = os.environ.get("HOME") or os.environ.get("USERPROFILE")
    if explicit:
        return Path(explicit)
    return Path.home()


def get_claude_dir() -> Path:
    return get_home_dir() / ".claude"


def _run_git(*args: str, cwd: str | None = None) -> str:
    try:
        r = subprocess.run(
            ["git"] + list(args),
            capture_output=True, text=True, timeout=5,
            cwd=cwd or os.getcwd(),
        )
        return r.stdout.strip() if r.returncode == 0 else ""
    except Exception:
        return ""


def get_project_root() -> Path | None:
    common = _run_git("rev-parse", "--path-format=absolute", "--git-common-dir")
    if common:
        p = Path(common)
        if p.name == ".git":
            return p.parent
        s = str(p)
        marker = os.sep + ".git"
        idx = s.lower().rfind(marker.lower())
        if idx > 0:
            return Path(s[:idx])

    top = _run_git("rev-parse", "--show-toplevel")
    if top:
        return Path(top)

    env = os.environ.get("CLAUDE_PROJECT_DIR")
    if env and Path(env).exists():
        return Path(env)

    return None


def get_homunculus_dir() -> Path:
    root = get_project_root()
    if root:
        return root / ".claude" / "projects" / "homunculus"
    return get_claude_dir() / "homunculus"


def get_sessions_dir() -> Path:
    root = get_project_root()
    if root:
        return root / ".claude" / SESSION_DATA_DIR
    return get_claude_dir() / SESSION_DATA_DIR


def get_session_search_dirs() -> list[Path]:
    root = get_project_root()
    if root:
        return [root / ".claude" / SESSION_DATA_DIR]
    seen: list[Path] = []
    for d in [get_claude_dir() / SESSION_DATA_DIR, get_claude_dir() / "sessions"]:
        if d not in seen:
            seen.append(d)
    return seen


def get_learned_skills_dir() -> Path:
    return get_claude_dir() / "skills" / "learned"


def get_project_name() -> str | None:
    top = _run_git("rev-parse", "--show-toplevel")
    if top:
        return Path(top).name
    return Path(os.getcwd()).name or None


def ensure_dir(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    return path


def get_date_string() -> str:
    return datetime.now().strftime("%Y-%m-%d")


def get_time_string() -> str:
    return datetime.now().strftime("%H:%M")


def get_datetime_string() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def sanitize_session_id(raw: str) -> str | None:
    if not raw:
        return None
    has_non_ascii = any(ord(c) > 0x7F for c in raw)
    normalized = raw.lstrip(".")
    sanitized = re.sub(r"[^a-zA-Z0-9_-]", "-", normalized)
    sanitized = re.sub(r"-{2,}", "-", sanitized).strip("-")
    if sanitized:
        suffix = hashlib.sha256(normalized.encode()).hexdigest()[:6]
        if sanitized.upper() in WINDOWS_RESERVED or has_non_ascii:
            return f"{sanitized}-{suffix}"
        return sanitized
    meaningful = re.sub(r"[\s\W]", "", normalized, flags=re.UNICODE)
    if not meaningful:
        return None
    return hashlib.sha256(normalized.encode()).hexdigest()[:8]


def get_session_id_short(fallback: str = "default") -> str:
    sid = os.environ.get("CLAUDE_SESSION_ID", "")
    if sid:
        s = sanitize_session_id(sid[-8:])
        if s:
            return s
    return (
        sanitize_session_id(get_project_name() or "")
        or sanitize_session_id(fallback)
        or "default"
    )


def find_files(
    dir_path: Path,
    pattern: str,
    max_age_days: float | None = None,
) -> list[dict]:
    """Return [{path: Path, mtime: float}] sorted newest first."""
    results = []
    try:
        for entry in dir_path.iterdir():
            if not entry.is_file() or not fnmatch.fnmatch(entry.name, pattern):
                continue
            try:
                mtime = entry.stat().st_mtime
            except OSError:
                continue
            if max_age_days is not None:
                age = (datetime.now().timestamp() - mtime) / 86400
                if age > max_age_days:
                    continue
            results.append({"path": entry, "mtime": mtime})
    except Exception:
        pass
    results.sort(key=lambda x: x["mtime"], reverse=True)
    return results


def read_file(path: Path) -> str | None:
    try:
        return path.read_text(encoding="utf-8", errors="replace")
    except Exception:
        return None


def write_file(path: Path, content: str) -> None:
    ensure_dir(path.parent)
    path.write_text(content, encoding="utf-8")


def append_file(path: Path, content: str) -> None:
    ensure_dir(path.parent)
    with open(path, "a", encoding="utf-8") as f:
        f.write(content)


_ANSI_RE = re.compile(
    r"\x1b(?:\[[0-9;?]*[A-Za-z]|\][^\x07\x1b]*(?:\x07|\x1b\\)|\([A-Z]|[A-Z])"
)


def strip_ansi(s: str) -> str:
    return _ANSI_RE.sub("", s) if isinstance(s, str) else ""


def log(msg: str) -> None:
    print(msg, file=sys.stderr)
