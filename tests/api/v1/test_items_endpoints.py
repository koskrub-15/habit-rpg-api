import pytest_asyncio
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from apps.models.item import Item, ItemType, Rarity
from apps.schemas.item import ItemCreate, ItemUpdate


@pytest_asyncio.fixture
async def create_test_item_payload():
    """
    Fixture providing data for creating an item (payload).
    """
    return ItemCreate(
        name="Sword of Testing",
        description="A mighty sword for testing purposes.",
        item_type=ItemType.WEAPON,
        attack=10,
        defense=2,
        rarity=Rarity.RARE,
    )


@pytest_asyncio.fixture
async def create_another_test_item_payload():
    """
    Fixture providing data for creating a second item.
    """
    return ItemCreate(
        name="Shield of Deflection",
        description="A shield that deflects bugs.",
        item_type=ItemType.ARMOR,
        attack=0,
        defense=8,
        rarity=Rarity.COMMON,
    )


@pytest_asyncio.fixture
async def create_update_item_payload():
    """
    Fixture providing data for updating an item.
    """
    return ItemUpdate(name="Grand Sword of Testing", attack=15, rarity=Rarity.EPIC)


@pytest.mark.asyncio
async def test_create_item(
    auth_client: AsyncClient, db_session: AsyncSession, create_test_item_payload: ItemCreate
):
    """Tests the POST /api/v1/items/ endpoint for creating a new item."""
    response = await auth_client.post(
        "/api/v1/items/", json=create_test_item_payload.model_dump(mode="json")
    )

    assert response.status_code == 201
    response_data = response.json()

    assert "id" in response_data
    assert response_data["item_type"] == create_test_item_payload.item_type.value

    created_item = await db_session.get(Item, response_data["id"])
    assert created_item is not None
    assert created_item.name == create_test_item_payload.name
    assert created_item.item_type == create_test_item_payload.item_type


@pytest.mark.asyncio
async def test_get_items(
    auth_client: AsyncClient,
    db_session: AsyncSession,
    create_test_item_payload: ItemCreate,
    create_another_test_item_payload: ItemCreate,
):
    """Tests the GET /api/v1/items/ endpoint for retrieving a list of items."""
    await auth_client.post(
        "/api/v1/items/", json=create_test_item_payload.model_dump(mode="json")
    )
    await auth_client.post(
        "/api/v1/items/", json=create_another_test_item_payload.model_dump(mode="json")
    )

    response = await auth_client.get("/api/v1/items/")

    assert response.status_code == 200
    response_data = response.json()

    assert isinstance(response_data, list)
    assert len(response_data) == 2

    assert "id" in response_data[0]
    assert "name" in response_data[0]
    assert "item_type" in response_data[0]


@pytest.mark.asyncio
async def test_get_items_pagination(
    auth_client: AsyncClient,
):
    """Tests pagination for the GET /api/v1/items/ endpoint."""
    for i in range(5):
        item_payload = ItemCreate(
            name=f"Item {i}",
            description=f"Description {i}",
            item_type=ItemType.MISC,
            rarity=Rarity.COMMON,
        )
        await auth_client.post("/api/v1/items/", json=item_payload.model_dump(mode="json"))

    response = await auth_client.get("/api/v1/items/?skip=1&limit=2&order_by=created_at")
    assert response.status_code == 200
    response_data = response.json()
    assert len(response_data) == 2
    assert response_data[0]["name"] == "Item 1"
    assert response_data[1]["name"] == "Item 2"


@pytest.mark.asyncio
async def test_get_items_filter_by_name(
    auth_client: AsyncClient,
    create_test_item_payload: ItemCreate,
    create_another_test_item_payload: ItemCreate,
):
    """Tests name filtering for the GET /api/v1/items/ endpoint."""
    await auth_client.post(
        "/api/v1/items/", json=create_test_item_payload.model_dump(mode="json")
    )
    await auth_client.post(
        "/api/v1/items/", json=create_another_test_item_payload.model_dump(mode="json")
    )

    response = await auth_client.get("/api/v1/items/?name=Sword")
    assert response.status_code == 200
    response_data = response.json()
    assert len(response_data) == 1
    assert response_data[0]["name"] == "Sword of Testing"


@pytest.mark.asyncio
async def test_get_item_by_id(
    auth_client: AsyncClient, db_session: AsyncSession, create_test_item_payload: ItemCreate
):
    """Tests the GET /api/v1/items/{id} endpoint for retrieving an item by ID."""
    create_response = await auth_client.post(
        "/api/v1/items/", json=create_test_item_payload.model_dump(mode="json")
    )
    item_id = create_response.json()["id"]

    response = await auth_client.get(f"/api/v1/items/{item_id}")
    assert response.status_code == 200
    response_data = response.json()

    assert response_data["id"] == item_id
    assert response_data["name"] == create_test_item_payload.name
    assert response_data["item_type"] == create_test_item_payload.item_type.value

    response_not_found = await auth_client.get("/api/v1/items/99999")
    assert response_not_found.status_code == 404
    assert "detail" in response_not_found.json()
    assert "Item with id 99999 not found" in response_not_found.json()["detail"]


@pytest.mark.asyncio
async def test_update_item(
    auth_client: AsyncClient,
    db_session: AsyncSession,
    create_test_item_payload: ItemCreate,
    create_update_item_payload: ItemUpdate,
):
    """Tests the PATCH /api/v1/items/{id} endpoint for updating an existing item."""
    create_response = await auth_client.post(
        "/api/v1/items/", json=create_test_item_payload.model_dump(mode="json")
    )
    item_id = create_response.json()["id"]

    response = await auth_client.patch(
        f"/api/v1/items/{item_id}",
        json=create_update_item_payload.model_dump(mode="json", exclude_unset=True),
    )
    assert response.status_code == 200
    response_data = response.json()

    assert response_data["id"] == item_id
    assert response_data["name"] == create_update_item_payload.name
    assert response_data["attack"] == create_update_item_payload.attack
    assert response_data["rarity"] == create_update_item_payload.rarity.value

    updated_item = await db_session.get(Item, item_id)
    assert updated_item.name == create_update_item_payload.name
    assert updated_item.attack == create_update_item_payload.attack
    assert updated_item.rarity == create_update_item_payload.rarity

    response_not_found = await auth_client.patch(
        "/api/v1/items/99999",
        json=create_update_item_payload.model_dump(mode="json", exclude_unset=True),
    )
    assert response_not_found.status_code == 404
    assert "detail" in response_not_found.json()


@pytest.mark.asyncio
async def test_delete_item(
    auth_client: AsyncClient, db_session: AsyncSession, create_test_item_payload: ItemCreate
):
    """Tests the DELETE /api/v1/items/{id} endpoint for deleting an item."""
    create_response = await auth_client.post(
        "/api/v1/items/", json=create_test_item_payload.model_dump(mode="json")
    )
    item_id = create_response.json()["id"]

    response = await auth_client.delete(f"/api/v1/items/{item_id}")
    assert response.status_code == 204

    deleted_item = await db_session.get(Item, item_id)
    assert deleted_item is None

    response_not_found = await auth_client.delete("/api/v1/items/99999")
    assert response_not_found.status_code == 404
    assert "detail" in response_not_found.json()


@pytest.mark.asyncio
async def test_get_item_count(
    auth_client: AsyncClient, db_session: AsyncSession, create_test_item_payload: ItemCreate
):
    """Tests the GET /api/v1/items/count endpoint for retrieving the item count."""
    response_initial = await auth_client.get("/api/v1/items/count")
    assert response_initial.status_code == 200
    assert response_initial.json()["count"] == 0

    await auth_client.post(
        "/api/v1/items/", json=create_test_item_payload.model_dump(mode="json")
    )

    response_after_create = await auth_client.get("/api/v1/items/count")
    assert response_after_create.status_code == 200
    assert response_after_create.json()["count"] == 1


@pytest.mark.asyncio
async def test_check_item_exists(
    auth_client: AsyncClient, db_session: AsyncSession, create_test_item_payload: ItemCreate
):
    """Tests the GET /api/v1/items/{id}/exists endpoint for checking item existence."""
    create_response = await auth_client.post(
        "/api/v1/items/", json=create_test_item_payload.model_dump(mode="json")
    )
    item_id = create_response.json()["id"]

    response_exists = await auth_client.get(f"/api/v1/items/{item_id}/exists")
    assert response_exists.status_code == 200
    assert response_exists.json()["exists"] is True

    response_not_exists = await auth_client.get("/api/v1/items/99999/exists")
    assert response_not_exists.status_code == 200
    assert response_not_exists.json()["exists"] is False


@pytest.mark.asyncio
async def test_bulk_create_items(
    auth_client: AsyncClient,
    db_session: AsyncSession,
    create_test_item_payload: ItemCreate,
    create_another_test_item_payload: ItemCreate,
):
    """Tests the POST /api/v1/items/bulk endpoint for bulk creating items."""
    items_payload = [
        create_test_item_payload.model_dump(mode="json"),
        create_another_test_item_payload.model_dump(mode="json"),
    ]

    response = await auth_client.post("/api/v1/items/bulk", json=items_payload)
    assert response.status_code == 201
    response_data = response.json()
    assert isinstance(response_data, list)
    assert len(response_data) == 2

    for item_data in response_data:
        created_item = await db_session.get(Item, item_data["id"])
        assert created_item is not None
        assert created_item.name == item_data["name"]

    large_items_payload = [
        ItemCreate(
            name=f"Bulk Item {i}",
            description=f"Bulk description {i}",
            item_type=ItemType.CONSUMABLE,
            rarity=Rarity.COMMON,
        ).model_dump(mode="json")
        for i in range(101)
    ]
    response_limit_exceeded = await auth_client.post(
        "/api/v1/items/bulk", json=large_items_payload
    )
    assert response_limit_exceeded.status_code == 400
    assert (
        "Cannot create more than 100 items at once"
        in response_limit_exceeded.json()["detail"]
    )
