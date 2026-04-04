from typing import List

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from apps.CRUD.from_models.activity_log import activity_log_crud
from apps.db.session import get_db
from apps.schemas.activity_log import ActivityLogResponse

router = APIRouter(prefix="/activity-log", tags=["Activity Log"])


@router.get("/", response_model=List[ActivityLogResponse])
async def get_activity_log(
    user_id: int,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
):
    """
    Get the activity history for a specific user.
    Supports pagination via 'skip' and 'limit'.
    """
    return await activity_log_crud.get_by_user(
        db, user_id=user_id, skip=skip, limit=limit
    )
