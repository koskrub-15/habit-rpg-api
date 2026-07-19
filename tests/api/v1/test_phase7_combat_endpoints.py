import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from apps.models.achievement import Achievement
from apps.models.boss import Boss, BossFight, BossFightStatus
from apps.models.item import Item, ItemType
from apps.models.user import EquippedItem, SlotType, User


async def _make_boss(
    db,
    *,
    max_health=100,
    attack=0,
    defense=0,
    required_level=0,
    reward_gold=0,
    reward_experience=0,
    name="Boss",
):
    boss = Boss(
        name=name,
        max_health=max_health,
        attack=attack,
        defense=defense,
        required_level=required_level,
        reward_gold=reward_gold,
        reward_experience=reward_experience,
    )
    db.add(boss)
    await db.flush()
    return boss


async def _equip(
    db, user_id, *, attack=0, defense=0, pet_power=0, slot=SlotType.WEAPON
):
    item = Item(
        name=f"Gear a{attack} d{defense} p{pet_power}",
        item_type=ItemType.WEAPON,
        attack=attack,
        defense=defense,
        pet_power=pet_power,
    )
    db.add(item)
    await db.flush()
    db.add(EquippedItem(user_id=user_id, item_id=item.id, slot=slot))
    await db.flush()
    return item


@pytest.mark.asyncio
async def test_attack_defeats_weak_boss_and_awards_rewards(
    client: AsyncClient, db_session: AsyncSession, auth_headers
):
    user = User(name="Hero", email="hero@example.com", password="pw", gold=0)
    db_session.add(user)
    await db_session.flush()
    await _equip(db_session, user.id, attack=100)
    boss = await _make_boss(
        db_session, max_health=5, reward_gold=50, reward_experience=0
    )
    await db_session.commit()

    response = await client.post(
        f"/api/v1/bosses/{boss.id}/attack", headers=auth_headers(user)
    )
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "WON"
    assert body["boss_health"] == 0
    assert body["boss_damage"] == 0
    assert body["reward_gold"] == 50

    await db_session.refresh(user)
    assert user.gold == 50


@pytest.mark.asyncio
async def test_pet_power_counts_toward_attack(
    client: AsyncClient, db_session: AsyncSession, auth_headers
):
    user = User(name="Beastmaster", email="beast@example.com", password="pw")
    db_session.add(user)
    await db_session.flush()
    await _equip(db_session, user.id, attack=3, pet_power=7, slot=SlotType.PET)
    boss = await _make_boss(db_session, max_health=10)
    await db_session.commit()

    response = await client.post(
        f"/api/v1/bosses/{boss.id}/attack", headers=auth_headers(user)
    )
    body = response.json()
    assert body["player_damage"] == 10
    assert body["status"] == "WON"


@pytest.mark.asyncio
async def test_boss_survives_and_counterattacks(
    client: AsyncClient, db_session: AsyncSession, auth_headers
):
    user = User(name="Grinder", email="grinder@example.com", password="pw")
    db_session.add(user)
    await db_session.flush()
    await _equip(db_session, user.id, attack=10)
    boss = await _make_boss(db_session, max_health=1000, attack=30)
    await db_session.commit()

    response = await client.post(
        f"/api/v1/bosses/{boss.id}/attack", headers=auth_headers(user)
    )
    body = response.json()
    assert body["status"] == "ACTIVE"
    assert body["boss_health"] == 990
    assert body["boss_damage"] == 30
    assert body["player_health"] == 70
    assert body["rounds"] == 1
    assert body["died"] is False


@pytest.mark.asyncio
async def test_defense_mitigates_boss_damage(
    client: AsyncClient, db_session: AsyncSession, auth_headers
):
    user = User(name="Tank", email="tank@example.com", password="pw")
    db_session.add(user)
    await db_session.flush()
    await _equip(db_session, user.id, attack=5, slot=SlotType.WEAPON)
    await _equip(db_session, user.id, defense=50, slot=SlotType.ARMOR)
    boss = await _make_boss(db_session, max_health=1000, attack=30)
    await db_session.commit()

    response = await client.post(
        f"/api/v1/bosses/{boss.id}/attack", headers=auth_headers(user)
    )
    body = response.json()
    assert body["boss_damage"] == 0
    assert body["player_health"] == 100


@pytest.mark.asyncio
async def test_minimum_chip_damage_is_one(
    client: AsyncClient, db_session: AsyncSession, auth_headers
):
    user = User(name="Weakling", email="weak@example.com", password="pw")
    db_session.add(user)
    await db_session.flush()
    await _equip(db_session, user.id, attack=10)
    boss = await _make_boss(db_session, max_health=5, defense=1000)
    await db_session.commit()

    response = await client.post(
        f"/api/v1/bosses/{boss.id}/attack", headers=auth_headers(user)
    )
    body = response.json()
    assert body["player_damage"] == 1
    assert body["boss_health"] == 4


@pytest.mark.asyncio
async def test_losing_fight_applies_death_penalty(
    client: AsyncClient, db_session: AsyncSession, auth_headers
):
    user = User(
        name="Doomed", email="doomed@example.com", password="pw", health_points=100
    )
    db_session.add(user)
    await db_session.flush()
    await _equip(db_session, user.id, attack=1)
    boss = await _make_boss(db_session, max_health=1000, attack=200)
    await db_session.commit()

    response = await client.post(
        f"/api/v1/bosses/{boss.id}/attack", headers=auth_headers(user)
    )
    body = response.json()
    assert body["status"] == "LOST"
    assert body["died"] is True
    assert body["player_health"] == 100  # death penalty heals to full

    await db_session.refresh(user)
    assert user.gold == 0


@pytest.mark.asyncio
async def test_defeated_boss_cannot_be_refought(
    client: AsyncClient, db_session: AsyncSession, auth_headers
):
    user = User(name="Farmer", email="farmer@example.com", password="pw")
    db_session.add(user)
    await db_session.flush()
    await _equip(db_session, user.id, attack=100)
    boss = await _make_boss(db_session, max_health=5, reward_gold=10)
    await db_session.commit()

    first = await client.post(
        f"/api/v1/bosses/{boss.id}/attack", headers=auth_headers(user)
    )
    assert first.json()["status"] == "WON"

    second = await client.post(
        f"/api/v1/bosses/{boss.id}/attack", headers=auth_headers(user)
    )
    assert second.status_code == 400
    assert "already defeated" in second.json()["detail"].lower()


@pytest.mark.asyncio
async def test_level_requirement_blocks_attack(
    client: AsyncClient, db_session: AsyncSession, auth_headers
):
    user = User(name="Rookie", email="rookie@example.com", password="pw", experience=0)
    db_session.add(user)
    await db_session.flush()
    boss = await _make_boss(db_session, max_health=5, required_level=5)
    await db_session.commit()

    response = await client.post(
        f"/api/v1/bosses/{boss.id}/attack", headers=auth_headers(user)
    )
    assert response.status_code == 400
    assert "level" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_win_awards_bosses_defeated_achievement(
    client: AsyncClient, db_session: AsyncSession, auth_headers
):
    user = User(name="Slayer", email="slayer@example.com", password="pw")
    achievement = Achievement(
        name="First Blood",
        condition_type="bosses_defeated",
        condition_value=1,
        description="Defeat your first boss",
    )
    db_session.add_all([user, achievement])
    await db_session.flush()
    await _equip(db_session, user.id, attack=100)
    boss = await _make_boss(db_session, max_health=5)
    await db_session.commit()

    response = await client.post(
        f"/api/v1/bosses/{boss.id}/attack", headers=auth_headers(user)
    )
    assert response.json()["status"] == "WON"

    await db_session.refresh(user, ["achievements"])
    assert any(a.id == achievement.id for a in user.achievements)


@pytest.mark.asyncio
async def test_get_active_fight_and_404_when_none(
    client: AsyncClient, db_session: AsyncSession, auth_headers
):
    user = User(name="Watcher", email="watcher@example.com", password="pw")
    db_session.add(user)
    await db_session.flush()
    await _equip(db_session, user.id, attack=10)
    boss = await _make_boss(db_session, max_health=1000, attack=5)
    await db_session.commit()

    missing = await client.get(
        f"/api/v1/bosses/{boss.id}/fight", headers=auth_headers(user)
    )
    assert missing.status_code == 404

    await client.post(f"/api/v1/bosses/{boss.id}/attack", headers=auth_headers(user))

    active = await client.get(
        f"/api/v1/bosses/{boss.id}/fight", headers=auth_headers(user)
    )
    assert active.status_code == 200
    assert active.json()["boss_health"] == 990
    assert active.json()["status"] == "ACTIVE"

    fight = (
        await db_session.execute(select(BossFight).where(BossFight.user_id == user.id))
    ).scalar_one()
    assert fight.status == BossFightStatus.ACTIVE
