import pytest_asyncio
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from apps.models.store_rotation import ShopRotation, ItemTheme
from apps.schemas.store_rotation import ShopRotationCreate, ShopRotationUpdate
from datetime import datetime, timedelta, timezone


@pytest_asyncio.fixture
async def create_test_shop_rotation_payload():
    """
    Fixture providing data for creating a shop rotation (payload).
    """
    return ShopRotationCreate(
        name="Winter Sale 2026",
        description="Special items for winter holidays.",
        start_date=datetime.now(timezone.utc) - timedelta(days=5),
        end_date=datetime.now(timezone.utc) + timedelta(days=5),
        theme=ItemTheme.WINTER,
    )


@pytest_asyncio.fixture
async def create_another_test_shop_rotation_payload():
    """
    Fixture providing data for creating a second shop rotation.
    """
    return ShopRotationCreate(
        name="Summer Collection 2026",
        description="Hot items for hot days.",
        start_date=datetime.now(timezone.utc) + timedelta(days=10),
        end_date=datetime.now(timezone.utc) + timedelta(days=20),
        theme=ItemTheme.SUMMER,
    )


@pytest_asyncio.fixture
async def create_update_shop_rotation_payload():
    """
    Fixture providing data for updating a shop rotation.
    """
    return ShopRotationUpdate(
        name="Extended Winter Sale",
        end_date=datetime.now(timezone.utc) + timedelta(days=10),
    )


@pytest.mark.asyncio
async def test_create_shop_rotation(
    auth_client: AsyncClient,
    db_session: AsyncSession,
    create_test_shop_rotation_payload: ShopRotationCreate,
):
    """Tests the POST /api/v1/shop_rotations/ endpoint for creating a new shop rotation."""
    response = await auth_client.post(
        "/api/v1/shop_rotations/",
        json=create_test_shop_rotation_payload.model_dump(mode="json"),
    )

    assert response.status_code == 201
    response_data = response.json()

    assert "id" in response_data
    assert response_data["name"] == create_test_shop_rotation_payload.name
    assert response_data["theme"] == create_test_shop_rotation_payload.theme.value

    created_rotation = await db_session.get(ShopRotation, response_data["id"])
    assert created_rotation is not None
    assert created_rotation.name == create_test_shop_rotation_payload.name
    assert created_rotation.theme == create_test_shop_rotation_payload.theme


@pytest.mark.asyncio
async def test_get_shop_rotations(
    auth_client: AsyncClient,
    db_session: AsyncSession,
    create_test_shop_rotation_payload: ShopRotationCreate,
    create_another_test_shop_rotation_payload: ShopRotationCreate,
):
    """Tests the GET /api/v1/shop_rotations/ endpoint for retrieving a list of shop rotations."""
    await auth_client.post(
        "/api/v1/shop_rotations/",
        json=create_test_shop_rotation_payload.model_dump(mode="json"),
    )
    await auth_client.post(
        "/api/v1/shop_rotations/",
        json=create_another_test_shop_rotation_payload.model_dump(mode="json"),
    )

    response = await auth_client.get("/api/v1/shop_rotations/")

    assert response.status_code == 200
    response_data = response.json()

    assert isinstance(response_data, list)
    assert len(response_data) == 2

    assert "id" in response_data[0]
    assert "name" in response_data[0]
    assert "theme" in response_data[0]


@pytest.mark.asyncio
async def test_get_shop_rotations_pagination(
    auth_client: AsyncClient,
):
    """Tests pagination for the GET /api/v1/shop_rotations/ endpoint."""
    for i in range(5):
        rotation_payload = ShopRotationCreate(
            name=f"Rotation {i}",
            description=f"Description {i}",
            start_date=datetime.now(timezone.utc) + timedelta(days=i),
            end_date=datetime.now(timezone.utc) + timedelta(days=i + 1),
            theme=ItemTheme.COMMON,
        )
        await auth_client.post(
            "/api/v1/shop_rotations/", json=rotation_payload.model_dump(mode="json")
        )

    response = await auth_client.get(
        "/api/v1/shop_rotations/?skip=1&limit=2&order_by=created_at"
    )
    assert response.status_code == 200
    response_data = response.json()
    assert len(response_data) == 2
    assert response_data[0]["name"] == "Rotation 1"
    assert response_data[1]["name"] == "Rotation 2"


@pytest.mark.asyncio
async def test_get_shop_rotations_filter_by_name(
    auth_client: AsyncClient,
    create_test_shop_rotation_payload: ShopRotationCreate,
    create_another_test_shop_rotation_payload: ShopRotationCreate,
):
    """Tests name filtering for the GET /api/v1/shop_rotations/ endpoint."""
    await auth_client.post(
        "/api/v1/shop_rotations/",
        json=create_test_shop_rotation_payload.model_dump(mode="json"),
    )
    await auth_client.post(
        "/api/v1/shop_rotations/",
        json=create_another_test_shop_rotation_payload.model_dump(mode="json"),
    )

    response = await auth_client.get("/api/v1/shop_rotations/?name=Winter")
    assert response.status_code == 200
    response_data = response.json()
    assert len(response_data) == 1
    assert response_data[0]["name"] == "Winter Sale 2026"


@pytest.mark.asyncio
async def test_get_shop_rotation_by_id(
    auth_client: AsyncClient,
    db_session: AsyncSession,
    create_test_shop_rotation_payload: ShopRotationCreate,
):
    """Tests the GET /api/v1/shop_rotations/{id} endpoint for retrieving a shop rotation by ID."""
    create_response = await auth_client.post(
        "/api/v1/shop_rotations/",
        json=create_test_shop_rotation_payload.model_dump(mode="json"),
    )
    rotation_id = create_response.json()["id"]

    response = await auth_client.get(f"/api/v1/shop_rotations/{rotation_id}")
    assert response.status_code == 200
    response_data = response.json()

    assert response_data["id"] == rotation_id
    assert response_data["name"] == create_test_shop_rotation_payload.name
    assert response_data["theme"] == create_test_shop_rotation_payload.theme.value

    response_not_found = await auth_client.get("/api/v1/shop_rotations/99999")
    assert response_not_found.status_code == 404
    assert "detail" in response_not_found.json()
    assert (
        "Shop_rotation with id 99999 not found" in response_not_found.json()["detail"]
    )


@pytest.mark.asyncio
async def test_update_shop_rotation(
    auth_client: AsyncClient,
    db_session: AsyncSession,
    create_test_shop_rotation_payload: ShopRotationCreate,
    create_update_shop_rotation_payload: ShopRotationUpdate,
):
    """Tests the PATCH /api/v1/shop_rotations/{id} endpoint for updating an existing shop rotation."""
    create_response = await auth_client.post(
        "/api/v1/shop_rotations/",
        json=create_test_shop_rotation_payload.model_dump(mode="json"),
    )
    rotation_id = create_response.json()["id"]

    response = await auth_client.patch(
        f"/api/v1/shop_rotations/{rotation_id}",
        json=create_update_shop_rotation_payload.model_dump(
            mode="json", exclude_unset=True
        ),
    )
    assert response.status_code == 200
    response_data = response.json()

    assert response_data["id"] == rotation_id
    assert response_data["name"] == create_update_shop_rotation_payload.name

    updated_rotation = await db_session.get(ShopRotation, rotation_id)
    assert updated_rotation.name == create_update_shop_rotation_payload.name

    assert updated_rotation.end_date.strftime(
        "%Y-%m-%d %H:%M:%S"
    ) == create_update_shop_rotation_payload.end_date.strftime("%Y-%m-%d %H:%M:%S")

    response_not_found = await auth_client.patch(
        "/api/v1/shop_rotations/99999",
        json=create_update_shop_rotation_payload.model_dump(
            mode="json", exclude_unset=True
        ),
    )
    assert response_not_found.status_code == 404
    assert "detail" in response_not_found.json()


@pytest.mark.asyncio
async def test_delete_shop_rotation(
    auth_client: AsyncClient,
    db_session: AsyncSession,
    create_test_shop_rotation_payload: ShopRotationCreate,
):
    """Tests the DELETE /api/v1/shop_rotations/{id} endpoint for deleting a shop rotation."""
    create_response = await auth_client.post(
        "/api/v1/shop_rotations/",
        json=create_test_shop_rotation_payload.model_dump(mode="json"),
    )
    rotation_id = create_response.json()["id"]

    response = await auth_client.delete(f"/api/v1/shop_rotations/{rotation_id}")
    assert response.status_code == 204

    deleted_rotation = await db_session.get(ShopRotation, rotation_id)
    assert deleted_rotation is None

    response_not_found = await auth_client.delete("/api/v1/shop_rotations/99999")
    assert response_not_found.status_code == 404
    assert "detail" in response_not_found.json()


@pytest.mark.asyncio
async def test_get_shop_rotation_count(
    auth_client: AsyncClient,
    db_session: AsyncSession,
    create_test_shop_rotation_payload: ShopRotationCreate,
):
    """Tests the GET /api/v1/shop_rotations/count endpoint for retrieving the shop rotation count."""
    response_initial = await auth_client.get("/api/v1/shop_rotations/count")
    assert response_initial.status_code == 200
    assert response_initial.json()["count"] == 0

    await auth_client.post(
        "/api/v1/shop_rotations/",
        json=create_test_shop_rotation_payload.model_dump(mode="json"),
    )

    response_after_create = await auth_client.get("/api/v1/shop_rotations/count")
    assert response_after_create.status_code == 200
    assert response_after_create.json()["count"] == 1


@pytest.mark.asyncio
async def test_check_shop_rotation_exists(
    auth_client: AsyncClient,
    db_session: AsyncSession,
    create_test_shop_rotation_payload: ShopRotationCreate,
):
    """Tests the GET /api/v1/shop_rotations/{id}/exists endpoint for checking shop rotation existence."""
    create_response = await auth_client.post(
        "/api/v1/shop_rotations/",
        json=create_test_shop_rotation_payload.model_dump(mode="json"),
    )
    rotation_id = create_response.json()["id"]

    response_exists = await auth_client.get(f"/api/v1/shop_rotations/{rotation_id}/exists")
    assert response_exists.status_code == 200
    assert response_exists.json()["exists"] is True

    response_not_exists = await auth_client.get("/api/v1/shop_rotations/99999/exists")
    assert response_not_exists.status_code == 200
    assert response_not_exists.json()["exists"] is False


@pytest.mark.asyncio
async def test_bulk_create_shop_rotations(
    auth_client: AsyncClient,
    db_session: AsyncSession,
    create_test_shop_rotation_payload: ShopRotationCreate,
    create_another_test_shop_rotation_payload: ShopRotationCreate,
):
    """Tests the POST /api/v1/shop_rotations/bulk endpoint for bulk creating shop rotations."""
    rotations_payload = [
        create_test_shop_rotation_payload.model_dump(mode="json"),
        create_another_test_shop_rotation_payload.model_dump(mode="json"),
    ]

    response = await auth_client.post("/api/v1/shop_rotations/bulk", json=rotations_payload)
    assert response.status_code == 201
    response_data = response.json()
    assert isinstance(response_data, list)
    assert len(response_data) == 2

    for rotation_data in response_data:
        created_rotation = await db_session.get(ShopRotation, rotation_data["id"])
        assert created_rotation is not None
        assert created_rotation.name == rotation_data["name"]

    # Test for the bulk creation limit (default 100)
    large_rotations_payload = [
        ShopRotationCreate(
            name=f"Bulk Rotation {i}",
            description=f"Bulk description {i}",
            start_date=datetime.now(timezone.utc),
            end_date=datetime.now(timezone.utc) + timedelta(days=1),
            theme=ItemTheme.COMMON,
        ).model_dump(mode="json")
        for i in range(101)
    ]
    response_limit_exceeded = await auth_client.post(
        "/api/v1/shop_rotations/bulk", json=large_rotations_payload
    )
    assert response_limit_exceeded.status_code == 400
    assert (
        "Cannot create more than 100 shop_rotations at once"
        in response_limit_exceeded.json()["detail"]
    )
