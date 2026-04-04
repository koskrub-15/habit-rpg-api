import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from apps.models.achievement import Achievement
from apps.schemas.achievement import AchievementCreate, AchievementUpdate


@pytest_asyncio.fixture
async def create_test_achievement_payload():
    """
    Fixture providing data for creating an achievement (payload).
    """
    return AchievementCreate(
        name="First Login",
        description="Achieved upon first login.",
        condition_type="login_count",
        condition_value=1,
    )


@pytest_asyncio.fixture
async def create_another_test_achievement_payload():
    """
    Fixture providing data for creating a second achievement.
    """
    return AchievementCreate(
        name="Complete 10 Tasks",
        description="Achieved after completing 10 tasks.",
        condition_type="tasks_completed",
        condition_value=10,
    )


@pytest_asyncio.fixture
async def create_update_achievement_payload():
    """
    Fixture providing data for updating an achievement.
    """
    return AchievementUpdate(name="First Login Bonus", condition_value=5)


@pytest.mark.asyncio
async def test_create_achievement(
    client: AsyncClient,
    db_session: AsyncSession,
    create_test_achievement_payload: AchievementCreate,
):
    """Tests the POST /api/v1/achievements/ endpoint for creating a new achievement."""
    response = await client.post(
        "/api/v1/achievements/",
        json=create_test_achievement_payload.model_dump(mode="json"),
    )

    assert response.status_code == 201
    response_data = response.json()

    assert "id" in response_data
    assert response_data["name"] == create_test_achievement_payload.name
    assert (
        response_data["condition_type"]
        == create_test_achievement_payload.condition_type
    )
    assert (
        response_data["condition_value"]
        == create_test_achievement_payload.condition_value
    )

    created_achievement = await db_session.get(Achievement, response_data["id"])
    assert created_achievement is not None
    assert created_achievement.name == create_test_achievement_payload.name
    assert (
        created_achievement.condition_type
        == create_test_achievement_payload.condition_type
    )


@pytest.mark.asyncio
async def test_get_achievements(
    client: AsyncClient,
    db_session: AsyncSession,
    create_test_achievement_payload: AchievementCreate,
    create_another_test_achievement_payload: AchievementCreate,
):
    """Tests the GET /api/v1/achievements/ endpoint for retrieving a list of achievements."""
    await client.post(
        "/api/v1/achievements/",
        json=create_test_achievement_payload.model_dump(mode="json"),
    )
    await client.post(
        "/api/v1/achievements/",
        json=create_another_test_achievement_payload.model_dump(mode="json"),
    )

    response = await client.get("/api/v1/achievements/")

    assert response.status_code == 200
    response_data = response.json()

    assert isinstance(response_data, list)
    assert len(response_data) == 2

    assert "id" in response_data[0]
    assert "name" in response_data[0]
    assert "condition_type" in response_data[0]


@pytest.mark.asyncio
async def test_get_achievements_pagination(
    client: AsyncClient,
):
    """Tests pagination for the GET /api/v1/achievements/ endpoint."""
    for i in range(5):
        achievement_payload = AchievementCreate(
            name=f"Achievement {i}",
            description=f"Description {i}",
            condition_type="generic",
            condition_value=i,
        )
        await client.post(
            "/api/v1/achievements/", json=achievement_payload.model_dump(mode="json")
        )

    response = await client.get(
        "/api/v1/achievements/?skip=1&limit=2&order_by=created_at"
    )
    assert response.status_code == 200
    response_data = response.json()
    assert len(response_data) == 2
    assert response_data[0]["name"] == "Achievement 1"
    assert response_data[1]["name"] == "Achievement 2"


@pytest.mark.asyncio
async def test_get_achievements_filter_by_name(
    client: AsyncClient,
    create_test_achievement_payload: AchievementCreate,
    create_another_test_achievement_payload: AchievementCreate,
):
    """Tests name filtering for the GET /api/v1/achievements/ endpoint."""
    await client.post(
        "/api/v1/achievements/",
        json=create_test_achievement_payload.model_dump(mode="json"),
    )
    await client.post(
        "/api/v1/achievements/",
        json=create_another_test_achievement_payload.model_dump(mode="json"),
    )

    response = await client.get("/api/v1/achievements/?name=Login")
    assert response.status_code == 200
    response_data = response.json()
    assert len(response_data) == 1
    assert response_data[0]["name"] == "First Login"


@pytest.mark.asyncio
async def test_get_achievement_by_id(
    client: AsyncClient,
    db_session: AsyncSession,
    create_test_achievement_payload: AchievementCreate,
):
    """Tests the GET /api/v1/achievements/{id} endpoint for retrieving an achievement by ID."""
    create_response = await client.post(
        "/api/v1/achievements/",
        json=create_test_achievement_payload.model_dump(mode="json"),
    )
    achievement_id = create_response.json()["id"]

    response = await client.get(f"/api/v1/achievements/{achievement_id}")
    assert response.status_code == 200
    response_data = response.json()

    assert response_data["id"] == achievement_id
    assert response_data["name"] == create_test_achievement_payload.name
    assert (
        response_data["condition_type"]
        == create_test_achievement_payload.condition_type
    )

    response_not_found = await client.get("/api/v1/achievements/99999")
    assert response_not_found.status_code == 404
    assert "detail" in response_not_found.json()
    assert "Achievement with id 99999 not found" in response_not_found.json()["detail"]


@pytest.mark.asyncio
async def test_update_achievement(
    client: AsyncClient,
    db_session: AsyncSession,
    create_test_achievement_payload: AchievementCreate,
    create_update_achievement_payload: AchievementUpdate,
):
    """Tests the PATCH /api/v1/achievements/{id} endpoint for updating an existing achievement."""
    create_response = await client.post(
        "/api/v1/achievements/",
        json=create_test_achievement_payload.model_dump(mode="json"),
    )
    achievement_id = create_response.json()["id"]

    response = await client.patch(
        f"/api/v1/achievements/{achievement_id}",
        json=create_update_achievement_payload.model_dump(
            mode="json", exclude_unset=True
        ),
    )
    assert response.status_code == 200
    response_data = response.json()

    assert response_data["id"] == achievement_id
    assert response_data["name"] == create_update_achievement_payload.name
    assert (
        response_data["condition_value"]
        == create_update_achievement_payload.condition_value
    )

    updated_achievement = await db_session.get(Achievement, achievement_id)
    assert updated_achievement.name == create_update_achievement_payload.name
    assert (
        updated_achievement.condition_value
        == create_update_achievement_payload.condition_value
    )

    response_not_found = await client.patch(
        "/api/v1/achievements/99999",
        json=create_update_achievement_payload.model_dump(
            mode="json", exclude_unset=True
        ),
    )
    assert response_not_found.status_code == 404
    assert "detail" in response_not_found.json()


@pytest.mark.asyncio
async def test_delete_achievement(
    client: AsyncClient,
    db_session: AsyncSession,
    create_test_achievement_payload: AchievementCreate,
):
    """Tests the DELETE /api/v1/achievements/{id} endpoint for deleting an achievement."""
    create_response = await client.post(
        "/api/v1/achievements/",
        json=create_test_achievement_payload.model_dump(mode="json"),
    )
    achievement_id = create_response.json()["id"]

    response = await client.delete(f"/api/v1/achievements/{achievement_id}")
    assert response.status_code == 204

    deleted_achievement = await db_session.get(Achievement, achievement_id)
    assert deleted_achievement is None

    response_not_found = await client.delete("/api/v1/achievements/99999")
    assert response_not_found.status_code == 404
    assert "detail" in response_not_found.json()


@pytest.mark.asyncio
async def test_get_achievement_count(
    client: AsyncClient,
    db_session: AsyncSession,
    create_test_achievement_payload: AchievementCreate,
):
    """Tests the GET /api/v1/achievements/count endpoint for retrieving the achievement count."""
    response_initial = await client.get("/api/v1/achievements/count")
    assert response_initial.status_code == 200
    assert response_initial.json()["count"] == 0

    await client.post(
        "/api/v1/achievements/",
        json=create_test_achievement_payload.model_dump(mode="json"),
    )

    response_after_create = await client.get("/api/v1/achievements/count")
    assert response_after_create.status_code == 200
    assert response_after_create.json()["count"] == 1


@pytest.mark.asyncio
async def test_check_achievement_exists(
    client: AsyncClient,
    db_session: AsyncSession,
    create_test_achievement_payload: AchievementCreate,
):
    """Tests the GET /api/v1/achievements/{id}/exists endpoint for checking achievement existence."""
    create_response = await client.post(
        "/api/v1/achievements/",
        json=create_test_achievement_payload.model_dump(mode="json"),
    )
    achievement_id = create_response.json()["id"]

    response_exists = await client.get(f"/api/v1/achievements/{achievement_id}/exists")
    assert response_exists.status_code == 200
    assert response_exists.json()["exists"] is True

    response_not_exists = await client.get("/api/v1/achievements/99999/exists")
    assert response_not_exists.status_code == 200
    assert response_not_exists.json()["exists"] is False


@pytest.mark.asyncio
async def test_bulk_create_achievements(
    client: AsyncClient,
    db_session: AsyncSession,
    create_test_achievement_payload: AchievementCreate,
    create_another_test_achievement_payload: AchievementCreate,
):
    """Tests the POST /api/v1/achievements/bulk endpoint for bulk creating achievements."""
    achievements_payload = [
        create_test_achievement_payload.model_dump(mode="json"),
        create_another_test_achievement_payload.model_dump(mode="json"),
    ]

    response = await client.post("/api/v1/achievements/bulk", json=achievements_payload)
    assert response.status_code == 201
    response_data = response.json()
    assert isinstance(response_data, list)
    assert len(response_data) == 2

    for achievement_data in response_data:
        created_achievement = await db_session.get(Achievement, achievement_data["id"])
        assert created_achievement is not None
        assert created_achievement.name == achievement_data["name"]

    large_achievements_payload = [
        AchievementCreate(
            name=f"Bulk Achievement {i}",
            description=f"Description {i}",
            condition_type="generic",
            condition_value=i,
        ).model_dump(mode="json")
        for i in range(101)
    ]
    response_limit_exceeded = await client.post(
        "/api/v1/achievements/bulk", json=large_achievements_payload
    )
    assert response_limit_exceeded.status_code == 400
    assert (
        "Cannot create more than 100 achievements at once"
        in response_limit_exceeded.json()["detail"]
    )
