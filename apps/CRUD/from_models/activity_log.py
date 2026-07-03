from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from apps.CRUD.base import BaseCRUD
from apps.models.activity_log import ActivityLog
from apps.schemas.activity_log import ActivityLogCreate, ActivityLogUpdate


class CRUDActivityLog(BaseCRUD[ActivityLog, ActivityLogCreate, ActivityLogUpdate]):
    async def get_by_user(
        self, db: AsyncSession, *, user_id: int, skip: int = 0, limit: int = 100
    ):
        result = await db.execute(
            select(self.model)
            .where(self.model.user_id == user_id)
            .offset(skip)
            .limit(limit)
            .order_by(self.model.created_at.desc())
        )
        return list(result.scalars().all())


activity_log_crud = CRUDActivityLog(ActivityLog)
