from sqlalchemy.orm import Session

from app.core.config import settings
from app.crud import crud_otp, crud_role, crud_user


def run_startup_bootstrap(db: Session) -> None:
    """Run startup bootstrap tasks while preserving existing behavior."""
    crud_user.ensure_block_columns(db)
    crud_user.ensure_course_access_columns(db)
    crud_user.ensure_otp_columns(db)
    crud_user.ensure_auth_session_columns(db)
    crud_otp.ensure_otp_verification_columns(db)
    crud_role.ensure_seed_roles(db)
    crud_user.get_or_create(db, settings.seed_admin_email.lower(), "admin")
