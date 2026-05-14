#!/usr/bin/env python3
"""
Stop Hook (Session End) — persist session summary after each response.
Ports session-end.js to Python.
"""
import json
import os
import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "lib"))
from utils import (
    ensure_dir, get_date_string, get_project_name,
    get_session_id_short, get_sessions_dir, get_time_string,
    log, read_file, strip_ansi, write_file,
)

SUMMARY_START = "<!-- ECC:SUMMARY:START -->"
SUMMARY_END = "<!-- ECC:SUMMARY:END -->"
SESSION_SEP = "\n---\n"
MAX_STDIN = 1024 * 1024


# ── transcript parsing ─────────────────────────────────────────────────────────

def extract_session_summary(transcript_path: str) -> dict | None:
    try:
        content = Path(transcript_path).read_text(encoding="utf-8", errors="replace")
    except Exception:
        return None

    lines = [ln for ln in content.splitlines() if ln.strip()]
    user_messages: list[str] = []
    tools_used: set[str] = set()
    files_modified: set[str] = set()
    parse_errors = 0

    for line in lines:
        try:
            entry = json.loads(line)

            # User messages
            role = (
                entry.get("role")
                or entry.get("type")
                or (entry.get("message") or {}).get("role")
            )
            if role == "user":
                raw = (entry.get("message") or {}).get("content") or entry.get("content")
                if isinstance(raw, str):
                    text = raw
                elif isinstance(raw, list):
                    text = " ".join((c or {}).get("text", "") for c in raw)
                else:
                    text = ""
                cleaned = strip_ansi(text).strip()
                if cleaned:
                    user_messages.append(cleaned[:200])

            # Direct tool_use entries
            if entry.get("type") == "tool_use" or entry.get("tool_name"):
                tool = entry.get("tool_name") or entry.get("name", "")
                if tool:
                    tools_used.add(tool)
                fp = (entry.get("tool_input") or {}).get("file_path") or (entry.get("input") or {}).get("file_path", "")
                if fp and tool in ("Edit", "Write"):
                    files_modified.add(fp)

            # Tool use blocks inside assistant messages
            if entry.get("type") == "assistant":
                for block in ((entry.get("message") or {}).get("content") or []):
                    if (block or {}).get("type") == "tool_use":
                        tool = block.get("name", "")
                        if tool:
                            tools_used.add(tool)
                        fp = (block.get("input") or {}).get("file_path", "")
                        if fp and tool in ("Edit", "Write"):
                            files_modified.add(fp)

        except Exception:
            parse_errors += 1

    if parse_errors:
        log(f"[SessionEnd] Skipped {parse_errors}/{len(lines)} unparseable transcript lines")

    if not user_messages:
        return None

    return {
        "userMessages": user_messages[-10:],
        "toolsUsed": list(tools_used)[:20],
        "filesModified": list(files_modified)[:30],
        "totalMessages": len(user_messages),
    }


# ── session file management ────────────────────────────────────────────────────

def get_git_branch() -> str:
    try:
        r = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            capture_output=True, text=True, timeout=5,
        )
        return r.stdout.strip() if r.returncode == 0 else "unknown"
    except Exception:
        return "unknown"


def get_session_metadata() -> dict:
    return {
        "project": get_project_name() or "unknown",
        "branch": get_git_branch(),
        "worktree": os.getcwd(),
    }


def _extract_header_field(content: str, label: str) -> str | None:
    m = re.search(rf"\*\*{re.escape(label)}:\*\*\s*(.+)$", content, re.MULTILINE)
    return m.group(1).strip() if m else None


def build_session_header(today: str, current_time: str, metadata: dict, existing: str = "") -> str:
    heading_m = re.search(r"^#\s+.+$", existing, re.MULTILINE)
    heading = heading_m.group(0) if heading_m else f"# Session: {today}"
    date = _extract_header_field(existing, "Date") or today
    started = _extract_header_field(existing, "Started") or current_time
    return "\n".join([
        heading,
        f"**Date:** {date}",
        f"**Started:** {started}",
        f"**Last Updated:** {current_time}",
        f"**Project:** {metadata['project']}",
        f"**Branch:** {metadata['branch']}",
        f"**Worktree:** {metadata['worktree']}",
        "",
    ])


def merge_session_header(content: str, today: str, current_time: str, metadata: dict) -> str | None:
    idx = content.find(SESSION_SEP)
    if idx == -1:
        return None
    existing_header = content[:idx]
    body = content[idx + len(SESSION_SEP):]
    new_header = build_session_header(today, current_time, metadata, existing_header)
    return f"{new_header}{SESSION_SEP}{body}"


def build_summary_section(summary: dict) -> str:
    s = "## Session Summary\n\n### Tasks\n"
    for msg in summary["userMessages"]:
        clean = msg.replace("\n", " ").replace("`", "\\`")
        s += f"- {clean}\n"
    s += "\n"
    if summary["filesModified"]:
        s += "### Files Modified\n"
        for f in summary["filesModified"]:
            s += f"- {f}\n"
        s += "\n"
    if summary["toolsUsed"]:
        s += f"### Tools Used\n{', '.join(summary['toolsUsed'])}\n\n"
    s += f"### Stats\n- Total user messages: {summary['totalMessages']}\n"
    return s


def build_summary_block(summary: dict) -> str:
    return f"{SUMMARY_START}\n{build_summary_section(summary).strip()}\n{SUMMARY_END}"


# ── main ───────────────────────────────────────────────────────────────────────

def main() -> None:
    stdin_data = sys.stdin.read(MAX_STDIN)
    transcript_path: str | None = None
    try:
        transcript_path = json.loads(stdin_data).get("transcript_path")
    except Exception:
        transcript_path = os.environ.get("CLAUDE_TRANSCRIPT_PATH")

    sessions_dir = get_sessions_dir()
    today = get_date_string()
    short_id = get_session_id_short()
    session_file = sessions_dir / f"{today}-{short_id}-session.tmp"
    metadata = get_session_metadata()
    current_time = get_time_string()

    ensure_dir(sessions_dir)

    summary = None
    if transcript_path:
        if Path(transcript_path).exists():
            summary = extract_session_summary(transcript_path)
        else:
            log(f"[SessionEnd] Transcript not found: {transcript_path}")

    if session_file.exists():
        existing = read_file(session_file) or ""
        updated = existing

        merged = merge_session_header(existing, today, current_time, metadata)
        if merged:
            updated = merged
        else:
            log(f"[SessionEnd] Failed to normalize header in {session_file}")

        if summary and updated:
            new_block = build_summary_block(summary)
            if SUMMARY_START in updated and SUMMARY_END in updated:
                updated = re.sub(
                    re.escape(SUMMARY_START) + r"[\s\S]*?" + re.escape(SUMMARY_END),
                    new_block,
                    updated,
                )
            else:
                # Migration: replace legacy section format
                updated = re.sub(
                    r"## (?:Session Summary|Current State)[\s\S]*?$",
                    f"{new_block}\n\n### Notes for Next Session\n-\n\n### Context to Load\n```\n[relevant files]\n```\n",
                    updated,
                )

        if updated:
            write_file(session_file, updated)
        log(f"[SessionEnd] Updated session file: {session_file}")

    else:
        if summary:
            body = (
                f"{build_summary_block(summary)}\n\n"
                "### Notes for Next Session\n-\n\n"
                "### Context to Load\n```\n[relevant files]\n```"
            )
        else:
            body = (
                "## Current State\n\n[Session context goes here]\n\n"
                "### Completed\n- [ ]\n\n"
                "### In Progress\n- [ ]\n\n"
                "### Notes for Next Session\n-\n\n"
                "### Context to Load\n```\n[relevant files]\n```"
            )
        header = build_session_header(today, current_time, metadata)
        write_file(session_file, f"{header}{SESSION_SEP}{body}\n")
        log(f"[SessionEnd] Created session file: {session_file}")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        log(f"[SessionEnd] Error: {e}")
        sys.exit(0)
