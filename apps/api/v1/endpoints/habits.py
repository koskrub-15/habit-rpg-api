from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.router_generator import RouterFactory
from apps.CRUD.from_models.habit import habit_crud
from apps.CRUD.from_models.user import user_crud
from apps.db.session import get_db
from apps.schemas.habit import (
    HabitCreate,
    HabitResponse,
    HabitResponseShort,
    HabitUpdate,
)

habit_factory = RouterFactory(
    crud=habit_crud,
    create_schema=HabitCreate,
    update_schema=HabitUpdate,
    response_schema=HabitResponse,
    response_short_schema=HabitResponseShort,
    resource_name="habit",
    resource_name_plural="habits",
    tag="Habits",
    prefix="/habits",
)

router = habit_factory.create_router()


@router.post("/{habit_id}/complete")
async def complete_habit(
    habit_id: int,
    db: AsyncSession = Depends(get_db),
):
    """
    Mark a habit as performed.
    """
    # We need to find the user_id for this habit first
    habit = await habit_crud.get(db, habit_id, raise_not_found=True)
    return await user_crud.complete_activity(
        db,
        user_id=habit.user_id,
        activity_type="habit",
        activity_id=habit_id,
        performed=True,
    )
