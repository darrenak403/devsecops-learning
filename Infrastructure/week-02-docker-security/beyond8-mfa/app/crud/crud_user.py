from sqlalchemy import func, select
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, lazyload
from datetime import datetime, timedelta, timezone

from app.core.config import settings
from app.crud.crud_role import crud_role
from app.models.user import User


class CRUDUser:
    def ensure_block_columns(self, db: Session) -> None:
        """
        Backward-compatible guard for production environments where the latest
        migration may not have been executed yet.
        """
        db.execute(text("ALTER TABLE users ADD COLUMN IF NOT EXISTS blocked_at TIMESTAMPTZ"))
        db.execute(text("ALTER TABLE users ADD COLUMN IF NOT EXISTS blocked_reason VARCHAR(255)"))
        db.execute(text("ALTER TABLE users ADD COLUMN IF NOT EXISTS blocked_by_user_id VARCHAR(36)"))

    def ensure_course_access_columns(self, db: Session) -> None:
        """
        Backward-compatible guard for production environments where the latest
        migration may not have been executed yet.
        """
        db.execute(text("ALTER TABLE users ADD COLUMN IF NOT EXISTS course_access_active BOOLEAN NOT NULL DEFAULT FALSE"))
        db.execute(text("ALTER TABLE users ADD COLUMN IF NOT EXISTS course_access_version INTEGER NOT NULL DEFAULT 0"))
        db.execute(text("ALTER TABLE users ADD COLUMN IF NOT EXISTS course_access_verified_at TIMESTAMPTZ"))
        db.execute(text("ALTER TABLE users ADD COLUMN IF NOT EXISTS course_access_period_started_at TIMESTAMPTZ"))
        db.execute(text("ALTER TABLE users ADD COLUMN IF NOT EXISTS course_access_period_expires_at TIMESTAMPTZ"))
        db.execute(text("ALTER TABLE users ADD COLUMN IF NOT EXISTS course_access_purchase_count INTEGER NOT NULL DEFAULT 0"))
        db.execute(text("ALTER TABLE users ADD COLUMN IF NOT EXISTS course_access_revoked_at TIMESTAMPTZ"))
        db.execute(text("CREATE INDEX IF NOT EXISTS ix_users_course_access_revoked_at ON users (course_access_revoked_at)"))

    def ensure_otp_columns(self, db: Session) -> None:
        """Backward-compatible guard for per-user OTP counter rollout."""
        db.execute(text("ALTER TABLE users ADD COLUMN IF NOT EXISTS otp_rotate_count INTEGER NOT NULL DEFAULT 0"))

    def ensure_auth_session_columns(self, db: Session) -> None:
        """Backward-compatible guard for single active browser session rollout."""
        db.execute(text("ALTER TABLE users ADD COLUMN IF NOT EXISTS active_session_id VARCHAR(36)"))
        db.execute(text("CREATE INDEX IF NOT EXISTS ix_users_active_session_id ON users (active_session_id)"))

    @staticmethod
    def _as_utc(dt: datetime | None) -> datetime | None:
        if dt is None:
            return None
        if dt.tzinfo is None:
            return dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)

    def get_by_id(self, db: Session, user_id: str) -> User | None:
        stmt = select(User).where(User.id == user_id)
        return db.execute(stmt).scalar_one_or_none()

    def get_by_email(self, db: Session, email: str) -> User | None:
        stmt = select(User).where(User.email == email.lower())
        return db.execute(stmt).scalar_one_or_none()

    def get_all(
        self,
        db: Session,
        offset: int = 0,
        limit: int = 100,
        search: str | None = None,
    ) -> tuple[list[User], int]:
        stmt = select(User)
        total_stmt = select(func.count(User.id))

        normalized_search = search.strip().lower() if search else ""
        if normalized_search:
            search_filter = func.lower(User.email).contains(normalized_search, autoescape=True)
            stmt = stmt.where(search_filter)
            total_stmt = total_stmt.where(search_filter)

        stmt = stmt.order_by(User.created_at.desc(), User.id.desc()).offset(offset).limit(limit)

        users = list(db.execute(stmt).scalars().all())
        total = int(db.execute(total_stmt).scalar_one() or 0)
        return users, total

    def get_or_create(self, db: Session, email: str, role_name: str) -> User:
        role = crud_role.get_by_name(db, role_name)
        if role is None:
            raise ValueError(f"Role '{role_name}' does not exist")

        user = self.get_by_email(db, email)
        if user is not None:
            if user.role_id != role.id:
                user.role_id = role.id
                db.add(user)
                db.flush()
                db.refresh(user)
            return user

        user = User(email=email.lower(), role_id=role.id)
        try:
            with db.begin_nested():
                db.add(user)
                db.flush()
            db.refresh(user)
            return user
        except IntegrityError:
            existing = self.get_by_email(db, email)
            if existing is None:
                raise
            return existing

    def set_block_status(
        self,
        db: Session,
        user_id: str,
        *,
        is_active: bool,
        blocked_by_user_id: str | None,
        blocked_reason: str | None = None,
    ) -> User | None:
        user = self.get_by_id(db, user_id)
        if user is None:
            return None

        user.is_active = is_active
        if is_active:
            user.blocked_at = None
            user.blocked_reason = None
            user.blocked_by_user_id = None
        else:
            user.blocked_at = datetime.now(timezone.utc)
            user.blocked_reason = (blocked_reason or "").strip() or None
            user.blocked_by_user_id = blocked_by_user_id

        db.add(user)
        db.flush()
        return user

    def revoke_course_access(self, db: Session, user_id: str) -> User | None:
        user = self.get_by_id(db, user_id)
        if user is None:
            return None

        user.course_access_active = False
        user.course_access_version = int(user.course_access_version or 0) + 1
        user.course_access_revoked_at = datetime.now(timezone.utc)
        db.add(user)
        db.flush()
        return user

    def bump_course_access_version(self, db: Session, user_id: str) -> User | None:
        user = db.execute(
            select(User)
            .options(lazyload(User.role))
            .where(User.id == user_id)
            .with_for_update(of=User)
        ).scalar_one_or_none()
        if user is None:
            return None

        now = datetime.now(timezone.utc)
        active_period_expires_at = self._as_utc(user.course_access_period_expires_at)
        should_start_new_purchase_period = active_period_expires_at is None or now >= active_period_expires_at

        if should_start_new_purchase_period:
            user.course_access_purchase_count = int(user.course_access_purchase_count or 0) + 1
            user.course_access_period_started_at = now
            user.course_access_period_expires_at = now + timedelta(days=settings.course_access_token_expire_days)

        user.course_access_active = True
        user.course_access_version = int(user.course_access_version or 0) + 1
        user.course_access_verified_at = now
        user.course_access_revoked_at = None

        db.add(user)
        db.flush()
        return user

    def clear_verified_otp_key(self, db: Session, user_id: str) -> User | None:
        user = self.get_by_id(db, user_id)
        if user is None:
            return None

        user.course_access_active = False
        user.course_access_revoked_at = datetime.now(timezone.utc)
        db.add(user)
        db.flush()
        return user

    def rotate_active_session(self, db: Session, *, user_id: str, session_id: str) -> User | None:
        user = self.get_by_id(db, user_id)
        if user is None:
            return None
        user.active_session_id = session_id
        db.add(user)
        db.flush()
        return user

    def hard_delete(self, db: Session, user_id: str) -> bool:
        user = self.get_by_id(db, user_id)
        if user is None:
            return False

        db.execute(
            text("DELETE FROM otp_verifications WHERE user_id = :uid"),
            {"uid": user_id},
        )
        db.execute(
            text("UPDATE users SET blocked_by_user_id = NULL WHERE blocked_by_user_id = :uid"),
            {"uid": user_id},
        )

        db.delete(user)
        db.flush()
        return True


crud_user = CRUDUser()
