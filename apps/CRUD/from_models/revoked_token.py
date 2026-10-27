from datetime import datetime

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from apps.CRUD.base import BaseCRUD
from apps.models.revoked_token import RevokedToken
from apps.schemas.revoked_token import RevokedTokenCreate, RevokedTokenUpdate


class CRUDRevokedToken(BaseCRUD[RevokedToken, RevokedTokenCreate, RevokedTokenUpdate]):
    async def is_revoked(self, db: AsyncSession, *, jti: str) -> bool:
        result = await db.execute(select(self.model).where(self.model.jti == jti))
        return result.scalar_one_or_none() is not None

    async def revoke(self, db: AsyncSession, *, jti: str, expires_at: datetime) -> bool:
        """Revoke a token by its jti.

        Relies on the unique index on ``jti`` so that concurrent callers cannot
        both succeed. Returns False if the token was already revoked.
        """
        db.add(self.model(jti=jti, expires_at=expires_at))
        try:
            await db.commit()
        except IntegrityError:
            await db.rollback()
            return False
        return True


revoked_token_crud = CRUDRevokedToken(RevokedToken)
