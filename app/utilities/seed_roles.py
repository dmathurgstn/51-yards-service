from sqlalchemy import select

from app.db.session import create_session_factory
from app.models.role import Role

ROLES = {
    "USER": "User",
    "OWNER": "Property Owner",
    "AGENT": "Agent",
    "BUILDER": "Builder",
    "ADMIN": "Administrator",
}


def seed_roles() -> None:
    with create_session_factory()() as session:
        existing = set(session.scalars(select(Role.code)).all())
        session.add_all(
            Role(code=code, name=name, is_active=True)
            for code, name in ROLES.items()
            if code not in existing
        )
        session.commit()


if __name__ == "__main__":
    seed_roles()
