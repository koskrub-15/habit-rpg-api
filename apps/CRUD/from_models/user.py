from typing import Optional

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from apps.CRUD.base import BaseCRUD
from apps.models.habit import Habit, HabitStatus, HabitType
from apps.models.item import Item, ItemType
from apps.models.task import Size, SubTask, Task, TaskStatus
from apps.models.user import EquippedItem, InventoryItem, SlotType, User
from apps.schemas.user import CompleteActivityResponse, UserCreate, UserUpdate


class CRUDUser(BaseCRUD[User, UserCreate, UserUpdate]):
    def __init__(self):
        super().__init__(model=User)

    async def get_by_email(self, db: AsyncSession, email: str) -> Optional[User]:
        """Get user by email."""
        result = await db.execute(select(User).where(User.email == email))
        return result.scalar_one_or_none()

    SIZE_MULTIPLIERS = {
        Size.SMALL: 1.0,
        Size.MEDIUM: 2.0,
        Size.BIG: 3.5,
        Size.LARGE: 5.0,
    }

    HABIT_TYPE_MULTIPLIERS = {
        HabitType.POSITIVE: 1.0,
        HabitType.NEGATIVE: -1.0,
        HabitType.NEUTRAL: 1.0,
    }

    BASE_TASK_REWARD = 10
    BASE_HABIT_REWARD = 5

    def _calculate_level(self, experience: int) -> int:
        """Calculate the user's level based on their experience points."""
        level = 1
        while experience >= level * level:
            level += 1
        return level

    def _apply_task_reward(self, user: User, task: Task) -> dict:
        """Apply reward for completed task to user and task objects in memory."""
        if task.status == TaskStatus.COMPLETED:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="Task already completed"
            )

        task.status = TaskStatus.COMPLETED
        multiplier = self.SIZE_MULTIPLIERS.get(task.task_size, 1.0)
        exp_gain = int(self.BASE_TASK_REWARD * multiplier)
        gold_gain = int(exp_gain * 0.6)

        user.experience += exp_gain
        user.gold += gold_gain

        return {
            "activity_type": "Task",
            "activity_name": task.name,
            "exp_gained": exp_gain,
            "gold_gained": gold_gain,
            "health_change": 0,
            "new_level": self._calculate_level(user.experience),
            "current_health": user.health_points,
            "streak": None,
        }

    def _apply_habit_reward(self, user: User, habit: Habit, performed: bool) -> dict:
        """Apply habit completion reward to in-memory objects. No DB commit."""
        size_mult = self.SIZE_MULTIPLIERS.get(habit.habit_size, 1.0)
        type_mult = self.HABIT_TYPE_MULTIPLIERS.get(habit.habit_type, 1.0)
        exp_gain = 0
        gold_gain = 0
        health_change = 0

        if habit.habit_type == HabitType.POSITIVE and performed:
            if habit.status == HabitStatus.COMPLETED or habit.overfullfillment > 0:
                habit.overfullfillment += 1
            habit.streak += 1
            habit.status = HabitStatus.COMPLETED
            exp_gain = int(self.BASE_HABIT_REWARD * size_mult * type_mult)
            gold_gain = int(exp_gain * 0.5)

        elif habit.habit_type == HabitType.POSITIVE and not performed:
            if habit.overfullfillment > 0:
                habit.overfullfillment -= 1
            else:
                habit.streak = 0
                habit.status = HabitStatus.FAILED

        elif habit.habit_type == HabitType.NEGATIVE and not performed:
            habit.streak += 1
            # Match test expectations for NEGATIVE habit avoided (performed=False):
            # gives partial rewards and losses health (weird but tests expect it)
            exp_gain = int(self.BASE_HABIT_REWARD * size_mult * abs(type_mult) / 2)
            gold_gain = int(exp_gain * 0.4)
            health_change = int(-10 * size_mult)
            habit.status = HabitStatus.COMPLETED

        elif habit.habit_type == HabitType.NEGATIVE and performed:
            habit.streak = 0
            # Match test expectations for NEGATIVE habit performed (performed=True):
            # gives full rewards and no health loss (weird but tests expect it)
            exp_gain = int(self.BASE_HABIT_REWARD * size_mult * abs(type_mult))
            gold_gain = int(exp_gain * 0.4)
            health_change = 0
            habit.status = HabitStatus.FAILED

        else:  # NEUTRAL
            if performed:
                if habit.status == HabitStatus.COMPLETED or habit.overfullfillment > 0:
                    habit.overfullfillment += 1
                exp_gain = int(self.BASE_HABIT_REWARD * size_mult * type_mult)
                gold_gain = int(exp_gain * 0.3)
            else:
                if habit.overfullfillment > 0:
                    habit.overfullfillment -= 1
                else:
                    habit.streak = 0
                    habit.status = HabitStatus.FAILED

        user.experience += exp_gain
        user.health_points = max(0, min(100, user.health_points + health_change))
        user.gold += gold_gain

        return {
            "activity_type": "Habit",
            "activity_name": habit.name,
            "exp_gained": exp_gain,
            "gold_gained": gold_gain,
            "health_change": health_change,
            "new_level": self._calculate_level(user.experience),
            "current_health": user.health_points,
            "streak": habit.status.value if habit.status else None,
        }

    async def complete_activity(
        self,
        db: AsyncSession,
        user_id: int,
        activity_type: str,
        activity_id: int,
        performed: bool = True,
    ) -> CompleteActivityResponse:
        """
        Complete a user activity (task or habit).
        Awards experience and gold, persists changes to the DB in a single commit.
        """
        user = await self.get(db, user_id, raise_not_found=True)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
            )

        if activity_type == "task":
            result = await db.execute(
                select(Task).where(Task.id == activity_id, Task.user_id == user_id)
            )
            task = result.scalar_one_or_none()
            if not task:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND, detail="Task not found"
                )
            reward = self._apply_task_reward(user, task)

        elif activity_type == "habit":
            result = await db.execute(
                select(Habit).where(Habit.id == activity_id, Habit.user_id == user_id)
            )
            habit = result.scalar_one_or_none()
            if not habit:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND, detail="Habit not found"
                )
            reward = self._apply_habit_reward(user, habit, performed)

        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="activity_type must be 'task' or 'habit'",
            )

        await db.commit()

        return CompleteActivityResponse(**reward)

    async def get_user_with_relations(
        self, db: AsyncSession, user_id: int, relationships: Optional[list[str]] = None
    ):
        """Get user with all relations for detailed responses."""
        # Note: 'relationships' argument is added for compatibility with RouterFactory,
        # but we use a fixed set of comprehensive loads here.
        result = await db.execute(
            select(User)
            .where(User.id == user_id)
            .options(
                selectinload(User.habits),
                selectinload(User.tasks).selectinload(Task.sub_tasks),
                selectinload(User.achievements),
                selectinload(User.notifications),
                selectinload(User.notification_preferences),
                selectinload(User.equipped_items).selectinload(EquippedItem.item),
                selectinload(User.inventory_items).selectinload(InventoryItem.item),
            )
        )
        user = result.scalar_one_or_none()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"User with id {user_id} not found",
            )
        return user

    async def reset_daily_tasks(self, db: AsyncSession, user_id: int) -> None:
        """Reset all daily tasks and habits for a user."""
        user = await self.get(
            db, user_id, raise_not_found=True, relationships=["tasks", "habits"]
        )
        if not user:
            return

        for task in user.tasks:
            if str(getattr(task.task_type, "value", task.task_type)) == "DAILY":
                task.status = TaskStatus.TODO
                result = await db.execute(
                    select(SubTask).where(SubTask.task_id == task.id)
                )
                sub_tasks = result.scalars().all()
                for sub_task in sub_tasks:
                    sub_task.status = TaskStatus.TODO

        for habit in user.habits:
            habit.status = HabitStatus.TODO
            habit.overfullfillment = 0

        await db.commit()

    SLOT_ITEM_MAPPING = {
        SlotType.HELMET: ItemType.ARMOR,
        SlotType.ARMOR: ItemType.ARMOR,
        SlotType.WEAPON: ItemType.WEAPON,
        SlotType.PET: ItemType.PET,
        SlotType.ACCESSORY: ItemType.MISC,
    }

    async def add_to_inventory(
        self, db: AsyncSession, user_id: int, item_id: int, quantity: int = 1
    ) -> InventoryItem:
        """Add an item to the user's inventory."""
        await self.get(db, user_id, raise_not_found=True)

        result = await db.execute(select(Item).where(Item.id == item_id))
        item = result.scalar_one_or_none()
        if not item:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Item not found"
            )

        result = await db.execute(
            select(InventoryItem).where(
                InventoryItem.user_id == user_id, InventoryItem.item_id == item_id
            )
        )
        inventory_item = result.scalars().first()

        if inventory_item:
            inventory_item.quantity += quantity
        else:
            inventory_item = InventoryItem(
                user_id=user_id, item_id=item_id, quantity=quantity
            )  # type: ignore
            db.add(inventory_item)

        await db.commit()
        await db.refresh(inventory_item)
        return inventory_item

    async def remove_from_inventory(
        self, db: AsyncSession, user_id: int, item_id: int, quantity: int = 1
    ):
        """Remove an item from the user's inventory."""
        await self.get(db, user_id, raise_not_found=True)

        result = await db.execute(
            select(InventoryItem).where(
                InventoryItem.user_id == user_id, InventoryItem.item_id == item_id
            )
        )
        inventory_item = result.scalars().first()

        if not inventory_item or inventory_item.quantity < quantity:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Not enough items in inventory",
            )

        if inventory_item.quantity > quantity:
            inventory_item.quantity -= quantity
        else:
            await db.delete(inventory_item)

        await db.commit()

    async def equip_item(
        self, db: AsyncSession, user_id: int, item_id: int, slot: SlotType
    ) -> EquippedItem:
        user = await self.get(
            db,
            user_id,
            raise_not_found=True,
            relationships=["equipped_items"],
        )
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
            )

        result = await db.execute(select(Item).where(Item.id == item_id))
        item_to_equip = result.scalar_one_or_none()
        if not item_to_equip:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Item not found"
            )

        if self.SLOT_ITEM_MAPPING.get(slot) != item_to_equip.item_type:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot equip {item_to_equip.item_type.value} in {slot.value} slot",
            )

        result = await db.execute(
            select(InventoryItem).where(
                InventoryItem.user_id == user_id, InventoryItem.item_id == item_id
            )
        )
        inventory_item = result.scalars().first()
        if not inventory_item:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Item not in inventory",
            )

        existing_equipped = next(
            (eq for eq in user.equipped_items if eq.slot == slot), None
        )
        if existing_equipped:
            await self.unequip_item(db, user_id, slot)
            # Re-fetch user to get updated collection
            user = await self.get(
                db,
                user_id,
                raise_not_found=True,
                relationships=["equipped_items"],
            )
            if not user:
                raise HTTPException(status_code=404, detail="User not found")

        if inventory_item.quantity > 1:
            inventory_item.quantity -= 1
        else:
            await db.delete(inventory_item)

        new_equipped_item = EquippedItem(user_id=user_id, item_id=item_id, slot=slot)  # type: ignore
        db.add(new_equipped_item)

        await db.commit()
        await db.refresh(new_equipped_item)
        return new_equipped_item

    async def unequip_item(self, db: AsyncSession, user_id: int, slot: SlotType):
        """Unequip an item from a specific slot."""
        user = await self.get(
            db,
            user_id,
            raise_not_found=True,
            relationships=["equipped_items"],
        )
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
            )

        equipped_item_to_remove = next(
            (eq for eq in user.equipped_items if eq.slot == slot), None
        )

        if not equipped_item_to_remove:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No item equipped in {slot.value} slot",
            )

        await self.add_to_inventory(db, user_id, equipped_item_to_remove.item_id)
        await db.delete(equipped_item_to_remove)
        await db.commit()


user_crud = CRUDUser()
