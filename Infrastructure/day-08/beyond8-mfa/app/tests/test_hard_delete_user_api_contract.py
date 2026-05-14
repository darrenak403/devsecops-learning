"""HTTP contract tests for admin DELETE user (no real DB)."""

import asyncio
from unittest.mock import Mock

import httpx
import pytest
from fastapi import HTTPException, status

from app.api.v1.endpoints import dashboard
from app.core import deps
from app.core.config import settings
from app.db.session import get_db
from app.main import app

ADMIN_ID = "00000000-0000-0000-0000-000000000099"
TARGET_ID = "00000000-0000-0000-0000-000000000001"


class _FakeAdmin:
    id = ADMIN_ID
    is_active = True

    @property
    def role_name(self) -> str:
        return "admin"


def _delete_url() -> str:
    return f"{settings.api_prefix}/users/{TARGET_ID}"


def _install_overrides() -> None:
    def _mock_get_db():
        yield Mock()

    app.dependency_overrides[deps.get_current_admin] = lambda: _FakeAdmin()
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


def test_delete_user_happy_path(monkeypatch):
    class _Auth:
        def delete_user(self, db, *, user_id, admin_user_id):
            assert user_id == TARGET_ID
            assert admin_user_id == ADMIN_ID

    monkeypatch.setattr(dashboard, "auth_service", _Auth())
    response = _run(
        "DELETE",
        _delete_url(),
        headers={"X-Confirm-Delete": "permanent"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body.get("success") is True
    assert body.get("data") is None
    assert "xóa" in (body.get("message") or "").lower()


def test_delete_user_missing_confirm_header():
    response = _run("DELETE", _delete_url())
    assert response.status_code == 400


def test_delete_user_wrong_confirm_header():
    response = _run(
        "DELETE",
        _delete_url(),
        headers={"X-Confirm-Delete": "yes"},
    )
    assert response.status_code == 400


def test_delete_user_not_found(monkeypatch):
    class _Auth:
        def delete_user(self, db, *, user_id, admin_user_id):
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Không tìm thấy người dùng")

    monkeypatch.setattr(dashboard, "auth_service", _Auth())
    response = _run(
        "DELETE",
        _delete_url(),
        headers={"X-Confirm-Delete": "permanent"},
    )
    assert response.status_code == 404


def test_delete_user_admin_role(monkeypatch):
    class _Auth:
        def delete_user(self, db, *, user_id, admin_user_id):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Không thể xóa tài khoản admin",
            )

    monkeypatch.setattr(dashboard, "auth_service", _Auth())
    response = _run(
        "DELETE",
        _delete_url(),
        headers={"X-Confirm-Delete": "permanent"},
    )
    assert response.status_code == 400


def test_delete_user_self_delete(monkeypatch):
    class _Auth:
        def delete_user(self, db, *, user_id, admin_user_id):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Không thể tự xóa chính mình",
            )

    monkeypatch.setattr(dashboard, "auth_service", _Auth())
    response = _run(
        "DELETE",
        _delete_url(),
        headers={"X-Confirm-Delete": "permanent"},
    )
    assert response.status_code == 400


def test_delete_user_unauthenticated():
    app.dependency_overrides.pop(deps.get_current_admin, None)

    def _mock_get_db():
        yield Mock()

    app.dependency_overrides[get_db] = _mock_get_db

    response = _run(
        "DELETE",
        _delete_url(),
        headers={"X-Confirm-Delete": "permanent"},
    )
    assert response.status_code == 401
