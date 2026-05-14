import hashlib
import logging
import math
import re
import unicodedata

from fastapi import HTTPException, UploadFile, status
from sqlalchemy import event
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

from app.crud import crud_question_source
from app.crud.crud_question_source_async import crud_question_source_async
from app.services.cache_service import cache_service

_SUBJECT_PATTERN = re.compile(r"^[A-Z]{3,4}[0-9]{3}[A-Z]?$")
_TERM_PATTERN = re.compile(r"^(SP|SU|FA)$")
_YEAR_PATTERN = re.compile(r"^(\d{2}|\d{4})$")
_TYPE_PATTERN = re.compile(r"^(FE|RE|TE1|TE2|BLOCK5|C1FE|C2FE|FINAL)$")
_QUESTION_START = re.compile(r"^\s*(?:(?:C[ÂA]U)|QUESTION)?\s*\d+\s*[\).:\-]\s*(.+)$", flags=re.IGNORECASE)
_OPTION_LINE = re.compile(r"^\s*([A-H])[\).:\-]\s*(.+)$", flags=re.IGNORECASE)
_ANSWER_LINE = re.compile(r"^\s*(?:(?:Đ|D)[ÁA]P\s*Á?N|ANSWER)\s*[:\-]\s*(.+)$", flags=re.IGNORECASE)
_INLINE_ANSWER = re.compile(r"\s*(?:(?:Đ|D)[ÁA]P\s*Á?N|ANSWER)\s*[:\-]\s*([A-H](?:\s*[,;/]\s*[A-H])*)\s*$", flags=re.IGNORECASE)
_MAX_UPLOAD_BYTES = 5 * 1024 * 1024
_CACHE_SUBJECTS_TTL_SECONDS = 3600
_CACHE_SUBJECT_READ_TTL_SECONDS = 1800
_CACHE_DECK_LIST_TTL_SECONDS = 600
_CACHE_DECK_QUESTIONS_TTL_SECONDS = 1800
logger = logging.getLogger(__name__)


def _error(status_code: int, code: str, message: str, details: dict | None = None) -> HTTPException:
    return HTTPException(status_code=status_code, detail={"error": {"code": code, "message": message, "details": details or {}}})


def _normalize_filename(filename: str) -> str:
    normalized = unicodedata.normalize("NFKC", filename)
    normalized = re.sub(r"\.md$", "", normalized, flags=re.IGNORECASE).upper().replace("_", " ")
    normalized = re.sub(r"\s*-\s*", " - ", normalized)
    normalized = re.sub(r"\s+", " ", normalized).strip()
    return normalized


def _to_year(raw_year: str) -> int:
    return int(f"20{raw_year}") if len(raw_year) == 2 else int(raw_year)


def _is_aggregated_bank_filename(file_name: str) -> bool:
    normalized = unicodedata.normalize("NFKC", file_name).strip().lower()
    return normalized == "cau-hoi-tong-hop.md" or normalized == "cau-hoi-tong-hop"


_EXAM_SORT_TERM_ORDER = {"SP": 1, "SU": 2, "FA": 3}
# FA2026, FA25, FA 2024, FA-2024, MLN122_SP26_C1FE — \b alone fails on FA+digits (both \w).
_TERM_YEAR_SORT_PATTERN = re.compile(r"(?<![A-Z])(SP|SU|FA)[\s\-_]*([0-9]{4}|[0-9]{2})(?![0-9])")


def filter_subject_deck_payloads_by_q(decks: list[dict], q: str | None) -> list[dict]:
    """Giữ deck dicts khớp substring `q` trên fileName / examCode (giống admin list sources)."""
    q_norm = (q or "").strip() or None
    if not q_norm:
        return decks
    return [
        d
        for d in decks
        if q_norm in (d.get("fileName") or "").lower() or q_norm in (d.get("examCode") or "").lower()
    ]


def _exam_sort_key(file_name: str, exam_code: str | None) -> tuple:
    """Sort key for ascending sort(): bank first, then year DESC, term FA→SU→SP DESC, fileName ASC; unparseable last.

    Ignores exam subtype (FE/RE/PT/Final/…). Parses SP|SU|FA + 2- or 4-digit year from glued or spaced forms.
    """
    if _is_aggregated_bank_filename(file_name):
        return (0, 0, 0, "")
    text = (exam_code or file_name or "").upper()
    m = _TERM_YEAR_SORT_PATTERN.search(text)
    if m is not None:
        term, raw_year = m.group(1), m.group(2)
    else:
        tokens = [tok for tok in re.split(r"[\s\-_]+", text) if tok]
        term = next((t for t in tokens if t in _EXAM_SORT_TERM_ORDER), None)
        raw_year = next((t for t in tokens if t.isdigit() and len(t) in (2, 4)), None)
        if term is None or raw_year is None:
            return (2, 9999, 99, (file_name or "").lower())
    year = int(f"20{raw_year}") if len(raw_year) == 2 else int(raw_year)
    return (1, -year, -_EXAM_SORT_TERM_ORDER[term], (file_name or "").lower())


def _subject_code_from_slug(subject_slug: str) -> str:
    if subject_slug.lower() == "prn232":
        return "PRN232"
    return subject_slug.upper()


def _stem_from_markdown_upload_filename(filename: str) -> str:
    """Basename without trailing .md (case-insensitive); NFKC + strip. Persist this as file_name for markdown uploads."""
    s = unicodedata.normalize("NFKC", (filename or "").strip())
    if len(s) >= 4 and s.lower().endswith(".md"):
        s = s[:-3]
    return s.strip()


def _cache_global_subjects_version() -> int:
    return cache_service.get_int("qs:subjects:ver", default=1)


def _cache_subject_version(slug: str) -> int:
    return cache_service.get_int(f"qs:subject:{slug}:ver", default=1)


def _cache_user_decks_version(slug: str, user_id: str) -> int:
    return cache_service.get_int(f"qs:subject:{slug}:user:{user_id}:decks:ver", default=1)


def _invalidate_subject_catalog() -> None:
    cache_service.bump_version("qs:subjects:ver")


def _invalidate_subject_reads(slug: str) -> None:
    cache_service.bump_version(f"qs:subject:{slug}:ver")


def _invalidate_user_decks(slug: str, user_id: str) -> None:
    cache_service.bump_version(f"qs:subject:{slug}:user:{user_id}:decks:ver")


def _schedule_after_commit(db: Session, callback) -> None:
    callbacks = db.info.setdefault("cache_after_commit_callbacks", [])
    callbacks.append(callback)
    if db.info.get("cache_after_commit_registered"):
        return
    db.info["cache_after_commit_registered"] = True

    @event.listens_for(db, "after_commit")
    def _after_commit(session: Session) -> None:  # pragma: no cover - integration behavior
        pending = session.info.pop("cache_after_commit_callbacks", [])
        for item in pending:
            try:
                item()
            except Exception as exc:
                # Cache invalidation failure must never break request flow.
                logger.warning("Cache invalidation callback failed: %s", exc, exc_info=True)

    @event.listens_for(db, "after_rollback")
    def _after_rollback(session: Session) -> None:  # pragma: no cover - integration behavior
        session.info.pop("cache_after_commit_callbacks", None)


def detect_subject_and_exam(file_name: str) -> dict:
    normalized = _normalize_filename(file_name)
    tokens = [tok for tok in re.split(r"[\s\-]+", normalized) if tok]
    subject = next((tok for tok in tokens if _SUBJECT_PATTERN.match(tok)), None)
    if subject is None:
        raise _error(status.HTTP_422_UNPROCESSABLE_ENTITY, "UNRECOGNIZED_FILENAME_PATTERN", "Cannot detect subject/exam from filename.")
    term = next((tok for tok in tokens if _TERM_PATTERN.match(tok)), None)
    year_token = next((tok for tok in tokens if _YEAR_PATTERN.match(tok)), None)
    exam_type = next((tok for tok in tokens if _TYPE_PATTERN.match(tok)), None)
    if not term or not year_token or not exam_type:
        raise _error(status.HTTP_422_UNPROCESSABLE_ENTITY, "UNRECOGNIZED_FILENAME_PATTERN", "Cannot detect subject/exam from filename.")
    year = _to_year(year_token)
    subject_slug = "prn232" if subject in {"PRN231", "PRN232"} else subject.lower()
    return {
        "subjectCode": subject,
        "subjectSlug": subject_slug,
        "term": term,
        "year": year,
        "type": exam_type,
        "examCode": f"{term}-{year}-{exam_type}",
    }


def detect_subject_and_exam_with_fallback(file_name: str, fallback_subject_slug: str | None = None) -> dict:
    if _is_aggregated_bank_filename(file_name):
        if not fallback_subject_slug:
            raise _error(
                status.HTTP_422_UNPROCESSABLE_ENTITY,
                "SUBJECT_SLUG_REQUIRED_FOR_AGGREGATED_FILE",
                "subjectSlug is required when uploading cau-hoi-tong-hop.md.",
            )
        subject_slug = fallback_subject_slug.strip().lower()
        if not subject_slug:
            raise _error(
                status.HTTP_422_UNPROCESSABLE_ENTITY,
                "SUBJECT_SLUG_REQUIRED_FOR_AGGREGATED_FILE",
                "subjectSlug is required when uploading cau-hoi-tong-hop.md.",
            )
        return {
            "subjectCode": _subject_code_from_slug(subject_slug),
            "subjectSlug": subject_slug,
            "term": "AGG",
            "year": 0,
            "type": "BANK",
            "examCode": "AGG-BANK",
        }
    return detect_subject_and_exam(file_name)


def parse_questions(markdown_text: str) -> tuple[list[dict], list[str]]:
    lines = [line.rstrip() for line in markdown_text.splitlines()]
    entries: list[dict] = []
    warnings: list[str] = []
    current: dict | None = None
    for raw_line in lines:
        line = raw_line.strip()
        if not line:
            continue
        question_match = _QUESTION_START.match(line)
        if question_match:
            if current is not None:
                entries.append(current)
            stem_text = question_match.group(1).strip()
            inline_answer_match = _INLINE_ANSWER.search(stem_text)
            answer_text = ""
            answers: list[str] = []
            if inline_answer_match:
                answer_text = inline_answer_match.group(1).strip().upper()
                answers = [item.strip().upper() for item in re.split(r"[;,/]+", answer_text) if item.strip()]
                stem_text = _INLINE_ANSWER.sub("", stem_text).strip()
            current = {"stem": stem_text, "options": [], "answer_text": answer_text, "answers": answers}
            continue
        if current is None:
            continue
        option_match = _OPTION_LINE.match(line)
        if option_match:
            current["options"].append({"label": option_match.group(1).upper(), "text": option_match.group(2).strip()})
            continue
        answer_match = _ANSWER_LINE.match(line)
        if answer_match:
            current["answer_text"] = answer_match.group(1).strip().upper()
            current["answers"] = [item.strip().upper() for item in re.split(r"[;,/]+", current["answer_text"]) if item.strip()]
            continue
        current["stem"] = f"{current['stem']} {line}".strip()
        warnings.append(f"Question parsing consumed unmatched line at question #{len(entries) + 1}: {line[:80]}")
    if current is not None:
        entries.append(current)

    if not entries:
        raise _error(status.HTTP_422_UNPROCESSABLE_ENTITY, "INVALID_MARKDOWN_FORMAT", "No valid questions parsed from markdown file.")

    normalized: list[dict] = []
    for idx, item in enumerate(entries, start=1):
        if not item["options"]:
            warnings.append(f"Question #{idx} has no options.")
        if not item["answer_text"]:
            warnings.append(f"Question #{idx} has no explicit answer line.")
        hash_source = f"{item['stem']}|{item['options']}|{item['answer_text']}".encode("utf-8")
        normalized_hash = f"sha256:{hashlib.sha256(hash_source).hexdigest()}"
        normalized.append(
            {
                "ordinal": idx,
                "stem": item["stem"],
                "options": item["options"],
                "answers": item["answers"],
                "answer_text": item["answer_text"],
                "normalized_hash": normalized_hash,
            }
        )
    return normalized, warnings


def ingest_markdown_file(
    db: Session, file: UploadFile, uploader_id: str | None, subject_slug: str | None = None
) -> dict:
    if not file.filename or not file.filename.lower().endswith(".md"):
        raise _error(status.HTTP_415_UNSUPPORTED_MEDIA_TYPE, "INVALID_FILE_TYPE", "Only .md files are accepted.")
    raw_bytes = file.file.read(_MAX_UPLOAD_BYTES + 1)
    if len(raw_bytes) > _MAX_UPLOAD_BYTES:
        raise _error(status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, "FILE_TOO_LARGE", "File exceeds 5MB limit.")
    stem = _stem_from_markdown_upload_filename(file.filename)
    if not stem:
        raise _error(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            "INVALID_UPLOAD_FILENAME",
            "Filename must yield a non-empty label after removing .md.",
        )
    metadata = detect_subject_and_exam_with_fallback(file.filename, subject_slug)
    checksum = f"sha256:{hashlib.sha256(raw_bytes).hexdigest()}"
    subject = crud_question_source.get_or_create_subject(
        db, slug=metadata["subjectSlug"], code=metadata["subjectCode"]
    )
    existing = crud_question_source.get_source_by_checksum(
        db, subject_id=subject.id, exam_code=metadata["examCode"], checksum_sha256=checksum
    )
    if existing is not None:
        return {
            "sourceId": existing.id,
            "subjectSlug": metadata["subjectSlug"],
            "subjectCode": metadata["subjectCode"],
            "examCode": metadata["examCode"],
            "fileName": existing.file_name,
            "checksum": existing.checksum_sha256,
            "questionCount": existing.question_count,
            "warnings": existing.parse_warnings or [],
            "deduplicated": True,
        }

    markdown_text = raw_bytes.decode("utf-8", errors="ignore")
    questions, warnings = parse_questions(markdown_text)
    source = crud_question_source.create_source(
        db,
        subject_id=subject.id,
        exam_code=metadata["examCode"],
        file_name=stem,
        checksum_sha256=checksum,
        uploaded_by=uploader_id,
        warnings=warnings,
        question_count=len(questions),
    )
    crud_question_source.replace_source_questions(db, source_id=source.id, payload=questions)
    _schedule_after_commit(
        db,
        lambda: (_invalidate_subject_catalog(), _invalidate_subject_reads(metadata["subjectSlug"])),
    )
    return {
        "sourceId": source.id,
        "subjectSlug": metadata["subjectSlug"],
        "subjectCode": metadata["subjectCode"],
        "examCode": metadata["examCode"],
        "fileName": stem,
        "checksum": checksum,
        "questionCount": len(questions),
        "warnings": warnings,
        "deduplicated": False,
    }


def list_subjects(db: Session) -> list[dict]:
    version = _cache_global_subjects_version()
    cache_key = f"qs:subjects:v{version}"
    cached = cache_service.get_json(cache_key)
    if isinstance(cached, list):
        return cached
    payload = [{"slug": row.slug, "code": row.code, "hint": "Mon luyen de"} for row in crud_question_source.list_subjects(db)]
    cache_service.set_json(cache_key, payload, _CACHE_SUBJECTS_TTL_SECONDS)
    return payload


def list_subjects_page(db: Session, *, page: int, limit: int, q: str | None = None) -> dict:
    q_norm = (q or "").strip() or None
    total = crud_question_source.count_subjects(db, q=q_norm)
    offset = (page - 1) * limit
    rows = crud_question_source.list_subjects_page(db, offset=offset, limit=limit, q=q_norm)
    subject_ids = [row.id for row in rows]
    bank_counts = crud_question_source.bank_question_counts_by_subject_ids(db, subject_ids)
    items = [
        {
            "slug": row.slug,
            "code": row.code,
            "hint": "Mon luyen de",
            "bankQuestionCount": bank_counts.get(row.id, 0),
        }
        for row in rows
    ]
    total_pages = 0 if total == 0 else max(1, math.ceil(total / limit))
    return {
        "items": items,
        "page": page,
        "limit": limit,
        "total": total,
        "totalPages": total_pages,
        "hasNext": total > 0 and page < total_pages,
        "hasPrevious": page > 1 and total > 0,
    }


def get_admin_subject_sources(db: Session, slug: str) -> list[dict]:
    normalized_slug = slug.lower()
    version = _cache_subject_version(normalized_slug)
    cache_key = f"qs:admin:subject:{normalized_slug}:sources:v{version}"
    cached = cache_service.get_json(cache_key)
    if isinstance(cached, list):
        return cached
    subject = crud_question_source.get_subject_by_slug(db, slug)
    if subject is None:
        raise _error(status.HTTP_404_NOT_FOUND, "SUBJECT_NOT_FOUND", "Subject not found.")
    sources = sorted(
        crud_question_source.list_sources_by_subject(db, subject.id),
        key=lambda s: _exam_sort_key(s.file_name, s.exam_code),
    )
    payload = [
        {
            "sourceId": source.id,
            # FE wants Exam column to display file name without `.md`.
            "examCode": re.sub(r"\.md$", "", source.file_name, flags=re.IGNORECASE),
            "fileName": source.file_name,
            "questionCount": int(source.question_count or 0),
            "isAggregatedBank": _is_aggregated_bank_filename(source.file_name),
            "uploadedAt": source.uploaded_at.isoformat() if source.uploaded_at else None,
        }
        for source in sources
    ]
    cache_service.set_json(cache_key, payload, _CACHE_SUBJECT_READ_TTL_SECONDS)
    return payload


def get_admin_subject_sources_page(db: Session, slug: str, *, page: int, limit: int, q: str | None = None) -> dict:
    subject = crud_question_source.get_subject_by_slug(db, slug)
    if subject is None:
        raise _error(status.HTTP_404_NOT_FOUND, "SUBJECT_NOT_FOUND", "Subject not found.")
    q_norm = (q or "").strip() or None
    offset = (page - 1) * limit
    all_sources = sorted(
        crud_question_source.list_sources_by_subject(db, subject.id),
        key=lambda s: _exam_sort_key(s.file_name, s.exam_code),
    )
    if q_norm:
        all_sources = [
            s
            for s in all_sources
            if q_norm in (s.file_name or "").lower() or q_norm in (s.exam_code or "").lower()
        ]
    total = len(all_sources)
    rows = all_sources[offset : offset + limit]
    items = [
        {
            "sourceId": source.id,
            "examCode": re.sub(r"\.md$", "", source.file_name, flags=re.IGNORECASE),
            "fileName": source.file_name,
            "questionCount": int(source.question_count or 0),
            "isAggregatedBank": _is_aggregated_bank_filename(source.file_name),
            "uploadedAt": source.uploaded_at.isoformat() if source.uploaded_at else None,
        }
        for source in rows
    ]
    total_pages = 0 if total == 0 else max(1, math.ceil(total / limit))
    return {
        "items": items,
        "page": page,
        "limit": limit,
        "total": total,
        "totalPages": total_pages,
        "hasNext": total > 0 and page < total_pages,
        "hasPrevious": page > 1 and total > 0,
    }


def get_source_state(db: Session, slug: str) -> dict:
    normalized_slug = slug.lower()
    version = _cache_subject_version(normalized_slug)
    cache_key = f"qs:subject:{normalized_slug}:source-state:v{version}"
    cached = cache_service.get_json(cache_key)
    if isinstance(cached, dict):
        return cached

    # Use optimized query that fetches sources and questions in single query
    sources, questions_by_source = crud_question_source.get_source_state_optimized(db, slug)

    if not sources:
        subject = crud_question_source.get_subject_by_slug(db, slug)
        if subject is None:
            raise _error(status.HTTP_404_NOT_FOUND, "SUBJECT_NOT_FOUND", "Subject not found.")
        payload = {"bankQuestions": [], "deckQuestions": [], "files": [], "hocTheoDeLayout": "markdownFiles"}
        cache_service.set_json(cache_key, payload, _CACHE_SUBJECT_READ_TTL_SECONDS)
        return payload

    bank_source = next((item for item in sources if _is_aggregated_bank_filename(item.file_name)), None) or sources[0]
    deck_sources = sorted(
        [item for item in sources if not _is_aggregated_bank_filename(item.file_name)],
        key=lambda s: _exam_sort_key(s.file_name, s.exam_code),
    )

    # Questions are already loaded by optimized query
    bank_questions = questions_by_source.get(bank_source.id, [])
    bank_formatted = [
        {"id": idx, "stem": item["stem"], "options": item["options"], "answer": item["answer"]}
        for idx, item in enumerate(bank_questions, start=1)
    ]
    deck_questions: list[dict] = []
    files: list[dict] = []
    running_index = 0
    for source in deck_sources:
        questions = questions_by_source.get(source.id, [])
        start = running_index
        next_questions = [
            {"id": idx + running_index + 1, "stem": item["stem"], "options": item["options"], "answer": item["answer"]}
            for idx, item in enumerate(questions)
        ]
        deck_questions.extend(next_questions)
        running_index = len(deck_questions)
        end = running_index - 1
        has_questions = len(questions) > 0
        files.append(
            {
                "deckId": source.id,
                "fileName": source.file_name,
                "isEmpty": not has_questions,
                "questionCount": int(source.question_count or 0),
                "range": {"start": start, "end": end} if has_questions else {"start": 0, "end": 0},
            }
        )

    payload = {
        "bankQuestions": bank_formatted,
        "deckQuestions": deck_questions,
        "files": files,
        "hocTheoDeLayout": "markdownFiles",
    }
    cache_service.set_json(cache_key, payload, _CACHE_SUBJECT_READ_TTL_SECONDS)
    return payload


def get_subject_bank(db: Session, slug: str) -> list[dict]:
    normalized_slug = slug.lower()
    version = _cache_subject_version(normalized_slug)
    cache_key = f"qs:subject:{normalized_slug}:bank:v{version}"
    cached = cache_service.get_json(cache_key)
    if isinstance(cached, list):
        return cached
    subject = crud_question_source.get_subject_by_slug(db, slug)
    if subject is None:
        raise _error(status.HTTP_404_NOT_FOUND, "SUBJECT_NOT_FOUND", "Subject not found.")
    sources = crud_question_source.list_sources_by_subject(db, subject.id)
    if not sources:
        cache_service.set_json(cache_key, [], _CACHE_SUBJECT_READ_TTL_SECONDS)
        return []
    source = next((item for item in sources if _is_aggregated_bank_filename(item.file_name)), None) or sources[0]
    questions = crud_question_source.list_source_questions_payload(db, source.id)
    payload = [{"id": idx, "stem": item["stem"], "options": item["options"], "answer": item["answer"]} for idx, item in enumerate(questions, start=1)]
    cache_service.set_json(cache_key, payload, _CACHE_SUBJECT_READ_TTL_SECONDS)
    return payload


def get_subject_bank_page(db: Session, slug: str, *, page: int, limit: int) -> dict:
    subject = crud_question_source.get_subject_by_slug(db, slug)
    if subject is None:
        raise _error(status.HTTP_404_NOT_FOUND, "SUBJECT_NOT_FOUND", "Subject not found.")
    sources = crud_question_source.list_sources_by_subject(db, subject.id)
    if not sources:
        return {"items": [], "page": page, "limit": limit, "total": 0, "totalPages": 0, "hasNext": False, "hasPrevious": page > 1}
    source = next((item for item in sources if _is_aggregated_bank_filename(item.file_name)), None) or sources[0]
    total = int(source.question_count or 0)
    offset = (page - 1) * limit
    slice_rows = crud_question_source.list_source_questions_payload_slice(db, source.id, offset=offset, limit=limit)
    items = [{"id": offset + idx + 1, "stem": item["stem"], "options": item["options"], "answer": item["answer"]} for idx, item in enumerate(slice_rows)]
    total_pages = 0 if total == 0 else max(1, math.ceil(total / limit))
    return {
        "items": items,
        "page": page,
        "limit": limit,
        "total": total,
        "totalPages": total_pages,
        "hasNext": total > 0 and page < total_pages,
        "hasPrevious": page > 1 and total > 0,
    }


def get_subject_bank_progress(db: Session, *, slug: str, user_id: str) -> dict:
    subject = crud_question_source.get_subject_by_slug(db, slug)
    if subject is None:
        raise _error(status.HTTP_404_NOT_FOUND, "SUBJECT_NOT_FOUND", "Subject not found.")

    sources = crud_question_source.list_sources_by_subject(db, subject.id)
    if not sources:
        return {
            "totalQuestions": 0,
            "lastQuestion": 0,
            "resumeQuestion": 0,
            "attemptedQuestionOrdinals": [],
            "completionRatePercent": 0,
            "updatedAt": None,
        }

    source = next((item for item in sources if _is_aggregated_bank_filename(item.file_name)), None) or sources[0]
    total_questions = int(source.question_count or 0)
    stats = crud_question_source.list_user_stats_by_source_ids(
        db, user_id=user_id, source_ids=[source.id]
    ).get(source.id, {})

    raw_current_question = min(
        max(int(stats.get("current_question_ordinal", stats.get("in_progress_count", 0))), 0),
        total_questions,
    )
    attempted_question_ordinals = _normalize_attempted_ordinals(
        stats.get("attempted_question_ordinals", []),
        question_count=total_questions,
    )
    resume_question = _resolve_resume_question_ordinal(
        current_question_ordinal=raw_current_question,
        attempted_question_ordinals=attempted_question_ordinals,
        question_count=total_questions,
    )

    completion_rate_percent = 0
    if total_questions > 0:
        completion_rate_percent = int(round((len(attempted_question_ordinals) / total_questions) * 100))

    updated_at = stats.get("updated_at")
    return {
        "totalQuestions": total_questions,
        "lastQuestion": raw_current_question,
        "resumeQuestion": resume_question,
        "attemptedQuestionOrdinals": attempted_question_ordinals,
        "completionRatePercent": max(0, min(completion_rate_percent, 100)),
        "updatedAt": updated_at.isoformat() if updated_at else None,
    }


def _build_deck_stats(
    total_questions: int,
    current_question_ordinal: int,
    completed_attempts: int,
    completion_rate_percent: int | None = None,
) -> dict:
    safe_total = max(total_questions, 0)
    safe_current = max(current_question_ordinal, 0)
    safe_completed_attempts = max(completed_attempts, 0)
    safe_completion_rate = (
        int(round(completion_rate_percent)) if completion_rate_percent is not None else None
    )
    if safe_total <= 0:
        safe_current = 0
        computed_rate = 0
    else:
        safe_current = min(safe_current, safe_total)
        if safe_completion_rate is None:
            computed_rate = int(round((safe_current / safe_total) * 100))
        else:
            computed_rate = max(0, min(safe_completion_rate, 100))
    return {
        "total": safe_total,
        "inProgress": safe_current,
        "completed": safe_completed_attempts,
        "learnedCount": safe_completed_attempts,
        "completionRatePercent": max(0, min(computed_rate, 100)),
    }


def _normalize_attempted_ordinals(raw_ordinals: object, *, question_count: int) -> list[int]:
    if not isinstance(raw_ordinals, list):
        return []
    normalized = sorted({value for value in raw_ordinals if isinstance(value, int) and not isinstance(value, bool) and 1 <= value <= question_count})
    return normalized


def _answer_count_from_payload(item: dict) -> int:
    raw_answers = item.get("answers", [])
    if isinstance(raw_answers, list):
        normalized_answers = [
            str(value).strip().upper()
            for value in raw_answers
            if str(value).strip()
        ]
        if normalized_answers:
            return len(set(normalized_answers))
    answer_text = str(item.get("answer", "") or "").strip()
    if not answer_text:
        return 0
    parsed = [part.strip().upper() for part in re.split(r"[;,/]+", answer_text) if part.strip()]
    if not parsed:
        return 0
    return len(set(parsed))


def _resolve_resume_question_ordinal(
    *,
    current_question_ordinal: int,
    attempted_question_ordinals: list[int],
    question_count: int,
) -> int:
    """Return the next question ordinal that the user should resume at."""
    if question_count <= 0:
        return 0

    clamped_current = min(max(int(current_question_ordinal or 0), 0), question_count)
    attempted_set = set(attempted_question_ordinals)

    # If current question is still unanswered, keep it.
    if 1 <= clamped_current <= question_count and clamped_current not in attempted_set:
        return clamped_current

    # Otherwise move forward to the next unanswered question.
    start = clamped_current + 1 if clamped_current >= 1 else 1
    for ordinal in range(start, question_count + 1):
        if ordinal not in attempted_set:
            return ordinal

    # Fallback: first unanswered question anywhere in deck.
    for ordinal in range(1, question_count + 1):
        if ordinal not in attempted_set:
            return ordinal

    # Fully attempted/completed deck.
    return question_count


def get_subject_decks(db: Session, slug: str, *, user_id: str | None = None) -> list[dict]:
    normalized_slug = slug.lower()
    if user_id:
        subject_version = _cache_subject_version(normalized_slug)
        user_version = _cache_user_decks_version(normalized_slug, user_id)
        cache_key = f"qs:subject:{normalized_slug}:user:{user_id}:decks:sv{subject_version}:uv{user_version}"
    else:
        version = _cache_subject_version(normalized_slug)
        cache_key = f"qs:subject:{normalized_slug}:decks:v{version}"
    cached = cache_service.get_json(cache_key)
    if isinstance(cached, list):
        return cached

    # Use optimized query when available, while keeping compatibility with mocked/test CRUD doubles.
    optimized_result = getattr(crud_question_source, "get_subject_decks_optimized", None)
    if callable(optimized_result):
        maybe_result = optimized_result(db, slug, user_id)
        if isinstance(maybe_result, tuple) and len(maybe_result) == 2:
            deck_sources, stats_by_source_id = maybe_result
        else:
            subject = crud_question_source.get_subject_by_slug(db, slug)
            if subject is None:
                raise _error(status.HTTP_404_NOT_FOUND, "SUBJECT_NOT_FOUND", "Subject not found.")
            sources = crud_question_source.list_sources_by_subject(db, subject.id)
            deck_sources = [source for source in sources if not _is_aggregated_bank_filename(source.file_name)]
            stats_by_source_id = (
                crud_question_source.list_user_stats_by_source_ids(
                    db, user_id=user_id, source_ids=[item.id for item in deck_sources]
                )
                if user_id
                else {}
            )
    else:
        subject = crud_question_source.get_subject_by_slug(db, slug)
        if subject is None:
            raise _error(status.HTTP_404_NOT_FOUND, "SUBJECT_NOT_FOUND", "Subject not found.")
        sources = crud_question_source.list_sources_by_subject(db, subject.id)
        deck_sources = [source for source in sources if not _is_aggregated_bank_filename(source.file_name)]
        stats_by_source_id = (
            crud_question_source.list_user_stats_by_source_ids(
                db, user_id=user_id, source_ids=[item.id for item in deck_sources]
            )
            if user_id
            else {}
        )

    deck_sources = sorted(deck_sources, key=lambda s: _exam_sort_key(s.file_name, s.exam_code))

    if not deck_sources:
        subject = crud_question_source.get_subject_by_slug(db, slug)
        if subject is None:
            raise _error(status.HTTP_404_NOT_FOUND, "SUBJECT_NOT_FOUND", "Subject not found.")
        cache_service.set_json(cache_key, [], _CACHE_DECK_LIST_TTL_SECONDS)
        return []

    result: list[dict] = []
    for source in deck_sources:
        total_questions = int(source.question_count or 0)
        user_stats = stats_by_source_id.get(source.id, {})
        raw_current_question_ordinal = int(
            user_stats.get("current_question_ordinal", user_stats.get("in_progress_count", 0))
        )
        attempted_question_ordinals = _normalize_attempted_ordinals(
            user_stats.get("attempted_question_ordinals", []),
            question_count=total_questions,
        )
        current_question_ordinal = min(max(raw_current_question_ordinal, 0), total_questions)
        completed_attempts = int(user_stats.get("completed_attempts", user_stats.get("completed_count", 0)))
        completion_rate_percent = 0
        if total_questions > 0:
            completion_rate_percent = int(round((len(attempted_question_ordinals) / total_questions) * 100))
        result.append(
            {
                "deckId": source.id,
                "examCode": source.exam_code,
                "fileName": source.file_name,
                "questionCount": total_questions,
                "stats": _build_deck_stats(
                    total_questions,
                    current_question_ordinal,
                    completed_attempts,
                    completion_rate_percent,
                ),
                "uploadedAt": source.uploaded_at.isoformat() if source.uploaded_at else None,
            }
        )
    cache_service.set_json(cache_key, result, _CACHE_DECK_LIST_TTL_SECONDS)
    return result


def get_deck_questions(db: Session, slug: str, deck_id: str) -> list[dict]:
    normalized_slug = slug.lower()
    version = _cache_subject_version(normalized_slug)
    cache_key = f"qs:subject:{normalized_slug}:deck:{deck_id}:questions:v{version}"
    cached = cache_service.get_json(cache_key)
    if isinstance(cached, list):
        return cached
    subject = crud_question_source.get_subject_by_slug(db, slug)
    if subject is None:
        raise _error(status.HTTP_404_NOT_FOUND, "SUBJECT_NOT_FOUND", "Subject not found.")
    source = crud_question_source.get_source_by_id(db, subject_id=subject.id, source_id=deck_id)
    if source is None:
        raise _error(status.HTTP_404_NOT_FOUND, "DECK_NOT_FOUND", "Deck not found for subject.")
    questions = crud_question_source.list_source_questions_payload(db, source.id)
    payload = [
        {
            "id": idx,
            "stem": item["stem"],
            "options": item["options"],
            "answer": item["answer"],
            "answerCount": _answer_count_from_payload(item),
            "imageUrl": item.get("imageUrl"),
        }
        for idx, item in enumerate(questions, start=1)
    ]
    cache_service.set_json(cache_key, payload, _CACHE_DECK_QUESTIONS_TTL_SECONDS)
    return payload


def get_deck_questions_page(
    db: Session, slug: str, deck_id: str, *, page: int, limit: int, q: str | None = None
) -> dict:
    """Paginated deck questions (no full-deck Redis cache; uses DB slice + subject question_count for total).

    Optional ``q`` filters by substring (case-insensitive) on stem, answer text, or options/answers JSON text.
    """
    normalized_slug = slug.lower()
    subject = crud_question_source.get_subject_by_slug(db, normalized_slug)
    if subject is None:
        raise _error(status.HTTP_404_NOT_FOUND, "SUBJECT_NOT_FOUND", "Subject not found.")
    source = crud_question_source.get_source_by_id(db, subject_id=subject.id, source_id=deck_id)
    if source is None:
        raise _error(status.HTTP_404_NOT_FOUND, "DECK_NOT_FOUND", "Deck not found for subject.")

    search_q = (q or "").strip()
    if search_q:
        total = crud_question_source.count_questions_for_source(db, source.id, q=search_q)
    else:
        total = int(source.question_count or 0)

    if total <= 0:
        total_pages = 0
        items: list[dict] = []
    else:
        total_pages = max(1, math.ceil(total / limit))
        offset = (page - 1) * limit
        slice_rows = crud_question_source.list_source_questions_payload_slice(
            db,
            source.id,
            offset=offset,
            limit=limit,
            q=search_q if search_q else None,
        )
        items = [
            {
                "id": item["ordinal"],
                "stem": item["stem"],
                "options": item["options"],
                "answer": item["answer"],
                "answerCount": _answer_count_from_payload(item),
                "imageUrl": item.get("imageUrl"),
            }
            for item in slice_rows
        ]

    has_next = total > 0 and page < total_pages
    has_previous = page > 1 and total > 0

    return {
        "items": items,
        "page": page,
        "limit": limit,
        "total": total,
        "totalPages": total_pages,
        "hasNext": has_next,
        "hasPrevious": has_previous,
    }


def update_deck_stats(
    db: Session,
    *,
    slug: str,
    deck_id: str,
    user_id: str,
    in_progress: int,
    completed: int,
) -> dict:
    subject = crud_question_source.get_subject_by_slug(db, slug)
    if subject is None:
        raise _error(status.HTTP_404_NOT_FOUND, "SUBJECT_NOT_FOUND", "Subject not found.")
    source = crud_question_source.get_source_by_id(db, subject_id=subject.id, source_id=deck_id)
    if source is None:
        raise _error(status.HTTP_404_NOT_FOUND, "DECK_NOT_FOUND", "Deck not found for subject.")

    total_questions = int(source.question_count or 0)
    if in_progress + completed > total_questions:
        raise _error(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            "INVALID_DECK_STATS",
            "inProgress + completed cannot exceed total questions of this deck.",
            details={
                "total": total_questions,
                "inProgress": in_progress,
                "completed": completed,
            },
        )

    completion_rate_percent = 0
    if total_questions > 0:
        completion_rate_percent = int(round((in_progress / total_questions) * 100))
    current_stats = crud_question_source.list_user_stats_by_source_ids(
        db, user_id=user_id, source_ids=[source.id]
    ).get(source.id, {})
    attempted_question_ordinals = _normalize_attempted_ordinals(
        current_stats.get("attempted_question_ordinals", []),
        question_count=total_questions,
    )

    crud_question_source.upsert_source_user_stats(
        db,
        source_id=source.id,
        user_id=user_id,
        current_question_ordinal=in_progress,
        attempted_question_ordinals=attempted_question_ordinals,
        completed_attempts=completed,
        in_progress_count=in_progress,
        completed_count=completed,
        completion_rate_percent=completion_rate_percent,
    )
    subject_slug = subject.slug
    _schedule_after_commit(db, lambda: _invalidate_user_decks(subject_slug, user_id))

    return {
        "deckId": source.id,
        "subjectSlug": subject.slug,
        "stats": _build_deck_stats(total_questions, in_progress, completed),
    }


def update_deck_progress(
    db: Session,
    *,
    slug: str,
    deck_id: str,
    user_id: str,
    current_question: int,
    attempted_question_ordinals: list[int],
) -> dict:
    subject = crud_question_source.get_subject_by_slug(db, slug)
    if subject is None:
        raise _error(status.HTTP_404_NOT_FOUND, "SUBJECT_NOT_FOUND", "Subject not found.")
    source = crud_question_source.get_source_by_id(db, subject_id=subject.id, source_id=deck_id)
    if source is None:
        raise _error(status.HTTP_404_NOT_FOUND, "DECK_NOT_FOUND", "Deck not found for subject.")

    total_questions = int(source.question_count or 0)
    invalid_ordinals = [
        value
        for value in attempted_question_ordinals
        if not isinstance(value, int) or isinstance(value, bool) or value < 1 or value > total_questions
    ]
    if invalid_ordinals:
        raise _error(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            "INVALID_ATTEMPTED_QUESTION_ORDINALS",
            "attemptedQuestionOrdinals must be within 1..questionCount.",
            details={"questionCount": total_questions, "invalidOrdinals": invalid_ordinals},
        )
    clamped_current_question = min(max(current_question, 0), total_questions)
    normalized_attempted_ordinals = _normalize_attempted_ordinals(
        attempted_question_ordinals,
        question_count=total_questions,
    )

    current_stats = crud_question_source.list_user_stats_by_source_ids(
        db, user_id=user_id, source_ids=[source.id]
    ).get(source.id, {})
    previous_current = int(
        current_stats.get("current_question_ordinal", current_stats.get("in_progress_count", 0))
    )
    completed_attempts = int(current_stats.get("completed_attempts", current_stats.get("completed_count", 0)))
    if total_questions > 0 and clamped_current_question >= total_questions and previous_current < total_questions:
        completed_attempts += 1

    completion_rate_percent = 0
    if total_questions > 0:
        completion_rate_percent = int(round((clamped_current_question / total_questions) * 100))
    resume_question = _resolve_resume_question_ordinal(
        current_question_ordinal=clamped_current_question,
        attempted_question_ordinals=normalized_attempted_ordinals,
        question_count=total_questions,
    )

    crud_question_source.upsert_source_user_stats(
        db,
        source_id=source.id,
        user_id=user_id,
        current_question_ordinal=clamped_current_question,
        attempted_question_ordinals=normalized_attempted_ordinals,
        completed_attempts=completed_attempts,
        in_progress_count=clamped_current_question,
        completed_count=completed_attempts,
        completion_rate_percent=completion_rate_percent,
    )
    subject_slug = subject.slug
    _schedule_after_commit(db, lambda: _invalidate_user_decks(subject_slug, user_id))
    return {
        "deckId": source.id,
        "subjectSlug": subject.slug,
        "stats": _build_deck_stats(total_questions, clamped_current_question, completed_attempts),
        "currentQuestion": resume_question,
        "attemptedQuestionOrdinals": normalized_attempted_ordinals,
    }


def get_deck_progress(
    db: Session,
    *,
    slug: str,
    deck_id: str,
    user_id: str,
) -> dict:
    subject = crud_question_source.get_subject_by_slug(db, slug)
    if subject is None:
        raise _error(status.HTTP_404_NOT_FOUND, "SUBJECT_NOT_FOUND", "Subject not found.")
    source = crud_question_source.get_source_by_id(db, subject_id=subject.id, source_id=deck_id)
    if source is None:
        raise _error(status.HTTP_404_NOT_FOUND, "DECK_NOT_FOUND", "Deck not found for subject.")

    total_questions = int(source.question_count or 0)
    current_stats = crud_question_source.list_user_stats_by_source_ids(
        db, user_id=user_id, source_ids=[source.id]
    ).get(source.id)
    if current_stats is None:
        return {
            "currentQuestion": 0,
            "attemptedQuestionOrdinals": [],
            "updatedAt": None,
        }

    raw_current_question = min(
        max(int(current_stats.get("current_question_ordinal", 0)), 0),
        total_questions,
    )
    attempted_question_ordinals = _normalize_attempted_ordinals(
        current_stats.get("attempted_question_ordinals", []),
        question_count=total_questions,
    )
    current_question = _resolve_resume_question_ordinal(
        current_question_ordinal=raw_current_question,
        attempted_question_ordinals=attempted_question_ordinals,
        question_count=total_questions,
    )
    updated_at = current_stats.get("updated_at")
    return {
        "currentQuestion": current_question,
        "attemptedQuestionOrdinals": attempted_question_ordinals,
        "updatedAt": updated_at.isoformat() if updated_at else None,
    }


def reset_deck_progress(
    db: Session,
    *,
    slug: str,
    deck_id: str,
    user_id: str,
) -> dict:
    subject = crud_question_source.get_subject_by_slug(db, slug)
    if subject is None:
        raise _error(status.HTTP_404_NOT_FOUND, "SUBJECT_NOT_FOUND", "Subject not found.")
    source = crud_question_source.get_source_by_id(db, subject_id=subject.id, source_id=deck_id)
    if source is None:
        raise _error(status.HTTP_404_NOT_FOUND, "DECK_NOT_FOUND", "Deck not found for subject.")

    current_stats = crud_question_source.list_user_stats_by_source_ids(
        db, user_id=user_id, source_ids=[source.id]
    ).get(source.id, {})
    completed_attempts = int(current_stats.get("completed_attempts", current_stats.get("completed_count", 0)))
    crud_question_source.upsert_source_user_stats(
        db,
        source_id=source.id,
        user_id=user_id,
        current_question_ordinal=0,
        attempted_question_ordinals=[],
        completed_attempts=completed_attempts,
        in_progress_count=0,
        completed_count=0,
        completion_rate_percent=0,
    )
    subject_slug = subject.slug
    _schedule_after_commit(db, lambda: _invalidate_user_decks(subject_slug, user_id))
    return {
        "deckId": source.id,
        "subjectSlug": subject.slug,
        "stats": _build_deck_stats(
            total_questions=int(source.question_count or 0),
            current_question_ordinal=0,
            completed_attempts=completed_attempts,
            completion_rate_percent=0,
        ),
        "currentQuestion": 0,
        "attemptedQuestionOrdinals": [],
    }


def check_deck_answer(
    db: Session,
    *,
    slug: str,
    deck_id: str,
    question_id: int,
    selected_answer: str,
) -> dict:
    subject = crud_question_source.get_subject_by_slug(db, slug)
    if subject is None:
        raise _error(status.HTTP_404_NOT_FOUND, "SUBJECT_NOT_FOUND", "Subject not found.")
    source = crud_question_source.get_source_by_id(db, subject_id=subject.id, source_id=deck_id)
    if source is None:
        raise _error(status.HTTP_404_NOT_FOUND, "DECK_NOT_FOUND", "Deck not found for subject.")

    question = crud_question_source.get_question_by_ordinal(db, source_id=source.id, ordinal=question_id)
    if question is None:
        raise _error(status.HTTP_404_NOT_FOUND, "QUESTION_NOT_FOUND", "Question not found for deck.")

    selected = selected_answer.strip().upper()
    if not selected:
        raise _error(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            "INVALID_SELECTED_ANSWER",
            "selectedAnswer must not be empty.",
        )

    correct_answers = [str(item).strip().upper() for item in (question.answers_json or []) if str(item).strip()]
    if not correct_answers and question.answer_text:
        correct_answers = [part.strip().upper() for part in re.split(r"[;,/]+", question.answer_text) if part.strip()]
    is_correct = selected in correct_answers
    return {
        "questionId": question_id,
        "selectedAnswer": selected,
        "correctAnswers": correct_answers,
        "isCorrect": is_correct,
    }


def _normalize_question_dict_for_source(stem: str, options: list, answer_text: str) -> dict:
    """Normalize stem/options/answer_text for storage (matches bulk replace row shape, without ordinal)."""
    answers = [part.strip().upper() for part in re.split(r"[;,/]+", answer_text) if part.strip()]
    normalized_options = [{"label": str(op.get("label", "")).strip(), "text": str(op.get("text", "")).strip()} for op in options]
    hash_source = f"{stem}|{normalized_options}|{answer_text}".encode("utf-8")
    normalized_hash = f"sha256:{hashlib.sha256(hash_source).hexdigest()}"
    return {
        "stem": stem,
        "options": normalized_options,
        "answers": answers,
        "answer_text": answer_text,
        "normalized_hash": normalized_hash,
    }


def update_source_questions(db: Session, slug: str, source_id: str, questions: list[dict]) -> dict:
    subject = crud_question_source.get_subject_by_slug(db, slug)
    if subject is None:
        raise _error(status.HTTP_404_NOT_FOUND, "SUBJECT_NOT_FOUND", "Subject not found.")

    source = crud_question_source.get_source_by_id(db, subject_id=subject.id, source_id=source_id)
    if source is None:
        raise _error(status.HTTP_404_NOT_FOUND, "SOURCE_NOT_FOUND", "Source not found for subject.")

    if not questions:
        raise _error(status.HTTP_422_UNPROCESSABLE_ENTITY, "INVALID_QUESTIONS_PAYLOAD", "Questions payload must not be empty.")

    normalized: list[dict] = []
    warnings: list[str] = []
    for idx, item in enumerate(questions, start=1):
        stem = (item.get("stem") or "").strip()
        options = item.get("options") or []
        answer_text = (item.get("answer") or "").strip()
        if not stem:
            raise _error(status.HTTP_422_UNPROCESSABLE_ENTITY, "INVALID_QUESTIONS_PAYLOAD", f"Question #{idx} is missing stem.")
        if not options:
            warnings.append(f"Question #{idx} has no options.")
        if not answer_text:
            warnings.append(f"Question #{idx} has no explicit answer.")
        parts = _normalize_question_dict_for_source(stem, options, answer_text)
        normalized.append(
            {
                "ordinal": idx,
                "stem": parts["stem"],
                "options": parts["options"],
                "answers": parts["answers"],
                "answer_text": parts["answer_text"],
                "normalized_hash": parts["normalized_hash"],
            }
        )

    crud_question_source.replace_source_questions(db, source_id=source.id, payload=normalized)
    crud_question_source.update_source_question_stats(
        db, source=source, question_count=len(normalized), warnings=warnings
    )

    # If this subject has an aggregated bank, re-merge this deck so `cau-hoi-tong-hop` matches the replaced deck.
    if not _is_aggregated_bank_filename(source.file_name):
        bank = _get_aggregated_bank_source(db, subject.id)
        if bank is not None:
            merge_deck_into_aggregated_bank(db, slug=subject.slug, deck_source_id=source.id, uploader_id=None)

    subject_slug = subject.slug
    _schedule_after_commit(db, lambda: (_invalidate_subject_catalog(), _invalidate_subject_reads(subject_slug)))
    return {
        "sourceId": source.id,
        "subjectSlug": subject.slug,
        "examCode": source.exam_code,
        "fileName": source.file_name,
        "questionCount": len(normalized),
        "warnings": warnings,
    }


def patch_source_question(
    db: Session,
    *,
    slug: str,
    source_id: str,
    ordinal: int,
    stem: str | None,
    options: list[dict] | None,
    answer: str | None,
) -> dict:
    subject = crud_question_source.get_subject_by_slug(db, slug)
    if subject is None:
        raise _error(status.HTTP_404_NOT_FOUND, "SUBJECT_NOT_FOUND", "Subject not found.")

    source = crud_question_source.get_source_by_id(db, subject_id=subject.id, source_id=source_id)
    if source is None:
        raise _error(status.HTTP_404_NOT_FOUND, "SOURCE_NOT_FOUND", "Source not found for subject.")

    question = crud_question_source.get_question_by_ordinal(db, source_id=source.id, ordinal=ordinal)
    if question is None:
        raise _error(status.HTTP_404_NOT_FOUND, "QUESTION_NOT_FOUND", "Question not found for this source.")

    final_stem = stem.strip() if stem is not None else question.stem
    if options is not None:
        opt_list = [{"label": str(o.get("label", "")).strip(), "text": str(o.get("text", "")).strip()} for o in options]
    else:
        opt_list = list(question.options_json or [])

    final_answer_text = answer.strip() if answer is not None else question.answer_text

    if not final_stem:
        raise _error(status.HTTP_422_UNPROCESSABLE_ENTITY, "INVALID_QUESTION", "Question stem must not be empty.")

    old_normalized_hash = question.normalized_hash
    parts = _normalize_question_dict_for_source(final_stem, opt_list, final_answer_text)
    crud_question_source.update_question_content(
        db,
        question=question,
        stem=parts["stem"],
        options_json=parts["options"],
        answers_json=parts["answers"],
        answer_text=parts["answer_text"],
        normalized_hash=parts["normalized_hash"],
    )

    # Keep `cau-hoi-tong-hop` in sync: bank merge dedupes by normalized_hash; update any bank row that matched the pre-edit hash.
    if not _is_aggregated_bank_filename(source.file_name):
        bank = _get_aggregated_bank_source(db, subject.id)
        if bank is not None:
            for bank_q in crud_question_source.list_questions_by_normalized_hash(
                db, source_id=bank.id, normalized_hash=old_normalized_hash
            ):
                crud_question_source.update_question_content(
                    db,
                    question=bank_q,
                    stem=parts["stem"],
                    options_json=parts["options"],
                    answers_json=parts["answers"],
                    answer_text=parts["answer_text"],
                    normalized_hash=parts["normalized_hash"],
                )
            merge_deck_into_aggregated_bank(db, slug=subject.slug, deck_source_id=source.id, uploader_id=None)

    subject_slug = subject.slug
    _schedule_after_commit(db, lambda: (_invalidate_subject_catalog(), _invalidate_subject_reads(subject_slug)))
    return {
        "sourceId": source.id,
        "subjectSlug": subject.slug,
        "examCode": source.exam_code,
        "fileName": source.file_name,
        "ordinal": ordinal,
    }


def check_bank_duplicate(
    db: Session,
    *,
    slug: str,
    stem: str,
    options: list[dict],
    answer: str,
) -> dict:
    subject = crud_question_source.get_subject_by_slug(db, slug)
    if subject is None:
        raise _error(status.HTTP_404_NOT_FOUND, "SUBJECT_NOT_FOUND", "Subject not found.")
    opt_list = [{"label": str(o.get("label", "")).strip(), "text": str(o.get("text", "")).strip()} for o in (options or [])]
    parts = _normalize_question_dict_for_source((stem or "").strip(), opt_list, (answer or "").strip())
    h = parts["normalized_hash"]
    bank = _get_aggregated_bank_source(db, subject.id)
    if bank is None:
        return {"normalizedHash": h, "existsInBank": False}
    existing = crud_question_source.list_questions_by_normalized_hash(db, source_id=bank.id, normalized_hash=h)
    return {"normalizedHash": h, "existsInBank": len(existing) > 0}


def append_question_to_source(
    db: Session,
    *,
    slug: str,
    source_id: str,
    stem: str,
    options: list[dict],
    answer: str,
) -> dict:
    subject = crud_question_source.get_subject_by_slug(db, slug)
    if subject is None:
        raise _error(status.HTTP_404_NOT_FOUND, "SUBJECT_NOT_FOUND", "Subject not found.")

    source = crud_question_source.get_source_by_id(db, subject_id=subject.id, source_id=source_id)
    if source is None:
        raise _error(status.HTTP_404_NOT_FOUND, "SOURCE_NOT_FOUND", "Source not found for subject.")

    stem_s = (stem or "").strip()
    opt_list = [{"label": str(o.get("label", "")).strip(), "text": str(o.get("text", "")).strip()} for o in (options or [])]
    answer_s = (answer or "").strip()
    if not stem_s:
        raise _error(status.HTTP_422_UNPROCESSABLE_ENTITY, "INVALID_QUESTION", "Question stem must not be empty.")

    warnings: list[str] = []
    if not opt_list:
        warnings.append("Question has no options.")
    if not answer_s:
        warnings.append("Question has no explicit answer.")

    parts = _normalize_question_dict_for_source(stem_s, opt_list, answer_s)
    next_ord = crud_question_source.get_max_ordinal_for_source(db, source_id=source.id) + 1

    crud_question_source.insert_question_row(
        db,
        source_id=source.id,
        ordinal=next_ord,
        stem=parts["stem"],
        options_json=parts["options"],
        answers_json=parts["answers"],
        answer_text=parts["answer_text"],
        normalized_hash=parts["normalized_hash"],
    )
    new_count = len(crud_question_source.list_source_questions_payload(db, source.id))
    crud_question_source.update_source_question_stats(
        db, source=source, question_count=new_count, warnings=warnings
    )

    if not _is_aggregated_bank_filename(source.file_name):
        bank = _get_aggregated_bank_source(db, subject.id)
        if bank is not None:
            merge_deck_into_aggregated_bank(db, slug=subject.slug, deck_source_id=source.id, uploader_id=None)

    subject_slug = subject.slug
    _schedule_after_commit(db, lambda: (_invalidate_subject_catalog(), _invalidate_subject_reads(subject_slug)))
    return {
        "sourceId": source.id,
        "subjectSlug": subject.slug,
        "examCode": source.exam_code,
        "fileName": source.file_name,
        "ordinal": next_ord,
        "questionCount": new_count,
        "warnings": warnings,
    }


def delete_source_question(db: Session, *, slug: str, source_id: str, ordinal: int) -> dict:
    subject = crud_question_source.get_subject_by_slug(db, slug)
    if subject is None:
        raise _error(status.HTTP_404_NOT_FOUND, "SUBJECT_NOT_FOUND", "Subject not found.")

    source = crud_question_source.get_source_by_id(db, subject_id=subject.id, source_id=source_id)
    if source is None:
        raise _error(status.HTTP_404_NOT_FOUND, "SOURCE_NOT_FOUND", "Source not found for subject.")

    rows = crud_question_source.list_source_questions_payload(db, source.id)
    removed_row = next((r for r in rows if int(r.get("ordinal") or 0) == ordinal), None)
    removed_hash = (removed_row or {}).get("normalized_hash") or ""
    filtered = [r for r in rows if int(r.get("ordinal") or 0) != ordinal]
    if len(filtered) == len(rows):
        raise _error(status.HTTP_404_NOT_FOUND, "QUESTION_NOT_FOUND", "Question not found for this source.")

    if not filtered:
        crud_question_source.replace_source_questions(db, source_id=source.id, payload=[])
        crud_question_source.update_source_question_stats(db, source=source, question_count=0, warnings=[])
        if not _is_aggregated_bank_filename(source.file_name):
            bank = _get_aggregated_bank_source(db, subject.id)
            if bank is not None:
                merge_deck_into_aggregated_bank(db, slug=subject.slug, deck_source_id=source.id, uploader_id=None)
                if removed_hash:
                    _prune_bank_row_if_hash_orphaned(db, subject=subject, bank=bank, normalized_hash=removed_hash)
        subject_slug = subject.slug
        _schedule_after_commit(db, lambda: (_invalidate_subject_catalog(), _invalidate_subject_reads(subject_slug)))
        return {
            "sourceId": source.id,
            "subjectSlug": subject.slug,
            "examCode": source.exam_code,
            "fileName": source.file_name,
            "questionCount": 0,
        }

    questions_for_replace = [
        {"stem": r["stem"], "options": r["options"], "answer": r["answer"]} for r in filtered
    ]
    out = update_source_questions(db, slug, source_id, questions_for_replace)
    if not _is_aggregated_bank_filename(source.file_name) and removed_hash:
        bank = _get_aggregated_bank_source(db, subject.id)
        if bank is not None:
            _prune_bank_row_if_hash_orphaned(db, subject=subject, bank=bank, normalized_hash=removed_hash)
            subject_slug = subject.slug
            _schedule_after_commit(db, lambda: (_invalidate_subject_catalog(), _invalidate_subject_reads(subject_slug)))
    return {
        "sourceId": out["sourceId"],
        "subjectSlug": out["subjectSlug"],
        "examCode": out["examCode"],
        "fileName": out["fileName"],
        "questionCount": out["questionCount"],
    }


def update_source_from_markdown(
    db: Session,
    *,
    slug: str,
    source_id: str,
    file: UploadFile,
) -> dict:
    subject = crud_question_source.get_subject_by_slug(db, slug)
    if subject is None:
        raise _error(status.HTTP_404_NOT_FOUND, "SUBJECT_NOT_FOUND", "Subject not found.")

    source = crud_question_source.get_source_by_id(db, subject_id=subject.id, source_id=source_id)
    if source is None:
        raise _error(status.HTTP_404_NOT_FOUND, "SOURCE_NOT_FOUND", "Source not found for subject.")

    if not file.filename or not file.filename.lower().endswith(".md"):
        raise _error(status.HTTP_415_UNSUPPORTED_MEDIA_TYPE, "INVALID_FILE_TYPE", "Only .md files are accepted.")

    raw_bytes = file.file.read(_MAX_UPLOAD_BYTES + 1)
    if len(raw_bytes) > _MAX_UPLOAD_BYTES:
        raise _error(status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, "FILE_TOO_LARGE", "File exceeds 5MB limit.")

    stem = _stem_from_markdown_upload_filename(file.filename)
    if not stem:
        raise _error(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            "INVALID_UPLOAD_FILENAME",
            "Filename must yield a non-empty label after removing .md.",
        )

    metadata = detect_subject_and_exam_with_fallback(file.filename, slug)
    if metadata["subjectSlug"] != slug.lower():
        raise _error(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            "SUBJECT_MISMATCH",
            "Uploaded markdown does not match target subject.",
        )

    markdown_text = raw_bytes.decode("utf-8", errors="ignore")
    parsed_questions, parse_warnings = parse_questions(markdown_text)
    checksum = f"sha256:{hashlib.sha256(raw_bytes).hexdigest()}"
    existing = crud_question_source.get_source_by_checksum(
        db, subject_id=subject.id, exam_code=metadata["examCode"], checksum_sha256=checksum
    )
    if existing is not None and existing.id != source.id:
        raise _error(
            status.HTTP_409_CONFLICT,
            "DUPLICATE_SOURCE",
            "A source with the same exam code and checksum already exists.",
            details={"existingSourceId": existing.id},
        )

    source.exam_code = metadata["examCode"]
    source.file_name = stem
    source.checksum_sha256 = checksum
    source.parse_warnings = parse_warnings
    source.question_count = len(parsed_questions)
    db.add(source)

    crud_question_source.replace_source_questions(db, source_id=source.id, payload=parsed_questions)
    db.flush()
    subject_slug = subject.slug
    _schedule_after_commit(db, lambda: (_invalidate_subject_catalog(), _invalidate_subject_reads(subject_slug)))

    return {
        "sourceId": source.id,
        "subjectSlug": subject.slug,
        "subjectCode": subject.code,
        "examCode": source.exam_code,
        "fileName": source.file_name,
        "checksum": source.checksum_sha256,
        "questionCount": source.question_count,
        "warnings": parse_warnings,
        "deduplicated": False,
    }


def upsert_source_from_markdown_by_slug(
    db: Session,
    *,
    slug: str,
    file: UploadFile,
    uploader_id: str | None,
) -> dict:
    """
    Simple admin flow: upload `.md` with explicit subject slug.

    Behavior:
    - Subject slug is the source-of-truth; if subject does not exist, create it.
    - New upload creates a new source row under that subject.
    - Exact duplicate (same examCode + checksum) returns existing source with deduplicated=True.
    - For mistaken upload, admin should hard-delete source, then upload again.
    """
    normalized_slug = slug.strip().lower()
    if not normalized_slug:
        raise _error(status.HTTP_422_UNPROCESSABLE_ENTITY, "INVALID_SUBJECT_SLUG", "Subject slug is required.")
    subject = crud_question_source.get_or_create_subject(
        db, slug=normalized_slug, code=_subject_code_from_slug(normalized_slug)
    )

    if not file.filename or not file.filename.lower().endswith(".md"):
        raise _error(status.HTTP_415_UNSUPPORTED_MEDIA_TYPE, "INVALID_FILE_TYPE", "Only .md files are accepted.")

    stem = _stem_from_markdown_upload_filename(file.filename)
    if not stem:
        raise _error(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            "INVALID_UPLOAD_FILENAME",
            "Filename must yield a non-empty label after removing .md.",
        )

    raw_bytes = file.file.read(_MAX_UPLOAD_BYTES + 1)
    if len(raw_bytes) > _MAX_UPLOAD_BYTES:
        raise _error(status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, "FILE_TOO_LARGE", "File exceeds 5MB limit.")

    if _is_aggregated_bank_filename(file.filename):
        metadata = detect_subject_and_exam_with_fallback(file.filename, normalized_slug)
    else:
        metadata = {"examCode": stem}

    checksum = f"sha256:{hashlib.sha256(raw_bytes).hexdigest()}"
    same_checksum = crud_question_source.get_source_by_checksum(
        db, subject_id=subject.id, exam_code=metadata["examCode"], checksum_sha256=checksum
    )
    if same_checksum is not None:
        return {
            "sourceId": same_checksum.id,
            "subjectSlug": subject.slug,
            "subjectCode": subject.code,
            "examCode": same_checksum.exam_code,
            "fileName": same_checksum.file_name,
            "checksum": same_checksum.checksum_sha256,
            "questionCount": int(same_checksum.question_count or 0),
            "warnings": same_checksum.parse_warnings or [],
            "deduplicated": True,
        }

    markdown_text = raw_bytes.decode("utf-8", errors="ignore")
    parsed_questions, parse_warnings = parse_questions(markdown_text)
    source = crud_question_source.create_source(
        db,
        subject_id=subject.id,
        exam_code=metadata["examCode"],
        file_name=stem,
        checksum_sha256=checksum,
        uploaded_by=uploader_id,
        warnings=parse_warnings,
        question_count=len(parsed_questions),
    )

    crud_question_source.replace_source_questions(db, source_id=source.id, payload=parsed_questions)
    db.flush()
    subject_slug = subject.slug
    _schedule_after_commit(db, lambda: (_invalidate_subject_catalog(), _invalidate_subject_reads(subject_slug)))
    return {
        "sourceId": source.id,
        "subjectSlug": subject.slug,
        "subjectCode": subject.code,
        "examCode": source.exam_code,
        "fileName": source.file_name,
        "checksum": source.checksum_sha256,
        "questionCount": source.question_count,
        "warnings": parse_warnings,
        "deduplicated": False,
    }


def ensure_admin_subject(db: Session, *, slug: str) -> dict:
    """Idempotent: ensure subject exists for admin deck tooling; bump subjects catalog cache."""
    normalized_slug = slug.strip().lower()
    if not normalized_slug:
        raise _error(status.HTTP_422_UNPROCESSABLE_ENTITY, "INVALID_SUBJECT_SLUG", "Subject slug is required.")
    subject = crud_question_source.get_or_create_subject(
        db, slug=normalized_slug, code=_subject_code_from_slug(normalized_slug)
    )
    _schedule_after_commit(db, lambda: _invalidate_subject_catalog())
    bank_counts = crud_question_source.bank_question_counts_by_subject_ids(db, [subject.id])
    return {
        "slug": subject.slug,
        "code": subject.code,
        "hint": "Mon luyen de",
        "bankQuestionCount": bank_counts.get(subject.id, 0),
    }


def delete_source(db: Session, *, slug: str, source_id: str) -> dict:
    subject = crud_question_source.get_subject_by_slug(db, slug)
    if subject is None:
        raise _error(status.HTTP_404_NOT_FOUND, "SUBJECT_NOT_FOUND", "Subject not found.")

    source = crud_question_source.get_source_by_id(db, subject_id=subject.id, source_id=source_id)
    if source is None:
        raise _error(status.HTTP_404_NOT_FOUND, "SOURCE_NOT_FOUND", "Source not found for subject.")

    source_file_name = source.file_name
    crud_question_source.hard_delete_source(db, source_id=source.id)
    subject_slug = subject.slug
    _schedule_after_commit(db, lambda: (_invalidate_subject_catalog(), _invalidate_subject_reads(subject_slug)))
    return {
        "sourceId": source_id,
        "subjectSlug": subject.slug,
        "fileName": source_file_name,
        "deleted": True,
        "hardDeleted": True,
    }


def _question_row_to_replace_payload(item: dict, ordinal: int) -> dict:
    return {
        "ordinal": ordinal,
        "stem": item["stem"],
        "options": item["options"],
        "answers": item.get("answers") or [],
        "answer_text": item.get("answer_text") or item.get("answer") or "",
        "normalized_hash": item["normalized_hash"],
    }


def _normalized_hash_present_in_any_deck(db: Session, subject_id: str, normalized_hash: str) -> bool:
    if not normalized_hash:
        return False
    for src in crud_question_source.list_sources_by_subject(db, subject_id):
        if _is_aggregated_bank_filename(src.file_name):
            continue
        for row in crud_question_source.list_source_questions_payload(db, src.id):
            if row.get("normalized_hash") == normalized_hash:
                return True
    return False


def _prune_bank_row_if_hash_orphaned(
    db: Session,
    *,
    subject,
    bank,
    normalized_hash: str,
) -> None:
    """Drop bank rows for this hash when no non-bank deck still has that question (bank-only rows unchanged)."""
    if not normalized_hash:
        return
    if _normalized_hash_present_in_any_deck(db, subject.id, normalized_hash):
        return
    bank_rows = crud_question_source.list_source_questions_payload(db, bank.id)
    kept = [r for r in bank_rows if r.get("normalized_hash") != normalized_hash]
    if len(kept) == len(bank_rows):
        return
    payload = [_question_row_to_replace_payload(row, i) for i, row in enumerate(kept, start=1)]
    crud_question_source.replace_source_questions(db, source_id=bank.id, payload=payload)
    crud_question_source.update_source_question_stats(db, source=bank, question_count=len(payload), warnings=[])
    db.flush()


def _compute_merge_deck_into_bank_payload(
    bank_questions: list[dict],
    deck_questions: list[dict],
) -> tuple[list[dict], int, int]:
    """Return (replace_payload, added_count, skipped_duplicate_count)."""
    seen: set[str] = set()
    merged_rows: list[dict] = []
    for q in bank_questions:
        h = q.get("normalized_hash")
        if not h:
            continue
        if h not in seen:
            seen.add(h)
            merged_rows.append(q)
    added = 0
    skipped = 0
    for q in deck_questions:
        h = q.get("normalized_hash")
        if not h:
            continue
        if h in seen:
            skipped += 1
            continue
        seen.add(h)
        merged_rows.append(q)
        added += 1
    replace_payload = [_question_row_to_replace_payload(row, i) for i, row in enumerate(merged_rows, start=1)]
    return replace_payload, added, skipped


def _get_aggregated_bank_source(db: Session, subject_id: str):
    sources = crud_question_source.list_sources_by_subject(db, subject_id)
    return next((s for s in sources if _is_aggregated_bank_filename(s.file_name)), None)


def _ensure_aggregated_bank_source(db: Session, *, subject_id: str, uploader_id: str | None):
    existing = _get_aggregated_bank_source(db, subject_id)
    if existing is not None:
        return existing
    seed = b""
    checksum = f"sha256:{hashlib.sha256(seed).hexdigest()}"
    bank = crud_question_source.create_source(
        db,
        subject_id=subject_id,
        exam_code="AGG-BANK",
        file_name="cau-hoi-tong-hop",
        checksum_sha256=checksum,
        uploaded_by=uploader_id,
        warnings=[],
        question_count=0,
    )
    crud_question_source.replace_source_questions(db, source_id=bank.id, payload=[])
    db.flush()
    return bank


def _validate_deck_for_merge(db: Session, *, subject, deck_source_id: str):
    deck = crud_question_source.get_source_by_id(db, subject_id=subject.id, source_id=deck_source_id)
    if deck is None:
        raise _error(status.HTTP_404_NOT_FOUND, "SOURCE_NOT_FOUND", "Deck source not found for subject.")
    if _is_aggregated_bank_filename(deck.file_name):
        raise _error(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            "CANNOT_MERGE_AGGREGATED_SOURCE",
            "Cannot merge the aggregated bank source into itself.",
        )
    return deck


def merge_deck_into_aggregated_bank_preview(db: Session, *, slug: str, deck_source_id: str) -> dict:
    normalized_slug = slug.strip().lower()
    if not normalized_slug:
        raise _error(status.HTTP_422_UNPROCESSABLE_ENTITY, "INVALID_SUBJECT_SLUG", "Subject slug is required.")
    subject = crud_question_source.get_subject_by_slug(db, normalized_slug)
    if subject is None:
        raise _error(status.HTTP_404_NOT_FOUND, "SUBJECT_NOT_FOUND", "Subject not found.")
    _validate_deck_for_merge(db, subject=subject, deck_source_id=deck_source_id)
    bank = _get_aggregated_bank_source(db, subject.id)
    bank_questions = crud_question_source.list_source_questions_payload(db, bank.id) if bank is not None else []
    deck_questions = crud_question_source.list_source_questions_payload(db, deck_source_id)
    replace_payload, added, skipped = _compute_merge_deck_into_bank_payload(bank_questions, deck_questions)
    return {
        "subjectSlug": subject.slug,
        "deckSourceId": deck_source_id,
        "added": added,
        "skippedDuplicate": skipped,
        "bankQuestionCountAfter": len(replace_payload),
        "wouldCreateBank": bank is None,
    }


def merge_deck_into_aggregated_bank(
    db: Session,
    *,
    slug: str,
    deck_source_id: str,
    uploader_id: str | None,
) -> dict:
    normalized_slug = slug.strip().lower()
    if not normalized_slug:
        raise _error(status.HTTP_422_UNPROCESSABLE_ENTITY, "INVALID_SUBJECT_SLUG", "Subject slug is required.")
    subject = crud_question_source.get_subject_by_slug(db, normalized_slug)
    if subject is None:
        raise _error(status.HTTP_404_NOT_FOUND, "SUBJECT_NOT_FOUND", "Subject not found.")
    _validate_deck_for_merge(db, subject=subject, deck_source_id=deck_source_id)
    bank = _ensure_aggregated_bank_source(db, subject_id=subject.id, uploader_id=uploader_id)
    bank_questions = crud_question_source.list_source_questions_payload(db, bank.id)
    deck_questions = crud_question_source.list_source_questions_payload(db, deck_source_id)
    replace_payload, added, skipped = _compute_merge_deck_into_bank_payload(bank_questions, deck_questions)
    crud_question_source.replace_source_questions(db, source_id=bank.id, payload=replace_payload)
    bank.question_count = len(replace_payload)
    db.add(bank)
    db.flush()
    subject_slug = subject.slug
    _schedule_after_commit(db, lambda: (_invalidate_subject_catalog(), _invalidate_subject_reads(subject_slug)))
    return {
        "subjectSlug": subject.slug,
        "bankSourceId": bank.id,
        "deckSourceId": deck_source_id,
        "added": added,
        "skippedDuplicate": skipped,
        "bankQuestionCount": len(replace_payload),
    }


async def list_subjects_page_async(db: AsyncSession, *, page: int, limit: int, q: str | None = None) -> dict:
    return await db.run_sync(lambda sync_db: list_subjects_page(sync_db, page=page, limit=limit, q=q))


async def get_admin_subject_sources_page_async(db: AsyncSession, slug: str, *, page: int, limit: int, q: str | None = None) -> dict:
    return await db.run_sync(lambda sync_db: get_admin_subject_sources_page(sync_db, slug, page=page, limit=limit, q=q))


async def get_source_state_async(db: AsyncSession, slug: str) -> dict:
    normalized_slug = slug.lower()
    version = _cache_subject_version(normalized_slug)
    cache_key = f"qs:subject:{normalized_slug}:source-state:v{version}"
    cached = cache_service.get_json(cache_key)
    if isinstance(cached, dict):
        return cached
    sources, questions_by_source = await crud_question_source_async.get_source_state_async(db, slug)
    if not sources:
        subject = await db.run_sync(lambda sync_db: crud_question_source.get_subject_by_slug(sync_db, slug))
        if subject is None:
            raise _error(status.HTTP_404_NOT_FOUND, "SUBJECT_NOT_FOUND", "Subject not found.")
        payload = {"bankQuestions": [], "deckQuestions": [], "files": [], "hocTheoDeLayout": "markdownFiles"}
        cache_service.set_json(cache_key, payload, _CACHE_SUBJECT_READ_TTL_SECONDS)
        return payload
    bank_source = next((item for item in sources if _is_aggregated_bank_filename(item.file_name)), None) or sources[0]
    deck_sources = sorted(
        [item for item in sources if not _is_aggregated_bank_filename(item.file_name)],
        key=lambda s: _exam_sort_key(s.file_name, s.exam_code),
    )
    bank_questions = questions_by_source.get(bank_source.id, [])
    bank_formatted = [
        {"id": idx, "stem": item["stem"], "options": item["options"], "answer": item["answer"]}
        for idx, item in enumerate(bank_questions, start=1)
    ]
    deck_questions: list[dict] = []
    files: list[dict] = []
    running_index = 0
    for source in deck_sources:
        questions = questions_by_source.get(source.id, [])
        start = running_index
        next_questions = [
            {"id": idx + running_index + 1, "stem": item["stem"], "options": item["options"], "answer": item["answer"]}
            for idx, item in enumerate(questions)
        ]
        deck_questions.extend(next_questions)
        running_index = len(deck_questions)
        end = running_index - 1
        has_questions = len(questions) > 0
        files.append(
            {
                "deckId": source.id,
                "fileName": source.file_name,
                "isEmpty": not has_questions,
                "questionCount": int(source.question_count or 0),
                "range": {"start": start, "end": end} if has_questions else {"start": 0, "end": 0},
            }
        )
    payload = {
        "bankQuestions": bank_formatted,
        "deckQuestions": deck_questions,
        "files": files,
        "hocTheoDeLayout": "markdownFiles",
    }
    cache_service.set_json(cache_key, payload, _CACHE_SUBJECT_READ_TTL_SECONDS)
    return payload


async def get_subject_bank_page_async(db: AsyncSession, slug: str, *, page: int, limit: int) -> dict:
    return await db.run_sync(lambda sync_db: get_subject_bank_page(sync_db, slug, page=page, limit=limit))


async def get_subject_bank_progress_async(db: AsyncSession, *, slug: str, user_id: str) -> dict:
    return await db.run_sync(lambda sync_db: get_subject_bank_progress(sync_db, slug=slug, user_id=user_id))


async def get_subject_decks_async(db: AsyncSession, slug: str, *, user_id: str | None = None) -> list[dict]:
    return await db.run_sync(lambda sync_db: get_subject_decks(sync_db, slug, user_id=user_id))


async def get_deck_questions_page_async(
    db: AsyncSession, slug: str, deck_id: str, *, page: int, limit: int, q: str | None = None
) -> dict:
    return await db.run_sync(
        lambda sync_db: get_deck_questions_page(sync_db, slug, deck_id, page=page, limit=limit, q=q)
    )


async def update_source_questions_async(
    db: AsyncSession, slug: str, source_id: str, questions: list[dict]
) -> dict:
    return await db.run_sync(lambda sync_db: update_source_questions(sync_db, slug, source_id, questions))


async def patch_source_question_async(
    db: AsyncSession,
    *,
    slug: str,
    source_id: str,
    ordinal: int,
    stem: str | None,
    options: list[dict] | None,
    answer: str | None,
) -> dict:
    return await db.run_sync(
        lambda sync_db: patch_source_question(
            sync_db,
            slug=slug,
            source_id=source_id,
            ordinal=ordinal,
            stem=stem,
            options=options,
            answer=answer,
        )
    )


async def check_bank_duplicate_async(
    db: AsyncSession,
    *,
    slug: str,
    stem: str,
    options: list[dict],
    answer: str,
) -> dict:
    return await db.run_sync(
        lambda sync_db: check_bank_duplicate(sync_db, slug=slug, stem=stem, options=options, answer=answer)
    )


async def append_question_to_source_async(
    db: AsyncSession,
    *,
    slug: str,
    source_id: str,
    stem: str,
    options: list[dict],
    answer: str,
) -> dict:
    return await db.run_sync(
        lambda sync_db: append_question_to_source(
            sync_db, slug=slug, source_id=source_id, stem=stem, options=options, answer=answer
        )
    )


async def delete_source_question_async(
    db: AsyncSession,
    *,
    slug: str,
    source_id: str,
    ordinal: int,
) -> dict:
    return await db.run_sync(lambda sync_db: delete_source_question(sync_db, slug=slug, source_id=source_id, ordinal=ordinal))


async def check_deck_answer_async(
    db: AsyncSession,
    *,
    slug: str,
    deck_id: str,
    question_id: int,
    selected_answer: str,
) -> dict:
    return await db.run_sync(
        lambda sync_db: check_deck_answer(
            sync_db, slug=slug, deck_id=deck_id, question_id=question_id, selected_answer=selected_answer
        )
    )


async def update_deck_progress_async(
    db: AsyncSession,
    *,
    slug: str,
    deck_id: str,
    user_id: str,
    current_question: int,
    attempted_question_ordinals: list[int],
) -> dict:
    return await db.run_sync(
        lambda sync_db: update_deck_progress(
            sync_db,
            slug=slug,
            deck_id=deck_id,
            user_id=user_id,
            current_question=current_question,
            attempted_question_ordinals=attempted_question_ordinals,
        )
    )


async def get_deck_progress_async(db: AsyncSession, *, slug: str, deck_id: str, user_id: str) -> dict:
    return await db.run_sync(lambda sync_db: get_deck_progress(sync_db, slug=slug, deck_id=deck_id, user_id=user_id))


async def reset_deck_progress_async(db: AsyncSession, *, slug: str, deck_id: str, user_id: str) -> dict:
    return await db.run_sync(lambda sync_db: reset_deck_progress(sync_db, slug=slug, deck_id=deck_id, user_id=user_id))


async def update_deck_stats_async(
    db: AsyncSession,
    *,
    slug: str,
    deck_id: str,
    user_id: str,
    in_progress: int,
    completed: int,
) -> dict:
    return await db.run_sync(
        lambda sync_db: update_deck_stats(
            sync_db, slug=slug, deck_id=deck_id, user_id=user_id, in_progress=in_progress, completed=completed
        )
    )
