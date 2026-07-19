import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from apps.models.achievement import Achievement
from apps.models.item import Item, ItemType
from apps.models.store_rotation import ShopItem
from apps.models.user import Friendship, FriendshipStatus, InventoryItem, User


async def _give_item(db, user_id, name="Trinket", quantity=1):
    item = Item(name=name, item_type=ItemType.MISC)
    db.add(item)
    await db.flush()
    db.add(InventoryItem(user_id=user_id, item_id=item.id, quantity=quantity))
    await db.flush()
    return item


@pytest.mark.asyncio
async def test_sell_item_credits_gold_and_removes_from_inventory(
    client: AsyncClient, db_session: AsyncSession, auth_headers
):
    user = User(name="Seller", email="seller@example.com", password="pw", gold=0)
    db_session.add(user)
    await db_session.flush()

    item = await _give_item(db_session, user.id, name="Old Sword", quantity=1)
    db_session.add(ShopItem(name="Old Sword shop", item_id=item.id, price=40, stock=5))
    await db_session.commit()

    response = await client.post(
        f"/api/v1/items/{item.id}/sell", headers=auth_headers(user)
    )
    assert response.status_code == 200
    body = response.json()
    assert body["gold_earned"] == 20
    assert body["new_gold"] == 20

    await db_session.refresh(user)
    assert user.gold == 20

    inv = (
        await db_session.execute(
            select(InventoryItem).where(
                InventoryItem.user_id == user.id, InventoryItem.item_id == item.id
            )
        )
    ).scalar_one_or_none()
    assert inv is None


@pytest.mark.asyncio
async def test_sell_item_not_in_inventory_returns_400(
    client: AsyncClient, db_session: AsyncSession, auth_headers
):
    user = User(name="Empty", email="empty@example.com", password="pw", gold=0)
    item = Item(name="Ghost", item_type=ItemType.MISC)
    db_session.add_all([user, item])
    await db_session.commit()

    response = await client.post(
        f"/api/v1/items/{item.id}/sell", headers=auth_headers(user)
    )
    assert response.status_code == 400
    assert "not in inventory" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_sell_item_flat_floor_when_not_in_shop(
    client: AsyncClient, db_session: AsyncSession, auth_headers
):
    user = User(name="Floorer", email="floorer@example.com", password="pw", gold=0)
    db_session.add(user)
    await db_session.flush()
    item = await _give_item(db_session, user.id, name="Junk")
    await db_session.commit()

    response = await client.post(
        f"/api/v1/items/{item.id}/sell", headers=auth_headers(user)
    )
    assert response.status_code == 200
    assert response.json()["gold_earned"] == 1


@pytest.mark.asyncio
async def test_buy_awards_items_purchased_achievement(
    client: AsyncClient, db_session: AsyncSession, auth_headers
):
    user = User(
        name="Collector", email="collector@example.com", password="pw", gold=100
    )
    item = Item(name="Gem", item_type=ItemType.MISC)
    achievement = Achievement(
        name="First Purchase",
        condition_type="items_purchased",
        condition_value=1,
        description="Buy your first item",
    )
    db_session.add_all([user, item, achievement])
    await db_session.flush()
    db_session.add(ShopItem(name="Gem shop", item_id=item.id, price=10, stock=5))
    await db_session.commit()

    shop_item = (
        await db_session.execute(select(ShopItem).where(ShopItem.item_id == item.id))
    ).scalar_one()
    response = await client.post(
        f"/api/v1/shop/buy/{shop_item.id}", headers=auth_headers(user)
    )
    assert response.status_code == 200

    await db_session.refresh(user, ["achievements"])
    assert any(a.id == achievement.id for a in user.achievements)


@pytest.mark.asyncio
async def test_accept_friend_awards_friends_count_achievement(
    client: AsyncClient, db_session: AsyncSession, auth_headers
):
    requester = User(name="Req", email="req@example.com", password="pw")
    accepter = User(name="Acc", email="acc@example.com", password="pw")
    achievement = Achievement(
        name="Social",
        condition_type="friends_count",
        condition_value=1,
        description="Make a friend",
    )
    db_session.add_all([requester, accepter, achievement])
    await db_session.flush()

    friendship = Friendship(
        user_id=requester.id,
        friend_id=accepter.id,
        status=FriendshipStatus.PENDING,
    )
    db_session.add(friendship)
    await db_session.commit()

    response = await client.post(
        f"/api/v1/friends/accept/{friendship.id}", headers=auth_headers(accepter)
    )
    assert response.status_code == 200

    await db_session.refresh(accepter, ["achievements"])
    await db_session.refresh(requester, ["achievements"])
    assert any(a.id == achievement.id for a in accepter.achievements)
    assert any(a.id == achievement.id for a in requester.achievements)
