import pytest_asyncio
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from apps.models.habit import Habit, HabitType, HabitStatus
from apps.models.user import User
from apps.schemas.habit import HabitCreate, HabitUpdate
from apps.schemas.user import UserCreate
from apps.models.task import Size


@pytest_asyncio.fixture
async def create_test_user_for_habits(db_session: AsyncSession):
    """
    Fixture to create a test user for habit-related tests.
    Habits are linked to users, so a user is required for most habit operations.
    """
    user_data = UserCreate(
        name="Habit User",
        email="habit@example.com",
        password="habitpassword",
        description="User for habits",
    )
    user = User(**user_data.model_dump(mode="json"))
    db_session.add(user)
    await db_session.commit()
    return user


@pytest_asyncio.fixture
async def create_test_habit_payload(create_test_user_for_habits: User):
    """
    Fixture providing data for creating a habit (payload).
    It uses the `create_test_user_for_habits` fixture to get a user ID.
    """
    return HabitCreate(
        name="Morning Run",
        description="Run for 30 minutes every morning",
        user_id=create_test_user_for_habits.id,
        habit_type=HabitType.POSITIVE,
        habit_size=Size.MEDIUM,
    )


@pytest_asyncio.fixture
async def create_another_test_habit_payload(create_test_user_for_habits: User):
    """
    Fixture providing data for creating a second habit.
    Used for tests requiring multiple habits, e.g., pagination or filtering.
    """
    return HabitCreate(
        name="Read Book",
        description="Read for 15 minutes before bed",
        user_id=create_test_user_for_habits.id,
        habit_type=HabitType.POSITIVE,
        habit_size=Size.SMALL,
    )


@pytest_asyncio.fixture
async def create_update_habit_payload():
    """
    Fixture providing data for updating a habit.
    """
    return HabitUpdate(name="Evening Walk", status=HabitStatus.COMPLETED)


@pytest.mark.asyncio
async def test_create_habit(
    client: AsyncClient,
    db_session: AsyncSession,
    create_test_user_for_habits: User,
    create_test_habit_payload: HabitCreate,
):
    """
    Tests the POST /api/v1/habits/ endpoint for creating a new habit.

    Checks:
    - Successful response status (HTTP 201 Created).
    - Returned data matches the HabitResponse schema.
    - Habit is correctly created in the database.
    """

    response = await client.post(
        "/api/v1/habits/", json=create_test_habit_payload.model_dump(mode="json")
    )

    assert response.status_code == 201
    response_data = response.json()

    assert "id" in response_data
    assert response_data["name"] == create_test_habit_payload.name
    assert response_data["user_id"] == create_test_user_for_habits.id
    assert response_data["habit_type"] == create_test_habit_payload.habit_type.value

    created_habit = await db_session.get(Habit, response_data["id"])
    assert created_habit is not None
    assert created_habit.name == create_test_habit_payload.name
    assert created_habit.user_id == create_test_user_for_habits.id


@pytest.mark.asyncio
async def test_get_habits(
    client: AsyncClient,
    db_session: AsyncSession,
    create_test_user_for_habits: User,
    create_test_habit_payload: HabitCreate,
    create_another_test_habit_payload: HabitCreate,
):
    """
    Tests the GET /api/v1/habits/ endpoint for retrieving a list of habits.

    Checks:
    - Successful response status (HTTP 200 OK).
    - A list of habits is returned.
    - The number of returned habits matches the expected count.
    - Habit data matches the HabitResponseShort schema.
    """
    await client.post(
        "/api/v1/habits/", json=create_test_habit_payload.model_dump(mode="json")
    )
    await client.post(
        "/api/v1/habits/",
        json=create_another_test_habit_payload.model_dump(mode="json"),
    )

    response = await client.get("/api/v1/habits/")

    assert response.status_code == 200
    response_data = response.json()

    assert isinstance(response_data, list)
    assert len(response_data) == 2

    assert "id" in response_data[0]
    assert "name" in response_data[0]
    assert "user_id" in response_data[0]


@pytest.mark.asyncio
async def test_get_habits_pagination(
    client: AsyncClient,
    create_test_user_for_habits: User,
):
    """
    Tests pagination for the GET /api/v1/habits/ endpoint.

    Checks:
    - Correct functionality of skip and limit parameters.
    """
    user = create_test_user_for_habits
    for i in range(5):
        habit_payload = HabitCreate(
            name=f"Habit {i}",
            description=f"Description {i}",
            user_id=user.id,
            habit_type=HabitType.POSITIVE,
            habit_size=Size.SMALL,
        )
        await client.post("/api/v1/habits/", json=habit_payload.model_dump(mode="json"))

    response = await client.get("/api/v1/habits/?skip=1&limit=2&order_by=created_at")
    assert response.status_code == 200
    response_data = response.json()
    assert len(response_data) == 2
    assert response_data[0]["name"] == "Habit 1"
    assert response_data[1]["name"] == "Habit 2"


@pytest.mark.asyncio
async def test_get_habits_filter_by_name(
    client: AsyncClient,
    create_test_user_for_habits: User,
    create_test_habit_payload: HabitCreate,
    create_another_test_habit_payload: HabitCreate,
):
    """
    Tests name filtering for the GET /api/v1/habits/ endpoint.

    Checks:
    - Correct functionality of the name parameter for partial matching.
    """
    await client.post(
        "/api/v1/habits/", json=create_test_habit_payload.model_dump(mode="json")
    )
    await client.post(
        "/api/v1/habits/",
        json=create_another_test_habit_payload.model_dump(mode="json"),
    )

    response = await client.get("/api/v1/habits/?name=Morning")
    assert response.status_code == 200
    response_data = response.json()
    assert len(response_data) == 1
    assert response_data[0]["name"] == "Morning Run"


@pytest.mark.asyncio
async def test_get_habit_by_id(
    client: AsyncClient,
    db_session: AsyncSession,
    create_test_user_for_habits: User,
    create_test_habit_payload: HabitCreate,
):
    """
    Tests the GET /api/v1/habits/{id} endpoint for retrieving a habit by ID.

    Checks:
    - Successful response status (HTTP 200 OK).
    - Returned data matches the HabitResponse schema.
    - HTTP 404 Not Found error is returned if the habit is not found.
    """
    create_response = await client.post(
        "/api/v1/habits/", json=create_test_habit_payload.model_dump(mode="json")
    )
    habit_id = create_response.json()["id"]

    response = await client.get(f"/api/v1/habits/{habit_id}")
    assert response.status_code == 200
    response_data = response.json()

    assert response_data["id"] == habit_id
    assert response_data["name"] == create_test_habit_payload.name
    assert response_data["user_id"] == create_test_user_for_habits.id

    response_not_found = await client.get("/api/v1/habits/99999")
    assert response_not_found.status_code == 404
    assert "detail" in response_not_found.json()
    assert "Habit with id 99999 not found" in response_not_found.json()["detail"]


@pytest.mark.asyncio
async def test_update_habit(
    client: AsyncClient,
    db_session: AsyncSession,
    create_test_user_for_habits: User,
    create_test_habit_payload: HabitCreate,
    create_update_habit_payload: HabitUpdate,
):
    """
    Tests the PATCH /api/v1/habits/{id} endpoint for updating an existing habit.

    Checks:
    - Successful response status (HTTP 200 OK).
    - Habit is correctly updated in the database.
    - Updated data is returned.
    - HTTP 404 Not Found error is returned if the habit is not found.
    """
    create_response = await client.post(
        "/api/v1/habits/", json=create_test_habit_payload.model_dump(mode="json")
    )
    habit_id = create_response.json()["id"]

    response = await client.patch(
        f"/api/v1/habits/{habit_id}",
        json=create_update_habit_payload.model_dump(mode="json", exclude_unset=True),
    )
    assert response.status_code == 200
    response_data = response.json()

    assert response_data["id"] == habit_id
    assert response_data["name"] == create_update_habit_payload.name
    assert response_data["status"] == create_update_habit_payload.status.value

    updated_habit = await db_session.get(Habit, habit_id)
    assert updated_habit.name == create_update_habit_payload.name
    assert updated_habit.status == create_update_habit_payload.status

    response_not_found = await client.patch(
        "/api/v1/habits/99999",
        json=create_update_habit_payload.model_dump(mode="json", exclude_unset=True),
    )
    assert response_not_found.status_code == 404
    assert "detail" in response_not_found.json()


@pytest.mark.asyncio
async def test_delete_habit(
    client: AsyncClient,
    db_session: AsyncSession,
    create_test_user_for_habits: User,
    create_test_habit_payload: HabitCreate,
):
    """
    Tests the DELETE /api/v1/habits/{id} endpoint for deleting a habit.

    Checks:
    - Successful response status (HTTP 204 No Content).
    - Habit is deleted from the database.
    - HTTP 404 Not Found error is returned if the habit is not found.
    """
    create_response = await client.post(
        "/api/v1/habits/", json=create_test_habit_payload.model_dump(mode="json")
    )
    habit_id = create_response.json()["id"]

    response = await client.delete(f"/api/v1/habits/{habit_id}")
    assert response.status_code == 204

    deleted_habit = await db_session.get(Habit, habit_id)
    assert deleted_habit is None

    response_not_found = await client.delete("/api/v1/habits/99999")
    assert response_not_found.status_code == 404
    assert "detail" in response_not_found.json()


@pytest.mark.asyncio
async def test_get_habit_count(
    client: AsyncClient,
    db_session: AsyncSession,
    create_test_user_for_habits: User,
    create_test_habit_payload: HabitCreate,
):
    """
    Tests the GET /api/v1/habits/count endpoint for retrieving the habit count.

    Checks:
    - Successful response status (HTTP 200 OK).
    - Correct habit count is returned.
    """
    response_initial = await client.get("/api/v1/habits/count")
    assert response_initial.status_code == 200
    assert response_initial.json()["count"] == 0

    await client.post(
        "/api/v1/habits/", json=create_test_habit_payload.model_dump(mode="json")
    )

    response_after_create = await client.get("/api/v1/habits/count")
    assert response_after_create.status_code == 200
    assert response_after_create.json()["count"] == 1


@pytest.mark.asyncio
async def test_check_habit_exists(
    client: AsyncClient,
    db_session: AsyncSession,
    create_test_user_for_habits: User,
    create_test_habit_payload: HabitCreate,
):
    """
    Tests the GET /api/v1/habits/{id}/exists endpoint for checking habit existence.

    Checks:
    - Returns {'exists': True} for an existing habit.
    - Returns {'exists': False} for a non-existent habit.
    """
    create_response = await client.post(
        "/api/v1/habits/", json=create_test_habit_payload.model_dump(mode="json")
    )
    habit_id = create_response.json()["id"]

    response_exists = await client.get(f"/api/v1/habits/{habit_id}/exists")
    assert response_exists.status_code == 200
    assert response_exists.json()["exists"] is True

    response_not_exists = await client.get("/api/v1/habits/99999/exists")
    assert response_not_exists.status_code == 200
    assert response_not_exists.json()["exists"] is False


@pytest.mark.asyncio
async def test_bulk_create_habits(
    client: AsyncClient,
    db_session: AsyncSession,
    create_test_user_for_habits: User,
    create_test_habit_payload: HabitCreate,
    create_another_test_habit_payload: HabitCreate,
):
    """
    Tests the POST /api/v1/habits/bulk endpoint for bulk creating habits.

    Checks:
    - Successful response status (HTTP 201 Created).
    - All habits are correctly created.
    - Limits on the number of habits for bulk creation.
    """

    user = create_test_user_for_habits
    habits_payload = [
        create_test_habit_payload.model_dump(mode="json"),
        create_another_test_habit_payload.model_dump(mode="json"),
    ]

    for payload in habits_payload:
        payload["user_id"] = user.id

    response = await client.post("/api/v1/habits/bulk", json=habits_payload)
    assert response.status_code == 201
    response_data = response.json()
    assert isinstance(response_data, list)
    assert len(response_data) == 2

    for habit_data in response_data:
        created_habit = await db_session.get(Habit, habit_data["id"])
        assert created_habit is not None
        assert created_habit.name == habit_data["name"]

    large_habits_payload = [
        HabitCreate(
            name=f"Bulk Habit {i}",
            description=f"Bulk description {i}",
            user_id=user.id,
            habit_type=HabitType.POSITIVE,
            habit_size=Size.SMALL,
        ).model_dump(mode="json")
        for i in range(101)
    ]
    response_limit_exceeded = await client.post(
        "/api/v1/habits/bulk", json=large_habits_payload
    )
    assert response_limit_exceeded.status_code == 400
    assert (
        "Cannot create more than 100 habits at once"
        in response_limit_exceeded.json()["detail"]
    )
