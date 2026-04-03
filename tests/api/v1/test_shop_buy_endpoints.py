import pytest
from datetime import datetime, timedelta, timezone
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from apps.models.user import User, InventoryItem
from apps.models.item import Item, ItemType
from apps.models.store_rotation import ShopItem

@pytest.mark.asyncio
async def test_buy_item_deducts_gold(client: AsyncClient, db_session: AsyncSession):
    """
    Tests that buying an item correctly deducts gold from the user.
    """
    # Create user with gold
    user = User(name="Buyer", email="buyer@example.com", password="password", gold=100)
    db_session.add(user)
    
    # Create item and shop item
    item = Item(name="Sword", item_type=ItemType.WEAPON, description="Sharp sword")
    db_session.add(item)
    await db_session.flush()
    
    shop_item = ShopItem(name="Sword in Shop", item_id=item.id, price=50, stock=5)
    db_session.add(shop_item)
    await db_session.commit()
    
    # Buy item (Assuming we have a way to authenticate or pass user_id)
    # For now, let's assume we pass user context or it's mocked
    # In a real scenario, this would be an authenticated request
    response = await client.post(f"/api/v1/shop/buy/{shop_item.id}", params={"user_id": user.id})
    
    assert response.status_code == 200
    await db_session.refresh(user)
    assert user.gold == 50

@pytest.mark.asyncio
async def test_buy_item_adds_to_inventory(client: AsyncClient, db_session: AsyncSession):
    """
    Tests that a purchased item is added to the user's inventory.
    """
    user = User(name="Buyer2", email="buyer2@example.com", password="password", gold=100)
    item = Item(name="Shield", item_type=ItemType.ARMOR, description="Strong shield")
    db_session.add_all([user, item])
    await db_session.flush()
    
    shop_item = ShopItem(name="Shield in Shop", item_id=item.id, price=30, stock=1)
    db_session.add(shop_item)
    await db_session.commit()
    
    await client.post(f"/api/v1/shop/buy/{shop_item.id}", params={"user_id": user.id})
    
    # Check inventory
    from sqlalchemy import select
    stmt = select(InventoryItem).where(InventoryItem.user_id == user.id, InventoryItem.item_id == item.id)
    result = await db_session.execute(stmt)
    inv_item = result.scalar_one_or_none()
    assert inv_item is not None
    assert inv_item.quantity == 1

@pytest.mark.asyncio
async def test_buy_item_not_enough_gold_returns_400(client: AsyncClient, db_session: AsyncSession):
    """
    Tests that a user cannot buy an item if they don't have enough gold.
    """
    user = User(name="Poor User", email="poor@example.com", password="password", gold=10)
    item = Item(name="Expensive Item", item_type=ItemType.MISC, description="Rich stuff")
    db_session.add_all([user, item])
    await db_session.flush()
    
    shop_item = ShopItem(name="Expensive Item in Shop", item_id=item.id, price=100, stock=1)
    db_session.add(shop_item)
    await db_session.commit()
    
    response = await client.post(f"/api/v1/shop/buy/{shop_item.id}", params={"user_id": user.id})
    assert response.status_code == 400
    assert "Not enough gold" in response.json()["detail"]

@pytest.mark.asyncio
async def test_buy_nonexistent_shop_item_returns_404(client: AsyncClient, db_session: AsyncSession):
    """
    Tests buying an item that doesn't exist in the shop.
    """
    user = User(name="User", email="user@example.com", password="password", gold=100)
    db_session.add(user)
    await db_session.commit()
    
    response = await client.post("/api/v1/shop/buy/9999", params={"user_id": user.id})
    assert response.status_code == 404

@pytest.mark.asyncio
async def test_buy_out_of_stock_returns_400(client: AsyncClient, db_session: AsyncSession):
    """
    Tests buying an item that is out of stock.
    """
    user = User(name="Buyer3", email="buyer3@example.com", password="password", gold=100)
    item = Item(name="Rare Item", item_type=ItemType.MISC, description="Sold out")
    db_session.add_all([user, item])
    await db_session.flush()
    
    shop_item = ShopItem(name="Sold Out Item", item_id=item.id, price=10, stock=0)
    db_session.add(shop_item)
    await db_session.commit()
    
    response = await client.post(f"/api/v1/shop/buy/{shop_item.id}", params={"user_id": user.id})
    assert response.status_code == 400
    assert "Out of stock" in response.json()["detail"]

@pytest.mark.asyncio
async def test_buy_reduces_stock_by_one(client: AsyncClient, db_session: AsyncSession):
    """
    Tests that buying an item reduces its stock by one.
    """
    user = User(name="Buyer4", email="buyer4@example.com", password="password", gold=100)
    item = Item(name="Limited Item", item_type=ItemType.MISC, description="Limited edition")
    db_session.add_all([user, item])
    await db_session.flush()
    
    shop_item = ShopItem(name="Limited Item in Shop", item_id=item.id, price=10, stock=10)
    db_session.add(shop_item)
    await db_session.commit()
    
    await client.post(f"/api/v1/shop/buy/{shop_item.id}", params={"user_id": user.id})
    
    await db_session.refresh(shop_item)
    assert shop_item.stock == 9

@pytest.mark.asyncio
async def test_buy_item_outside_availability_window_returns_400(client: AsyncClient, db_session: AsyncSession):
    """
    Tests buying an item outside its available date range.
    """
    user = User(name="Buyer5", email="buyer5@example.com", password="password", gold=100)
    item = Item(name="Future Item", item_type=ItemType.MISC, description="Not yet")
    db_session.add_all([user, item])
    await db_session.flush()
    
    # Item available only in the future
    start_date = datetime.now(timezone.utc) + timedelta(days=1)
    end_date = datetime.now(timezone.utc) + timedelta(days=2)
    
    shop_item = ShopItem(
        name="Future Shop Item", 
        item_id=item.id, 
        price=10, 
        stock=10,
        available_from=start_date,
        available_until=end_date
    )
    db_session.add(shop_item)
    await db_session.commit()
    
    response = await client.post(f"/api/v1/shop/buy/{shop_item.id}", params={"user_id": user.id})
    assert response.status_code == 400
    assert "Item not currently available" in response.json()["detail"]
