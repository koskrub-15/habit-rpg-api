from apps.CRUD.base import BaseCRUD
from apps.models.habit import Habit
from apps.schemas.habit import HabitCreate, HabitUpdate


class CRUDHabit(BaseCRUD[Habit, HabitCreate, HabitUpdate]):
    def __init__(self):
        super().__init__(model=Habit)


habit_crud = CRUDHabit()
