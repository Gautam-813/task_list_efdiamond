from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import hash_password
from app.models.user import User


def ensure_default_admin(db: Session) -> None:
    existing_admin = db.query(User).filter(User.username == settings.default_admin_username).first()
    if existing_admin:
        return

    admin = User(
        username=settings.default_admin_username,
        full_name="System Admin",
        password_hash=hash_password(settings.default_admin_password),
        role="admin",
        is_active=True,
    )
    db.add(admin)
    db.commit()

