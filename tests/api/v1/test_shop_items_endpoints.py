import pytest_asyncio
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from apps.models.store_rotation import ShopItem
from apps.models.item import Item, ItemType, Rarity
from apps.schemas.store_rotation import ShopItemCreate, ShopItemUpdate
from apps.schemas.item import ItemCreate
from datetime import datetime, timedelta, timezone


@pytest_asyncio.fixture
async def create_test_item_for_shop(db_session: AsyncSession):
    """
    Fixture to create a test item for shop item-related tests.
    Shop items are linked to items.
    """
    item_data = ItemCreate(
        name="Shop Sword",
        description="A sword available in shop.",
        item_type=ItemType.WEAPON,
        attack=10,
        rarity=Rarity.COMMON,
    )
    item = Item(**item_data.model_dump(mode="json"))
    db_session.add(item)
    await db_session.commit()
    return item


@pytest_asyncio.fixture
async def create_test_shop_item_payload(create_test_item_for_shop: Item):
    """
    Fixture providing data for creating a shop item (payload).
    """
    return ShopItemCreate(
        name="Basic Shop Sword",
        description="A basic sword available for purchase.",
        item_id=create_test_item_for_shop.id,
        price=100,
        rarity=Rarity.COMMON,
        stock=10,
        available_from=datetime.now(timezone.utc),
        available_until=datetime.now(timezone.utc) + timedelta(days=7),
    )


@pytest_asyncio.fixture
async def create_another_test_shop_item_payload(db_session: AsyncSession):
    """
    Fixture providing data for creating a second shop item.
    Needs its own item.
    """
    item_data = ItemCreate(
        name="Shop Shield",
        description="A shield available in shop.",
        item_type=ItemType.ARMOR,
        defense=5,
        rarity=Rarity.UNCOMMON,
    )
    item = Item(**item_data.model_dump(mode="json"))
    db_session.add(item)
    await db_session.commit()

    return ShopItemCreate(
        name="Basic Shop Shield",
        description="A basic shield available for purchase.",
        item_id=item.id,
        price=150,
        rarity=Rarity.UNCOMMON,
        stock=5,
        available_from=datetime.now(timezone.utc),
        available_until=datetime.now(timezone.utc) + timedelta(days=7),
    )


@pytest_asyncio.fixture
async def create_update_shop_item_payload():
    """
    Fixture providing data for updating a shop item.
    """
    return ShopItemUpdate(name="Advanced Shop Sword", price=150, stock=8)


@pytest.mark.asyncio
async def test_create_shop_item(
    auth_client: AsyncClient,
    db_session: AsyncSession,
    create_test_item_for_shop: Item,
    create_test_shop_item_payload: ShopItemCreate,
):
    """Tests the POST /api/v1/shop_items/ endpoint for creating a new shop item."""
    response = await auth_client.post(
        "/api/v1/shop_items/",
        json=create_test_shop_item_payload.model_dump(mode="json"),
    )

    assert response.status_code == 201
    response_data = response.json()

    assert "id" in response_data
    assert response_data["name"] == create_test_shop_item_payload.name
    assert response_data["item"]["id"] == create_test_item_for_shop.id
    assert response_data["price"] == create_test_shop_item_payload.price

    created_shop_item = await db_session.get(ShopItem, response_data["id"])
    assert created_shop_item is not None
    assert created_shop_item.name == create_test_shop_item_payload.name
    assert created_shop_item.item_id == create_test_item_for_shop.id


@pytest.mark.asyncio
async def test_get_shop_items(
    auth_client: AsyncClient,
    db_session: AsyncSession,
    create_test_item_for_shop: Item,
    create_test_shop_item_payload: ShopItemCreate,
    create_another_test_shop_item_payload: ShopItemCreate,
):
    """Tests the GET /api/v1/shop_items/ endpoint for retrieving a list of shop items."""
    await auth_client.post(
        "/api/v1/shop_items/",
        json=create_test_shop_item_payload.model_dump(mode="json"),
    )
    await auth_client.post(
        "/api/v1/shop_items/",
        json=create_another_test_shop_item_payload.model_dump(mode="json"),
    )

    response = await auth_client.get("/api/v1/shop_items/")

    assert response.status_code == 200
    response_data = response.json()

    assert isinstance(response_data, list)
    assert len(response_data) == 2

    assert "id" in response_data[0]
    assert "name" in response_data[0]
    assert "price" in response_data[0]


@pytest.mark.asyncio
async def test_get_shop_items_pagination(
    auth_client: AsyncClient, create_test_item_for_shop: Item
):
    """Tests pagination for the GET /api/v1/shop_items/ endpoint."""
    item_id = create_test_item_for_shop.id
    for i in range(5):
        shop_item_payload = ShopItemCreate(
            name=f"ShopItem {i}",
            description=f"Description {i}",
            item_id=item_id,
            price=100 + i,
            rarity=Rarity.COMMON,
        )
        await auth_client.post(
            "/api/v1/shop_items/", json=shop_item_payload.model_dump(mode="json")
        )

    response = await auth_client.get(
        "/api/v1/shop_items/?skip=1&limit=2&order_by=created_at"
    )
    assert response.status_code == 200
    response_data = response.json()
    assert len(response_data) == 2
    assert response_data[0]["name"] == "ShopItem 1"
    assert response_data[1]["name"] == "ShopItem 2"


@pytest.mark.asyncio
async def test_get_shop_items_filter_by_name(
    auth_client: AsyncClient,
    create_test_item_for_shop: Item,
    create_test_shop_item_payload: ShopItemCreate,
    create_another_test_shop_item_payload: ShopItemCreate,
):
    """Tests name filtering for the GET /api/v1/shop_items/ endpoint."""
    await auth_client.post(
        "/api/v1/shop_items/",
        json=create_test_shop_item_payload.model_dump(mode="json"),
    )
    await auth_client.post(
        "/api/v1/shop_items/",
        json=create_another_test_shop_item_payload.model_dump(mode="json"),
    )

    response = await auth_client.get("/api/v1/shop_items/?name=Sword")
    assert response.status_code == 200
    response_data = response.json()
    assert len(response_data) == 1
    assert response_data[0]["name"] == "Basic Shop Sword"


@pytest.mark.asyncio
async def test_get_shop_item_by_id(
    auth_client: AsyncClient,
    db_session: AsyncSession,
    create_test_item_for_shop: Item,
    create_test_shop_item_payload: ShopItemCreate,
):
    """Tests the GET /api/v1/shop_items/{id} endpoint for retrieving a shop item by ID."""
    create_response = await auth_client.post(
        "/api/v1/shop_items/",
        json=create_test_shop_item_payload.model_dump(mode="json"),
    )
    shop_item_id = create_response.json()["id"]

    response = await auth_client.get(f"/api/v1/shop_items/{shop_item_id}")
    assert response.status_code == 200
    response_data = response.json()

    assert response_data["id"] == shop_item_id
    assert response_data["name"] == create_test_shop_item_payload.name
    assert response_data["item"]["id"] == create_test_item_for_shop.id

    response_not_found = await auth_client.get("/api/v1/shop_items/99999")
    assert response_not_found.status_code == 404
    assert "detail" in response_not_found.json()
    assert "Shop_item with id 99999 not found" in response_not_found.json()["detail"]


@pytest.mark.asyncio
async def test_update_shop_item(
    auth_client: AsyncClient,
    db_session: AsyncSession,
    create_test_item_for_shop: Item,
    create_test_shop_item_payload: ShopItemCreate,
    create_update_shop_item_payload: ShopItemUpdate,
):
    """Tests the PATCH /api/v1/shop_items/{id} endpoint for updating an existing shop item."""
    create_response = await auth_client.post(
        "/api/v1/shop_items/",
        json=create_test_shop_item_payload.model_dump(mode="json"),
    )
    shop_item_id = create_response.json()["id"]

    response = await auth_client.patch(
        f"/api/v1/shop_items/{shop_item_id}",
        json=create_update_shop_item_payload.model_dump(
            mode="json", exclude_unset=True
        ),
    )
    assert response.status_code == 200
    response_data = response.json()

    assert response_data["id"] == shop_item_id
    assert response_data["name"] == create_update_shop_item_payload.name
    assert response_data["price"] == create_update_shop_item_payload.price
    assert response_data["stock"] == create_update_shop_item_payload.stock

    updated_shop_item = await db_session.get(ShopItem, shop_item_id)
    assert updated_shop_item.name == create_update_shop_item_payload.name
    assert updated_shop_item.price == create_update_shop_item_payload.price
    assert updated_shop_item.stock == create_update_shop_item_payload.stock

    response_not_found = await auth_client.patch(
        "/api/v1/shop_items/99999",
        json=create_update_shop_item_payload.model_dump(
            mode="json", exclude_unset=True
        ),
    )
    assert response_not_found.status_code == 404
    assert "detail" in response_not_found.json()


@pytest.mark.asyncio
async def test_delete_shop_item(
    auth_client: AsyncClient,
    db_session: AsyncSession,
    create_test_item_for_shop: Item,
    create_test_shop_item_payload: ShopItemCreate,
):
    """Tests the DELETE /api/v1/shop_items/{id} endpoint for deleting a shop item."""
    create_response = await auth_client.post(
        "/api/v1/shop_items/",
        json=create_test_shop_item_payload.model_dump(mode="json"),
    )
    shop_item_id = create_response.json()["id"]

    response = await auth_client.delete(f"/api/v1/shop_items/{shop_item_id}")
    assert response.status_code == 204

    deleted_shop_item = await db_session.get(ShopItem, shop_item_id)
    assert deleted_shop_item is None

    response_not_found = await auth_client.delete("/api/v1/shop_items/99999")
    assert response_not_found.status_code == 404
    assert "detail" in response_not_found.json()


@pytest.mark.asyncio
async def test_get_shop_item_count(
    auth_client: AsyncClient,
    db_session: AsyncSession,
    create_test_item_for_shop: Item,
    create_test_shop_item_payload: ShopItemCreate,
):
    """Tests the GET /api/v1/shop_items/count endpoint for retrieving the shop item count."""
    response_initial = await auth_client.get("/api/v1/shop_items/count")
    assert response_initial.status_code == 200
    assert response_initial.json()["count"] == 0

    await auth_client.post(
        "/api/v1/shop_items/",
        json=create_test_shop_item_payload.model_dump(mode="json"),
    )

    response_after_create = await auth_client.get("/api/v1/shop_items/count")
    assert response_after_create.status_code == 200
    assert response_after_create.json()["count"] == 1


@pytest.mark.asyncio
async def test_check_shop_item_exists(
    auth_client: AsyncClient,
    db_session: AsyncSession,
    create_test_item_for_shop: Item,
    create_test_shop_item_payload: ShopItemCreate,
):
    """Tests the GET /api/v1/shop_items/{id}/exists endpoint for checking shop item existence."""
    create_response = await auth_client.post(
        "/api/v1/shop_items/",
        json=create_test_shop_item_payload.model_dump(mode="json"),
    )
    shop_item_id = create_response.json()["id"]

    response_exists = await auth_client.get(f"/api/v1/shop_items/{shop_item_id}/exists")
    assert response_exists.status_code == 200
    assert response_exists.json()["exists"] is True

    response_not_exists = await auth_client.get("/api/v1/shop_items/99999/exists")
    assert response_not_exists.status_code == 200
    assert response_not_exists.json()["exists"] is False


@pytest.mark.asyncio
async def test_bulk_create_shop_items(
    auth_client: AsyncClient,
    db_session: AsyncSession,
    create_test_item_for_shop: Item,
    create_test_shop_item_payload: ShopItemCreate,
    create_another_test_shop_item_payload: ShopItemCreate,
):
    """Tests the POST /api/v1/shop_items/bulk endpoint for bulk creating shop items."""

    first_item_data = ItemCreate(
        name="Bulk Item 1",
        description="Bulk Item Description 1",
        item_type=ItemType.WEAPON,
        rarity=Rarity.COMMON,
    )
    first_item = Item(**first_item_data.model_dump(mode="json"))
    db_session.add(first_item)
    await db_session.commit()

    second_item_data = ItemCreate(
        name="Bulk Item 2",
        description="Bulk Item Description 2",
        item_type=ItemType.ARMOR,
        rarity=Rarity.UNCOMMON,
    )
    second_item = Item(**second_item_data.model_dump(mode="json"))
    db_session.add(second_item)
    await db_session.commit()

    shop_items_payload = [
        ShopItemCreate(
            name="Bulk Shop Item 1",
            description="Description 1",
            item_id=first_item.id,
            price=10,
            rarity=Rarity.COMMON,
        ).model_dump(mode="json"),
        ShopItemCreate(
            name="Bulk Shop Item 2",
            description="Description 2",
            item_id=second_item.id,
            price=20,
            rarity=Rarity.UNCOMMON,
        ).model_dump(mode="json"),
    ]

    response = await auth_client.post(
        "/api/v1/shop_items/bulk", json=shop_items_payload
    )
    assert response.status_code == 201
    response_data = response.json()
    assert isinstance(response_data, list)
    assert len(response_data) == 2

    for shop_item_data in response_data:
        created_shop_item = await db_session.get(ShopItem, shop_item_data["id"])
        assert created_shop_item is not None
        assert created_shop_item.name == shop_item_data["name"]

    bulk_items_list = []
    for i in range(101):
        item_data = ItemCreate(
            name=f"Limit Item {i}",
            description=f"Limit Item Description {i}",
            item_type=ItemType.MISC,
            rarity=Rarity.COMMON,
        )
        item = Item(**item_data.model_dump(mode="json"))
        db_session.add(item)
        bulk_items_list.append(item)
    await db_session.commit()

    large_shop_items_payload = [
        ShopItemCreate(
            name=f"Bulk Limit Shop Item {i}",
            description=f"Description {i}",
            item_id=bulk_items_list[i].id,
            price=10 + i,
            rarity=Rarity.COMMON,
        ).model_dump(mode="json")
        for i in range(101)
    ]
    response_limit_exceeded = await auth_client.post(
        "/api/v1/shop_items/bulk", json=large_shop_items_payload
    )
    assert response_limit_exceeded.status_code == 400
    assert (
        "Cannot create more than 100 shop_items at once"
        in response_limit_exceeded.json()["detail"]
    )
