from apps.CRUD.from_models.habit import habit_crud
from apps.schemas.habit import (
    HabitCreate,
    HabitUpdate,
    HabitResponse,
    HabitResponseShort,
)
from apps.api.router_generator import RouterFactory

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
