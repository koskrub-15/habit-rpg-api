from sqlalchemy import Column, DateTime, String

from apps.db.base import MinimalBase


class RevokedToken(MinimalBase):
    __tablename__ = "revoked_tokens"

    jti = Column(String(36), nullable=False, unique=True, index=True)
    expires_at = Column(DateTime(timezone=True), nullable=False)

    def __repr__(self) -> str:
        return f"<RevokedToken(jti={self.jti}, expires_at={self.expires_at})>"
