from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.role import Role


class CRUDRole:
    def get_by_name(self, db: Session, name: str) -> Role | None:
        stmt = select(Role).where(Role.name == name)
        return db.execute(stmt).scalar_one_or_none()

    def ensure_seed_roles(self, db: Session) -> None:
        for role_name in ("admin", "user"):
            if self.get_by_name(db, role_name) is None:
                db.add(Role(name=role_name))
        db.flush()


crud_role = CRUDRole()
