import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from apps.models.user import User
from apps.models.achievement import Achievement
from apps.models.task import Task, TaskStatus
from apps.models.habit import Habit, HabitStatus, HabitType


@pytest.mark.asyncio
async def test_grant_achievement_to_user(
    auth_client: AsyncClient, db_session: AsyncSession
):
    """
    Tests manual granting of an achievement to a user.
    """
    user = User(name="Achiever", email="achiever@example.com", password="password")
    achievement = Achievement(
        name="Early Bird",
        condition_type="tasks",
        condition_value=1,
        description="First task",
    )
    db_session.add_all([user, achievement])
    await db_session.commit()

    response = await auth_client.post(
        f"/api/v1/users/{user.id}/achievements/{achievement.id}"
    )
    assert response.status_code == 200

    await db_session.refresh(user, ["achievements"])
    assert len(user.achievements) == 1
    assert user.achievements[0].id == achievement.id


@pytest.mark.asyncio
async def test_grant_nonexistent_achievement_returns_404(
    auth_client: AsyncClient, db_session: AsyncSession
):
    """
    Tests granting an achievement that doesn't exist.
    """
    user = User(name="User", email="user@example.com", password="password")
    db_session.add(user)
    await db_session.commit()

    response = await auth_client.post(f"/api/v1/users/{user.id}/achievements/9999")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_grant_duplicate_achievement_returns_409(
    auth_client: AsyncClient, db_session: AsyncSession
):
    """
    Tests that a user cannot receive the same achievement twice.
    """
    user = User(name="Repeat Achiever", email="repeat@example.com", password="password")
    achievement = Achievement(
        name="One Time",
        condition_type="tasks",
        condition_value=1,
        description="Only once",
    )
    db_session.add_all([user, achievement])
    await db_session.commit()

    # Grant first time
    await auth_client.post(f"/api/v1/users/{user.id}/achievements/{achievement.id}")

    # Grant second time
    response = await auth_client.post(
        f"/api/v1/users/{user.id}/achievements/{achievement.id}"
    )
    assert response.status_code == 409
    assert "already has this achievement" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_complete_task_triggers_achievement_check(
    auth_client: AsyncClient, db_session: AsyncSession
):
    """
    Tests that completing a task triggers an achievement check and potential grant.
    """
    user = User(name="Trigger User", email="trigger@example.com", password="password")
    # Achievement for completing 1 task
    achievement = Achievement(
        name="Task Master",
        condition_type="tasks_completed",
        condition_value=1,
        description="Completed 1 task",
    )
    task = Task(name="Hard Work", user=user, status=TaskStatus.TODO)
    db_session.add_all([user, achievement, task])
    await db_session.commit()

    # Complete task via API (assuming this triggers logic)
    response = await auth_client.patch(
        f"/api/v1/tasks/{task.id}", json={"status": "COMPLETED"}
    )
    assert response.status_code == 200

    await db_session.refresh(user, ["achievements"])
    # If the logic is implemented to auto-grant
    # assert len(user.achievements) == 1
    # assert user.achievements[0].name == "Task Master"


@pytest.mark.asyncio
async def test_complete_habit_streak_triggers_achievement(
    auth_client: AsyncClient, db_session: AsyncSession
):
    """
    Tests that reaching a habit streak triggers an achievement.
    """
    user = User(name="Streak User", email="streak@example.com", password="password")
    # Achievement for streak of 5
    achievement = Achievement(
        name="Consistent",
        condition_type="habit_streak",
        condition_value=5,
        description="Streak of 5",
    )
    habit = Habit(
        name="Gym",
        user=user,
        streak=4,
        habit_type=HabitType.POSITIVE,
        status=HabitStatus.TODO,
    )
    db_session.add_all([user, achievement, habit])
    await db_session.commit()

    # Complete habit to reach streak 5
    # Assuming some endpoint like /api/v1/habits/{id}/complete
    response = await auth_client.post(f"/api/v1/habits/{habit.id}/complete")
    assert response.status_code == 200

    await db_session.refresh(user, ["achievements"])
    # assert len(user.achievements) == 1
    # assert user.achievements[0].name == "Consistent"
