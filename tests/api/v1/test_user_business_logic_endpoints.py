from datetime import datetime, timedelta, timezone

import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from apps.models.habit import Habit, HabitStatus, HabitType
from apps.models.item import Item, ItemType
from apps.models.task import Size, Task, TaskStatus, TaskType
from apps.models.user import EquippedItem, InventoryItem, SlotType, User

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest_asyncio.fixture
async def test_task(db_session: AsyncSession, test_user: User) -> Task:
    """Create a regular task linked to test_user."""
    task = Task(
        name="Test Task",
        description="A test task",
        user_id=test_user.id,
        task_type=TaskType.REGULAR,
        task_size=Size.MEDIUM,
        status=TaskStatus.TODO,
    )
    db_session.add(task)
    await db_session.commit()
    await db_session.refresh(task)
    return task


@pytest_asyncio.fixture
async def test_daily_task(db_session: AsyncSession, test_user: User) -> Task:
    """Create a daily task linked to test_user."""
    task = Task(
        name="Daily Task",
        description="A daily task",
        user_id=test_user.id,
        task_type=TaskType.DAILY,
        task_size=Size.SMALL,
        status=TaskStatus.TODO,
    )
    db_session.add(task)
    await db_session.commit()
    await db_session.refresh(task)
    return task


@pytest_asyncio.fixture
async def test_positive_habit(db_session: AsyncSession, test_user: User) -> Habit:
    """Create a positive habit linked to test_user."""
    habit = Habit(
        name="Exercise",
        description="Daily exercise",
        user_id=test_user.id,
        habit_type=HabitType.POSITIVE,
        habit_size=Size.MEDIUM,
        streak=0,
        overfulfillment=0,
        status=HabitStatus.TODO,
    )
    db_session.add(habit)
    await db_session.commit()
    await db_session.refresh(habit)
    return habit


@pytest_asyncio.fixture
async def test_negative_habit(db_session: AsyncSession, test_user: User) -> Habit:
    """Create a negative habit linked to test_user."""
    habit = Habit(
        name="Smoking",
        description="Avoid smoking",
        user_id=test_user.id,
        habit_type=HabitType.NEGATIVE,
        habit_size=Size.MEDIUM,
        streak=0,
        overfulfillment=0,
        status=HabitStatus.TODO,
    )
    db_session.add(habit)
    await db_session.commit()
    await db_session.refresh(habit)
    return habit


@pytest_asyncio.fixture
async def test_neutral_habit(db_session: AsyncSession, test_user: User) -> Habit:
    """Create a neutral habit linked to test_user."""
    habit = Habit(
        name="Reading",
        description="Read a book",
        user_id=test_user.id,
        habit_type=HabitType.NEUTRAL,
        habit_size=Size.SMALL,
        streak=0,
        overfulfillment=0,
        status=HabitStatus.TODO,
    )
    db_session.add(habit)
    await db_session.commit()
    await db_session.refresh(habit)
    return habit


@pytest_asyncio.fixture
async def test_armor_item(db_session: AsyncSession) -> Item:
    """Create an armor item."""
    item = Item(
        name="Iron Helmet", item_type=ItemType.ARMOR, description="A sturdy helmet"
    )
    db_session.add(item)
    await db_session.commit()
    await db_session.refresh(item)
    return item


@pytest_asyncio.fixture
async def test_weapon_item(db_session: AsyncSession) -> Item:
    """Create a weapon item."""
    item = Item(
        name="Iron Sword", item_type=ItemType.WEAPON, description="A sharp sword"
    )
    db_session.add(item)
    await db_session.commit()
    await db_session.refresh(item)
    return item


@pytest_asyncio.fixture
async def test_misc_item(db_session: AsyncSession) -> Item:
    """Create a misc item (accessory)."""
    item = Item(name="Lucky Ring", item_type=ItemType.MISC, description="A lucky ring")
    db_session.add(item)
    await db_session.commit()
    await db_session.refresh(item)
    return item


# ---------------------------------------------------------------------------
# Tests: _calculate_level
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_calculate_level_initial(auth_client: AsyncClient, test_user: User):
    """User starts at level 1 with 0 experience."""
    response = await auth_client.get(f"/api/v1/users/{test_user.id}")
    assert response.status_code == 200
    assert response.json()["experience"] == 0


# ---------------------------------------------------------------------------
# Tests: complete_activity — TASK
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_complete_task_rewards_exp_and_gold(
    auth_client: AsyncClient,
    db_session: AsyncSession,
    test_user: User,
    test_task: Task,
):
    """Completing a task should award exp and gold based on task size."""
    response = await auth_client.post(
        f"/api/v1/users/{test_user.id}/complete-activity",
        json={"activity_type": "task", "activity_id": test_task.id},
    )
    assert response.status_code == 200
    data = response.json()

    # MEDIUM size: 10 * 2.0 = 20 exp, 20 * 0.6 = 12 gold
    assert data["activity_type"] == "Task"
    assert data["activity_name"] == test_task.name
    assert data["exp_gained"] == 20
    assert data["gold_gained"] == 12
    assert data["health_change"] == 0

    await db_session.refresh(test_user)
    assert test_user.experience == 20
    assert test_user.gold == 12

    await db_session.refresh(test_task)
    assert test_task.status == TaskStatus.COMPLETED


@pytest.mark.asyncio
async def test_complete_task_size_multipliers(
    auth_client: AsyncClient,
    db_session: AsyncSession,
    test_user: User,
):
    """Test that different task sizes give correct rewards."""
    sizes_and_expected = [
        (Size.SMALL, 10, 6),  # 10 * 1.0 = 10 exp, 10 * 0.6 = 6 gold
        (Size.BIG, 35, 21),  # 10 * 3.5 = 35 exp, 35 * 0.6 = 21 gold
        (Size.LARGE, 50, 30),  # 10 * 5.0 = 50 exp, 50 * 0.6 = 30 gold
    ]
    for task_size, expected_exp, expected_gold in sizes_and_expected:
        task = Task(
            name=f"Task {task_size.value}",
            user_id=test_user.id,
            task_type=TaskType.REGULAR,
            task_size=task_size,
            status=TaskStatus.TODO,
        )
        db_session.add(task)
        await db_session.commit()
        await db_session.refresh(task)

        response = await auth_client.post(
            f"/api/v1/users/{test_user.id}/complete-activity",
            json={"activity_type": "task", "activity_id": task.id},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["exp_gained"] == expected_exp, f"Failed for size {task_size}"
        assert data["gold_gained"] == expected_gold, f"Failed for size {task_size}"


@pytest.mark.asyncio
async def test_complete_already_completed_task_returns_error(
    auth_client: AsyncClient,
    db_session: AsyncSession,
    test_user: User,
    test_task: Task,
):
    """Completing an already-completed task should return an error."""
    test_task.status = TaskStatus.COMPLETED
    await db_session.commit()

    response = await auth_client.post(
        f"/api/v1/users/{test_user.id}/complete-activity",
        json={"activity_type": "task", "activity_id": test_task.id},
    )
    assert response.status_code == 400
    assert "already completed" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_complete_task_not_found(
    auth_client: AsyncClient,
    test_user: User,
):
    """Completing a non-existent task returns 404."""
    response = await auth_client.post(
        f"/api/v1/users/{test_user.id}/complete-activity",
        json={"activity_type": "task", "activity_id": 99999},
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_complete_task_wrong_user(
    client: AsyncClient,
    db_session: AsyncSession,
    test_task: Task,
    create_test_user,
    auth_headers,
):
    """A regular user cannot complete an activity for another user (403)."""
    caller = await create_test_user(name="Caller", email="caller@example.com")
    other_user = await create_test_user(name="Other User", email="other@example.com")

    response = await client.post(
        f"/api/v1/users/{other_user.id}/complete-activity",
        json={"activity_type": "task", "activity_id": test_task.id},
        headers=auth_headers(caller),
    )
    assert response.status_code == 403


# ---------------------------------------------------------------------------
# Tests: complete_activity — HABIT (POSITIVE)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_complete_positive_habit_performed(
    auth_client: AsyncClient,
    db_session: AsyncSession,
    test_user: User,
    test_positive_habit: Habit,
):
    """Performing a positive habit gives exp, gold, increments streak."""
    response = await auth_client.post(
        f"/api/v1/users/{test_user.id}/complete-activity",
        json={
            "activity_type": "habit",
            "activity_id": test_positive_habit.id,
            "performed": True,
        },
    )
    assert response.status_code == 200
    data = response.json()

    # MEDIUM size, POSITIVE: 5 * 2.0 * 1.0 = 10 exp, 10 * 0.5 = 5 gold
    assert data["exp_gained"] == 10
    assert data["gold_gained"] == 5
    assert data["health_change"] == 0

    await db_session.refresh(test_positive_habit)
    assert test_positive_habit.streak == 1
    assert test_positive_habit.status == HabitStatus.COMPLETED

    await db_session.refresh(test_user)
    assert test_user.experience == 10
    assert test_user.gold == 5


@pytest.mark.asyncio
async def test_complete_positive_habit_not_performed_resets_streak(
    auth_client: AsyncClient,
    db_session: AsyncSession,
    test_user: User,
    test_positive_habit: Habit,
):
    """Not performing a positive habit resets streak and marks as FAILED."""
    test_positive_habit.streak = 5
    await db_session.commit()

    response = await auth_client.post(
        f"/api/v1/users/{test_user.id}/complete-activity",
        json={
            "activity_type": "habit",
            "activity_id": test_positive_habit.id,
            "performed": False,
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["exp_gained"] == 0
    assert data["gold_gained"] == 0

    await db_session.refresh(test_positive_habit)
    assert test_positive_habit.streak == 0
    assert test_positive_habit.status == HabitStatus.FAILED


@pytest.mark.asyncio
async def test_positive_habit_overfulfillment_increases_on_repeat(
    auth_client: AsyncClient,
    db_session: AsyncSession,
    test_user: User,
    test_positive_habit: Habit,
):
    """Performing a positive habit again the same day increments overfulfillment."""
    test_positive_habit.status = HabitStatus.COMPLETED
    test_positive_habit.overfulfillment = 0
    test_positive_habit.last_completed_at = datetime.now(timezone.utc)
    await db_session.commit()

    response = await auth_client.post(
        f"/api/v1/users/{test_user.id}/complete-activity",
        json={
            "activity_type": "habit",
            "activity_id": test_positive_habit.id,
            "performed": True,
        },
    )
    assert response.status_code == 200

    await db_session.refresh(test_positive_habit)
    assert test_positive_habit.overfulfillment == 1


@pytest.mark.asyncio
async def test_positive_habit_overfulfillment_decreases_on_miss(
    auth_client: AsyncClient,
    db_session: AsyncSession,
    test_user: User,
    test_positive_habit: Habit,
):
    """Missing a positive habit with overfulfillment reduces it instead of resetting streak."""
    test_positive_habit.overfulfillment = 2
    test_positive_habit.streak = 3
    await db_session.commit()

    response = await auth_client.post(
        f"/api/v1/users/{test_user.id}/complete-activity",
        json={
            "activity_type": "habit",
            "activity_id": test_positive_habit.id,
            "performed": False,
        },
    )
    assert response.status_code == 200

    await db_session.refresh(test_positive_habit)
    assert test_positive_habit.overfulfillment == 1
    assert (
        test_positive_habit.streak == 3
    )  # streak preserved because overfulfillment was > 0


@pytest.mark.asyncio
async def test_positive_habit_repeat_same_day_gives_diminishing_reward(
    auth_client: AsyncClient,
    db_session: AsyncSession,
    test_user: User,
    test_positive_habit: Habit,
):
    """Repeating a habit the same day yields a smaller reward (decay 0.7)."""
    payload = {
        "activity_type": "habit",
        "activity_id": test_positive_habit.id,
        "performed": True,
    }
    url = f"/api/v1/users/{test_user.id}/complete-activity"

    first = await auth_client.post(url, json=payload)
    second = await auth_client.post(url, json=payload)
    assert first.status_code == 200 and second.status_code == 200

    first_exp = first.json()["exp_gained"]
    second_exp = second.json()["exp_gained"]
    assert first_exp > 0
    # size MEDIUM (x2), base 5 -> 10 full; second is int(10 * 0.7) = 7
    assert second_exp == int(first_exp * 0.7)

    await db_session.refresh(test_positive_habit)
    assert test_positive_habit.overfulfillment == 1
    assert test_positive_habit.last_completed_at is not None


@pytest.mark.asyncio
async def test_positive_habit_new_day_resets_reward_and_counter(
    auth_client: AsyncClient,
    db_session: AsyncSession,
    test_user: User,
    test_positive_habit: Habit,
):
    """A completion on a new UTC day resets overfulfillment and pays full reward."""
    test_positive_habit.status = HabitStatus.COMPLETED
    test_positive_habit.overfulfillment = 5
    test_positive_habit.last_completed_at = datetime.now(timezone.utc) - timedelta(
        days=1
    )
    await db_session.commit()

    response = await auth_client.post(
        f"/api/v1/users/{test_user.id}/complete-activity",
        json={
            "activity_type": "habit",
            "activity_id": test_positive_habit.id,
            "performed": True,
        },
    )
    assert response.status_code == 200
    # Full reward again: base 5 * MEDIUM 2 = 10, no decay
    assert response.json()["exp_gained"] == 10

    await db_session.refresh(test_positive_habit)
    assert test_positive_habit.overfulfillment == 0


@pytest.mark.asyncio
async def test_task_completed_again_same_day_returns_409(
    auth_client: AsyncClient,
    db_session: AsyncSession,
    test_user: User,
    test_daily_task: Task,
):
    """A daily task reset to TODO cannot be re-farmed the same day."""
    test_daily_task.status = TaskStatus.TODO
    test_daily_task.last_completed_at = datetime.now(timezone.utc)
    await db_session.commit()

    response = await auth_client.post(
        f"/api/v1/users/{test_user.id}/complete-activity",
        json={"activity_type": "task", "activity_id": test_daily_task.id},
    )
    assert response.status_code == 409
    assert "today" in response.json()["detail"].lower()


# ---------------------------------------------------------------------------
# Tests: complete_activity — HABIT (NEGATIVE)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_negative_habit_not_performed_gives_rewards(
    auth_client: AsyncClient,
    db_session: AsyncSession,
    test_user: User,
    test_negative_habit: Habit,
):
    """Successfully avoiding a negative habit gives full exp/gold, no health loss."""
    response = await auth_client.post(
        f"/api/v1/users/{test_user.id}/complete-activity",
        json={
            "activity_type": "habit",
            "activity_id": test_negative_habit.id,
            "performed": False,
        },
    )
    assert response.status_code == 200
    data = response.json()

    # MEDIUM, NEGATIVE, avoided: 5 * 2.0 * 1.0 = 10 exp, 10 * 0.4 = 4 gold
    assert data["exp_gained"] == 10
    assert data["gold_gained"] == 4
    assert data["health_change"] == 0

    await db_session.refresh(test_negative_habit)
    assert test_negative_habit.streak == 1
    assert test_negative_habit.status == HabitStatus.COMPLETED


@pytest.mark.asyncio
async def test_negative_habit_performed_resets_streak(
    auth_client: AsyncClient,
    db_session: AsyncSession,
    test_user: User,
    test_negative_habit: Habit,
):
    """Giving in to a negative habit loses health, gives no reward, resets streak."""
    test_negative_habit.streak = 3
    await db_session.commit()

    response = await auth_client.post(
        f"/api/v1/users/{test_user.id}/complete-activity",
        json={
            "activity_type": "habit",
            "activity_id": test_negative_habit.id,
            "performed": True,
        },
    )
    assert response.status_code == 200
    data = response.json()
    # Giving in: no reward, health loss of 10 * 2.0 = 20
    assert data["exp_gained"] == 0
    assert data["gold_gained"] == 0
    assert data["health_change"] == int(-10 * 2.0)  # -20

    await db_session.refresh(test_negative_habit)
    assert test_negative_habit.streak == 0
    assert test_negative_habit.status == HabitStatus.FAILED


@pytest.mark.asyncio
async def test_negative_habit_zero_health_triggers_death(
    auth_client: AsyncClient,
    db_session: AsyncSession,
    test_user: User,
    test_negative_habit: Habit,
    test_armor_item: Item,
):
    """Dropping to 0 HP triggers the death penalty: lose one level, all gold and a
    random equipped item; health resets to full."""
    test_user.health_points = 5
    test_user.gold = 100
    test_user.experience = 20  # level 5
    db_session.add(
        EquippedItem(
            user_id=test_user.id, item_id=test_armor_item.id, slot=SlotType.ARMOR
        )
    )
    await db_session.commit()

    response = await auth_client.post(
        f"/api/v1/users/{test_user.id}/complete-activity",
        json={
            "activity_type": "habit",
            "activity_id": test_negative_habit.id,
            "performed": True,
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["died"] is True
    assert data["current_health"] == 100
    assert data["new_level"] == 4

    await db_session.refresh(test_user)
    assert test_user.health_points == 100
    assert test_user.gold == 0
    assert test_user.experience == 9  # floor of level 4, XP bar reset

    equipped = await db_session.execute(
        select(EquippedItem).where(EquippedItem.user_id == test_user.id)
    )
    assert equipped.scalars().first() is None


@pytest.mark.asyncio
async def test_level_up_heals_to_full(
    auth_client: AsyncClient,
    db_session: AsyncSession,
    test_user: User,
    test_task: Task,
):
    """Crossing a level threshold restores health to full."""
    test_user.health_points = 30
    test_user.experience = 0  # level 1
    await db_session.commit()

    # MEDIUM task: +20 exp -> level 5, a level up
    response = await auth_client.post(
        f"/api/v1/users/{test_user.id}/complete-activity",
        json={"activity_type": "task", "activity_id": test_task.id},
    )
    assert response.status_code == 200
    assert response.json()["current_health"] == 100

    await db_session.refresh(test_user)
    assert test_user.health_points == 100


# ---------------------------------------------------------------------------
# Tests: complete_activity — HABIT (NEUTRAL)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_neutral_habit_performed(
    auth_client: AsyncClient,
    db_session: AsyncSession,
    test_user: User,
    test_neutral_habit: Habit,
):
    """Performing a neutral habit gives exp and gold."""
    response = await auth_client.post(
        f"/api/v1/users/{test_user.id}/complete-activity",
        json={
            "activity_type": "habit",
            "activity_id": test_neutral_habit.id,
            "performed": True,
        },
    )
    assert response.status_code == 200
    data = response.json()

    # SMALL, NEUTRAL: 5 * 1.0 * 1.0 = 5 exp, 5 * 0.3 = 1 gold
    assert data["exp_gained"] == 5
    assert data["gold_gained"] == 1


@pytest.mark.asyncio
async def test_neutral_habit_not_performed_fails(
    auth_client: AsyncClient,
    db_session: AsyncSession,
    test_user: User,
    test_neutral_habit: Habit,
):
    """Not performing a neutral habit marks it FAILED and resets streak."""
    test_neutral_habit.streak = 2
    await db_session.commit()

    response = await auth_client.post(
        f"/api/v1/users/{test_user.id}/complete-activity",
        json={
            "activity_type": "habit",
            "activity_id": test_neutral_habit.id,
            "performed": False,
        },
    )
    assert response.status_code == 200

    await db_session.refresh(test_neutral_habit)
    assert test_neutral_habit.streak == 0
    assert test_neutral_habit.status == HabitStatus.FAILED


# ---------------------------------------------------------------------------
# Tests: complete_activity — invalid activity_type
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_complete_activity_invalid_type(
    auth_client: AsyncClient,
    test_user: User,
):
    """Invalid activity_type returns 400."""
    response = await auth_client.post(
        f"/api/v1/users/{test_user.id}/complete-activity",
        json={"activity_type": "dungeon", "activity_id": 1},
    )
    assert response.status_code == 400
    assert "activity_type" in response.json()["detail"].lower()


# ---------------------------------------------------------------------------
# Tests: reset_daily_tasks
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_reset_daily_tasks(
    auth_client: AsyncClient,
    db_session: AsyncSession,
    test_user: User,
    test_daily_task: Task,
    test_task: Task,
):
    """Daily tasks should be reset to TODO; regular tasks should be unaffected."""
    test_daily_task.status = TaskStatus.COMPLETED
    test_task.status = TaskStatus.COMPLETED
    await db_session.commit()

    response = await auth_client.post(f"/api/v1/users/{test_user.id}/reset-daily-tasks")
    assert response.status_code == 200

    await db_session.refresh(test_daily_task)
    await db_session.refresh(test_task)
    assert test_daily_task.status == TaskStatus.TODO
    assert test_task.status == TaskStatus.COMPLETED  # unchanged


# ---------------------------------------------------------------------------
# Tests: add_to_inventory
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_add_item_to_inventory(
    auth_client: AsyncClient,
    db_session: AsyncSession,
    test_user: User,
    test_armor_item: Item,
):
    """Adding a new item to inventory creates an InventoryItem with quantity 1."""
    response = await auth_client.post(
        f"/api/v1/users/{test_user.id}/inventory",
        json={"item_id": test_armor_item.id, "quantity": 1},
    )
    assert response.status_code == 201
    data = response.json()
    assert data["item_id"] == test_armor_item.id
    assert data["quantity"] == 1


@pytest.mark.asyncio
async def test_add_same_item_increases_quantity(
    auth_client: AsyncClient,
    db_session: AsyncSession,
    test_user: User,
    test_armor_item: Item,
):
    """Adding the same item twice stacks the quantity."""
    await auth_client.post(
        f"/api/v1/users/{test_user.id}/inventory",
        json={"item_id": test_armor_item.id, "quantity": 1},
    )
    response = await auth_client.post(
        f"/api/v1/users/{test_user.id}/inventory",
        json={"item_id": test_armor_item.id, "quantity": 2},
    )
    assert response.status_code == 201
    assert response.json()["quantity"] == 3


@pytest.mark.asyncio
async def test_add_nonexistent_item_to_inventory(
    auth_client: AsyncClient,
    test_user: User,
):
    """Adding a non-existent item returns 404."""
    response = await auth_client.post(
        f"/api/v1/users/{test_user.id}/inventory",
        json={"item_id": 99999, "quantity": 1},
    )
    assert response.status_code == 404


# ---------------------------------------------------------------------------
# Tests: remove_from_inventory
# ---------------------------------------------------------------------------


@pytest_asyncio.fixture
async def user_with_inventory_item(
    db_session: AsyncSession,
    test_user: User,
    test_armor_item: Item,
) -> tuple[User, InventoryItem]:
    """User with 3 armor items in inventory."""
    print("\n--- user_with_inventory_item fixture start ---")
    print(f"test_user.id: {test_user.id}")
    print(f"test_armor_item.id: {test_armor_item.id}")
    inv = InventoryItem(user_id=test_user.id, item_id=test_armor_item.id, quantity=3)
    db_session.add(inv)
    await db_session.commit()
    await db_session.refresh(inv)
    await db_session.refresh(test_user)  # Explicitly refresh the user object
    print(
        f"Created InventoryItem: inv.id={inv.id}, user_id={inv.user_id}, item_id={inv.item_id}, quantity={inv.quantity}"
    )
    print("--- user_with_inventory_item fixture end ---\n")
    return test_user, inv


@pytest.mark.asyncio
async def test_remove_item_reduces_quantity(
    auth_client: AsyncClient,
    db_session: AsyncSession,
    user_with_inventory_item: tuple,
    test_armor_item: Item,
):
    """Removing fewer items than available reduces quantity."""
    user, inv = user_with_inventory_item
    print("\n--- test_remove_item_reduces_quantity test start ---")
    print(f"API Call: DELETE /api/v1/users/{user.id}/inventory/{test_armor_item.id}")
    print(f"user.id from test: {user.id}")
    print(f"test_armor_item.id from test: {test_armor_item.id}")
    response = await auth_client.delete(
        f"/api/v1/users/{user.id}/inventory/{test_armor_item.id}",
        params={"quantity": 2},
    )
    assert response.status_code == 200

    await db_session.refresh(inv)
    assert inv.quantity == 1
    print("--- test_remove_item_reduces_quantity test end ---\n")


@pytest.mark.asyncio
async def test_remove_all_items_deletes_inventory_entry(
    auth_client: AsyncClient,
    db_session: AsyncSession,
    user_with_inventory_item: tuple,
    test_armor_item: Item,
):
    """Removing all items deletes the InventoryItem record."""
    user, inv = user_with_inventory_item
    response = await auth_client.delete(
        f"/api/v1/users/{user.id}/inventory/{test_armor_item.id}",
        params={"quantity": 3},
    )
    assert response.status_code == 200

    result = await db_session.get(InventoryItem, inv.id)
    assert result is None


@pytest.mark.asyncio
async def test_remove_more_than_available_returns_error(
    auth_client: AsyncClient,
    user_with_inventory_item: tuple,
    test_armor_item: Item,
):
    """Removing more items than available returns 400."""
    user, _ = user_with_inventory_item
    response = await auth_client.delete(
        f"/api/v1/users/{user.id}/inventory/{test_armor_item.id}",
        params={"quantity": 99},
    )
    assert response.status_code == 400
    assert "not enough" in response.json()["detail"].lower()


# ---------------------------------------------------------------------------
# Tests: equip_item
# ---------------------------------------------------------------------------


@pytest_asyncio.fixture
async def user_with_helmet_in_inventory(
    db_session: AsyncSession,
    test_user: User,
    test_armor_item: Item,
) -> tuple[User, InventoryItem]:
    inv = InventoryItem(user_id=test_user.id, item_id=test_armor_item.id, quantity=1)
    db_session.add(inv)
    await db_session.commit()
    await db_session.refresh(inv)
    return test_user, inv


@pytest.mark.asyncio
async def test_equip_item_from_inventory(
    auth_client: AsyncClient,
    db_session: AsyncSession,
    user_with_helmet_in_inventory: tuple,
    test_armor_item: Item,
):
    """Equipping an item moves it from inventory to equipped slot."""
    user, inv = user_with_helmet_in_inventory
    response = await auth_client.post(
        f"/api/v1/users/{user.id}/equip",
        json={"item_id": test_armor_item.id, "slot": SlotType.HELMET.value},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["item_id"] == test_armor_item.id
    assert data["slot"] == SlotType.HELMET.value

    result = await db_session.get(InventoryItem, inv.id)
    assert result is None  # consumed from inventory


@pytest.mark.asyncio
async def test_equip_item_wrong_slot_type(
    auth_client: AsyncClient,
    user_with_helmet_in_inventory: tuple,
    test_armor_item: Item,
):
    """Equipping armor in a weapon slot returns 400."""
    user, _ = user_with_helmet_in_inventory
    response = await auth_client.post(
        f"/api/v1/users/{user.id}/equip",
        json={"item_id": test_armor_item.id, "slot": SlotType.WEAPON.value},
    )
    assert response.status_code == 400
    assert "cannot equip" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_equip_item_not_in_inventory(
    auth_client: AsyncClient,
    test_user: User,
    test_armor_item: Item,
):
    """Equipping an item not in inventory returns 400."""
    response = await auth_client.post(
        f"/api/v1/users/{test_user.id}/equip",
        json={"item_id": test_armor_item.id, "slot": SlotType.HELMET.value},
    )
    assert response.status_code == 400
    assert "not in inventory" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_equip_replaces_existing_item_in_slot(
    auth_client: AsyncClient,
    db_session: AsyncSession,
    test_user: User,
    test_armor_item: Item,
):
    """Equipping a new item in an occupied slot unequips the old one back to inventory."""
    # Put 2 helmets in inventory
    inv = InventoryItem(user_id=test_user.id, item_id=test_armor_item.id, quantity=2)
    db_session.add(inv)
    await db_session.commit()

    # Equip the first
    await auth_client.post(
        f"/api/v1/users/{test_user.id}/equip",
        json={"item_id": test_armor_item.id, "slot": SlotType.HELMET.value},
    )

    # Add another helmet to inventory (simulating a different item; reuse same for simplicity)
    inv2 = InventoryItem(user_id=test_user.id, item_id=test_armor_item.id, quantity=1)
    db_session.add(inv2)
    await db_session.commit()

    # Equip again — should replace and send old back to inventory
    response = await auth_client.post(
        f"/api/v1/users/{test_user.id}/equip",
        json={"item_id": test_armor_item.id, "slot": SlotType.HELMET.value},
    )
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_equip_nonexistent_item(
    auth_client: AsyncClient,
    test_user: User,
):
    """Equipping a non-existent item returns 404."""
    response = await auth_client.post(
        f"/api/v1/users/{test_user.id}/equip",
        json={"item_id": 99999, "slot": SlotType.HELMET.value},
    )
    assert response.status_code == 404


# ---------------------------------------------------------------------------
# Tests: unequip_item
# ---------------------------------------------------------------------------


@pytest_asyncio.fixture
async def user_with_equipped_helmet(
    db_session: AsyncSession,
    test_user: User,
    test_armor_item: Item,
) -> tuple[User, EquippedItem]:
    equipped = EquippedItem(
        user_id=test_user.id, item_id=test_armor_item.id, slot=SlotType.HELMET
    )
    db_session.add(equipped)
    await db_session.commit()
    await db_session.refresh(equipped)
    return test_user, equipped


@pytest.mark.asyncio
async def test_unequip_item_moves_to_inventory(
    auth_client: AsyncClient,
    db_session: AsyncSession,
    user_with_equipped_helmet: tuple,
    test_armor_item: Item,
):
    """Unequipping an item returns it to the inventory."""
    user, equipped = user_with_equipped_helmet
    response = await auth_client.post(
        f"/api/v1/users/{user.id}/unequip",
        json={"slot": SlotType.HELMET.value},
    )
    assert response.status_code == 200

    result = await db_session.get(EquippedItem, equipped.id)
    assert result is None  # removed from equipped

    from sqlalchemy import select

    from apps.models.user import InventoryItem as InvModel

    stmt = select(InvModel).where(
        InvModel.user_id == user.id, InvModel.item_id == test_armor_item.id
    )
    inv_result = await db_session.execute(stmt)
    inv = inv_result.scalar_one_or_none()
    assert inv is not None
    assert inv.quantity == 1


@pytest.mark.asyncio
async def test_unequip_empty_slot_returns_404(
    auth_client: AsyncClient,
    test_user: User,
):
    """Unequipping from an empty slot returns 404."""
    response = await auth_client.post(
        f"/api/v1/users/{test_user.id}/unequip",
        json={"slot": SlotType.WEAPON.value},
    )
    assert response.status_code == 404
    assert "no item equipped" in response.json()["detail"].lower()


# ---------------------------------------------------------------------------
# Tests: get_user_with_relations
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_user_with_relations(
    auth_client: AsyncClient,
    db_session: AsyncSession,
    test_user: User,
    test_task: Task,
    test_positive_habit: Habit,
):
    """User detail endpoint returns related tasks, habits, and other relations."""
    response = await auth_client.get(f"/api/v1/users/{test_user.id}/details")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == test_user.id
    assert "tasks" in data
    assert "habits" in data
    assert len(data["tasks"]) >= 1
    assert len(data["habits"]) >= 1


@pytest.mark.asyncio
async def test_get_user_with_relations_not_found(auth_client: AsyncClient):
    """Requesting details for non-existent user returns 404."""
    response = await auth_client.get("/api/v1/users/99999/details")
    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


# ---------------------------------------------------------------------------
# Tests: daily cron rollover
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_cron_missed_daily_damages_and_resets(
    auth_client: AsyncClient,
    db_session: AsyncSession,
    test_user: User,
    test_daily_task: Task,
):
    """A daily left un-completed costs HP and is reset to TODO for the new day."""
    test_user.health_points = 100
    test_user.last_cron_at = None
    test_daily_task.status = TaskStatus.TODO
    await db_session.commit()

    response = await auth_client.post(f"/api/v1/users/{test_user.id}/cron")
    assert response.status_code == 200
    data = response.json()
    assert data["ran"] is True
    assert data["missed_dailies"] == 1
    assert data["health_lost"] == 10  # SMALL daily: 10 * 1.0
    assert data["current_health"] == 90
    assert data["died"] is False

    await db_session.refresh(test_daily_task)
    assert test_daily_task.status == TaskStatus.TODO


@pytest.mark.asyncio
async def test_cron_completed_daily_no_damage(
    auth_client: AsyncClient,
    db_session: AsyncSession,
    test_user: User,
    test_daily_task: Task,
):
    """A completed daily is reset without any HP damage."""
    test_user.health_points = 100
    test_user.last_cron_at = None
    test_daily_task.status = TaskStatus.COMPLETED
    await db_session.commit()

    response = await auth_client.post(f"/api/v1/users/{test_user.id}/cron")
    assert response.status_code == 200
    data = response.json()
    assert data["missed_dailies"] == 0
    assert data["health_lost"] == 0
    assert data["current_health"] == 100

    await db_session.refresh(test_daily_task)
    assert test_daily_task.status == TaskStatus.TODO


@pytest.mark.asyncio
async def test_cron_is_idempotent_within_day(
    auth_client: AsyncClient,
    db_session: AsyncSession,
    test_user: User,
    test_daily_task: Task,
):
    """Running cron a second time the same UTC day is a no-op."""
    test_user.health_points = 50
    test_user.last_cron_at = datetime.now(timezone.utc)
    test_daily_task.status = TaskStatus.TODO
    await db_session.commit()

    response = await auth_client.post(f"/api/v1/users/{test_user.id}/cron")
    assert response.status_code == 200
    data = response.json()
    assert data["ran"] is False
    assert data["health_lost"] == 0
    assert data["current_health"] == 50


@pytest.mark.asyncio
async def test_cron_missed_daily_can_trigger_death(
    auth_client: AsyncClient,
    db_session: AsyncSession,
    test_user: User,
    test_daily_task: Task,
):
    """Enough missed-daily damage to reach 0 HP triggers the death penalty."""
    test_user.health_points = 5
    test_user.gold = 100
    test_user.experience = 20  # level 5
    test_user.last_cron_at = None
    test_daily_task.status = TaskStatus.TODO
    await db_session.commit()

    response = await auth_client.post(f"/api/v1/users/{test_user.id}/cron")
    assert response.status_code == 200
    data = response.json()
    assert data["died"] is True
    assert data["current_health"] == 100

    await db_session.refresh(test_user)
    assert test_user.gold == 0
    assert test_user.experience == 9  # dropped from level 5 to level 4


# ---------------------------------------------------------------------------
# Tests: derived character stats from equipped items
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_user_stats_sum_equipped_items(
    auth_client: AsyncClient,
    db_session: AsyncSession,
    test_user: User,
):
    """GET /stats sums attack/defense/pet_power across all equipped items."""
    sword = Item(name="Sword", item_type=ItemType.WEAPON, attack=10, defense=1)
    armor = Item(name="Plate", item_type=ItemType.ARMOR, attack=0, defense=5)
    pet = Item(name="Dragon", item_type=ItemType.PET, pet_power=7)
    db_session.add_all([sword, armor, pet])
    await db_session.commit()

    db_session.add_all(
        [
            EquippedItem(user_id=test_user.id, item_id=sword.id, slot=SlotType.WEAPON),
            EquippedItem(user_id=test_user.id, item_id=armor.id, slot=SlotType.ARMOR),
            EquippedItem(user_id=test_user.id, item_id=pet.id, slot=SlotType.PET),
        ]
    )
    await db_session.commit()

    response = await auth_client.get(f"/api/v1/users/{test_user.id}/stats")
    assert response.status_code == 200
    data = response.json()
    assert data["attack"] == 10
    assert data["defense"] == 6
    assert data["pet_power"] == 7


@pytest.mark.asyncio
async def test_user_stats_zero_when_nothing_equipped(
    auth_client: AsyncClient,
    test_user: User,
):
    """With no equipment the derived stats are all zero."""
    response = await auth_client.get(f"/api/v1/users/{test_user.id}/stats")
    assert response.status_code == 200
    data = response.json()
    assert data["attack"] == 0
    assert data["defense"] == 0
    assert data["pet_power"] == 0
    assert data["level"] >= 1
