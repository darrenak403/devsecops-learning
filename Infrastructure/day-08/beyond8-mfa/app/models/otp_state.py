"""
OTPState — singleton table (always 1 row, id=1).
Persists rotate_count across server restarts so the active OTP window
changes every time someone verifies, even after a restart.
"""

from datetime import datetime

from sqlalchemy import DateTime, Integer
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class OTPState(Base):
    __tablename__ = "otp_state"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, default=1)
    # Incremented atomically each time an OTP is successfully consumed.
    # This shifts the active HMAC window so the old OTP is immediately invalid.
    rotate_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=datetime.utcnow
    )
