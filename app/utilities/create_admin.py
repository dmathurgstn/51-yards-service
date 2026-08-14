import os
import sys

from app.core.security import hash_password
from app.db.session import create_session_factory
from app.models.user import User
from app.repositories.user_repository import RoleRepository, UserRepository


def create_admin() -> None:
    email = os.environ.get("YARDS_ADMIN_EMAIL", "").strip().lower()
    password = os.environ.get("YARDS_ADMIN_PASSWORD", "")
    full_name = os.environ.get("YARDS_ADMIN_FULL_NAME", "Local Administrator").strip()
    if not email or len(password) < 8:
        sys.exit("Set YARDS_ADMIN_EMAIL and YARDS_ADMIN_PASSWORD (minimum 8 characters).")
    with create_session_factory()() as session:
        users, roles = UserRepository(session), RoleRepository(session)
        if users.by_email(email):
            sys.exit("A user with that email already exists.")
        admin = roles.by_code("ADMIN")
        if admin is None or not admin.is_active:
            sys.exit("Seed the active ADMIN role first.")
        users.add(
            User(
                full_name=full_name,
                email=email,
                password_hash=hash_password(password),
                roles=[admin],
            )
        )
        session.commit()


if __name__ == "__main__":
    create_admin()
