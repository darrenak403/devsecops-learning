"""Repair questions where MCQ labels E-H were merged into stem by markdown parser bug.

Default: --dry-run (scan + print proposed fixes, no DB writes).
Use --apply after reviewing output to persist fixes and bump question-source cache versions.

Usage:
  python scripts/repair_questions_orphan_options.py
  python scripts/repair_questions_orphan_options.py --source-id <uuid>
  python scripts/repair_questions_orphan_options.py --apply
"""

from __future__ import annotations

import argparse
import hashlib
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import select

from app.db.session import SessionLocal
from app.models.question import Question
from app.models.question_source import QuestionSource
from app.models.subject import Subject
from app.services.cache_service import cache_service

_LABEL_RANGE = frozenset("ABCDEFGH")
_LABEL_TAIL_RE = re.compile(r"(?:(?<=^)|(?<=\s))([A-H])[\).:\-]\s+", re.IGNORECASE)


def _letter_labels_from_answers(answers_json: list | None, answer_text: str | None) -> set[str]:
    labels: set[str] = set()
    if answers_json:
        for raw in answers_json:
            s = str(raw).strip().upper()
            if len(s) == 1 and s in _LABEL_RANGE:
                labels.add(s)
    if answer_text:
        for part in re.split(r"[;,/]+", answer_text):
            s = part.strip().upper()
            if len(s) == 1 and s in _LABEL_RANGE:
                labels.add(s)
    return labels


def _option_labels(options_json: list | None) -> set[str]:
    if not options_json:
        return set()
    return {
        str(o.get("label", "")).strip().upper()
        for o in options_json
        if str(o.get("label", "")).strip()
    }


def _parse_tail_options(tail: str) -> list[dict[str, str]]:
    matches = list(_LABEL_TAIL_RE.finditer(tail))
    if not matches or matches[0].start() != 0:
        return []
    out: list[dict[str, str]] = []
    for i, m in enumerate(matches):
        label = m.group(1).upper()
        start = m.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(tail)
        text = tail[start:end].strip()
        out.append({"label": label, "text": text})
    return out


def _find_orphan_cut_index(stem: str, first_missing: str) -> int | None:
    """Last match: orphan options are assumed at end of stem."""
    pat = re.compile(rf"(?:^|\s){re.escape(first_missing)}[\).:\-]\s+", re.IGNORECASE)
    matches = list(pat.finditer(stem))
    if not matches:
        return None
    return matches[-1].start()


def _normalized_hash(stem: str, options: list[dict], answer_text: str) -> str:
    hash_source = f"{stem}|{options}|{answer_text}".encode("utf-8")
    return f"sha256:{hashlib.sha256(hash_source).hexdigest()}"


def repair_row(question: Question) -> dict | None:
    """Return change dict or None if this row does not match the bug pattern."""
    opts = list(question.options_json or [])
    opt_labels = _option_labels(opts)
    ans_labels = _letter_labels_from_answers(question.answers_json, question.answer_text)
    missing_from_answers = ans_labels - opt_labels
    missing_from_stem = {
        label
        for label in _LABEL_RANGE
        if label not in opt_labels and _find_orphan_cut_index(question.stem, label) is not None
    }
    missing = missing_from_answers | missing_from_stem
    if not missing:
        return None
    cut_candidates = [
        _find_orphan_cut_index(question.stem, label)
        for label in sorted(missing)
    ]
    valid_cuts = [idx for idx in cut_candidates if idx is not None]
    cut = min(valid_cuts) if valid_cuts else None
    if cut is None:
        return {"status": "skip", "reason": "no_pattern_in_stem", "missing": sorted(missing)}
    cleaned_stem = question.stem[:cut].rstrip()
    tail = question.stem[cut:].strip()
    parsed = _parse_tail_options(tail)
    if not parsed:
        return {"status": "skip", "reason": "unparseable_tail", "tail_preview": tail[:160]}
    parsed_labels_list = [p["label"] for p in parsed]
    if len(parsed_labels_list) != len(set(parsed_labels_list)):
        return {
            "status": "skip",
            "reason": "duplicate_labels_in_tail",
            "tail_preview": tail[:160],
            "labels": parsed_labels_list,
        }
    parsed_labels = set(parsed_labels_list)
    if not parsed_labels <= missing:
        return {
            "status": "skip",
            "reason": "parsed_tail_has_unexpected_labels",
            "missing": sorted(missing),
            "parsed_labels": sorted(parsed_labels),
        }
    if not missing_from_answers <= parsed_labels:
        return {
            "status": "skip",
            "reason": "parsed_tail_missing_answer_labels",
            "missing_answer_labels": sorted(missing_from_answers),
            "parsed_labels": sorted(parsed_labels),
        }
    merged = opts + [p for p in parsed if p["label"] not in opt_labels]
    new_hash = _normalized_hash(cleaned_stem, merged, question.answer_text)
    return {
        "status": "ok",
        "cleaned_stem": cleaned_stem,
        "new_options": merged,
        "new_hash": new_hash,
        "parsed_tail": parsed,
    }


def _preview(text: str, limit: int = 140) -> str:
    t = text.replace("\n", " ")
    return t if len(t) <= limit else t[: limit - 3] + "..."


def main() -> int:
    parser = argparse.ArgumentParser(description="Repair orphan E-H options merged into question stem.")
    parser.add_argument("--apply", action="store_true", help="Persist fixes and bump cache versions (default: dry-run).")
    parser.add_argument("--source-id", default=None, help="Only scan questions for this question_sources.id.")
    args = parser.parse_args()

    scanned = bug_candidates = repaired = skipped = 0
    affected_slugs: set[str] = set()

    db = SessionLocal()
    try:
        stmt = (
            select(Question, Subject.slug)
            .join(QuestionSource, Question.source_id == QuestionSource.id)
            .join(Subject, QuestionSource.subject_id == Subject.id)
            .where(QuestionSource.is_deleted.is_(False))
        )
        if args.source_id:
            stmt = stmt.where(Question.source_id == args.source_id)

        for question, slug in db.execute(stmt).all():
            scanned += 1
            result = repair_row(question)
            if result is None:
                continue
            bug_candidates += 1
            if result["status"] != "ok":
                skipped += 1
                detail = {k: v for k, v in result.items() if k != "status"}
                print(
                    f"SKIP question_id={question.id} source_id={question.source_id} ordinal={question.ordinal} "
                    f"slug={slug} reason={result.get('reason')} detail={detail}"
                )
                continue

            repaired += 1
            mode = "APPLY" if args.apply else "DRY-RUN"
            print(
                f"{mode} question_id={question.id} source_id={question.source_id} ordinal={question.ordinal} slug={slug}\n"
                f"  stem_was: {_preview(question.stem)}\n"
                f"  stem_new: {_preview(result['cleaned_stem'])}\n"
                f"  appended_options={result['parsed_tail']}"
            )

            if args.apply:
                question.stem = result["cleaned_stem"]
                question.options_json = result["new_options"]
                question.normalized_hash = result["new_hash"]
                db.add(question)
                affected_slugs.add(slug.lower())

        if args.apply:
            if repaired > 0:
                db.commit()
                cache_service.bump_version("qs:subjects:ver")
                for s in sorted(affected_slugs):
                    cache_service.bump_version(f"qs:subject:{s}:ver")
                print(f"\nCache bumped: qs:subjects:ver + qs:subject:<slug>:ver for {sorted(affected_slugs)}")
            else:
                db.rollback()
        else:
            db.rollback()

        repair_line = f"committed={repaired}" if args.apply else f"would_repair={repaired}"
        print(f"\nSummary: scanned={scanned} bug_candidates={bug_candidates} {repair_line} skipped={skipped}")
        return 0
    except Exception as exc:
        db.rollback()
        print(f"Lỗi: {exc}", file=sys.stderr)
        raise
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
