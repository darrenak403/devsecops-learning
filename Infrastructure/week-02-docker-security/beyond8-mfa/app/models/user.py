import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    role_id: Mapped[str] = mapped_column(String(36), ForeignKey("roles.id"), nullable=False, index=True)
    role = relationship("Role", lazy="joined")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    blocked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    blocked_reason: Mapped[str | None] = mapped_column(String(255), nullable=True)
    blocked_by_user_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("users.id"), nullable=True, index=True
    )
    active_session_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    # Course access revocation controls (for beyond8_course_access JWT invalidation).
    course_access_active: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    course_access_version: Mapped[int] = mapped_column(default=0, nullable=False)
    course_access_verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    course_access_period_started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    course_access_period_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    course_access_purchase_count: Mapped[int] = mapped_column(default=0, nullable=False)
    course_access_revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    otp_rotate_count: Mapped[int] = mapped_column(default=0, nullable=False)
    last_generated_otp: Mapped[str | None] = mapped_column(String(32), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    @property
    def role_name(self) -> str:
        return self.role.name if self.role is not None else "user"
