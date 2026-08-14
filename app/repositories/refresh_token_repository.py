from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.refresh_token import RefreshToken


class RefreshTokenRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def by_jti(self, jti: str) -> RefreshToken | None:
        return self.session.scalar(select(RefreshToken).where(RefreshToken.jti == jti))

    def add(self, token: RefreshToken) -> None:
        self.session.add(token)
