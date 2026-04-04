import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from apps.models.user import User
from apps.models.task import Task, TaskStatus, TaskType
from apps.models.habit import Habit, HabitStatus, HabitType


@pytest.mark.asyncio
async def test_reset_daily_tasks_also_resets_habits(
    client: AsyncClient, db_session: AsyncSession
):
    """
    Tests that the daily reset endpoint correctly resets both daily tasks and habits.
    """
    user = User(name="Daily User", email="daily@example.com", password="password")
    db_session.add(user)
    await db_session.flush()

    # Create a completed daily task
    task = Task(
        name="Daily Task",
        user_id=user.id,
        task_type=TaskType.DAILY,
        status=TaskStatus.COMPLETED,
    )
    # Create a completed positive habit
    habit = Habit(
        name="Daily Habit",
        user_id=user.id,
        habit_type=HabitType.POSITIVE,
        status=HabitStatus.COMPLETED,
    )

    db_session.add_all([task, habit])
    await db_session.commit()

    # Trigger reset (Assuming an endpoint for this)
    response = await client.post(f"/api/v1/users/{user.id}/reset-daily")
    assert response.status_code == 200

    await db_session.refresh(task)
    await db_session.refresh(habit)

    assert task.status == TaskStatus.TODO
    assert habit.status == HabitStatus.TODO
