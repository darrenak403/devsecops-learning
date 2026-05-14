from fastapi import HTTPException
from io import BytesIO
from types import SimpleNamespace
from unittest.mock import ANY, Mock

from app.services import question_source_service
from app.services.question_source_service import (
    _answer_count_from_payload,
    _exam_sort_key,
    filter_subject_deck_payloads_by_q,
    get_admin_subject_sources_page,
    _stem_from_markdown_upload_filename,
    check_deck_answer,
    detect_subject_and_exam,
    detect_subject_and_exam_with_fallback,
    ensure_admin_subject,
    get_deck_progress,
    get_subject_decks,
    ingest_markdown_file,
    merge_deck_into_aggregated_bank,
    merge_deck_into_aggregated_bank_preview,
    parse_questions,
    patch_source_question,
    reset_deck_progress,
    update_deck_progress,
    update_deck_stats,
    update_source_questions,
)


def test_detect_subject_and_exam_success() -> None:
    payload = detect_subject_and_exam("PRN232 - SP 2025 - FE.md")
    assert payload["subjectSlug"] == "prn232"
    assert payload["examCode"] == "SP-2025-FE"


def test_detect_subject_and_exam_invalid_filename() -> None:
    try:
        detect_subject_and_exam("abc.md")
    except HTTPException as exc:
        assert exc.status_code == 422
        assert exc.detail["error"]["code"] == "UNRECOGNIZED_FILENAME_PATTERN"
    else:
        raise AssertionError("Expected HTTPException for invalid filename")


def test_stem_from_markdown_upload_filename_strips_md() -> None:
    assert _stem_from_markdown_upload_filename("SWE201c - FA 2024 - FE.md") == "SWE201c - FA 2024 - FE"
    assert _stem_from_markdown_upload_filename("  SWE201c - FA 2024 - FE.MD  ") == "SWE201c - FA 2024 - FE"
    assert _stem_from_markdown_upload_filename("MLN111C2 - SU 2025 - FEKTS.md") == "MLN111C2 - SU 2025 - FEKTS"


def test_filter_subject_deck_payloads_by_q() -> None:
    decks = [
        {"deckId": "1", "examCode": "SP-2024-FE", "fileName": "a.md"},
        {"deckId": "2", "examCode": "FA-2024-FE", "fileName": "b.md"},
    ]
    assert len(filter_subject_deck_payloads_by_q(decks, "  sp  ")) == 1
    assert filter_subject_deck_payloads_by_q(decks, "  sp  ")[0]["deckId"] == "1"
    assert len(filter_subject_deck_payloads_by_q(decks, None)) == 2
    assert len(filter_subject_deck_payloads_by_q(decks, "")) == 2


def test_exam_sort_key_bank_first_then_newest_first_then_unparseable() -> None:
    bank = _exam_sort_key("cau-hoi-tong-hop", "AGG-BANK")
    sp_2024 = _exam_sort_key("deck-a.md", "SP-2024-FE")
    fa_2024 = _exam_sort_key("deck-b.md", "FA-2024-FE")
    fa_2023 = _exam_sort_key("deck-c.md", "FA-2023-FE")
    weird = _exam_sort_key("custom-deck.md", "custom-deck")

    assert bank < fa_2024
    assert fa_2024 < sp_2024
    assert sp_2024 < fa_2023
    for k in (sp_2024, fa_2024, fa_2023):
        assert k < weird


def test_exam_sort_key_no_exam_type_still_parses() -> None:
    """Subtype (FE/RE/PT) not required; term+year enough."""
    sp_plain = _exam_sort_key("x.md", "SP-2024")
    fa_xyz = _exam_sort_key("y.md", "FA-2025-XYZ")
    assert sp_plain[0] == 1 and fa_xyz[0] == 1
    assert fa_xyz < sp_plain  # 2025 before 2024


def test_exam_sort_key_glued_term_year_and_abbr() -> None:
    fa2026 = _exam_sort_key("a.md", "FA2026")
    fa25 = _exam_sort_key("b.md", "FA25")
    fa_2024 = _exam_sort_key("c.md", "FA 2024")
    assert fa2026 < fa25 < fa_2024  # newest year first


def test_exam_sort_key_sp26_equals_sp2026() -> None:
    k26 = _exam_sort_key("MLN122_SP26_C1FE.md", "MLN122_SP26_C1FE")
    k2026 = _exam_sort_key("other.md", "SP-2026-FE")
    assert k26[:3] == k2026[:3]


def test_exam_sort_key_year_27_before_26() -> None:
    fa27 = _exam_sort_key("a.md", "FA2027")
    fa26 = _exam_sort_key("b.md", "FA2026")
    assert fa27 < fa26


def test_exam_sort_key_same_term_year_tiebreak_filename() -> None:
    fe = _exam_sort_key("MLN122 - SP 2024 - FE.md", "SP-2024-FE")
    re = _exam_sort_key("MLN122 - SP 2024 - RE.md", "SP-2024-RE")
    assert fe < re  # same sort prefix; filename lower wins


def test_exam_sort_key_mixed_filename_with_block() -> None:
    k = _exam_sort_key("MLN122 FA25 BLOCK5.md", "MLN122 FA25 BLOCK5")
    assert k == (1, -2025, -3, "mln122 fa25 block5.md")


def test_get_admin_subject_sources_page_filters_by_q(monkeypatch) -> None:
    fake_subject = SimpleNamespace(id="sub-1", slug="mln122", code="MLN122")
    sources = [
        SimpleNamespace(
            id="bank-1",
            file_name="cau-hoi-tong-hop",
            exam_code="AGG-BANK",
            question_count=500,
            uploaded_at=None,
        ),
        SimpleNamespace(
            id="src-sp-fe",
            file_name="MLN122 - SP 2024 - FE.md",
            exam_code="SP-2024-FE",
            question_count=10,
            uploaded_at=None,
        ),
        SimpleNamespace(
            id="src-sp-re",
            file_name="MLN122 - SP 2024 - RE.md",
            exam_code="SP-2024-RE",
            question_count=10,
            uploaded_at=None,
        ),
        SimpleNamespace(
            id="src-fa",
            file_name="MLN122 - FA 2024 - FE.md",
            exam_code="FA-2024-FE",
            question_count=10,
            uploaded_at=None,
        ),
    ]
    fake_crud = Mock()
    fake_crud.get_subject_by_slug.return_value = fake_subject
    fake_crud.list_sources_by_subject.return_value = sources
    monkeypatch.setattr(question_source_service, "crud_question_source", fake_crud)

    out = get_admin_subject_sources_page(Mock(), "mln122", page=1, limit=10, q="sp")
    assert out["total"] == 2
    assert {i["sourceId"] for i in out["items"]} == {"src-sp-fe", "src-sp-re"}

    out_all = get_admin_subject_sources_page(Mock(), "mln122", page=1, limit=10, q=None)
    assert out_all["total"] == 4


def test_upsert_source_from_markdown_by_slug_arbitrary_filename(monkeypatch) -> None:
    fake_subject = SimpleNamespace(id="sub-1", slug="mln111", code="MLN111")
    fake_crud = Mock()
    fake_crud.get_or_create_subject.return_value = fake_subject
    fake_crud.get_source_by_checksum.return_value = None

    def _create_source(_db, **kwargs):
        return SimpleNamespace(
            id="src-1",
            exam_code=kwargs["exam_code"],
            file_name=kwargs["file_name"],
            checksum_sha256=kwargs["checksum_sha256"],
            question_count=kwargs["question_count"],
            parse_warnings=kwargs.get("warnings") or [],
        )

    fake_crud.create_source.side_effect = _create_source
    monkeypatch.setattr(question_source_service, "crud_question_source", fake_crud)

    content = b"Cau 1: Test?\nA. Yes\nB. No\nDap an: A\n"
    upload = SimpleNamespace(filename="Anything goes - no pattern.md", file=BytesIO(content))

    question_source_service.upsert_source_from_markdown_by_slug(
        db=Mock(), slug="mln111", file=upload, uploader_id=None
    )

    exam_code = fake_crud.create_source.call_args.kwargs["exam_code"]
    file_name = fake_crud.create_source.call_args.kwargs["file_name"]
    assert exam_code == "Anything goes - no pattern"
    assert file_name == "Anything goes - no pattern"


def test_upsert_source_from_markdown_by_slug_bank_file_uses_agg_bank(monkeypatch) -> None:
    fake_subject = SimpleNamespace(id="sub-1", slug="mln111", code="MLN111")
    fake_crud = Mock()
    fake_crud.get_or_create_subject.return_value = fake_subject
    fake_crud.get_source_by_checksum.return_value = None

    def _create_source(_db, **kwargs):
        return SimpleNamespace(
            id="src-bank",
            exam_code=kwargs["exam_code"],
            file_name=kwargs["file_name"],
            checksum_sha256=kwargs["checksum_sha256"],
            question_count=kwargs["question_count"],
            parse_warnings=kwargs.get("warnings") or [],
        )

    fake_crud.create_source.side_effect = _create_source
    monkeypatch.setattr(question_source_service, "crud_question_source", fake_crud)

    content = b"Cau 1: Bank row?\nA. Yes\nB. No\nDap an: A\n"
    upload = SimpleNamespace(filename="cau-hoi-tong-hop.md", file=BytesIO(content))

    question_source_service.upsert_source_from_markdown_by_slug(
        db=Mock(), slug="mln111", file=upload, uploader_id=None
    )

    assert fake_crud.create_source.call_args.kwargs["exam_code"] == "AGG-BANK"
    assert fake_crud.create_source.call_args.kwargs["file_name"] == "cau-hoi-tong-hop"


def test_ensure_admin_subject_calls_get_or_create(monkeypatch) -> None:
    fake_subject = SimpleNamespace(id="sub-1", slug="newsub", code="NEWSUB")
    fake_crud = Mock()
    fake_crud.get_or_create_subject.return_value = fake_subject
    fake_crud.bank_question_counts_by_subject_ids.return_value = {"sub-1": 0}
    monkeypatch.setattr(question_source_service, "crud_question_source", fake_crud)
    monkeypatch.setattr(question_source_service, "_schedule_after_commit", lambda db, fn: None)
    monkeypatch.setattr(question_source_service, "_invalidate_subject_catalog", lambda: None)

    out = ensure_admin_subject(Mock(), slug="  newsub  ")
    assert out["slug"] == "newsub"
    assert out["code"] == "NEWSUB"
    assert out["bankQuestionCount"] == 0
    fake_crud.get_or_create_subject.assert_called_once()


def test_parse_questions_extracts_basic_fields() -> None:
    markdown = """
    Câu 1: Python là gì?
    A. Ngôn ngữ lập trình
    B. Món ăn
    Đáp án: A
    """
    questions, warnings = parse_questions(markdown)
    assert len(questions) == 1
    assert questions[0]["stem"] == "Python là gì?"
    assert questions[0]["options"][0]["label"] == "A"
    assert warnings == []


def test_parse_questions_extracts_inline_answer_from_stem() -> None:
    markdown = """
    Câu 1: Theo Mác-Lênin lực lượng cơ bản của xã hội là gì? Đáp án: A
    A. Quần chúng nhân dân
    B. Giai cấp nông dân
    C. Lãnh tụ
    D. Vĩ nhân
    """
    questions, _ = parse_questions(markdown)
    assert len(questions) == 1
    assert questions[0]["stem"].endswith("là gì?")
    assert questions[0]["answer_text"] == "A"


def test_parse_questions_supports_options_e_to_h() -> None:
    markdown = """
Câu 1: Pick the constant sum scale.
A. Ordinal
B. Nominal
C. Semantic differential
D. Likert
E. Constant sum
F. None
Đáp án: E
"""
    questions, warnings = parse_questions(markdown)
    assert len(questions) == 1
    assert warnings == []
    assert len(questions[0]["options"]) == 6
    assert questions[0]["options"][4] == {"label": "E", "text": "Constant sum"}
    assert questions[0]["answer_text"] == "E"
    assert questions[0]["answers"] == ["E"]
    assert "Constant sum" not in questions[0]["stem"]


def test_inline_answer_supports_letters_beyond_d() -> None:
    markdown = "Câu 1: ABC? Đáp án: E,F\nA. a\nB. b\nC. c\nD. d\nE. e\nF. f"
    questions, _ = parse_questions(markdown)
    assert questions[0]["answers"] == ["E", "F"]


def test_answer_count_from_payload() -> None:
    assert _answer_count_from_payload({"answers": ["A"], "answer": "A"}) == 1
    assert _answer_count_from_payload({"answers": ["A", "C"], "answer": "A,C"}) == 2
    assert _answer_count_from_payload({"answers": [], "answer": "A; C; D"}) == 3


def test_ingest_markdown_file_persists_via_crud_path(monkeypatch) -> None:
    fake_subject = SimpleNamespace(id="subject-1")
    fake_source = SimpleNamespace(id="source-1")
    fake_crud = Mock()
    fake_crud.get_or_create_subject.return_value = fake_subject
    fake_crud.get_source_by_checksum.return_value = None
    fake_crud.create_source.return_value = fake_source
    monkeypatch.setattr(question_source_service, "crud_question_source", fake_crud)

    content = b"Cau 1: What is Python?\nA. Language\nB. Animal\nDap an: A\n"
    upload = SimpleNamespace(filename="PRN232 - SP 2025 - FE.md", file=BytesIO(content))

    result = ingest_markdown_file(db=Mock(), file=upload, uploader_id="admin-1")

    assert result["sourceId"] == "source-1"
    assert result["deduplicated"] is False
    assert result["fileName"] == "PRN232 - SP 2025 - FE"
    fake_crud.create_source.assert_called_once()
    assert fake_crud.create_source.call_args.kwargs["file_name"] == "PRN232 - SP 2025 - FE"
    fake_crud.replace_source_questions.assert_called_once()


def test_detect_aggregated_file_requires_subject_slug() -> None:
    try:
        detect_subject_and_exam_with_fallback("cau-hoi-tong-hop.md", None)
    except HTTPException as exc:
        assert exc.status_code == 422
        assert exc.detail["error"]["code"] == "SUBJECT_SLUG_REQUIRED_FOR_AGGREGATED_FILE"
    else:
        raise AssertionError("Expected HTTPException for missing subjectSlug")


def test_get_subject_decks_excludes_aggregated_bank(monkeypatch) -> None:
    fake_subject = SimpleNamespace(id="subject-1")
    aggregated = SimpleNamespace(
        id="src-bank", exam_code="AGG-BANK", file_name="cau-hoi-tong-hop.md", question_count=200, uploaded_at=None
    )
    deck = SimpleNamespace(
        id="src-deck", exam_code="FA-2024-FE", file_name="PMG201c - FA 2024 - FE.md", question_count=50, uploaded_at=None
    )
    fake_crud = Mock()
    fake_crud.get_subject_by_slug.return_value = fake_subject
    fake_crud.list_sources_by_subject.return_value = [aggregated, deck]
    fake_crud.list_user_stats_by_source_ids.return_value = {}
    monkeypatch.setattr(question_source_service, "crud_question_source", fake_crud)
    monkeypatch.setattr(question_source_service.cache_service, "get_json", lambda _key: None)
    monkeypatch.setattr(question_source_service.cache_service, "set_json", lambda _key, _value, _ttl=None: None)

    decks = get_subject_decks(Mock(), "pmg201c")
    assert len(decks) == 1
    assert decks[0]["deckId"] == "src-deck"
    assert decks[0]["stats"]["total"] == 50
    assert decks[0]["stats"]["inProgress"] == 0
    assert decks[0]["stats"]["completed"] == 0
    assert decks[0]["stats"]["learnedCount"] == 0
    assert decks[0]["stats"]["completionRatePercent"] == 0


def test_update_deck_stats_validates_total(monkeypatch) -> None:
    fake_subject = SimpleNamespace(id="subject-1", slug="pmg201c")
    fake_source = SimpleNamespace(id="src-deck", question_count=50)
    fake_crud = Mock()
    fake_crud.get_subject_by_slug.return_value = fake_subject
    fake_crud.get_source_by_id.return_value = fake_source
    monkeypatch.setattr(question_source_service, "crud_question_source", fake_crud)

    result = update_deck_stats(
        Mock(),
        slug="pmg201c",
        deck_id="src-deck",
        user_id="user-1",
        in_progress=2,
        completed=3,
    )
    assert result["stats"]["total"] == 50
    assert result["stats"]["completionRatePercent"] == 4  # inProgress/total = 2/50 = 4%

    try:
        update_deck_stats(
            Mock(),
            slug="pmg201c",
            deck_id="src-deck",
            user_id="user-1",
            in_progress=40,
            completed=20,
        )
    except HTTPException as exc:
        assert exc.status_code == 422
        assert exc.detail["error"]["code"] == "INVALID_DECK_STATS"
    else:
        raise AssertionError("Expected HTTPException when deck stats exceed total questions")


def test_update_deck_progress_increments_completed_attempts(monkeypatch) -> None:
    fake_subject = SimpleNamespace(id="subject-1", slug="pmg201c")
    fake_source = SimpleNamespace(id="src-deck", question_count=50)
    fake_crud = Mock()
    fake_crud.get_subject_by_slug.return_value = fake_subject
    fake_crud.get_source_by_id.return_value = fake_source
    fake_crud.list_user_stats_by_source_ids.return_value = {
        "src-deck": {"current_question_ordinal": 49, "completed_attempts": 0}
    }
    monkeypatch.setattr(question_source_service, "crud_question_source", fake_crud)

    result = update_deck_progress(
        Mock(),
        slug="pmg201c",
        deck_id="src-deck",
        user_id="user-1",
        current_question=50,
        attempted_question_ordinals=[5, 2, 2, 1],
    )
    assert result["stats"]["completionRatePercent"] == 100
    assert result["stats"]["completed"] == 1
    assert result["attemptedQuestionOrdinals"] == [1, 2, 5]
    fake_crud.upsert_source_user_stats.assert_called_once()


def test_update_deck_progress_rejects_invalid_attempted_ordinals(monkeypatch) -> None:
    fake_subject = SimpleNamespace(id="subject-1", slug="pmg201c")
    fake_source = SimpleNamespace(id="src-deck", question_count=5)
    fake_crud = Mock()
    fake_crud.get_subject_by_slug.return_value = fake_subject
    fake_crud.get_source_by_id.return_value = fake_source
    fake_crud.list_user_stats_by_source_ids.return_value = {}
    monkeypatch.setattr(question_source_service, "crud_question_source", fake_crud)

    try:
        update_deck_progress(
            Mock(),
            slug="pmg201c",
            deck_id="src-deck",
            user_id="user-1",
            current_question=3,
            attempted_question_ordinals=[1, 2, 9],
        )
    except HTTPException as exc:
        assert exc.status_code == 422
        assert exc.detail["error"]["code"] == "INVALID_ATTEMPTED_QUESTION_ORDINALS"
    else:
        raise AssertionError("Expected HTTPException for invalid attempted ordinals")


def test_get_deck_progress_filters_invalid_ordinals(monkeypatch) -> None:
    fake_subject = SimpleNamespace(id="subject-1", slug="pmg201c")
    fake_source = SimpleNamespace(id="src-deck", question_count=5)
    fake_updated_at = SimpleNamespace(isoformat=lambda: "2026-04-20T03:10:00+00:00")
    fake_crud = Mock()
    fake_crud.get_subject_by_slug.return_value = fake_subject
    fake_crud.get_source_by_id.return_value = fake_source
    fake_crud.list_user_stats_by_source_ids.return_value = {
        "src-deck": {
            "current_question_ordinal": 8,
            "attempted_question_ordinals": [5, 3, 3, 10, 0],
            "updated_at": fake_updated_at,
        }
    }
    monkeypatch.setattr(question_source_service, "crud_question_source", fake_crud)

    result = get_deck_progress(
        Mock(),
        slug="pmg201c",
        deck_id="src-deck",
        user_id="user-1",
    )
    assert result["currentQuestion"] == 1
    assert result["attemptedQuestionOrdinals"] == [3, 5]
    assert result["updatedAt"] == "2026-04-20T03:10:00+00:00"


def test_check_deck_answer_returns_correctness(monkeypatch) -> None:
    fake_subject = SimpleNamespace(id="subject-1", slug="pmg201c")
    fake_source = SimpleNamespace(id="src-deck", question_count=50)
    fake_question = SimpleNamespace(answers_json=["B"], answer_text="B")
    fake_crud = Mock()
    fake_crud.get_subject_by_slug.return_value = fake_subject
    fake_crud.get_source_by_id.return_value = fake_source
    fake_crud.get_question_by_ordinal.return_value = fake_question
    monkeypatch.setattr(question_source_service, "crud_question_source", fake_crud)

    correct = check_deck_answer(
        Mock(),
        slug="pmg201c",
        deck_id="src-deck",
        question_id=3,
        selected_answer="b",
    )
    assert correct["isCorrect"] is True
    assert correct["correctAnswers"] == ["B"]


def test_reset_deck_progress_resets_state_but_keeps_learned_count(monkeypatch) -> None:
    fake_subject = SimpleNamespace(id="subject-1", slug="pmg201c")
    fake_source = SimpleNamespace(id="src-deck", question_count=50)
    fake_crud = Mock()
    fake_crud.get_subject_by_slug.return_value = fake_subject
    fake_crud.get_source_by_id.return_value = fake_source
    fake_crud.list_user_stats_by_source_ids.return_value = {
        "src-deck": {"completed_attempts": 3, "current_question_ordinal": 17, "attempted_question_ordinals": [1, 2, 3]}
    }
    monkeypatch.setattr(question_source_service, "crud_question_source", fake_crud)

    result = reset_deck_progress(
        Mock(),
        slug="pmg201c",
        deck_id="src-deck",
        user_id="user-1",
    )

    assert result["currentQuestion"] == 0
    assert result["attemptedQuestionOrdinals"] == []
    assert result["stats"]["inProgress"] == 0
    assert result["stats"]["completionRatePercent"] == 0
    assert result["stats"]["learnedCount"] == 3
    fake_crud.upsert_source_user_stats.assert_called_once()


MLN111_GOLD_SNIPPET = """1. Chọn phương án trả lời phù hợp nhất: "Sự ra đời của Triết học Mác là một quá trình ..........". Từ còn thiếu trong chỗ trống là gì?

A. Tất yếu khách quan

B. Thiết yếu

C. "nhiều hơn và đồ sộ hơn" ... "thế hệ trước"

D. Đấu tranh của giai cấp. Tư còn thiếu

Đáp án: A

2. Ai được xem là nhà triết học thiên tài vào thế kỷ XVIII - XIX?

A. Heraclitus

B. Immanuel Kant

C. Socrates

D. Bruno Fesnades

Đáp án: B

3. Thuyết có thể biết còn gọi là gì?

A. Thuyết nhận biết

B. Thuyết khả tri

C. Thuyết bất khả tri

D. Thuyết nhận biết luận

Đáp án: B
"""


def test_parse_questions_mln111_gold_numbered_format() -> None:
    """Gold snippet from `source/mln111/MLN111 - FA 2024 - RE (done).md` — stems, options, answers."""
    questions, warnings = parse_questions(MLN111_GOLD_SNIPPET)
    assert len(questions) == 3
    assert "Triết học Mác" in questions[0]["stem"]
    assert questions[0]["answer_text"] == "A"
    assert len(questions[0]["options"]) == 4
    assert questions[0]["options"][0]["label"] == "A"
    assert questions[1]["stem"].startswith("Ai được xem là nhà triết học")
    assert any("Immanuel Kant" in o["text"] for o in questions[1]["options"])
    assert questions[1]["answer_text"] == "B"
    assert "Thuyết có thể biết" in questions[2]["stem"]
    assert questions[2]["answer_text"] == "B"
    assert all("normalized_hash" in q for q in questions)
    assert warnings == []


def test_merge_deck_into_aggregated_bank_preview_dedupes(monkeypatch) -> None:
    subject = SimpleNamespace(id="sub-1", slug="mln111")
    bank = SimpleNamespace(id="bank-1", file_name="cau-hoi-tong-hop.md")
    deck = SimpleNamespace(id="deck-1", file_name="MLN111 - FA 2024 - FE.md")
    h_shared = "sha256:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
    h_new = "sha256:bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb"
    bank_q = [
        {
            "stem": "Existing",
            "options": [{"label": "A", "text": "x"}],
            "answer": "A",
            "answers": ["A"],
            "normalized_hash": h_shared,
        },
    ]
    deck_q = [
        {
            "stem": "Dup",
            "options": [{"label": "A", "text": "y"}],
            "answer": "A",
            "answers": ["A"],
            "normalized_hash": h_shared,
        },
        {
            "stem": "New Q",
            "options": [{"label": "B", "text": "z"}],
            "answer": "B",
            "answers": ["B"],
            "normalized_hash": h_new,
        },
    ]
    fake_crud = Mock()
    fake_crud.get_subject_by_slug.return_value = subject
    fake_crud.get_source_by_id.return_value = deck
    fake_crud.list_sources_by_subject.return_value = [bank, deck]

    def payload_side_effect(_db, sid: str):
        if sid == "bank-1":
            return bank_q
        if sid == "deck-1":
            return deck_q
        return []

    fake_crud.list_source_questions_payload.side_effect = payload_side_effect
    monkeypatch.setattr(question_source_service, "crud_question_source", fake_crud)

    out = merge_deck_into_aggregated_bank_preview(Mock(), slug="mln111", deck_source_id="deck-1")
    assert out["added"] == 1
    assert out["skippedDuplicate"] == 1
    assert out["bankQuestionCountAfter"] == 2
    assert out["wouldCreateBank"] is False


def test_merge_deck_into_aggregated_bank_creates_bank_when_absent(monkeypatch) -> None:
    subject = SimpleNamespace(id="sub-1", slug="mln111")
    deck = SimpleNamespace(id="deck-1", file_name="MLN111 - FA 2024 - FE.md")
    new_bank = SimpleNamespace(id="bank-new", file_name="cau-hoi-tong-hop.md", question_count=0)
    deck_q = [
        {
            "stem": "Only deck",
            "options": [{"label": "A", "text": "a"}],
            "answer": "A",
            "answers": ["A"],
            "normalized_hash": "sha256:cccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccc",
        },
    ]
    fake_crud = Mock()
    fake_crud.get_subject_by_slug.return_value = subject
    fake_crud.get_source_by_id.return_value = deck
    fake_crud.list_sources_by_subject.return_value = [deck]
    fake_crud.create_source.return_value = new_bank

    def payload_side_effect(_db, sid: str):
        if sid == "bank-new":
            return []
        if sid == "deck-1":
            return deck_q
        return []

    fake_crud.list_source_questions_payload.side_effect = payload_side_effect
    monkeypatch.setattr(question_source_service, "crud_question_source", fake_crud)
    monkeypatch.setattr(question_source_service, "_schedule_after_commit", lambda _db, _cb: None)

    out = merge_deck_into_aggregated_bank(Mock(), slug="mln111", deck_source_id="deck-1", uploader_id="admin-1")
    assert out["bankSourceId"] == "bank-new"
    assert out["added"] == 1
    assert out["skippedDuplicate"] == 0
    assert out["bankQuestionCount"] == 1
    fake_crud.create_source.assert_called_once()
    assert fake_crud.replace_source_questions.call_count == 2
    last_kw = fake_crud.replace_source_questions.call_args_list[-1].kwargs
    assert last_kw["source_id"] == "bank-new"
    assert len(last_kw["payload"]) == 1
    assert last_kw["payload"][0]["ordinal"] == 1


def test_patch_source_question_updates_matching_bank_rows(monkeypatch) -> None:
    subject = SimpleNamespace(id="sub-1", slug="mln111")
    deck = SimpleNamespace(id="deck-1", file_name="MLN111 - FA 2024 - FE.md", exam_code="X")
    bank = SimpleNamespace(id="bank-1", file_name="cau-hoi-tong-hop.md")
    old_h = "sha256:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
    deck_q = SimpleNamespace(
        stem="Old stem",
        options_json=[{"label": "A", "text": "x"}],
        answer_text="A",
        normalized_hash=old_h,
    )
    bank_q = SimpleNamespace(
        stem="Old stem",
        options_json=[{"label": "A", "text": "x"}],
        answer_text="A",
        normalized_hash=old_h,
    )
    fake_crud = Mock()
    fake_crud.get_subject_by_slug.return_value = subject
    fake_crud.get_source_by_id.return_value = deck
    fake_crud.get_question_by_ordinal.return_value = deck_q
    fake_crud.list_questions_by_normalized_hash.return_value = [bank_q]
    monkeypatch.setattr(question_source_service, "crud_question_source", fake_crud)
    monkeypatch.setattr(question_source_service, "_get_aggregated_bank_source", lambda _db, _sid: bank)
    merge_calls: list[tuple] = []

    def fake_merge(db, *, slug, deck_source_id, uploader_id):
        merge_calls.append((slug, deck_source_id, uploader_id))

    monkeypatch.setattr(question_source_service, "merge_deck_into_aggregated_bank", fake_merge)
    monkeypatch.setattr(question_source_service, "_schedule_after_commit", lambda _db, _cb: None)

    patch_source_question(
        Mock(),
        slug="mln111",
        source_id="deck-1",
        ordinal=1,
        stem="New stem for bank sync",
        options=None,
        answer=None,
    )

    assert merge_calls == [("mln111", "deck-1", None)]
    assert fake_crud.update_question_content.call_count == 2
    first = fake_crud.update_question_content.call_args_list[0].kwargs
    second = fake_crud.update_question_content.call_args_list[1].kwargs
    assert first["question"] is deck_q
    assert second["question"] is bank_q
    assert first["stem"] == second["stem"] == "New stem for bank sync"
    fake_crud.list_questions_by_normalized_hash.assert_called_once_with(
        ANY, source_id="bank-1", normalized_hash=old_h
    )


def test_patch_source_question_skips_bank_when_editing_aggregated_file(monkeypatch) -> None:
    subject = SimpleNamespace(id="sub-1", slug="mln111")
    bank_source = SimpleNamespace(
        id="bank-1",
        file_name="cau-hoi-tong-hop.md",
        exam_code="AGG-BANK",
    )
    q = SimpleNamespace(
        stem="Stem",
        options_json=[{"label": "A", "text": "x"}],
        answer_text="A",
        normalized_hash="sha256:aa",
    )
    fake_crud = Mock()
    fake_crud.get_subject_by_slug.return_value = subject
    fake_crud.get_source_by_id.return_value = bank_source
    fake_crud.get_question_by_ordinal.return_value = q
    monkeypatch.setattr(question_source_service, "crud_question_source", fake_crud)
    monkeypatch.setattr(question_source_service, "_schedule_after_commit", lambda _db, _cb: None)

    patch_source_question(Mock(), slug="mln111", source_id="bank-1", ordinal=1, stem="Edited", options=None, answer=None)

    assert fake_crud.update_question_content.call_count == 1
    fake_crud.list_questions_by_normalized_hash.assert_not_called()


def test_update_source_questions_remerges_bank_when_present(monkeypatch) -> None:
    subject = SimpleNamespace(id="sub-1", slug="mln111")
    deck = SimpleNamespace(id="deck-1", file_name="deck.md", exam_code="X")
    merge_calls: list[tuple] = []

    def fake_merge(db, *, slug, deck_source_id, uploader_id):
        merge_calls.append((slug, deck_source_id, uploader_id))

    fake_crud = Mock()
    fake_crud.get_subject_by_slug.return_value = subject
    fake_crud.get_source_by_id.return_value = deck
    monkeypatch.setattr(question_source_service, "crud_question_source", fake_crud)
    monkeypatch.setattr(question_source_service, "_get_aggregated_bank_source", lambda _db, _sid: SimpleNamespace(id="bank-1"))
    monkeypatch.setattr(question_source_service, "merge_deck_into_aggregated_bank", fake_merge)
    monkeypatch.setattr(question_source_service, "_schedule_after_commit", lambda _db, _cb: None)

    update_source_questions(
        Mock(),
        "mln111",
        "deck-1",
        [{"stem": "Q", "options": [{"label": "A", "text": "a"}], "answer": "A"}],
    )
    assert merge_calls == [("mln111", "deck-1", None)]


def test_update_source_questions_skips_merge_when_no_bank(monkeypatch) -> None:
    subject = SimpleNamespace(id="sub-1", slug="mln111")
    deck = SimpleNamespace(id="deck-1", file_name="deck.md", exam_code="X")
    merge_calls: list[int] = []

    def fake_merge(*_a, **_k):
        merge_calls.append(1)

    fake_crud = Mock()
    fake_crud.get_subject_by_slug.return_value = subject
    fake_crud.get_source_by_id.return_value = deck
    monkeypatch.setattr(question_source_service, "crud_question_source", fake_crud)
    monkeypatch.setattr(question_source_service, "_get_aggregated_bank_source", lambda _db, _sid: None)
    monkeypatch.setattr(question_source_service, "merge_deck_into_aggregated_bank", fake_merge)
    monkeypatch.setattr(question_source_service, "_schedule_after_commit", lambda _db, _cb: None)

    update_source_questions(
        Mock(),
        "mln111",
        "deck-1",
        [{"stem": "Q", "options": [{"label": "A", "text": "a"}], "answer": "A"}],
    )
    assert merge_calls == []


def test_check_bank_duplicate_no_bank(monkeypatch) -> None:
    subject = SimpleNamespace(id="sub-1", slug="mln111")
    fake_crud = Mock()
    fake_crud.get_subject_by_slug.return_value = subject
    monkeypatch.setattr(question_source_service, "crud_question_source", fake_crud)
    monkeypatch.setattr(question_source_service, "_get_aggregated_bank_source", lambda _db, _sid: None)

    out = question_source_service.check_bank_duplicate(
        Mock(),
        slug="mln111",
        stem="Stem text",
        options=[{"label": "A", "text": "opt"}],
        answer="A",
    )
    assert out["existsInBank"] is False
    assert out["normalizedHash"].startswith("sha256:")


def test_check_bank_duplicate_found(monkeypatch) -> None:
    subject = SimpleNamespace(id="sub-1", slug="mln111")
    bank = SimpleNamespace(id="bank-1", file_name="cau-hoi-tong-hop.md")
    fake_crud = Mock()
    fake_crud.get_subject_by_slug.return_value = subject
    fake_crud.list_questions_by_normalized_hash.return_value = [Mock()]
    monkeypatch.setattr(question_source_service, "crud_question_source", fake_crud)
    monkeypatch.setattr(question_source_service, "_get_aggregated_bank_source", lambda _db, _sid: bank)

    out = question_source_service.check_bank_duplicate(
        Mock(),
        slug="mln111",
        stem="Stem text",
        options=[{"label": "A", "text": "opt"}],
        answer="A",
    )
    assert out["existsInBank"] is True


def test_append_question_inserts_and_merges_when_bank_present(monkeypatch) -> None:
    subject = SimpleNamespace(id="sub-1", slug="mln111")
    deck = SimpleNamespace(id="deck-1", file_name="MLN111 - FA 2024 - FE.md", exam_code="E")
    bank = SimpleNamespace(id="bank-1")
    merge_calls: list[int] = []

    def fake_merge(*_a, **_k):
        merge_calls.append(1)

    fake_crud = Mock()
    fake_crud.get_subject_by_slug.return_value = subject
    fake_crud.get_source_by_id.return_value = deck
    fake_crud.get_max_ordinal_for_source.return_value = 5
    fake_crud.list_source_questions_payload.return_value = [{}] * 6
    monkeypatch.setattr(question_source_service, "crud_question_source", fake_crud)
    monkeypatch.setattr(question_source_service, "_get_aggregated_bank_source", lambda _db, _sid: bank)
    monkeypatch.setattr(question_source_service, "merge_deck_into_aggregated_bank", fake_merge)
    monkeypatch.setattr(question_source_service, "_schedule_after_commit", lambda _db, _cb: None)

    out = question_source_service.append_question_to_source(
        Mock(),
        slug="mln111",
        source_id="deck-1",
        stem="Added stem",
        options=[{"label": "A", "text": "x"}],
        answer="A",
    )
    assert out["ordinal"] == 6
    assert out["questionCount"] == 6
    fake_crud.insert_question_row.assert_called_once()
    assert merge_calls == [1]


def test_delete_source_question_replaces_remaining(monkeypatch) -> None:
    subject = SimpleNamespace(id="sub-1", slug="mln111")
    deck = SimpleNamespace(id="deck-1", file_name="deck.md", exam_code="E")
    rows = [
        {
            "ordinal": 1,
            "stem": "First",
            "options": [{"label": "A", "text": "a"}],
            "answer": "A",
            "answers": ["A"],
            "imageUrl": None,
            "normalized_hash": "sha256:aa",
        },
        {
            "ordinal": 2,
            "stem": "Second",
            "options": [{"label": "A", "text": "b"}],
            "answer": "A",
            "answers": ["A"],
            "imageUrl": None,
            "normalized_hash": "sha256:bb",
        },
    ]
    captured: list[list[dict[str, str]]] = []

    def fake_update(db, slug, source_id, questions):
        captured.append(questions)
        return {
            "sourceId": source_id,
            "subjectSlug": slug,
            "examCode": "E",
            "fileName": "deck.md",
            "questionCount": len(questions),
            "warnings": [],
        }

    fake_crud = Mock()
    fake_crud.get_subject_by_slug.return_value = subject
    fake_crud.get_source_by_id.return_value = deck
    fake_crud.list_source_questions_payload.return_value = rows
    monkeypatch.setattr(question_source_service, "crud_question_source", fake_crud)
    monkeypatch.setattr(question_source_service, "update_source_questions", fake_update)
    monkeypatch.setattr(question_source_service, "_get_aggregated_bank_source", lambda _db, _sid: None)
    monkeypatch.setattr(question_source_service, "_schedule_after_commit", lambda _db, _cb: None)

    question_source_service.delete_source_question(Mock(), slug="mln111", source_id="deck-1", ordinal=1)
    assert len(captured) == 1
    assert len(captured[0]) == 1
    assert captured[0][0]["stem"] == "Second"


def test_prune_bank_row_if_hash_orphaned_replaces_bank(monkeypatch) -> None:
    subject = SimpleNamespace(id="sub-1")
    bank = SimpleNamespace(id="bank-1", file_name="cau-hoi-tong-hop.md")
    deck = SimpleNamespace(id="deck-1", file_name="exam.md")
    H = "sha256:deadbeefdeadbeefdeadbeefdeadbeefdeadbeefdeadbeefdeadbeefdeadbeef"
    bank_rows = [
        {
            "ordinal": 1,
            "stem": "keep",
            "options": [],
            "answer": "A",
            "answers": ["A"],
            "imageUrl": None,
            "normalized_hash": "sha256:1111111111111111111111111111111111111111111111111111111111111111",
        },
        {
            "ordinal": 2,
            "stem": "gone",
            "options": [],
            "answer": "A",
            "answers": ["A"],
            "imageUrl": None,
            "normalized_hash": H,
        },
    ]
    fake_crud = Mock()
    fake_crud.list_sources_by_subject.return_value = [deck]

    def lp(_db, sid: str):
        if sid == bank.id:
            return bank_rows
        if sid == deck.id:
            return []
        return []

    fake_crud.list_source_questions_payload.side_effect = lp
    monkeypatch.setattr(question_source_service, "crud_question_source", fake_crud)

    question_source_service._prune_bank_row_if_hash_orphaned(Mock(), subject=subject, bank=bank, normalized_hash=H)
    fake_crud.replace_source_questions.assert_called_once()
    payload = fake_crud.replace_source_questions.call_args.kwargs["payload"]
    assert len(payload) == 1
    assert payload[0]["ordinal"] == 1
    assert payload[0]["normalized_hash"] == "sha256:1111111111111111111111111111111111111111111111111111111111111111"
    fake_crud.update_source_question_stats.assert_called_once()


def test_prune_bank_row_if_hash_orphaned_skips_when_other_deck_has_hash(monkeypatch) -> None:
    subject = SimpleNamespace(id="sub-1")
    bank = SimpleNamespace(id="bank-1", file_name="cau-hoi-tong-hop.md")
    d1 = SimpleNamespace(id="deck-1", file_name="a.md")
    d2 = SimpleNamespace(id="deck-2", file_name="b.md")
    H = "sha256:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
    bank_rows = [
        {
            "ordinal": 1,
            "stem": "bank q",
            "options": [],
            "answer": "A",
            "answers": ["A"],
            "imageUrl": None,
            "normalized_hash": H,
        },
    ]
    fake_crud = Mock()
    fake_crud.list_sources_by_subject.return_value = [d1, d2]

    def lp(_db, sid: str):
        if sid == bank.id:
            return bank_rows
        if sid == d1.id:
            return []
        if sid == d2.id:
            return [
                {
                    "ordinal": 1,
                    "stem": "other",
                    "options": [],
                    "answer": "A",
                    "answers": ["A"],
                    "imageUrl": None,
                    "normalized_hash": H,
                },
            ]
        return []

    fake_crud.list_source_questions_payload.side_effect = lp
    monkeypatch.setattr(question_source_service, "crud_question_source", fake_crud)

    question_source_service._prune_bank_row_if_hash_orphaned(Mock(), subject=subject, bank=bank, normalized_hash=H)
    fake_crud.replace_source_questions.assert_not_called()
