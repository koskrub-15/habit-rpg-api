import enum
from datetime import datetime
from typing import Optional, Union

from sqlalchemy import Column, DateTime, Enum, ForeignKey, Integer, String
from sqlalchemy.orm import relationship

from apps.db.base import Base
from apps.models.habit import Habit, HabitStatus, HabitType
from apps.models.item import Item, ItemType
from apps.models.notification import Notification, UserNotificationPreference
from apps.models.task import Size, Task, TaskStatus


class SlotType(enum.Enum):
    HELMET = "HELMET"
    ARMOR = "ARMOR"
    ACCESSORY = "ACCESSORY"
    WEAPON = "WEAPON"
    PET = "PET"


class User(Base):
    __tablename__ = "users"
    email = Column(String(255), unique=True, nullable=False)
    password = Column(String(255), nullable=False)

    last_login = Column(DateTime, default=datetime.utcnow)
    health_points = Column(Integer, default=100)
    experience = Column(Integer, default=0)
    gold = Column(Integer, default=0)

    habits = relationship("Habit", back_populates="user")
    tasks = relationship("Task", back_populates="user")
    achievements = relationship("Achievement", back_populates="user")

    # friends = relationship("User", back_populates="user")
    notifications = relationship("Notification", back_populates="user")
    notification_preferences = relationship(
        "UserNotificationPreference", back_populates="user"
    )
    equipped_items = relationship(
        "EquippedItem", back_populates="user", cascade="all, delete-orphan"
    )

    inventory_items = relationship(
        "InventoryItem", back_populates="user", cascade="all, delete-orphan"
    )

    SLOT_ITEM_MAPPING = {
        SlotType.HELMET: ItemType.ARMOR,
        SlotType.ARMOR: ItemType.ARMOR,
        SlotType.WEAPON: ItemType.WEAPON,
        SlotType.PET: ItemType.PET,
        SlotType.ACCESSORY: ItemType.MISC,
    }

    def equip_item(self, item: Item, slot: SlotType):
        """Equip an item to a specific slot."""
        if self.SLOT_ITEM_MAPPING.get(slot) != item.item_type:
            raise ValueError(
                f"Cannot equip {item.item_type.value} in {slot.value} slot"
            )

        existing = next(
            (
                equipped_item
                for equipped_item in self.equipped_items
                if equipped_item.slot == slot
            ),
            None,
        )
        if existing:
            self.unequip_item(slot)

        equipped = EquippedItem(user=self, item=item, slot=slot)
        self.equipped_items.append(equipped)

        inventory_item = next(
            (
                inventory_item
                for inventory_item in self.inventory_items
                if inventory_item.item_id == item.id
            )
        )
        if inventory_item:
            self.inventory_items.remove(inventory_item)

    def unequip_item(self, slot: SlotType):
        """unequip an item from a specific slot."""
        equipped_item = next(
            (
                equipped_item
                for equipped_item in self.equipped_items
                if equipped_item.slot == slot
            ),
            None,
        )
        if equipped_item:
            self.add_to_inventory(equipped_item.item)

            self.equipped_items.remove(equipped_item)

    def add_to_inventory(self, item: Item, quantity: int = 1):
        """add an item to the user's inventory."""
        existing = next(
            (
                inventory_item
                for inventory_item in self.inventory_items
                if inventory_item.item_id == item.id
            ),
            None,
        )
        if existing:
            existing.quantity += quantity
        else:
            self.inventory_items.append(
                InventoryItem(user=self, item=item, quantity=quantity)
            )

    def remove_from_inventory(self, item: Item, quantity: int = 1):
        inventory_item = next(
            (
                inventory_item
                for inventory_item in self.inventory_items
                if inventory_item.item_id == item.id
            ),
            None,
        )
        if inventory_item:
            if inventory_item.quantity > quantity:
                inventory_item.quantity -= quantity
            else:
                self.inventory_items.remove(inventory_item)

    def get_equipped_item(self, slot: SlotType) -> Optional[Item]:
        equipped = next(
            (
                equipped_item
                for equipped_item in self.equipped_items
                if equipped_item.slot == slot
            ),
            None,
        )
        return equipped.item if equipped else None

    def calculate_level(self):
        """Calculate the user's level based on their experience points."""
        level = 1
        while self.experience >= level * level:
            level += 1
        return level

    def reset_daily_tasks(self):
        """Reset all daily tasks for this user."""
        for task in self.tasks:
            task.reset_if_daily()

    BASE_TASK_REWARD = 10
    BASE_HABIT_REWARD = 5

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

    def complete_activity(
        self, activity: Union[Task, Habit], performed: bool = True
    ) -> dict:
        """

        Args:
            activity: Task or habit
            performed: For habits - True if you did good/didn’t do bad

        Returns:
            dict: Information about the received reward

        """

        exp_gain = 0
        gold_gain = 0
        health_change = 0

        if isinstance(activity, Task):
            if activity.status == TaskStatus.COMPLETED:
                return {"error": "Task already completed"}

            activity.status = TaskStatus.COMPLETED

            multiplier = self.SIZE_MULTIPLIERS.get(activity.task_size, 1.0)
            exp_gain = int(self.BASE_TASK_REWARD * multiplier)
            gold_gain = int(exp_gain * 0.6)

        elif isinstance(activity, Habit):
            size_mult = self.SIZE_MULTIPLIERS.get(activity.habit_size, 1.0)
            type_mult = self.HABIT_TYPE_MULTIPLIERS.get(activity.habit_type, 1.0)

            if activity.habit_type == HabitType.POSITIVE and performed:
                if (
                    activity.status == HabitStatus.COMPLETED
                    or activity.overfullfillment > 0
                ):
                    activity.overfullfillment += 1
                activity.streak += 1
                activity.status = HabitStatus.COMPLETED
                exp_gain = int(self.BASE_HABIT_REWARD * size_mult * type_mult)
                gold_gain = int(exp_gain * 0.5)

            elif activity.habit_type == HabitType.POSITIVE and not performed:
                if activity.overfullfillment > 0:
                    activity.overfullfillment -= 1
                else:
                    activity.streak = 0
                    activity.status = HabitStatus.FAILED

            elif activity.habit_type == HabitType.NEGATIVE and not performed:
                activity.streak += 1
                exp_gain = int(
                    self.BASE_HABIT_REWARD
                    * size_mult
                    * type_mult
                    / 2
                    * (activity.streak / activity.streak)
                )
                gold_gain = int(exp_gain * 0.4)
                health_change = int(-10 * size_mult)
                activity.status = HabitStatus.COMPLETED

            elif activity.habit_type == HabitType.NEGATIVE and performed:
                activity.streak = 0
                exp_gain = int(self.BASE_HABIT_REWARD * size_mult * abs(type_mult))
                gold_gain = int(exp_gain * 0.4)
                activity.status = HabitStatus.FAILED

            else:
                if performed:
                    if (
                        activity.status == HabitStatus.COMPLETED
                        or activity.overfullfillment > 0
                    ):
                        activity.overfullfillment += 1

                    exp_gain = int(self.BASE_HABIT_REWARD * size_mult * type_mult)
                    gold_gain = int(exp_gain * 0.3)
                else:
                    if activity.overfullfillment > 0:
                        activity.overfullfillment -= 1
                    else:
                        activity.streak = 0
                        activity.status = HabitStatus.FAILED

        self.experience += exp_gain
        self.health_points = max(0, min(100, self.health_points + health_change))
        self.gold += gold_gain

        return {
            "activity_type": type(activity).__name__,
            "activity_name": activity.name,
            "exp_gained": exp_gain,
            "gold_gained": gold_gain,
            "health_change": health_change,
            "new_level": self.calculate_level(),
            "current_health": self.health_points,
            "streak": activity.status if isinstance(activity, Habit) else None,
        }

    def reset_day(self):
        pass

    def __repr__(self):
        return f"<User(name={self.name}, level={self.calculate_level()})>"


class EquippedItem(Base):
    __tablename__ = "equipped_items"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    item_id = Column(Integer, ForeignKey("items.id"), nullable=False)
    slot = Column(Enum(SlotType), nullable=False)

    user = relationship("User", back_populates="equipped_items")
    item = relationship("Item")

    def __repr__(self):
        return f"<EquippedItem(slot={self.slot}, item={self.item.name})>"


class InventoryItem(Base):
    __tablename__ = "inventory_items"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    item_id = Column(Integer, ForeignKey("items.id"), nullable=False)
    quantity = Column(Integer, default=1)

    user = relationship("User", back_populates="inventory_items")
    item = relationship("Item")

    def __repr__(self):
        return f"<InventoryItem(item={self.item.name}, quantity={self.quantity})>"
