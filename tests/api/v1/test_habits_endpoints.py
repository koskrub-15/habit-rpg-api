import pytest_asyncio
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from apps.models.habit import Habit, HabitType, HabitStatus
from apps.models.user import User
from apps.schemas.habit import HabitCreate, HabitUpdate
from apps.models.task import Size


@pytest_asyncio.fixture
async def create_test_habit_payload(test_user: User):
    """
    Fixture providing data for creating a habit (payload).
    It uses the `test_user` fixture to get a user ID.
    """
    return HabitCreate(
        name="Morning Run",
        description="Run for 30 minutes every morning",
        user_id=test_user.id,
        habit_type=HabitType.POSITIVE,
        habit_size=Size.MEDIUM,
    )


@pytest_asyncio.fixture
async def create_another_test_habit_payload(test_user: User):
    """
    Fixture providing data for creating a second habit.
    Used for tests requiring multiple habits, e.g., pagination or filtering.
    """
    return HabitCreate(
        name="Read Book",
        description="Read for 15 minutes before bed",
        user_id=test_user.id,
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
    auth_client: AsyncClient,
    db_session: AsyncSession,
    test_user: User,
    create_test_habit_payload: HabitCreate,
):
    """
    Tests the POST /api/v1/habits/ endpoint for creating a new habit.

    Checks:
    - Successful response status (HTTP 201 Created).
    - Returned data matches the HabitResponse schema.
    - Habit is correctly created in the database.
    """

    response = await auth_client.post(
        "/api/v1/habits/", json=create_test_habit_payload.model_dump(mode="json")
    )

    assert response.status_code == 201
    response_data = response.json()

    assert "id" in response_data
    assert response_data["name"] == create_test_habit_payload.name
    assert response_data["user_id"] == test_user.id
    assert response_data["habit_type"] == create_test_habit_payload.habit_type.value

    created_habit = await db_session.get(Habit, response_data["id"])
    assert created_habit is not None
    assert created_habit.name == create_test_habit_payload.name
    assert created_habit.user_id == test_user.id


@pytest.mark.asyncio
async def test_get_habits(
    auth_client: AsyncClient,
    db_session: AsyncSession,
    test_user: User,
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
    await auth_client.post(
        "/api/v1/habits/", json=create_test_habit_payload.model_dump(mode="json")
    )
    await auth_client.post(
        "/api/v1/habits/",
        json=create_another_test_habit_payload.model_dump(mode="json"),
    )

    response = await auth_client.get("/api/v1/habits/")

    assert response.status_code == 200
    response_data = response.json()

    assert isinstance(response_data, list)
    assert len(response_data) == 2

    assert "id" in response_data[0]
    assert "name" in response_data[0]
    assert "user_id" in response_data[0]


@pytest.mark.asyncio
async def test_get_habits_pagination(
    auth_client: AsyncClient,
    test_user: User,
):
    """
    Tests pagination for the GET /api/v1/habits/ endpoint.

    Checks:
    - Correct functionality of skip and limit parameters.
    """
    user = test_user
    for i in range(5):
        habit_payload = HabitCreate(
            name=f"Habit {i}",
            description=f"Description {i}",
            user_id=user.id,
            habit_type=HabitType.POSITIVE,
            habit_size=Size.SMALL,
        )
        await auth_client.post(
            "/api/v1/habits/", json=habit_payload.model_dump(mode="json")
        )

    response = await auth_client.get(
        "/api/v1/habits/?skip=1&limit=2&order_by=created_at"
    )
    assert response.status_code == 200
    response_data = response.json()
    assert len(response_data) == 2
    assert response_data[0]["name"] == "Habit 1"
    assert response_data[1]["name"] == "Habit 2"


@pytest.mark.asyncio
async def test_get_habits_filter_by_name(
    auth_client: AsyncClient,
    test_user: User,
    create_test_habit_payload: HabitCreate,
    create_another_test_habit_payload: HabitCreate,
):
    """
    Tests name filtering for the GET /api/v1/habits/ endpoint.

    Checks:
    - Correct functionality of the name parameter for partial matching.
    """
    await auth_client.post(
        "/api/v1/habits/", json=create_test_habit_payload.model_dump(mode="json")
    )
    await auth_client.post(
        "/api/v1/habits/",
        json=create_another_test_habit_payload.model_dump(mode="json"),
    )

    response = await auth_client.get("/api/v1/habits/?name=Morning")
    assert response.status_code == 200
    response_data = response.json()
    assert len(response_data) == 1
    assert response_data[0]["name"] == "Morning Run"


@pytest.mark.asyncio
async def test_get_habit_by_id(
    auth_client: AsyncClient,
    db_session: AsyncSession,
    test_user: User,
    create_test_habit_payload: HabitCreate,
):
    """
    Tests the GET /api/v1/habits/{id} endpoint for retrieving a habit by ID.

    Checks:
    - Successful response status (HTTP 200 OK).
    - Returned data matches the HabitResponse schema.
    - HTTP 404 Not Found error is returned if the habit is not found.
    """
    create_response = await auth_client.post(
        "/api/v1/habits/", json=create_test_habit_payload.model_dump(mode="json")
    )
    habit_id = create_response.json()["id"]

    response = await auth_client.get(f"/api/v1/habits/{habit_id}")
    assert response.status_code == 200
    response_data = response.json()

    assert response_data["id"] == habit_id
    assert response_data["name"] == create_test_habit_payload.name
    assert response_data["user_id"] == test_user.id

    response_not_found = await auth_client.get("/api/v1/habits/99999")
    assert response_not_found.status_code == 404
    assert "detail" in response_not_found.json()
    assert "Habit with id 99999 not found" in response_not_found.json()["detail"]


@pytest.mark.asyncio
async def test_update_habit(
    auth_client: AsyncClient,
    db_session: AsyncSession,
    test_user: User,
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
    create_response = await auth_client.post(
        "/api/v1/habits/", json=create_test_habit_payload.model_dump(mode="json")
    )
    habit_id = create_response.json()["id"]

    response = await auth_client.patch(
        f"/api/v1/habits/{habit_id}",
        json=create_update_habit_payload.model_dump(mode="json", exclude_unset=True),
    )
    assert response.status_code == 200
    response_data = response.json()

    assert response_data["id"] == habit_id
    assert response_data["name"] == create_update_habit_payload.name
    assert response_data["status"] == create_update_habit_payload.status.value  # type: ignore[union-attr]

    updated_habit = await db_session.get(Habit, habit_id)
    assert updated_habit.name == create_update_habit_payload.name
    assert updated_habit.status == create_update_habit_payload.status

    response_not_found = await auth_client.patch(
        "/api/v1/habits/99999",
        json=create_update_habit_payload.model_dump(mode="json", exclude_unset=True),
    )
    assert response_not_found.status_code == 404
    assert "detail" in response_not_found.json()


@pytest.mark.asyncio
async def test_delete_habit(
    auth_client: AsyncClient,
    db_session: AsyncSession,
    test_user: User,
    create_test_habit_payload: HabitCreate,
):
    """
    Tests the DELETE /api/v1/habits/{id} endpoint for deleting a habit.

    Checks:
    - Successful response status (HTTP 204 No Content).
    - Habit is deleted from the database.
    - HTTP 404 Not Found error is returned if the habit is not found.
    """
    create_response = await auth_client.post(
        "/api/v1/habits/", json=create_test_habit_payload.model_dump(mode="json")
    )
    habit_id = create_response.json()["id"]

    response = await auth_client.delete(f"/api/v1/habits/{habit_id}")
    assert response.status_code == 204

    deleted_habit = await db_session.get(Habit, habit_id)
    assert deleted_habit is None

    response_not_found = await auth_client.delete("/api/v1/habits/99999")
    assert response_not_found.status_code == 404
    assert "detail" in response_not_found.json()


@pytest.mark.asyncio
async def test_get_habit_count(
    auth_client: AsyncClient,
    db_session: AsyncSession,
    test_user: User,
    create_test_habit_payload: HabitCreate,
):
    """
    Tests the GET /api/v1/habits/count endpoint for retrieving the habit count.

    Checks:
    - Successful response status (HTTP 200 OK).
    - Correct habit count is returned.
    """
    response_initial = await auth_client.get("/api/v1/habits/count")
    assert response_initial.status_code == 200
    assert response_initial.json()["count"] == 0

    await auth_client.post(
        "/api/v1/habits/", json=create_test_habit_payload.model_dump(mode="json")
    )

    response_after_create = await auth_client.get("/api/v1/habits/count")
    assert response_after_create.status_code == 200
    assert response_after_create.json()["count"] == 1


@pytest.mark.asyncio
async def test_check_habit_exists(
    auth_client: AsyncClient,
    db_session: AsyncSession,
    test_user: User,
    create_test_habit_payload: HabitCreate,
):
    """
    Tests the GET /api/v1/habits/{id}/exists endpoint for checking habit existence.

    Checks:
    - Returns {'exists': True} for an existing habit.
    - Returns {'exists': False} for a non-existent habit.
    """
    create_response = await auth_client.post(
        "/api/v1/habits/", json=create_test_habit_payload.model_dump(mode="json")
    )
    habit_id = create_response.json()["id"]

    response_exists = await auth_client.get(f"/api/v1/habits/{habit_id}/exists")
    assert response_exists.status_code == 200
    assert response_exists.json()["exists"] is True

    response_not_exists = await auth_client.get("/api/v1/habits/99999/exists")
    assert response_not_exists.status_code == 200
    assert response_not_exists.json()["exists"] is False


@pytest.mark.asyncio
async def test_bulk_create_habits(
    auth_client: AsyncClient,
    db_session: AsyncSession,
    test_user: User,
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

    user = test_user
    habits_payload = [
        create_test_habit_payload.model_dump(mode="json"),
        create_another_test_habit_payload.model_dump(mode="json"),
    ]

    for payload in habits_payload:
        payload["user_id"] = user.id

    response = await auth_client.post("/api/v1/habits/bulk", json=habits_payload)
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
    response_limit_exceeded = await auth_client.post(
        "/api/v1/habits/bulk", json=large_habits_payload
    )
    assert response_limit_exceeded.status_code == 400
    assert (
        "Cannot create more than 100 habits at once"
        in response_limit_exceeded.json()["detail"]
    )
