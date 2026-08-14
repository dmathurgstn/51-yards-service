from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.role import Role
from app.models.user import User


class UserRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def by_email(self, email: str) -> User | None:
        return self.session.scalar(select(User).where(User.email == email))

    def by_mobile(self, mobile: str) -> User | None:
        return self.session.scalar(select(User).where(User.mobile_number == mobile))

    def by_public_id(self, public_id: str) -> User | None:
        return self.session.scalar(select(User).where(User.public_id == public_id))

    def add(self, user: User) -> User:
        self.session.add(user)
        self.session.flush()
        return user


class RoleRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def by_code(self, code: str) -> Role | None:
        return self.session.scalar(select(Role).where(Role.code == code))
