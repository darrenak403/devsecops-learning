from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from app.services.auth_service import AuthService


def _mock_user(
    *,
    user_id: str = "user-1",
    email: str = "user@gmail.com",
    role_name: str = "user",
    is_active: bool = True,
):
    return SimpleNamespace(id=user_id, email=email, role_name=role_name, is_active=is_active)


def test_signup_rejects_invalid_domain() -> None:
    service = AuthService()

    with pytest.raises(HTTPException) as exc:
        service.signup(db=SimpleNamespace(), email="demo@yahoo.com")

    assert exc.value.status_code == 400
    assert exc.value.detail == "Chỉ hỗ trợ email đuôi @gmail.com hoặc @fpt.edu.vn"


def test_signup_rejects_existing_account(monkeypatch) -> None:
    service = AuthService()
    existing_user = _mock_user()
    monkeypatch.setattr("app.services.auth_service.crud_user.get_by_email", lambda *_args, **_kwargs: existing_user)

    with pytest.raises(HTTPException) as exc:
        service.signup(db=SimpleNamespace(), email="user@gmail.com")

    assert exc.value.status_code == 400
    assert exc.value.detail == "Tài khoản đã tồn tại"


def test_signin_rejects_invalid_domain() -> None:
    service = AuthService()

    with pytest.raises(HTTPException) as exc:
        service.signin(db=SimpleNamespace(), email="demo@yahoo.com")

    assert exc.value.status_code == 400
    assert exc.value.detail == "Chỉ hỗ trợ email đuôi @gmail.com hoặc @fpt.edu.vn"


def test_signin_rejects_unregistered_account(monkeypatch) -> None:
    service = AuthService()
    monkeypatch.setattr("app.services.auth_service.crud_user.get_by_email", lambda *_args, **_kwargs: None)

    with pytest.raises(HTTPException) as exc:
        service.signin(db=SimpleNamespace(), email="missing@gmail.com")

    assert exc.value.status_code == 400
    assert exc.value.detail == "Tài khoản chưa đăng ký"


def test_signin_success_for_existing_allowed_account(monkeypatch) -> None:
    service = AuthService()
    existing_user = _mock_user()

    monkeypatch.setattr("app.services.auth_service.crud_user.get_by_email", lambda *_args, **_kwargs: existing_user)
    monkeypatch.setattr(
        "app.services.auth_service.crud_user.rotate_active_session",
        lambda *_args, **_kwargs: existing_user,
    )
    monkeypatch.setattr("app.services.auth_service.create_access_token", lambda **_kwargs: "token-123")

    token, user, session_id = service.signin(db=SimpleNamespace(), email="user@gmail.com")

    assert token == "token-123"
    assert user.id == "user-1"
    assert session_id
