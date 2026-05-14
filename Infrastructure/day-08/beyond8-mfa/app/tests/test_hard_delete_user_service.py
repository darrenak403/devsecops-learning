"""Unit tests for admin hard-delete user (service + CRUD ordering)."""

import importlib
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from fastapi import HTTPException

from app.crud.crud_user import crud_user

# Package ``app.services`` exports ``auth_service`` instance, so plain
# ``import app.services.auth_service`` resolves to that object, not the module.
auth_mod = importlib.import_module("app.services.auth_service")


def test_delete_user_not_found(monkeypatch):
    db = MagicMock()
    monkeypatch.setattr(auth_mod.crud_user, "get_by_id", lambda _db, _uid: None)
    with pytest.raises(HTTPException) as exc:
        auth_mod.auth_service.delete_user(db, user_id="missing", admin_user_id="admin-1")
    assert exc.value.status_code == 404


def test_delete_user_admin_role_blocked(monkeypatch):
    db = MagicMock()
    target = SimpleNamespace(id="u1", role_name="admin")
    monkeypatch.setattr(auth_mod.crud_user, "get_by_id", lambda _db, _uid: target)
    with pytest.raises(HTTPException) as exc:
        auth_mod.auth_service.delete_user(db, user_id="u1", admin_user_id="admin-1")
    assert exc.value.status_code == 400
    assert "admin" in exc.value.detail.lower()


def test_delete_user_self_delete_blocked(monkeypatch):
    db = MagicMock()
    target = SimpleNamespace(id="same-id", role_name="user")
    monkeypatch.setattr(auth_mod.crud_user, "get_by_id", lambda _db, _uid: target)
    with pytest.raises(HTTPException) as exc:
        auth_mod.auth_service.delete_user(db, user_id="same-id", admin_user_id="same-id")
    assert exc.value.status_code == 400


def test_delete_user_happy_path(monkeypatch):
    db = MagicMock()
    target = SimpleNamespace(id="target-id", role_name="user")
    monkeypatch.setattr(auth_mod.crud_user, "get_by_id", lambda _db, _uid: target)
    monkeypatch.setattr(auth_mod.crud_user, "hard_delete", lambda _db, _uid: True)
    auth_mod.auth_service.delete_user(db, user_id="target-id", admin_user_id="admin-1")


def test_hard_delete_crud_ordered_sql(monkeypatch):
    user_obj = SimpleNamespace(id="target-id")
    db = MagicMock()

    monkeypatch.setattr(
        crud_user,
        "get_by_id",
        lambda _db, uid: user_obj if uid == "target-id" else None,
    )

    assert crud_user.hard_delete(db, "target-id") is True

    calls = db.execute.call_args_list
    assert len(calls) >= 2
    assert "otp_verifications" in str(calls[0][0][0]).lower()
    assert "delete" in str(calls[0][0][0]).lower()
    assert "blocked_by_user_id" in str(calls[1][0][0]).lower()
    db.delete.assert_called_once_with(user_obj)
    db.flush.assert_called_once()
