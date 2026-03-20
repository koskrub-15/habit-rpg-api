import enum
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import Column, DateTime, Enum, ForeignKey, Integer, String
from sqlalchemy.orm import relationship

from apps.db.base import SimpleBase
from apps.models.achievement import user_achievement_table
from apps.models.item import Item, ItemType


class SlotType(enum.Enum):
    HELMET = "HELMET"
    ARMOR = "ARMOR"
    ACCESSORY = "ACCESSORY"
    WEAPON = "WEAPON"
    PET = "PET"


class User(SimpleBase):
    __tablename__ = "users"
    email = Column(String(255), unique=True, nullable=False)
    password = Column(String(255), nullable=False)
    last_login = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    health_points = Column(Integer, default=100)
    experience = Column(Integer, default=0)
    gold = Column(Integer, default=0)

    habits = relationship("Habit", back_populates="user")
    tasks = relationship("Task", back_populates="user")
    achievements = relationship(
        "Achievement", secondary=user_achievement_table, back_populates="users"
    )

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

    def __repr__(self):
        return f"<User(name={self.name}, email={self.email})>"


class EquippedItem(SimpleBase):
    __tablename__ = "equipped_items"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    item_id = Column(Integer, ForeignKey("items.id"), nullable=False)
    slot = Column(Enum(SlotType), nullable=False)

    user = relationship("User", back_populates="equipped_items")
    item = relationship("Item")

    def __repr__(self):
        return f"<EquippedItem(slot={self.slot}, item={self.item.name})>"


class InventoryItem(SimpleBase):
    __tablename__ = "inventory_items"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    item_id = Column(Integer, ForeignKey("items.id"), nullable=False)
    quantity = Column(Integer, default=1)

    user = relationship("User", back_populates="inventory_items")
    item = relationship("Item")

    def __repr__(self):
        return f"<InventoryItem(item={self.item.name}, quantity={self.quantity})>"
