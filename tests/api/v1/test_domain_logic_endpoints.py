import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from apps.models.achievement import Achievement, Reward
from apps.models.activity_log import ActivityLog, ActivityType
from apps.models.item import Item, ItemType
from apps.models.store_rotation import ShopItem
from apps.models.task import Size, Task, TaskStatus, TaskType
from apps.models.user import InventoryItem, SlotType, User

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _logs_of_type(
    db: AsyncSession, user_id: int, activity_type: ActivityType
) -> list[ActivityLog]:
    result = await db.execute(
        select(ActivityLog).where(
            ActivityLog.user_id == user_id,
            ActivityLog.activity_type == activity_type,
        )
    )
    return list(result.scalars().all())


# ---------------------------------------------------------------------------
# Point 1 + 4: Reward application & ACHIEVEMENT_UNLOCKED on manual grant
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_grant_achievement_applies_reward_gold_exp_and_item(
    auth_client: AsyncClient,
    db_session: AsyncSession,
    test_user: User,
):
    """Granting an achievement grants its reward: gold, exp and an inventory item."""
    item = Item(name="Reward Blade", item_type=ItemType.WEAPON)
    reward = Reward(
        name="Hero Reward", gold=50, experience=30, health_points=0, items=[item]
    )
    achievement = Achievement(
        name="Hero", condition_type="manual", condition_value=0, rewards=[reward]
    )
    db_session.add(achievement)
    await db_session.commit()
    await db_session.refresh(achievement)
    await db_session.refresh(item)

    response = await auth_client.post(
        f"/api/v1/users/{test_user.id}/achievements/{achievement.id}"
    )
    assert response.status_code == 200

    await db_session.refresh(test_user)
    assert test_user.gold == 50
    assert test_user.experience == 30

    inv = await db_session.execute(
        select(InventoryItem).where(
            InventoryItem.user_id == test_user.id, InventoryItem.item_id == item.id
        )
    )
    assert inv.scalar_one_or_none() is not None

    unlocked = await _logs_of_type(
        db_session, test_user.id, ActivityType.ACHIEVEMENT_UNLOCKED
    )
    assert len(unlocked) == 1
    assert unlocked[0].achievement_id == achievement.id


@pytest.mark.asyncio
async def test_grant_achievement_health_reward_clamped_to_100(
    auth_client: AsyncClient,
    db_session: AsyncSession,
    test_user: User,
):
    """Health from a reward never pushes the user above 100."""
    test_user.health_points = 98
    await db_session.commit()

    reward = Reward(name="Potion", gold=0, experience=0, health_points=10)
    achievement = Achievement(
        name="Healthy", condition_type="manual", condition_value=0, rewards=[reward]
    )
    db_session.add(achievement)
    await db_session.commit()
    await db_session.refresh(achievement)

    response = await auth_client.post(
        f"/api/v1/users/{test_user.id}/achievements/{achievement.id}"
    )
    assert response.status_code == 200

    await db_session.refresh(test_user)
    assert test_user.health_points == 100


@pytest.mark.asyncio
async def test_grant_achievement_without_reward_changes_nothing(
    auth_client: AsyncClient,
    db_session: AsyncSession,
    test_user: User,
):
    """An achievement with no reward only unlocks — no gold/exp side effects."""
    achievement = Achievement(name="Plain", condition_type="manual", condition_value=0)
    db_session.add(achievement)
    await db_session.commit()
    await db_session.refresh(achievement)

    response = await auth_client.post(
        f"/api/v1/users/{test_user.id}/achievements/{achievement.id}"
    )
    assert response.status_code == 200

    await db_session.refresh(test_user)
    assert test_user.gold == 0
    assert test_user.experience == 0


@pytest.mark.asyncio
async def test_grant_same_achievement_twice_conflicts(
    auth_client: AsyncClient,
    db_session: AsyncSession,
    test_user: User,
):
    """Re-granting an achievement returns 409 and does not double the reward."""
    reward = Reward(name="Once", gold=40, experience=0, health_points=0)
    achievement = Achievement(
        name="Unique", condition_type="manual", condition_value=0, rewards=[reward]
    )
    db_session.add(achievement)
    await db_session.commit()
    await db_session.refresh(achievement)

    first = await auth_client.post(
        f"/api/v1/users/{test_user.id}/achievements/{achievement.id}"
    )
    assert first.status_code == 200

    second = await auth_client.post(
        f"/api/v1/users/{test_user.id}/achievements/{achievement.id}"
    )
    assert second.status_code == 409

    await db_session.refresh(test_user)
    assert test_user.gold == 40


# ---------------------------------------------------------------------------
# Point 1: Reward application on auto-awarded achievements
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_auto_awarded_achievement_applies_reward(
    auth_client: AsyncClient,
    db_session: AsyncSession,
    test_user: User,
):
    """Completing a task that satisfies an achievement condition grants its reward."""
    item = Item(name="Auto Trophy", item_type=ItemType.MISC)
    reward = Reward(
        name="Trophy Reward", gold=50, experience=30, health_points=0, items=[item]
    )
    achievement = Achievement(
        name="First Task",
        condition_type="tasks_completed",
        condition_value=1,
        rewards=[reward],
    )
    task = Task(
        name="Do it",
        user_id=test_user.id,
        task_type=TaskType.REGULAR,
        task_size=Size.MEDIUM,
        status=TaskStatus.TODO,
    )
    db_session.add_all([achievement, task])
    await db_session.commit()
    await db_session.refresh(task)
    await db_session.refresh(item)

    response = await auth_client.post(
        f"/api/v1/users/{test_user.id}/complete-activity",
        json={"activity_type": "task", "activity_id": task.id},
    )
    assert response.status_code == 200

    await db_session.refresh(test_user)
    # MEDIUM task: +20 exp, +12 gold; reward: +30 exp, +50 gold
    assert test_user.experience == 50
    assert test_user.gold == 62

    inv = await db_session.execute(
        select(InventoryItem).where(
            InventoryItem.user_id == test_user.id, InventoryItem.item_id == item.id
        )
    )
    assert inv.scalar_one_or_none() is not None


# ---------------------------------------------------------------------------
# Point 2: LEVEL_UP logging
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_level_up_logged_when_threshold_crossed(
    auth_client: AsyncClient,
    db_session: AsyncSession,
    test_user: User,
):
    """Crossing a level threshold on task completion writes a LEVEL_UP log."""
    task = Task(
        name="Level task",
        user_id=test_user.id,
        task_type=TaskType.REGULAR,
        task_size=Size.MEDIUM,
        status=TaskStatus.TODO,
    )
    db_session.add(task)
    await db_session.commit()
    await db_session.refresh(task)

    # 0 exp (level 1) -> +20 exp (level 5): a level up
    response = await auth_client.post(
        f"/api/v1/users/{test_user.id}/complete-activity",
        json={"activity_type": "task", "activity_id": task.id},
    )
    assert response.status_code == 200

    level_ups = await _logs_of_type(db_session, test_user.id, ActivityType.LEVEL_UP)
    assert len(level_ups) == 1


@pytest.mark.asyncio
async def test_no_level_up_logged_below_threshold(
    auth_client: AsyncClient,
    db_session: AsyncSession,
    test_user: User,
):
    """A small gain that stays within a level writes no LEVEL_UP log."""
    test_user.experience = 1000  # level 32
    await db_session.commit()

    task = Task(
        name="Tiny task",
        user_id=test_user.id,
        task_type=TaskType.REGULAR,
        task_size=Size.SMALL,
        status=TaskStatus.TODO,
    )
    db_session.add(task)
    await db_session.commit()
    await db_session.refresh(task)

    # 1000 exp -> +10 exp = 1010: still level 32
    response = await auth_client.post(
        f"/api/v1/users/{test_user.id}/complete-activity",
        json={"activity_type": "task", "activity_id": task.id},
    )
    assert response.status_code == 200

    level_ups = await _logs_of_type(db_session, test_user.id, ActivityType.LEVEL_UP)
    assert len(level_ups) == 0


# ---------------------------------------------------------------------------
# Point 3: required_level enforced on equip
# ---------------------------------------------------------------------------


@pytest_asyncio.fixture
async def high_level_item(db_session: AsyncSession, test_user: User) -> Item:
    """An armor item requiring level 50, sitting in test_user's inventory."""
    item = Item(name="Dragon Helm", item_type=ItemType.ARMOR, required_level=50)
    db_session.add(item)
    await db_session.commit()
    await db_session.refresh(item)
    db_session.add(InventoryItem(user_id=test_user.id, item_id=item.id, quantity=1))
    await db_session.commit()
    return item


@pytest.mark.asyncio
async def test_equip_below_required_level_rejected(
    auth_client: AsyncClient,
    test_user: User,
    high_level_item: Item,
):
    """A level-1 player cannot equip an item requiring level 50."""
    response = await auth_client.post(
        f"/api/v1/users/{test_user.id}/equip",
        json={"item_id": high_level_item.id, "slot": SlotType.HELMET.value},
    )
    assert response.status_code == 400
    assert "level" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_equip_allowed_when_level_sufficient(
    auth_client: AsyncClient,
    db_session: AsyncSession,
    test_user: User,
    high_level_item: Item,
):
    """With enough experience the required-level item equips fine."""
    test_user.experience = 3000  # level ~55 > 50
    await db_session.commit()

    response = await auth_client.post(
        f"/api/v1/users/{test_user.id}/equip",
        json={"item_id": high_level_item.id, "slot": SlotType.HELMET.value},
    )
    assert response.status_code == 200


# ---------------------------------------------------------------------------
# Point 4: ITEM_PURCHASED logging
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_buy_item_logs_item_purchased(
    client: AsyncClient,
    db_session: AsyncSession,
    auth_headers,
):
    """Buying an item writes an ITEM_PURCHASED activity log."""
    user = User(name="Shopper", email="shopper@example.com", password="pw", gold=100)
    item = Item(name="Cloak", item_type=ItemType.ARMOR)
    db_session.add_all([user, item])
    await db_session.flush()
    shop_item = ShopItem(name="Cloak in Shop", item_id=item.id, price=30, stock=2)
    db_session.add(shop_item)
    await db_session.commit()

    response = await client.post(
        f"/api/v1/shop/buy/{shop_item.id}", headers=auth_headers(user)
    )
    assert response.status_code == 200

    logs = await _logs_of_type(db_session, user.id, ActivityType.ITEM_PURCHASED)
    assert len(logs) == 1
    assert logs[0].item_id == item.id
