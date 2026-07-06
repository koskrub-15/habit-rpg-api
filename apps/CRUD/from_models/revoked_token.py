from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from apps.CRUD.base import BaseCRUD
from apps.models.revoked_token import RevokedToken
from apps.schemas.revoked_token import RevokedTokenCreate, RevokedTokenUpdate


class CRUDRevokedToken(BaseCRUD[RevokedToken, RevokedTokenCreate, RevokedTokenUpdate]):
    async def is_revoked(self, db: AsyncSession, *, jti: str) -> bool:
        result = await db.execute(select(self.model).where(self.model.jti == jti))
        return result.scalar_one_or_none() is not None


revoked_token_crud = CRUDRevokedToken(RevokedToken)
