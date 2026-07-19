from datetime import datetime, timedelta, timezone

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from apps.models.item import Item, ItemTheme, ItemType
from apps.models.store_rotation import ShopItem, ShopRotation, ShopRotationItem
from apps.models.user import User


def _now():
    return datetime.now(timezone.utc)


async def _make_shop_item(db, name, price=10, stock=5):
    item = Item(name=f"{name} item", item_type=ItemType.MISC)
    db.add(item)
    await db.flush()
    shop_item = ShopItem(name=name, item_id=item.id, price=price, stock=stock)
    db.add(shop_item)
    await db.flush()
    return shop_item


@pytest.mark.asyncio
async def test_current_shop_returns_active_rotation_ordered_by_slot(
    client: AsyncClient, db_session: AsyncSession, auth_headers
):
    user = User(name="Shopper", email="shopper@example.com", password="pw")
    db_session.add(user)

    rotation = ShopRotation(
        name="Summer Sale",
        start_date=_now() - timedelta(hours=1),
        end_date=_now() + timedelta(days=3),
        theme=ItemTheme.SUMMER,
    )
    db_session.add(rotation)
    await db_session.flush()

    si_a = await _make_shop_item(db_session, "Beach Ball")
    si_b = await _make_shop_item(db_session, "Sunglasses")
    db_session.add_all(
        [
            ShopRotationItem(
                name="slot2",
                rotation_id=rotation.id,
                shop_item_id=si_a.id,
                slot_in_display=2,
            ),
            ShopRotationItem(
                name="slot1",
                rotation_id=rotation.id,
                shop_item_id=si_b.id,
                slot_in_display=1,
            ),
        ]
    )
    await db_session.commit()

    response = await client.get("/api/v1/shop/current", headers=auth_headers(user))
    assert response.status_code == 200
    body = response.json()
    assert body["rotation"]["name"] == "Summer Sale"
    assert body["rotation"]["theme"] == "SUMMER"
    slots = [i["slot_in_display"] for i in body["items"]]
    assert slots == [1, 2]
    assert body["items"][0]["shop_item"]["item"] is not None


@pytest.mark.asyncio
async def test_current_shop_empty_when_no_active_rotation(
    client: AsyncClient, db_session: AsyncSession, auth_headers
):
    user = User(name="NoShop", email="noshop@example.com", password="pw")
    db_session.add(user)
    await db_session.commit()

    response = await client.get("/api/v1/shop/current", headers=auth_headers(user))
    assert response.status_code == 200
    body = response.json()
    assert body["rotation"] is None
    assert body["items"] == []


@pytest.mark.asyncio
async def test_current_shop_ignores_expired_and_future_rotations(
    client: AsyncClient, db_session: AsyncSession, auth_headers
):
    user = User(name="Timely", email="timely@example.com", password="pw")
    db_session.add(user)
    db_session.add_all(
        [
            ShopRotation(
                name="Past",
                start_date=_now() - timedelta(days=5),
                end_date=_now() - timedelta(days=1),
            ),
            ShopRotation(
                name="Future",
                start_date=_now() + timedelta(days=1),
                end_date=_now() + timedelta(days=5),
            ),
        ]
    )
    await db_session.commit()

    response = await client.get("/api/v1/shop/current", headers=auth_headers(user))
    assert response.status_code == 200
    assert response.json()["rotation"] is None


@pytest.mark.asyncio
async def test_current_shop_picks_most_recent_when_overlapping(
    client: AsyncClient, db_session: AsyncSession, auth_headers
):
    user = User(name="Overlap", email="overlap@example.com", password="pw")
    db_session.add(user)
    db_session.add_all(
        [
            ShopRotation(
                name="Older",
                start_date=_now() - timedelta(days=2),
                end_date=_now() + timedelta(days=2),
            ),
            ShopRotation(
                name="Newer",
                start_date=_now() - timedelta(hours=1),
                end_date=_now() + timedelta(days=2),
            ),
        ]
    )
    await db_session.commit()

    response = await client.get("/api/v1/shop/current", headers=auth_headers(user))
    assert response.status_code == 200
    assert response.json()["rotation"]["name"] == "Newer"


@pytest.mark.asyncio
async def test_buy_rotation_item_blocked_outside_active_rotation(
    client: AsyncClient, db_session: AsyncSession, auth_headers
):
    user = User(name="EarlyBird", email="early@example.com", password="pw", gold=100)
    db_session.add(user)

    future = ShopRotation(
        name="Winter",
        start_date=_now() + timedelta(days=1),
        end_date=_now() + timedelta(days=5),
    )
    db_session.add(future)
    await db_session.flush()

    shop_item = await _make_shop_item(db_session, "Snow Globe", price=10)
    db_session.add(
        ShopRotationItem(name="link", rotation_id=future.id, shop_item_id=shop_item.id)
    )
    await db_session.commit()

    response = await client.post(
        f"/api/v1/shop/buy/{shop_item.id}", headers=auth_headers(user)
    )
    assert response.status_code == 400
    assert "shop rotation" in response.json()["detail"]


@pytest.mark.asyncio
async def test_buy_rotation_item_succeeds_during_active_rotation(
    client: AsyncClient, db_session: AsyncSession, auth_headers
):
    user = User(name="OnTime", email="ontime@example.com", password="pw", gold=100)
    db_session.add(user)

    live = ShopRotation(
        name="LiveSale",
        start_date=_now() - timedelta(hours=1),
        end_date=_now() + timedelta(days=1),
    )
    db_session.add(live)
    await db_session.flush()

    shop_item = await _make_shop_item(db_session, "Party Hat", price=10)
    db_session.add(
        ShopRotationItem(name="link", rotation_id=live.id, shop_item_id=shop_item.id)
    )
    await db_session.commit()

    response = await client.post(
        f"/api/v1/shop/buy/{shop_item.id}", headers=auth_headers(user)
    )
    assert response.status_code == 200
    await db_session.refresh(user)
    assert user.gold == 90
