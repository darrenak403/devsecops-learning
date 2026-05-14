"""HTTP contract tests for question-source user APIs (no real DB).

Uses httpx.AsyncClient + ASGITransport because Starlette TestClient can break
on newer httpx (sync Client no longer accepts ``app=`` from TestClient).
"""

import asyncio
from unittest.mock import Mock

import httpx
import pytest
from fastapi import HTTPException, status

from app.api.v1.endpoints import question_sources as qs
from app.core import deps
from app.db.session import get_db
from app.main import app


class _FakeUser:
    id = "00000000-0000-0000-0000-000000000001"
    is_active = True

    @property
    def role_name(self) -> str:
        return "user"


class _FakeAdmin:
    id = "00000000-0000-0000-0000-000000000002"
    is_active = True

    @property
    def role_name(self) -> str:
        return "admin"


def _install_overrides() -> None:
    def _mock_get_db():
        yield Mock()

    app.dependency_overrides[deps.require_course_access] = lambda: _FakeUser()
    app.dependency_overrides[get_db] = _mock_get_db


def _clear_overrides() -> None:
    app.dependency_overrides.clear()


async def _request(method: str, path: str, **kwargs):
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as ac:
        return await ac.request(method, path, **kwargs)


def _run(method: str, path: str, **kwargs):
    return asyncio.run(_request(method, path, **kwargs))


@pytest.fixture(autouse=True)
def _overrides_cleanup():
    _install_overrides()
    yield
    _clear_overrides()


def test_get_subjects_empty(monkeypatch):
    monkeypatch.setattr(
        qs,
        "service_list_subjects_page",
        lambda _db, page, limit, q=None: {
            "items": [],
            "page": page,
            "limit": limit,
            "total": 0,
            "totalPages": 0,
            "hasNext": False,
            "hasPrevious": False,
        },
    )
    response = _run("GET", "/api/v1/subjects")
    assert response.status_code == 200
    body = response.json()
    assert body.get("success") is True
    data = body.get("data")
    assert isinstance(data, dict)
    assert data["items"] == []
    assert data["total"] == 0
    assert data["page"] == 1
    assert data["limit"] == 10


def test_get_subjects_nonempty(monkeypatch):
    monkeypatch.setattr(
        qs,
        "service_list_subjects_page",
        lambda _db, page, limit, q=None: {
            "items": [{"slug": "pmg201c", "code": "PMG201C", "hint": "Mon luyen de", "bankQuestionCount": 42}],
            "page": page,
            "limit": limit,
            "total": 1,
            "totalPages": 1,
            "hasNext": False,
            "hasPrevious": False,
        },
    )
    response = _run("GET", "/api/v1/subjects")
    assert response.status_code == 200
    data = response.json().get("data")
    assert isinstance(data, dict)
    assert data["items"][0]["slug"] == "pmg201c"
    assert data["items"][0]["bankQuestionCount"] == 42
    assert data["total"] == 1
    assert data["hasNext"] is False


def test_get_decks_ok(monkeypatch):
    def _decks(_db, slug, user_id=None):
        assert slug == "pmg201c"
        assert user_id == _FakeUser.id
        return [
            {
                "deckId": "d1",
                "examCode": "FA-2024-FE",
                "fileName": "PMG201c - FA 2024 - FE.md",
                "questionCount": 2,
                "stats": {
                    "total": 2,
                    "inProgress": 0,
                    "completed": 0,
                    "learnedCount": 0,
                    "completionRatePercent": 0,
                },
                "uploadedAt": None,
            }
        ]

    monkeypatch.setattr(qs, "get_subject_decks", _decks)
    response = _run("GET", "/api/v1/subjects/pmg201c/decks")
    assert response.status_code == 200
    assert response.json()["data"]["items"][0]["deckId"] == "d1"
    assert response.json()["data"]["total"] == 1


def test_get_bank_empty(monkeypatch):
    monkeypatch.setattr(
        qs,
        "get_subject_bank_page",
        lambda _db, _slug, page, limit: {
            "items": [],
            "page": page,
            "limit": limit,
            "total": 0,
            "totalPages": 0,
            "hasNext": False,
            "hasPrevious": False,
        },
    )
    monkeypatch.setattr(
        qs,
        "get_subject_bank_progress",
        lambda _db, slug, user_id: {"resumeQuestion": 0, "attemptedQuestionOrdinals": []},
    )
    response = _run("GET", "/api/v1/subjects/pmg201c/bank?page=1&limit=10")
    assert response.status_code == 200
    assert response.json()["data"]["items"] == []


def test_get_bank_paginated(monkeypatch):
    monkeypatch.setattr(
        qs,
        "get_subject_bank_page",
        lambda _db, _slug, page, limit: {
            "items": [{"id": 1, "stem": "A", "options": [], "answer": "A"}],
            "page": page,
            "limit": limit,
            "total": 2,
            "totalPages": 2,
            "hasNext": True,
            "hasPrevious": False,
        },
    )
    monkeypatch.setattr(
        qs,
        "get_subject_bank_progress",
        lambda _db, slug, user_id: {
            "totalQuestions": 2,
            "lastQuestion": 2,
            "resumeQuestion": 2,
            "attemptedQuestionOrdinals": [1],
            "completionRatePercent": 50,
            "updatedAt": "2026-04-21T02:00:00+00:00",
        },
    )
    response = _run("GET", "/api/v1/subjects/pmg201c/bank?page=1&limit=1")
    assert response.status_code == 200
    data = response.json()["data"]
    assert isinstance(data, dict)
    assert len(data["items"]) == 1
    assert data["items"][0]["stem"] == "A"
    assert data["total"] == 2
    assert data["hasNext"] is True
    assert data["progress"]["resumeQuestion"] == 2


def test_get_deck_questions_ok(monkeypatch):
    monkeypatch.setattr(
        qs,
        "get_deck_questions_page",
        lambda _db, slug, deck_id, page, limit: {
            "items": [
                {
                    "id": 1,
                    "stem": "Q1",
                    "options": [{"label": "A", "text": "Yes"}],
                    "answer": "A",
                    "answerCount": 1,
                    "imageUrl": None,
                }
            ],
            "page": page,
            "limit": limit,
            "total": 1,
            "totalPages": 1,
            "hasNext": False,
            "hasPrevious": False,
        },
    )
    response = _run("GET", "/api/v1/subjects/pmg201c/decks/d1/questions?page=1&limit=1")
    assert response.status_code == 200
    assert response.json()["data"]["items"][0]["stem"] == "Q1"
    assert response.json()["data"]["items"][0]["answerCount"] == 1
    assert response.json()["data"]["items"][0]["imageUrl"] is None


def test_get_deck_questions_paginated_page1_limit1(monkeypatch):
    monkeypatch.setattr(
        qs,
        "get_deck_questions_page",
        lambda _db, slug, deck_id, page, limit: {
            "items": [
                {
                    "id": 1,
                    "stem": "Q1",
                    "options": [{"label": "A", "text": "Yes"}],
                    "answer": "A",
                    "answerCount": 1,
                    "imageUrl": None,
                }
            ],
            "page": 1,
            "limit": 1,
            "total": 3,
            "totalPages": 3,
            "hasNext": True,
            "hasPrevious": False,
        },
    )
    response = _run("GET", "/api/v1/subjects/pmg201c/decks/d1/questions?page=1&limit=1")
    assert response.status_code == 200
    body = response.json()
    assert isinstance(body["data"], dict)
    assert body["data"]["page"] == 1
    assert body["data"]["limit"] == 1
    assert body["data"]["total"] == 3
    assert body["data"]["totalPages"] == 3
    assert body["data"]["hasNext"] is True
    assert body["data"]["hasPrevious"] is False
    assert len(body["data"]["items"]) == 1
    assert body["data"]["items"][0]["id"] == 1
    assert body["data"]["items"][0]["stem"] == "Q1"
    assert body["data"]["items"][0]["answerCount"] == 1


def test_get_deck_questions_paginated_page_default_limit(monkeypatch):
    """When `limit` is omitted, endpoint default is 1."""

    def _page(_db, slug, deck_id, *, page, limit):
        assert page == 2
        assert limit == 1
        return {
            "items": [{"id": 2, "stem": "Q2", "options": [], "answer": "B", "answerCount": 1, "imageUrl": None}],
            "page": 2,
            "limit": 1,
            "total": 2,
            "totalPages": 2,
            "hasNext": False,
            "hasPrevious": True,
        }

    monkeypatch.setattr(qs, "get_deck_questions_page", _page)
    response = _run("GET", "/api/v1/subjects/pmg201c/decks/d1/questions?page=2")
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["items"][0]["id"] == 2
    assert data["hasNext"] is False
    assert data["hasPrevious"] is True


def test_get_deck_questions_paginated_beyond_last_page(monkeypatch):
    monkeypatch.setattr(
        qs,
        "get_deck_questions_page",
        lambda _db, slug, deck_id, page, limit: {
            "items": [],
            "page": 99,
            "limit": 1,
            "total": 2,
            "totalPages": 2,
            "hasNext": False,
            "hasPrevious": True,
        },
    )
    response = _run("GET", "/api/v1/subjects/pmg201c/decks/d1/questions?page=99&limit=1")
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["items"] == []
    assert data["hasNext"] is False


def test_get_source_state_ok(monkeypatch):
    monkeypatch.setattr(
        qs,
        "get_source_state",
        lambda _db, slug: {
            "bankQuestions": [],
            "deckQuestions": [],
            "files": [],
            "hocTheoDeLayout": "markdownFiles",
        },
    )
    response = _run("GET", "/api/v1/subjects/pmg201c/source-state")
    assert response.status_code == 200
    assert response.json()["data"]["hocTheoDeLayout"] == "markdownFiles"


def test_subject_not_found_decks(monkeypatch):
    def _boom(_db, slug, user_id=None):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": {"code": "SUBJECT_NOT_FOUND", "message": "Subject not found.", "details": {}}},
        )

    monkeypatch.setattr(qs, "get_subject_decks", _boom)
    response = _run("GET", "/api/v1/subjects/nope/decks")
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "SUBJECT_NOT_FOUND"


def test_check_answer_ok(monkeypatch):
    def _check(_db, **kwargs):
        qid = kwargs["question_id"]
        sel = kwargs["selected_answer"]
        return {
            "questionId": qid,
            "selectedAnswer": sel,
            "correctAnswers": ["A"],
            "isCorrect": True,
        }

    monkeypatch.setattr(qs, "check_deck_answer", _check)
    response = _run(
        "POST",
        "/api/v1/subjects/pmg201c/decks/d1/questions/1/check",
        json={"selectedAnswer": "A"},
    )
    assert response.status_code == 200
    assert response.json()["data"]["isCorrect"] is True


def test_put_deck_progress_ok(monkeypatch):
    def _update(_db, **kwargs):
        assert kwargs["attempted_question_ordinals"] == [1, 2, 2, 3]
        return {"ok": True}

    monkeypatch.setattr(qs, "update_deck_progress", _update)
    response = _run(
        "PUT",
        "/api/v1/subjects/pmg201c/decks/d1/progress",
        json={"currentQuestion": 3, "attemptedQuestionOrdinals": [1, 2, 2, 3]},
    )
    assert response.status_code == 200


def test_get_deck_progress_ok(monkeypatch):
    monkeypatch.setattr(
        qs,
        "get_deck_progress",
        lambda _db, **kwargs: {
            "currentQuestion": 12,
            "attemptedQuestionOrdinals": [1, 2, 3],
            "updatedAt": "2026-04-20T03:10:00+00:00",
        },
    )
    response = _run("GET", "/api/v1/subjects/pmg201c/decks/d1/progress")
    assert response.status_code == 200
    assert response.json()["data"]["attemptedQuestionOrdinals"] == [1, 2, 3]


def test_post_deck_progress_reset_ok(monkeypatch):
    monkeypatch.setattr(
        qs,
        "reset_deck_progress",
        lambda _db, **kwargs: {
            "deckId": "d1",
            "subjectSlug": "pmg201c",
            "currentQuestion": 0,
            "attemptedQuestionOrdinals": [],
            "stats": {
                "total": 60,
                "inProgress": 0,
                "completed": 0,
                "learnedCount": 2,
                "completionRatePercent": 0,
            },
        },
    )
    response = _run("POST", "/api/v1/subjects/pmg201c/decks/d1/progress/reset")
    assert response.status_code == 200
    assert response.json()["data"]["currentQuestion"] == 0
    assert response.json()["data"]["stats"]["learnedCount"] == 2


def test_put_deck_stats_ok(monkeypatch):
    monkeypatch.setattr(qs, "update_deck_stats", lambda _db, **kwargs: {"ok": True})
    response = _run(
        "PUT",
        "/api/v1/subjects/pmg201c/decks/d1/stats",
        json={"inProgress": 1, "completed": 0},
    )
    assert response.status_code == 200


def _with_admin():
    app.dependency_overrides[deps.get_current_admin] = lambda: _FakeAdmin()


def _clear_admin():
    app.dependency_overrides.pop(deps.get_current_admin, None)


def test_admin_get_source_questions_ok(monkeypatch):
    _with_admin()
    try:

        def _page(_db, slug, source_id, page, limit, q=None):
            assert slug == "mln111"
            assert source_id == "s1"
            return {
                "items": [
                    {
                        "id": 1,
                        "stem": "Q1",
                        "options": [{"label": "A", "text": "a"}],
                        "answer": "A",
                        "answerCount": 1,
                        "imageUrl": None,
                    }
                ],
                "page": page,
                "limit": limit,
                "total": 1,
                "totalPages": 1,
                "hasNext": False,
                "hasPrevious": False,
            }

        async def _page_async(_db, slug, source_id, *, page, limit, q=None):
            return _page(_db, slug, source_id, page, limit, q=q)

        monkeypatch.setattr(qs, "get_deck_questions_page", _page)
        monkeypatch.setattr(qs, "get_deck_questions_page_async", _page_async)
        response = _run("GET", "/api/v1/admin/question-sources/subjects/mln111/sources/s1/questions")
        assert response.status_code == 200
        data = response.json()["data"]
        assert data["items"][0]["stem"] == "Q1"
        assert data["total"] == 1
    finally:
        _clear_admin()


def test_admin_put_source_questions_ok(monkeypatch):
    _with_admin()
    try:
        called: dict = {}

        def _put(_db, slug, source_id, questions):
            called["slug"] = slug
            called["source_id"] = source_id
            called["n"] = len(questions)
            return {
                "sourceId": source_id,
                "subjectSlug": slug,
                "examCode": "E1",
                "fileName": "f.md",
                "questionCount": len(questions),
                "warnings": [],
            }

        monkeypatch.setattr(qs, "update_source_questions", _put)
        response = _run(
            "PUT",
            "/api/v1/admin/question-sources/subjects/mln111/sources/s1/questions",
            json={
                "questions": [
                    {
                        "stem": "Hi",
                        "options": [{"label": "A", "text": "a"}],
                        "answer": "A",
                    }
                ]
            },
        )
        assert response.status_code == 200
        assert called["slug"] == "mln111"
        assert called["source_id"] == "s1"
        assert called["n"] == 1
        assert response.json()["data"]["questionCount"] == 1
    finally:
        _clear_admin()


def test_admin_patch_source_question_ok(monkeypatch):
    _with_admin()
    try:

        def _patch(_db, **kwargs):
            assert kwargs["slug"] == "mln111"
            assert kwargs["source_id"] == "s1"
            assert kwargs["ordinal"] == 3
            assert kwargs["stem"] == "New stem"
            assert kwargs["options"] is None
            assert kwargs["answer"] is None
            return {
                "sourceId": "s1",
                "subjectSlug": "mln111",
                "examCode": "E1",
                "fileName": "f.md",
                "ordinal": 3,
            }

        monkeypatch.setattr(qs, "patch_source_question", _patch)
        response = _run(
            "PATCH",
            "/api/v1/admin/question-sources/subjects/mln111/sources/s1/questions/3",
            json={"stem": "New stem"},
        )
        assert response.status_code == 200
        assert response.json()["data"]["ordinal"] == 3
    finally:
        _clear_admin()
