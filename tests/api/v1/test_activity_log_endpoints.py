import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from apps.models.user import User
from apps.models.task import Task, TaskStatus
from apps.models.habit import Habit, HabitStatus, HabitType


@pytest.mark.asyncio
async def test_complete_task_creates_log_entry(
    client: AsyncClient, db_session: AsyncSession
):
    """
    Tests that completing a task automatically creates an activity log entry.
    """
    user = User(name="Tasker", email="tasker@example.com", password="password")
    task = Task(name="Log Task", user=user, status=TaskStatus.TODO)
    db_session.add_all([user, task])
    await db_session.commit()

    # Complete task
    await client.patch(f"/api/v1/tasks/{task.id}", json={"status": "COMPLETED"})

    # Check logs
    response = await client.get("/api/v1/activity-log/", params={"user_id": user.id})
    assert response.status_code == 200
    logs = response.json()
    assert len(logs) >= 1
    assert logs[0]["activity_type"] == "TASK_COMPLETED"
    assert logs[0]["task_id"] == task.id


@pytest.mark.asyncio
async def test_complete_habit_creates_log_entry(
    client: AsyncClient, db_session: AsyncSession
):
    """
    Tests that completing a habit automatically creates an activity log entry.
    """
    user = User(name="Habiter", email="habiter@example.com", password="password")
    habit = Habit(
        name="Log Habit",
        user=user,
        habit_type=HabitType.POSITIVE,
        status=HabitStatus.TODO,
    )
    db_session.add_all([user, habit])
    await db_session.commit()

    # Complete habit
    await client.post(f"/api/v1/habits/{habit.id}/complete")

    # Check logs
    response = await client.get("/api/v1/activity-log/", params={"user_id": user.id})
    assert response.status_code == 200
    logs = response.json()
    assert any(
        log["activity_type"] == "HABIT_COMPLETED" and log["habit_id"] == habit.id
        for log in logs
    )


@pytest.mark.asyncio
async def test_get_user_activity_log(client: AsyncClient, db_session: AsyncSession):
    """
    Tests retrieving the activity log for a specific user.
    """
    user = User(name="Logger", email="logger@example.com", password="password")
    db_session.add(user)
    await db_session.commit()

    # Assuming some manual log creation for testing the GET endpoint
    # or just use the completion flow
    response = await client.get("/api/v1/activity-log/", params={"user_id": user.id})
    assert response.status_code == 200
    assert isinstance(response.json(), list)


@pytest.mark.asyncio
async def test_activity_log_pagination(client: AsyncClient, db_session: AsyncSession):
    """
    Tests pagination for the activity log endpoint.
    """
    user = User(name="Paginator", email="paginator@example.com", password="password")
    db_session.add(user)
    await db_session.commit()

    # Create 15 log entries (via completion or direct DB insert if possible)
    # For testing, let's assume we have an endpoint or we've done 15 activities
    for i in range(15):
        # This is a bit slow but ensures triggers work if they are there
        task = Task(name=f"Task {i}", user=user, status=TaskStatus.TODO)
        db_session.add(task)
        await db_session.commit()
        await client.patch(f"/api/v1/tasks/{task.id}", json={"status": "COMPLETED"})

    # Test pagination
    response = await client.get(
        "/api/v1/activity-log/", params={"user_id": user.id, "skip": 5, "limit": 5}
    )
    assert response.status_code == 200
    logs = response.json()
    assert len(logs) == 5
