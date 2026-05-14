import asyncio
from datetime import datetime, timezone
from unittest.mock import Mock

import httpx
import pytest

from app.api.v1.endpoints import dashboard
from app.core import deps
from app.core.config import settings
from app.db.session import get_db
from app.main import app
from app.schemas.stats import OTPVerificationHistoryItem

USER_ID = "03d29752-6cdb-49e0-a837-e213046f9eb6"


class _FakeAdmin:
    id = "00000000-0000-0000-0000-000000000099"
    is_active = True

    @property
    def role_name(self) -> str:
        return "admin"


def _detail_url() -> str:
    return f"{settings.api_prefix}/users/{USER_ID}"


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


def test_get_user_by_id_dashboard_accepts_stats_tuple(monkeypatch):
    fake_user = Mock()
    fake_user.id = USER_ID
    fake_user.email = "u@example.com"
    fake_user.role_name = "user"
    fake_user.is_active = True
    fake_user.course_access_active = False
    fake_user.course_access_version = 0
    fake_user.course_access_verified_at = None
    fake_user.course_access_revoked_at = None
    fake_user.blocked_at = None
    fake_user.blocked_reason = None
    fake_user.blocked_by_user_id = None
    fake_user.last_generated_otp = None
    fake_user.created_at = datetime(2026, 1, 1, tzinfo=timezone.utc)

    class _Auth:
        def get_user_by_id(self, db, *, user_id: str):
            assert user_id == USER_ID
            return fake_user

    class _Stats:
        def get_otp_verification_history(self, db, *, user_id: str):
            assert user_id == USER_ID
            return (
                1,
                [
                    OTPVerificationHistoryItem(
                        user_id=USER_ID,
                        email="u@example.com",
                        verification_count=2,
                        last_verified_at=datetime(2026, 1, 2, tzinfo=timezone.utc),
                    )
                ],
            )

    monkeypatch.setattr(dashboard, "auth_service", _Auth())
    monkeypatch.setattr(dashboard, "stats_service", _Stats())

    response = _run("GET", _detail_url())
    assert response.status_code == 200
    body = response.json()
    assert body.get("success") is True
    data = body.get("data")
    assert data["user"]["id"] == USER_ID
    assert data["otp_verification_history"]["verification_count"] == 2
