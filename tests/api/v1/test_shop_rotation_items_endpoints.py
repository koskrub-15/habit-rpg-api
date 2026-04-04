import pytest_asyncio
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from apps.models.store_rotation import ShopRotationItem, ShopRotation, ShopItem
from apps.models.item import Item, ItemType, Rarity
from apps.schemas.store_rotation import (
    ShopRotationItemCreate,
    ShopRotationItemUpdate,
    ShopRotationCreate,
    ShopItemCreate,
)
from apps.schemas.item import ItemCreate
from datetime import datetime, timedelta, timezone


@pytest_asyncio.fixture
async def create_test_shop_rotation_for_sri(db_session: AsyncSession):
    """
    Fixture to create a test shop rotation for ShopRotationItem-related tests.
    """
    rotation_data = ShopRotationCreate(
        name="SRI Test Rotation",
        description="Rotation for SRI testing",
        start_date=datetime.now(timezone.utc) - timedelta(days=1),
        end_date=datetime.now(timezone.utc) + timedelta(days=1),
    )
    rotation = ShopRotation(**rotation_data.model_dump())
    db_session.add(rotation)
    await db_session.commit()
    return rotation


@pytest_asyncio.fixture
async def create_test_shop_item_for_sri(db_session: AsyncSession):
    """
    Fixture to create a test shop item for ShopRotationItem-related tests.
    """
    item_data = ItemCreate(
        name="SRI Test Item",
        description="Item for SRI testing",
        item_type=ItemType.MISC,
        rarity=Rarity.COMMON,
    )
    item = Item(**item_data.model_dump(mode="json"))
    db_session.add(item)
    await db_session.commit()

    shop_item_data = ShopItemCreate(
        name="SRI Test Shop Item",
        description="Shop Item for SRI testing",
        item_id=item.id,
        price=100,
        rarity=Rarity.COMMON,
    )
    shop_item = ShopItem(**shop_item_data.model_dump(mode="json"))
    db_session.add(shop_item)
    await db_session.commit()
    return shop_item


@pytest_asyncio.fixture
async def create_test_shop_rotation_item_payload(
    create_test_shop_rotation_for_sri: ShopRotation,
    create_test_shop_item_for_sri: ShopItem,
):
    """
    Fixture providing data for creating a shop rotation item (payload).
    """
    return ShopRotationItemCreate(
        name="SRI Entry 1",
        description="First entry in SRI",
        rotation_id=create_test_shop_rotation_for_sri.id,
        shop_item_id=create_test_shop_item_for_sri.id,
        is_random_common=True,
        slot_in_display=1,
    )


@pytest_asyncio.fixture
async def create_another_test_shop_item_for_sri(db_session: AsyncSession):
    """
    Fixture to create another test shop item for ShopRotationItem-related tests.
    """
    item_data = ItemCreate(
        name="SRI Test Item 2",
        description="Second item for SRI testing",
        item_type=ItemType.MISC,
        rarity=Rarity.UNCOMMON,
    )
    item = Item(**item_data.model_dump(mode="json"))
    db_session.add(item)
    await db_session.commit()

    shop_item_data = ShopItemCreate(
        name="SRI Test Shop Item 2",
        description="Second Shop Item for SRI testing",
        item_id=item.id,
        price=200,
        rarity=Rarity.UNCOMMON,
    )
    shop_item = ShopItem(**shop_item_data.model_dump(mode="json"))
    db_session.add(shop_item)
    await db_session.commit()
    return shop_item


@pytest_asyncio.fixture
async def create_another_test_shop_rotation_item_payload(
    create_test_shop_rotation_for_sri: ShopRotation,
    create_another_test_shop_item_for_sri: ShopItem,
):
    """
    Fixture providing data for creating a second shop rotation item.
    """
    return ShopRotationItemCreate(
        name="SRI Entry 2",
        description="Second entry in SRI",
        rotation_id=create_test_shop_rotation_for_sri.id,
        shop_item_id=create_another_test_shop_item_for_sri.id,
        is_themed=True,
        slot_in_display=2,
    )


@pytest_asyncio.fixture
async def create_update_shop_rotation_item_payload():
    """
    Fixture providing data for updating a shop rotation item.
    """
    return ShopRotationItemUpdate(
        name="Updated SRI Entry 1", is_random_common=False, slot_in_display=3
    )


@pytest.mark.asyncio
async def test_create_shop_rotation_item(
    client: AsyncClient,
    db_session: AsyncSession,
    create_test_shop_rotation_for_sri: ShopRotation,
    create_test_shop_item_for_sri: ShopItem,
    create_test_shop_rotation_item_payload: ShopRotationItemCreate,
):
    """Tests the POST /api/v1/shop_rotation_items/ endpoint for creating a new shop rotation item."""
    response = await client.post(
        "/api/v1/shop_rotation_items/",
        json=create_test_shop_rotation_item_payload.model_dump(mode="json"),
    )

    assert response.status_code == 201
    response_data = response.json()

    assert "id" in response_data
    assert response_data["name"] == create_test_shop_rotation_item_payload.name
    assert response_data["rotation_id"] == create_test_shop_rotation_for_sri.id
    assert response_data["shop_item_id"] == create_test_shop_item_for_sri.id
    assert (
        response_data["is_random_common"]
        == create_test_shop_rotation_item_payload.is_random_common
    )
    assert (
        response_data["slot_in_display"]
        == create_test_shop_rotation_item_payload.slot_in_display
    )

    created_sri = await db_session.get(ShopRotationItem, response_data["id"])
    assert created_sri is not None
    assert created_sri.name == create_test_shop_rotation_item_payload.name
    assert created_sri.rotation_id == create_test_shop_rotation_for_sri.id


@pytest.mark.asyncio
async def test_get_shop_rotation_items(
    client: AsyncClient,
    db_session: AsyncSession,
    create_test_shop_rotation_for_sri: ShopRotation,
    create_test_shop_item_for_sri: ShopItem,
    create_another_test_shop_item_for_sri: ShopItem,
    create_test_shop_rotation_item_payload: ShopRotationItemCreate,
    create_another_test_shop_rotation_item_payload: ShopRotationItemCreate,
):
    """Tests the GET /api/v1/shop_rotation_items/ endpoint for retrieving a list of shop rotation items."""
    await client.post(
        "/api/v1/shop_rotation_items/",
        json=create_test_shop_rotation_item_payload.model_dump(mode="json"),
    )
    await client.post(
        "/api/v1/shop_rotation_items/",
        json=create_another_test_shop_rotation_item_payload.model_dump(mode="json"),
    )

    response = await client.get("/api/v1/shop_rotation_items/")

    assert response.status_code == 200
    response_data = response.json()

    assert isinstance(response_data, list)
    assert len(response_data) == 2

    assert "id" in response_data[0]
    assert "name" in response_data[0]
    assert "rotation_id" in response_data[0]
    assert "shop_item_id" in response_data[0]


@pytest.mark.asyncio
async def test_get_shop_rotation_items_pagination(
    client: AsyncClient,
    db_session: AsyncSession,
    create_test_shop_rotation_for_sri: ShopRotation,
):
    """Tests pagination for the GET /api/v1/shop_rotation_items/ endpoint."""
    rotation_id = create_test_shop_rotation_for_sri.id

    shop_items = []
    for i in range(5):
        item_data = ItemCreate(
            name=f"Pagination Item {i}",
            description="desc",
            item_type=ItemType.MISC,
            rarity=Rarity.COMMON,
        )
        item = Item(**item_data.model_dump(mode="json"))
        db_session.add(item)
        await db_session.flush()

        shop_item_data = ShopItemCreate(
            name=f"Pagination Shop Item {i}",
            description="desc",
            item_id=item.id,
            price=100 + i,
        )
        shop_item = ShopItem(**shop_item_data.model_dump(mode="json"))
        db_session.add(shop_item)
        shop_items.append(shop_item)

    await db_session.commit()

    for i, shop_item in enumerate(shop_items):
        sri_payload = ShopRotationItemCreate(
            name=f"SRI {i}",
            description=f"Description {i}",
            rotation_id=rotation_id,
            shop_item_id=shop_item.id,
            slot_in_display=i + 1,
        )
        await client.post(
            "/api/v1/shop_rotation_items/", json=sri_payload.model_dump(mode="json")
        )

    response = await client.get(
        "/api/v1/shop_rotation_items/?skip=1&limit=2&order_by=created_at"
    )
    assert response.status_code == 200
    response_data = response.json()
    assert len(response_data) == 2
    assert response_data[0]["name"] == "SRI 1"
    assert response_data[1]["name"] == "SRI 2"


@pytest.mark.asyncio
async def test_get_shop_rotation_items_filter_by_name(
    client: AsyncClient,
    create_test_shop_rotation_for_sri: ShopRotation,
    create_test_shop_item_for_sri: ShopItem,
    create_another_test_shop_item_for_sri: ShopItem,
    create_test_shop_rotation_item_payload: ShopRotationItemCreate,
    create_another_test_shop_rotation_item_payload: ShopRotationItemCreate,
):
    """Tests name filtering for the GET /api/v1/shop_rotation_items/ endpoint."""
    await client.post(
        "/api/v1/shop_rotation_items/",
        json=create_test_shop_rotation_item_payload.model_dump(mode="json"),
    )
    await client.post(
        "/api/v1/shop_rotation_items/",
        json=create_another_test_shop_rotation_item_payload.model_dump(mode="json"),
    )

    response = await client.get("/api/v1/shop_rotation_items/?name=Entry 1")
    assert response.status_code == 200
    response_data = response.json()
    assert len(response_data) == 1
    assert response_data[0]["name"] == "SRI Entry 1"


@pytest.mark.asyncio
async def test_get_shop_rotation_item_by_id(
    client: AsyncClient,
    db_session: AsyncSession,
    create_test_shop_rotation_for_sri: ShopRotation,
    create_test_shop_item_for_sri: ShopItem,
    create_test_shop_rotation_item_payload: ShopRotationItemCreate,
):
    """Tests the GET /api/v1/shop_rotation_items/{id} endpoint for retrieving a shop rotation item by ID."""
    create_response = await client.post(
        "/api/v1/shop_rotation_items/",
        json=create_test_shop_rotation_item_payload.model_dump(mode="json"),
    )
    sri_id = create_response.json()["id"]

    response = await client.get(f"/api/v1/shop_rotation_items/{sri_id}")
    assert response.status_code == 200
    response_data = response.json()

    assert response_data["id"] == sri_id
    assert response_data["name"] == create_test_shop_rotation_item_payload.name
    assert response_data["rotation_id"] == create_test_shop_rotation_for_sri.id
    assert response_data["shop_item_id"] == create_test_shop_item_for_sri.id

    response_not_found = await client.get("/api/v1/shop_rotation_items/99999")
    assert response_not_found.status_code == 404
    assert "detail" in response_not_found.json()
    assert (
        "Shop_rotation_item with id 99999 not found"
        in response_not_found.json()["detail"]
    )


@pytest.mark.asyncio
async def test_update_shop_rotation_item(
    client: AsyncClient,
    db_session: AsyncSession,
    create_test_shop_rotation_for_sri: ShopRotation,
    create_test_shop_item_for_sri: ShopItem,
    create_test_shop_rotation_item_payload: ShopRotationItemCreate,
    create_update_shop_rotation_item_payload: ShopRotationItemUpdate,
):
    """Tests the PATCH /api/v1/shop_rotation_items/{id} endpoint for updating an existing shop rotation item."""
    create_response = await client.post(
        "/api/v1/shop_rotation_items/",
        json=create_test_shop_rotation_item_payload.model_dump(mode="json"),
    )
    sri_id = create_response.json()["id"]

    response = await client.patch(
        f"/api/v1/shop_rotation_items/{sri_id}",
        json=create_update_shop_rotation_item_payload.model_dump(
            mode="json", exclude_unset=True
        ),
    )
    assert response.status_code == 200
    response_data = response.json()

    assert response_data["id"] == sri_id
    assert response_data["name"] == create_update_shop_rotation_item_payload.name
    assert (
        response_data["is_random_common"]
        == create_update_shop_rotation_item_payload.is_random_common
    )
    assert (
        response_data["slot_in_display"]
        == create_update_shop_rotation_item_payload.slot_in_display
    )

    updated_sri = await db_session.get(ShopRotationItem, sri_id)
    assert updated_sri.name == create_update_shop_rotation_item_payload.name
    assert (
        updated_sri.is_random_common
        == create_update_shop_rotation_item_payload.is_random_common
    )
    assert (
        updated_sri.slot_in_display
        == create_update_shop_rotation_item_payload.slot_in_display
    )

    response_not_found = await client.patch(
        "/api/v1/shop_rotation_items/99999",
        json=create_update_shop_rotation_item_payload.model_dump(
            mode="json", exclude_unset=True
        ),
    )
    assert response_not_found.status_code == 404
    assert "detail" in response_not_found.json()


@pytest.mark.asyncio
async def test_delete_shop_rotation_item(
    client: AsyncClient,
    db_session: AsyncSession,
    create_test_shop_rotation_for_sri: ShopRotation,
    create_test_shop_item_for_sri: ShopItem,
    create_test_shop_rotation_item_payload: ShopRotationItemCreate,
):
    """Tests the DELETE /api/v1/shop_rotation_items/{id} endpoint for deleting a shop rotation item."""
    create_response = await client.post(
        "/api/v1/shop_rotation_items/",
        json=create_test_shop_rotation_item_payload.model_dump(mode="json"),
    )
    sri_id = create_response.json()["id"]

    response = await client.delete(f"/api/v1/shop_rotation_items/{sri_id}")
    assert response.status_code == 204

    deleted_sri = await db_session.get(ShopRotationItem, sri_id)
    assert deleted_sri is None

    response_not_found = await client.delete("/api/v1/shop_rotation_items/99999")
    assert response_not_found.status_code == 404
    assert "detail" in response_not_found.json()


@pytest.mark.asyncio
async def test_get_shop_rotation_item_count(
    client: AsyncClient,
    db_session: AsyncSession,
    create_test_shop_rotation_for_sri: ShopRotation,
    create_test_shop_item_for_sri: ShopItem,
    create_test_shop_rotation_item_payload: ShopRotationItemCreate,
):
    """Tests the GET /api/v1/shop_rotation_items/count endpoint for retrieving the shop rotation item count."""
    response_initial = await client.get("/api/v1/shop_rotation_items/count")
    assert response_initial.status_code == 200
    assert response_initial.json()["count"] == 0

    await client.post(
        "/api/v1/shop_rotation_items/",
        json=create_test_shop_rotation_item_payload.model_dump(mode="json"),
    )

    response_after_create = await client.get("/api/v1/shop_rotation_items/count")
    assert response_after_create.status_code == 200
    assert response_after_create.json()["count"] == 1


@pytest.mark.asyncio
async def test_check_shop_rotation_item_exists(
    client: AsyncClient,
    db_session: AsyncSession,
    create_test_shop_rotation_for_sri: ShopRotation,
    create_test_shop_item_for_sri: ShopItem,
    create_test_shop_rotation_item_payload: ShopRotationItemCreate,
):
    """Tests the GET /api/v1/shop_rotation_items/{id}/exists endpoint for checking shop rotation item existence."""
    create_response = await client.post(
        "/api/v1/shop_rotation_items/",
        json=create_test_shop_rotation_item_payload.model_dump(mode="json"),
    )
    sri_id = create_response.json()["id"]

    response_exists = await client.get(f"/api/v1/shop_rotation_items/{sri_id}/exists")
    assert response_exists.status_code == 200
    assert response_exists.json()["exists"] is True

    response_not_exists = await client.get("/api/v1/shop_rotation_items/99999/exists")
    assert response_not_exists.status_code == 200
    assert response_not_exists.json()["exists"] is False


@pytest.mark.asyncio
async def test_bulk_create_shop_rotation_items(
    client: AsyncClient,
    db_session: AsyncSession,
    create_test_shop_rotation_for_sri: ShopRotation,
    create_test_shop_item_for_sri: ShopItem,
    create_another_test_shop_item_for_sri: ShopItem,
    create_test_shop_rotation_item_payload: ShopRotationItemCreate,
    create_another_test_shop_rotation_item_payload: ShopRotationItemCreate,
):
    """Tests the POST /api/v1/shop_rotation_items/bulk endpoint for bulk creating shop rotation items."""
    rotation = create_test_shop_rotation_for_sri
    shop_item_1 = create_test_shop_item_for_sri
    shop_item_2 = create_another_test_shop_item_for_sri

    sri_payloads = [
        ShopRotationItemCreate(
            name="Bulk SRI 1",
            description="Description 1",
            rotation_id=rotation.id,
            shop_item_id=shop_item_1.id,
            slot_in_display=1,
        ).model_dump(mode="json"),
        ShopRotationItemCreate(
            name="Bulk SRI 2",
            description="Description 2",
            rotation_id=rotation.id,
            shop_item_id=shop_item_2.id,
            slot_in_display=2,
        ).model_dump(mode="json"),
    ]

    response = await client.post("/api/v1/shop_rotation_items/bulk", json=sri_payloads)
    assert response.status_code == 201
    response_data = response.json()
    assert isinstance(response_data, list)
    assert len(response_data) == 2

    for sri_data in response_data:
        created_sri = await db_session.get(ShopRotationItem, sri_data["id"])
        assert created_sri is not None
        assert created_sri.name == sri_data["name"]

    bulk_shop_items = []
    for i in range(101):
        item_data = ItemCreate(
            name=f"Bulk Item {i}",
            description="desc",
            item_type=ItemType.MISC,
            rarity=Rarity.COMMON,
        )
        item = Item(**item_data.model_dump(mode="json"))
        db_session.add(item)
        await db_session.flush()
        shop_item_data = ShopItemCreate(
            name=f"Bulk Shop Item {i}",
            description="desc",
            item_id=item.id,
            price=i + 1,
        )
        shop_item = ShopItem(**shop_item_data.model_dump(mode="json"))
        db_session.add(shop_item)
        bulk_shop_items.append(shop_item)
    await db_session.commit()

    large_sri_payloads = [
        ShopRotationItemCreate(
            name=f"Bulk Limit SRI {i}",
            description=f"Description {i}",
            rotation_id=rotation.id,
            shop_item_id=bulk_shop_items[i].id,
            slot_in_display=i + 1,
        ).model_dump(mode="json")
        for i in range(101)
    ]
    response_limit_exceeded = await client.post(
        "/api/v1/shop_rotation_items/bulk", json=large_sri_payloads
    )
    assert response_limit_exceeded.status_code == 400
    assert (
        "Cannot create more than 100 shop_rotation_items at once"
        in response_limit_exceeded.json()["detail"]
    )
