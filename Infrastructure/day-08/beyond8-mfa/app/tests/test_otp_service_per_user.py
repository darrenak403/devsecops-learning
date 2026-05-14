from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.models.otp_verification import OTPVerification
from app.models.role import Role
from app.models.user import User
from app.services.otp_service import otp_service


def _create_session() -> Session:
    engine = create_engine("sqlite+pysqlite:///:memory:", future=True)
    Role.__table__.create(engine)
    User.__table__.create(engine)
    OTPVerification.__table__.create(engine)
    local_session = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    return local_session()


def _seed_user(db: Session, email: str) -> User:
    role = db.query(Role).filter(Role.name == "user").first()
    if role is None:
        role = Role(name="user")
        db.add(role)
        db.flush()

    user = User(email=email, role_id=role.id, is_active=True)
    db.add(user)
    db.flush()
    return user


def test_generate_otp_is_scoped_per_user() -> None:
    db = _create_session()
    try:
        user_a = _seed_user(db, "a@example.com")
        user_b = _seed_user(db, "b@example.com")

        otp_a, _, version_a = otp_service.generate_otp(db, target_user_id=user_a.id)
        otp_b, _, version_b = otp_service.generate_otp(db, target_user_id=user_b.id)

        assert otp_a != otp_b
        assert version_a == 0
        assert version_b == 0
    finally:
        db.close()


def test_verify_one_user_does_not_invalidate_another_user() -> None:
    db = _create_session()
    try:
        user_a = _seed_user(db, "a@example.com")
        user_b = _seed_user(db, "b@example.com")

        otp_a, _, _ = otp_service.generate_otp(db, target_user_id=user_a.id)
        otp_b, _, _ = otp_service.generate_otp(db, target_user_id=user_b.id)

        valid_a, _, _ = otp_service.verify_and_rotate(db, user_id=user_a.id, otp_raw=otp_a, enforce_cooldown=False)
        valid_b, _, _ = otp_service.verify_and_rotate(db, user_id=user_b.id, otp_raw=otp_b, enforce_cooldown=False)

        assert valid_a is True
        assert valid_b is True

        reused_a_valid, _, _ = otp_service.verify_and_rotate(db, user_id=user_a.id, otp_raw=otp_a, enforce_cooldown=False)
        assert reused_a_valid is False

        refreshed_a, _, _ = otp_service.generate_otp(db, target_user_id=user_a.id)
        assert refreshed_a != otp_a
    finally:
        db.close()


def test_historical_verifications_do_not_block_current_counter() -> None:
    db = _create_session()
    try:
        user = _seed_user(db, "history@example.com")
        user.otp_rotate_count = 1
        db.add(user)
        db.flush()

        db.add(
            OTPVerification(
                user_id=user.id,
                window_id=111,
                otp_rotate_count=0,
            )
        )
        db.flush()

        otp, _, version = otp_service.generate_otp(db, target_user_id=user.id)
        valid, _, _ = otp_service.verify_and_rotate(db, user_id=user.id, otp_raw=otp, enforce_cooldown=False)

        assert version == 1
        assert valid is True
    finally:
        db.close()
