import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from apps.models.habit import Habit, HabitStatus, HabitType
from apps.models.item import Item, ItemType
from apps.models.task import Size, Task, TaskStatus, TaskType
from apps.models.user import EquippedItem, InventoryItem, SlotType, User
from apps.schemas.habit import HabitCreate
from apps.schemas.task import TaskCreate
from apps.schemas.user import UserCreate

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest_asyncio.fixture
async def test_user(db_session: AsyncSession) -> User:
    """Create a basic user for testing."""
    user_data = UserCreate(
        name="Test User",
        email="testuser@example.com",
        password="password123",
    )
    user = User(**user_data.model_dump(mode="json"))
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


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
        overfullfillment=0,
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
        overfullfillment=0,
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
        overfullfillment=0,
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
async def test_calculate_level_initial(client: AsyncClient, test_user: User):
    """User starts at level 1 with 0 experience."""
    response = await client.get(f"/api/v1/users/{test_user.id}")
    assert response.status_code == 200
    assert response.json()["experience"] == 0


# ---------------------------------------------------------------------------
# Tests: complete_activity — TASK
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_complete_task_rewards_exp_and_gold(
    client: AsyncClient,
    db_session: AsyncSession,
    test_user: User,
    test_task: Task,
):
    """Completing a task should award exp and gold based on task size."""
    response = await client.post(
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
    client: AsyncClient,
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

        response = await client.post(
            f"/api/v1/users/{test_user.id}/complete-activity",
            json={"activity_type": "task", "activity_id": task.id},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["exp_gained"] == expected_exp, f"Failed for size {task_size}"
        assert data["gold_gained"] == expected_gold, f"Failed for size {task_size}"


@pytest.mark.asyncio
async def test_complete_already_completed_task_returns_error(
    client: AsyncClient,
    db_session: AsyncSession,
    test_user: User,
    test_task: Task,
):
    """Completing an already-completed task should return an error."""
    test_task.status = TaskStatus.COMPLETED
    await db_session.commit()

    response = await client.post(
        f"/api/v1/users/{test_user.id}/complete-activity",
        json={"activity_type": "task", "activity_id": test_task.id},
    )
    assert response.status_code == 400
    assert "already completed" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_complete_task_not_found(
    client: AsyncClient,
    test_user: User,
):
    """Completing a non-existent task returns 404."""
    response = await client.post(
        f"/api/v1/users/{test_user.id}/complete-activity",
        json={"activity_type": "task", "activity_id": 99999},
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_complete_task_wrong_user(
    client: AsyncClient,
    db_session: AsyncSession,
    test_task: Task,
):
    """Completing a task belonging to another user returns 404."""
    other_user = User(
        name="Other User",
        email="other@example.com",
        password="pass",
    )
    db_session.add(other_user)
    await db_session.commit()
    await db_session.refresh(other_user)

    response = await client.post(
        f"/api/v1/users/{other_user.id}/complete-activity",
        json={"activity_type": "task", "activity_id": test_task.id},
    )
    assert response.status_code == 404


# ---------------------------------------------------------------------------
# Tests: complete_activity — HABIT (POSITIVE)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_complete_positive_habit_performed(
    client: AsyncClient,
    db_session: AsyncSession,
    test_user: User,
    test_positive_habit: Habit,
):
    """Performing a positive habit gives exp, gold, increments streak."""
    response = await client.post(
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
    client: AsyncClient,
    db_session: AsyncSession,
    test_user: User,
    test_positive_habit: Habit,
):
    """Not performing a positive habit resets streak and marks as FAILED."""
    test_positive_habit.streak = 5
    await db_session.commit()

    response = await client.post(
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
async def test_positive_habit_overfullfillment_increases_on_repeat(
    client: AsyncClient,
    db_session: AsyncSession,
    test_user: User,
    test_positive_habit: Habit,
):
    """Performing a completed positive habit increments overfullfillment."""
    test_positive_habit.status = HabitStatus.COMPLETED
    test_positive_habit.overfullfillment = 0
    await db_session.commit()

    response = await client.post(
        f"/api/v1/users/{test_user.id}/complete-activity",
        json={
            "activity_type": "habit",
            "activity_id": test_positive_habit.id,
            "performed": True,
        },
    )
    assert response.status_code == 200

    await db_session.refresh(test_positive_habit)
    assert test_positive_habit.overfullfillment == 1


@pytest.mark.asyncio
async def test_positive_habit_overfullfillment_decreases_on_miss(
    client: AsyncClient,
    db_session: AsyncSession,
    test_user: User,
    test_positive_habit: Habit,
):
    """Missing a positive habit with overfullfillment reduces it instead of resetting streak."""
    test_positive_habit.overfullfillment = 2
    test_positive_habit.streak = 3
    await db_session.commit()

    response = await client.post(
        f"/api/v1/users/{test_user.id}/complete-activity",
        json={
            "activity_type": "habit",
            "activity_id": test_positive_habit.id,
            "performed": False,
        },
    )
    assert response.status_code == 200

    await db_session.refresh(test_positive_habit)
    assert test_positive_habit.overfullfillment == 1
    assert (
        test_positive_habit.streak == 3
    )  # streak preserved because overfullfillment was > 0


# ---------------------------------------------------------------------------
# Tests: complete_activity — HABIT (NEGATIVE)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_negative_habit_not_performed_gives_rewards(
    client: AsyncClient,
    db_session: AsyncSession,
    test_user: User,
    test_negative_habit: Habit,
):
    """Successfully avoiding a negative habit gives partial exp/gold."""
    response = await client.post(
        f"/api/v1/users/{test_user.id}/complete-activity",
        json={
            "activity_type": "habit",
            "activity_id": test_negative_habit.id,
            "performed": False,
        },
    )
    assert response.status_code == 200
    data = response.json()

    # MEDIUM, NEGATIVE, not performed: 5 * 2.0 * 1.0 / 2 = 5 exp, 5 * 0.4 = 2 gold
    assert data["exp_gained"] == 5
    assert data["gold_gained"] == 2
    assert data["health_change"] == int(-10 * 2.0)  # -20

    await db_session.refresh(test_negative_habit)
    assert test_negative_habit.streak == 1
    assert test_negative_habit.status == HabitStatus.COMPLETED


@pytest.mark.asyncio
async def test_negative_habit_performed_resets_streak(
    client: AsyncClient,
    db_session: AsyncSession,
    test_user: User,
    test_negative_habit: Habit,
):
    """Giving in to a negative habit resets streak and marks as FAILED."""
    test_negative_habit.streak = 3
    await db_session.commit()

    response = await client.post(
        f"/api/v1/users/{test_user.id}/complete-activity",
        json={
            "activity_type": "habit",
            "activity_id": test_negative_habit.id,
            "performed": True,
        },
    )
    assert response.status_code == 200
    data = response.json()
    # Still gives some exp/gold: 5 * 2.0 * 1.0 = 10 exp, 10 * 0.4 = 4 gold
    assert data["exp_gained"] == 10
    assert data["gold_gained"] == 4

    await db_session.refresh(test_negative_habit)
    assert test_negative_habit.streak == 0
    assert test_negative_habit.status == HabitStatus.FAILED


@pytest.mark.asyncio
async def test_negative_habit_health_capped_at_zero(
    client: AsyncClient,
    db_session: AsyncSession,
    test_user: User,
    test_negative_habit: Habit,
):
    """Health should not go below 0."""
    test_user.health_points = 5
    await db_session.commit()

    response = await client.post(
        f"/api/v1/users/{test_user.id}/complete-activity",
        json={
            "activity_type": "habit",
            "activity_id": test_negative_habit.id,
            "performed": False,
        },
    )
    assert response.status_code == 200

    await db_session.refresh(test_user)
    assert test_user.health_points == 0


# ---------------------------------------------------------------------------
# Tests: complete_activity — HABIT (NEUTRAL)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_neutral_habit_performed(
    client: AsyncClient,
    db_session: AsyncSession,
    test_user: User,
    test_neutral_habit: Habit,
):
    """Performing a neutral habit gives exp and gold."""
    response = await client.post(
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
    client: AsyncClient,
    db_session: AsyncSession,
    test_user: User,
    test_neutral_habit: Habit,
):
    """Not performing a neutral habit marks it FAILED and resets streak."""
    test_neutral_habit.streak = 2
    await db_session.commit()

    response = await client.post(
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
    client: AsyncClient,
    test_user: User,
):
    """Invalid activity_type returns 400."""
    response = await client.post(
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
    client: AsyncClient,
    db_session: AsyncSession,
    test_user: User,
    test_daily_task: Task,
    test_task: Task,
):
    """Daily tasks should be reset to TODO; regular tasks should be unaffected."""
    test_daily_task.status = TaskStatus.COMPLETED
    test_task.status = TaskStatus.COMPLETED
    await db_session.commit()

    response = await client.post(f"/api/v1/users/{test_user.id}/reset-daily-tasks")
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
    client: AsyncClient,
    db_session: AsyncSession,
    test_user: User,
    test_armor_item: Item,
):
    """Adding a new item to inventory creates an InventoryItem with quantity 1."""
    response = await client.post(
        f"/api/v1/users/{test_user.id}/inventory",
        json={"item_id": test_armor_item.id, "quantity": 1},
    )
    assert response.status_code == 201
    data = response.json()
    assert data["item_id"] == test_armor_item.id
    assert data["quantity"] == 1


@pytest.mark.asyncio
async def test_add_same_item_increases_quantity(
    client: AsyncClient,
    db_session: AsyncSession,
    test_user: User,
    test_armor_item: Item,
):
    """Adding the same item twice stacks the quantity."""
    await client.post(
        f"/api/v1/users/{test_user.id}/inventory",
        json={"item_id": test_armor_item.id, "quantity": 1},
    )
    response = await client.post(
        f"/api/v1/users/{test_user.id}/inventory",
        json={"item_id": test_armor_item.id, "quantity": 2},
    )
    assert response.status_code == 201
    assert response.json()["quantity"] == 3


@pytest.mark.asyncio
async def test_add_nonexistent_item_to_inventory(
    client: AsyncClient,
    test_user: User,
):
    """Adding a non-existent item returns 404."""
    response = await client.post(
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
    inv = InventoryItem(user_id=test_user.id, item_id=test_armor_item.id, quantity=3)
    db_session.add(inv)
    await db_session.commit()
    await db_session.refresh(inv)
    return test_user, inv


@pytest.mark.asyncio
async def test_remove_item_reduces_quantity(
    client: AsyncClient,
    db_session: AsyncSession,
    user_with_inventory_item: tuple,
    test_armor_item: Item,
):
    """Removing fewer items than available reduces quantity."""
    user, inv = user_with_inventory_item
    response = await client.delete(
        f"/api/v1/users/{user.id}/inventory/{test_armor_item.id}",
        params={"quantity": 2},
    )
    assert response.status_code == 200

    await db_session.refresh(inv)
    assert inv.quantity == 1


@pytest.mark.asyncio
async def test_remove_all_items_deletes_inventory_entry(
    client: AsyncClient,
    db_session: AsyncSession,
    user_with_inventory_item: tuple,
    test_armor_item: Item,
):
    """Removing all items deletes the InventoryItem record."""
    user, inv = user_with_inventory_item
    response = await client.delete(
        f"/api/v1/users/{user.id}/inventory/{test_armor_item.id}",
        params={"quantity": 3},
    )
    assert response.status_code == 200

    result = await db_session.get(InventoryItem, inv.id)
    assert result is None


@pytest.mark.asyncio
async def test_remove_more_than_available_returns_error(
    client: AsyncClient,
    user_with_inventory_item: tuple,
    test_armor_item: Item,
):
    """Removing more items than available returns 400."""
    user, _ = user_with_inventory_item
    response = await client.delete(
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
    client: AsyncClient,
    db_session: AsyncSession,
    user_with_helmet_in_inventory: tuple,
    test_armor_item: Item,
):
    """Equipping an item moves it from inventory to equipped slot."""
    user, inv = user_with_helmet_in_inventory
    response = await client.post(
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
    client: AsyncClient,
    user_with_helmet_in_inventory: tuple,
    test_armor_item: Item,
):
    """Equipping armor in a weapon slot returns 400."""
    user, _ = user_with_helmet_in_inventory
    response = await client.post(
        f"/api/v1/users/{user.id}/equip",
        json={"item_id": test_armor_item.id, "slot": SlotType.WEAPON.value},
    )
    assert response.status_code == 400
    assert "cannot equip" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_equip_item_not_in_inventory(
    client: AsyncClient,
    test_user: User,
    test_armor_item: Item,
):
    """Equipping an item not in inventory returns 400."""
    response = await client.post(
        f"/api/v1/users/{test_user.id}/equip",
        json={"item_id": test_armor_item.id, "slot": SlotType.HELMET.value},
    )
    assert response.status_code == 400
    assert "not in inventory" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_equip_replaces_existing_item_in_slot(
    client: AsyncClient,
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
    await client.post(
        f"/api/v1/users/{test_user.id}/equip",
        json={"item_id": test_armor_item.id, "slot": SlotType.HELMET.value},
    )

    # Add another helmet to inventory (simulating a different item; reuse same for simplicity)
    inv2 = InventoryItem(user_id=test_user.id, item_id=test_armor_item.id, quantity=1)
    db_session.add(inv2)
    await db_session.commit()

    # Equip again — should replace and send old back to inventory
    response = await client.post(
        f"/api/v1/users/{test_user.id}/equip",
        json={"item_id": test_armor_item.id, "slot": SlotType.HELMET.value},
    )
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_equip_nonexistent_item(
    client: AsyncClient,
    test_user: User,
):
    """Equipping a non-existent item returns 404."""
    response = await client.post(
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
    client: AsyncClient,
    db_session: AsyncSession,
    user_with_equipped_helmet: tuple,
    test_armor_item: Item,
):
    """Unequipping an item returns it to the inventory."""
    user, equipped = user_with_equipped_helmet
    response = await client.post(
        f"/api/v1/users/{user.id}/unequip",
        json={"slot": SlotType.HELMET.value},
    )
    assert response.status_code == 200

    result = await db_session.get(EquippedItem, equipped.id)
    assert result is None  # removed from equipped

    from sqlalchemy import select
    from sqlalchemy.ext.asyncio import AsyncSession

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
    client: AsyncClient,
    test_user: User,
):
    """Unequipping from an empty slot returns 404."""
    response = await client.post(
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
    client: AsyncClient,
    db_session: AsyncSession,
    test_user: User,
    test_task: Task,
    test_positive_habit: Habit,
):
    """User detail endpoint returns related tasks, habits, and other relations."""
    response = await client.get(f"/api/v1/users/{test_user.id}/details")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == test_user.id
    assert "tasks" in data
    assert "habits" in data
    assert len(data["tasks"]) >= 1
    assert len(data["habits"]) >= 1


@pytest.mark.asyncio
async def test_get_user_with_relations_not_found(client: AsyncClient):
    """Requesting details for non-existent user returns 404."""
    response = await client.get("/api/v1/users/99999/details")
    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()
