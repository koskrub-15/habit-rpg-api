from typing import List

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from apps.CRUD.base import BaseCRUD
from apps.models.activity_log import ActivityLog
from apps.schemas.activity_log import ActivityLogCreate, ActivityLogUpdate


class CRUDActivityLog(BaseCRUD[ActivityLog, ActivityLogCreate, ActivityLogUpdate]):
    def __init__(self):
        super().__init__(model=ActivityLog)

    async def get_by_user(
        self, db: AsyncSession, user_id: int, skip: int = 0, limit: int = 100
    ) -> List[ActivityLog]:
        """Get activity logs for a specific user with pagination."""
        result = await db.execute(
            select(ActivityLog)
            .where(ActivityLog.user_id == user_id)
            .offset(skip)
            .limit(limit)
            .order_by(ActivityLog.created_at.desc())
        )
        return list(result.scalars().all())


activity_log_crud = CRUDActivityLog()
