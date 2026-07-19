import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from apps.models.item import Item, ItemType
from apps.models.user import InventoryItem, User


async def _add_item(db_session, user_id, **kwargs) -> Item:
    item = Item(**kwargs)
    db_session.add(item)
    await db_session.commit()
    await db_session.refresh(item)
    db_session.add(InventoryItem(user_id=user_id, item_id=item.id, quantity=1))
    await db_session.commit()
    return item


@pytest.mark.asyncio
async def test_use_consumable_heals_and_consumes(
    auth_client: AsyncClient,
    db_session: AsyncSession,
    test_user: User,
):
    """Using a consumable restores HP and removes one unit from the inventory."""
    test_user.health_points = 50
    await db_session.commit()
    potion = await _add_item(
        db_session,
        test_user.id,
        name="Potion",
        item_type=ItemType.CONSUMABLE,
        heal_amount=30,
    )

    response = await auth_client.post(f"/api/v1/items/{potion.id}/use")
    assert response.status_code == 200
    data = response.json()
    assert data["health_restored"] == 30
    assert data["current_health"] == 80

    inv = await db_session.execute(
        select(InventoryItem).where(
            InventoryItem.user_id == test_user.id, InventoryItem.item_id == potion.id
        )
    )
    assert inv.scalars().first() is None


@pytest.mark.asyncio
async def test_use_consumable_clamps_health_to_100(
    auth_client: AsyncClient,
    db_session: AsyncSession,
    test_user: User,
):
    """Healing never pushes health above 100."""
    test_user.health_points = 90
    await db_session.commit()
    potion = await _add_item(
        db_session,
        test_user.id,
        name="Big Potion",
        item_type=ItemType.CONSUMABLE,
        heal_amount=50,
    )

    response = await auth_client.post(f"/api/v1/items/{potion.id}/use")
    assert response.status_code == 200
    data = response.json()
    assert data["current_health"] == 100
    assert data["health_restored"] == 10


@pytest.mark.asyncio
async def test_use_non_consumable_rejected(
    auth_client: AsyncClient,
    db_session: AsyncSession,
    test_user: User,
):
    """A non-consumable item cannot be used."""
    sword = await _add_item(
        db_session, test_user.id, name="Sword", item_type=ItemType.WEAPON, attack=5
    )
    response = await auth_client.post(f"/api/v1/items/{sword.id}/use")
    assert response.status_code == 400
    assert "consumable" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_use_item_not_in_inventory_rejected(
    auth_client: AsyncClient,
    db_session: AsyncSession,
    test_user: User,
):
    """Using a consumable the user does not own is rejected."""
    potion = Item(name="Orphan Potion", item_type=ItemType.CONSUMABLE, heal_amount=10)
    db_session.add(potion)
    await db_session.commit()
    await db_session.refresh(potion)

    response = await auth_client.post(f"/api/v1/items/{potion.id}/use")
    assert response.status_code == 400
    assert "inventory" in response.json()["detail"].lower()
