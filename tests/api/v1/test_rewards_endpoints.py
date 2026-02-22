import pytest_asyncio
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from apps.models.achievement import Reward
from apps.schemas.achievement import RewardCreate, RewardUpdate





@pytest_asyncio.fixture
async def create_test_reward_payload():
    """
    Fixture providing data for creating a reward (payload).
    """
    return RewardCreate(
        name="Beginner's Luck",
        description="Reward for new players.",
        gold=100,
        experience=50,
        health_points=5,
    )


@pytest_asyncio.fixture
async def create_another_test_reward_payload():
    """
    Fixture providing data for creating a second reward.
    """
    return RewardCreate(
        name="Task Master Bonus",
        description="Reward for completing many tasks.",
        gold=200,
        experience=100,
        health_points=10,
    )


@pytest_asyncio.fixture
async def create_update_reward_payload():
    """
    Fixture providing data for updating a reward.
    """
    return RewardUpdate(name="Grand Beginner's Luck", gold=150, experience=75)





@pytest.mark.asyncio
async def test_create_reward(
    client: AsyncClient,
    db_session: AsyncSession,
    create_test_reward_payload: RewardCreate,
):
    """Tests the POST /api/v1/rewards/ endpoint for creating a new reward."""
    response = await client.post("/api/v1/rewards/", json=create_test_reward_payload.model_dump(mode='json'))

    assert response.status_code == 201
    response_data = response.json()

    assert "id" in response_data
    assert response_data["name"] == create_test_reward_payload.name
    assert response_data["gold"] == create_test_reward_payload.gold
    assert response_data["experience"] == create_test_reward_payload.experience

    created_reward = await db_session.get(Reward, response_data["id"])
    assert created_reward is not None
    assert created_reward.name == create_test_reward_payload.name
    assert created_reward.gold == create_test_reward_payload.gold


@pytest.mark.asyncio
async def test_get_rewards(
    client: AsyncClient,
    db_session: AsyncSession,
    create_test_reward_payload: RewardCreate,
    create_another_test_reward_payload: RewardCreate,
):
    """Tests the GET /api/v1/rewards/ endpoint for retrieving a list of rewards."""
    await client.post("/api/v1/rewards/", json=create_test_reward_payload.model_dump(mode='json'))
    await client.post("/api/v1/rewards/", json=create_another_test_reward_payload.model_dump(mode='json'))

    response = await client.get("/api/v1/rewards/")

    assert response.status_code == 200
    response_data = response.json()

    assert isinstance(response_data, list)
    assert len(response_data) == 2

    assert "id" in response_data[0]
    assert "name" in response_data[0]
    assert "gold" in response_data[0]


@pytest.mark.asyncio
async def test_get_rewards_pagination(
    client: AsyncClient,
):
    """Tests pagination for the GET /api/v1/rewards/ endpoint."""
    for i in range(5):
        reward_payload = RewardCreate(
            name=f"Reward {i}",
            description=f"Description {i}",
            gold=10 * i,
            experience=5 * i,
            health_points=i,
        )
        await client.post("/api/v1/rewards/", json=reward_payload.model_dump(mode='json'))

    response = await client.get("/api/v1/rewards/?skip=1&limit=2&order_by=created_at")
    assert response.status_code == 200
    response_data = response.json()
    assert len(response_data) == 2
    assert response_data[0]["name"] == "Reward 1"
    assert response_data[1]["name"] == "Reward 2"


@pytest.mark.asyncio
async def test_get_rewards_filter_by_name(
    client: AsyncClient,
    create_test_reward_payload: RewardCreate,
    create_another_test_reward_payload: RewardCreate,
):
    """Tests name filtering for the GET /api/v1/rewards/ endpoint."""
    await client.post("/api/v1/rewards/", json=create_test_reward_payload.model_dump(mode='json'))
    await client.post("/api/v1/rewards/", json=create_another_test_reward_payload.model_dump(mode='json'))

    response = await client.get("/api/v1/rewards/?name=Bonus")
    assert response.status_code == 200
    response_data = response.json()
    assert len(response_data) == 1
    assert response_data[0]["name"] == "Task Master Bonus"


@pytest.mark.asyncio
async def test_get_reward_by_id(
    client: AsyncClient,
    db_session: AsyncSession,
    create_test_reward_payload: RewardCreate,
):
    """Tests the GET /api/v1/rewards/{id} endpoint for retrieving a reward by ID."""
    create_response = await client.post(
        "/api/v1/rewards/", json=create_test_reward_payload.model_dump(mode='json')
    )
    reward_id = create_response.json()["id"]

    response = await client.get(f"/api/v1/rewards/{reward_id}")
    assert response.status_code == 200
    response_data = response.json()

    assert response_data["id"] == reward_id
    assert response_data["name"] == create_test_reward_payload.name
    assert response_data["gold"] == create_test_reward_payload.gold

    response_not_found = await client.get("/api/v1/rewards/99999")
    assert response_not_found.status_code == 404
    assert "detail" in response_not_found.json()
    assert "Reward with id 99999 not found" in response_not_found.json()["detail"]


@pytest.mark.asyncio
async def test_update_reward(
    client: AsyncClient,
    db_session: AsyncSession,
    create_test_reward_payload: RewardCreate,
    create_update_reward_payload: RewardUpdate,
):
    """Tests the PATCH /api/v1/rewards/{id} endpoint for updating an existing reward."""
    create_response = await client.post(
        "/api/v1/rewards/", json=create_test_reward_payload.model_dump(mode='json')
    )
    reward_id = create_response.json()["id"]

    response = await client.patch(
        f"/api/v1/rewards/{reward_id}", json=create_update_reward_payload.model_dump(mode='json', exclude_unset=True)
    )
    assert response.status_code == 200
    response_data = response.json()

    assert response_data["id"] == reward_id
    assert response_data["name"] == create_update_reward_payload.name
    assert response_data["gold"] == create_update_reward_payload.gold
    assert response_data["experience"] == create_update_reward_payload.experience

    updated_reward = await db_session.get(Reward, reward_id)
    assert updated_reward.name == create_update_reward_payload.name
    assert updated_reward.gold == create_update_reward_payload.gold
    assert updated_reward.experience == create_update_reward_payload.experience

    response_not_found = await client.patch(
        "/api/v1/rewards/99999", json=create_update_reward_payload.model_dump(mode='json', exclude_unset=True)
    )
    assert response_not_found.status_code == 404
    assert "detail" in response_not_found.json()


@pytest.mark.asyncio
async def test_delete_reward(
    client: AsyncClient,
    db_session: AsyncSession,
    create_test_reward_payload: RewardCreate,
):
    """Tests the DELETE /api/v1/rewards/{id} endpoint for deleting a reward."""
    create_response = await client.post(
        "/api/v1/rewards/", json=create_test_reward_payload.model_dump(mode='json')
    )
    reward_id = create_response.json()["id"]

    response = await client.delete(f"/api/v1/rewards/{reward_id}")
    assert response.status_code == 204

    deleted_reward = await db_session.get(Reward, reward_id)
    assert deleted_reward is None

    response_not_found = await client.delete("/api/v1/rewards/99999")
    assert response_not_found.status_code == 404
    assert "detail" in response_not_found.json()


@pytest.mark.asyncio
async def test_get_reward_count(
    client: AsyncClient,
    db_session: AsyncSession,
    create_test_reward_payload: RewardCreate,
):
    """Tests the GET /api/v1/rewards/count endpoint for retrieving the reward count."""
    response_initial = await client.get("/api/v1/rewards/count")
    assert response_initial.status_code == 200
    assert response_initial.json()["count"] == 0

    await client.post("/api/v1/rewards/", json=create_test_reward_payload.model_dump(mode='json'))

    response_after_create = await client.get("/api/v1/rewards/count")
    assert response_after_create.status_code == 200
    assert response_after_create.json()["count"] == 1


@pytest.mark.asyncio
async def test_check_reward_exists(
    client: AsyncClient,
    db_session: AsyncSession,
    create_test_reward_payload: RewardCreate,
):
    """Tests the GET /api/v1/rewards/{id}/exists endpoint for checking reward existence."""
    create_response = await client.post(
        "/api/v1/rewards/", json=create_test_reward_payload.model_dump(mode='json')
    )
    reward_id = create_response.json()["id"]

    response_exists = await client.get(f"/api/v1/rewards/{reward_id}/exists")
    assert response_exists.status_code == 200
    assert response_exists.json()["exists"] is True

    response_not_exists = await client.get("/api/v1/rewards/99999/exists")
    assert response_not_exists.status_code == 200
    assert response_not_exists.json()["exists"] is False


@pytest.mark.asyncio
async def test_bulk_create_rewards(
    client: AsyncClient,
    db_session: AsyncSession,
    create_test_reward_payload: RewardCreate,
    create_another_test_reward_payload: RewardCreate,
):
    """Tests the POST /api/v1/rewards/bulk endpoint for bulk creating rewards."""
    rewards_payload = [
        create_test_reward_payload.model_dump(mode='json'),
        create_another_test_reward_payload.model_dump(mode='json'),
    ]

    response = await client.post("/api/v1/rewards/bulk", json=rewards_payload)
    assert response.status_code == 201
    response_data = response.json()
    assert isinstance(response_data, list)
    assert len(response_data) == 2

    for reward_data in response_data:
        created_reward = await db_session.get(Reward, reward_data["id"])
        assert created_reward is not None
        assert created_reward.name == reward_data["name"]

    # Test for the bulk creation limit (default 100)
    large_rewards_payload = [
        RewardCreate(
            name=f"Bulk Reward {i}",
            description=f"Description {i}",
            gold=i,
            experience=i,
            health_points=i,
        ).model_dump(mode='json')
        for i in range(101)
    ]
    response_limit_exceeded = await client.post(
        "/api/v1/rewards/bulk", json=large_rewards_payload
    )
    assert response_limit_exceeded.status_code == 400
    assert "Cannot create more than 100 rewards at once" in response_limit_exceeded.json()["detail"]
