import enum
from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, Enum, ForeignKey, Integer, String
from sqlalchemy.orm import relationship

from apps.db.base import SimpleBase
from apps.models.achievement import user_achievement_table


class SlotType(enum.Enum):
    HELMET = "HELMET"
    ARMOR = "ARMOR"
    ACCESSORY = "ACCESSORY"
    WEAPON = "WEAPON"
    PET = "PET"


class FriendshipStatus(enum.Enum):
    PENDING = "PENDING"
    ACCEPTED = "ACCEPTED"
    DECLINED = "DECLINED"


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
    _equipped_items = relationship(
        "EquippedItem", back_populates="user", cascade="all, delete-orphan"
    )

    _inventory_items = relationship(
        "InventoryItem", back_populates="user", cascade="all, delete-orphan"
    )

    # Relationships for friendships
    sent_friend_requests = relationship(
        "Friendship", foreign_keys="Friendship.user_id", back_populates="user"
    )
    received_friend_requests = relationship(
        "Friendship", foreign_keys="Friendship.friend_id", back_populates="friend"
    )

    @property
    def equipped_items(self):
        return [ei.item for ei in self._equipped_items if ei.item]

    @property
    def inventory_items(self):
        return [ii.item for ii in self._inventory_items if ii.item]

    def __repr__(self):
        return f"<User(name={self.name}, email={self.email})>"


class Friendship(SimpleBase):
    __tablename__ = "friendships"

    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    friend_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    status = Column(Enum(FriendshipStatus), default=FriendshipStatus.PENDING)

    user = relationship(
        "User", foreign_keys=[user_id], back_populates="sent_friend_requests"
    )
    friend = relationship(
        "User", foreign_keys=[friend_id], back_populates="received_friend_requests"
    )

    def __repr__(self):
        return f"<Friendship(from={self.user_id}, to={self.friend_id}, status={self.status})>"


class EquippedItem(SimpleBase):
    __tablename__ = "equipped_items"

    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    item_id = Column(Integer, ForeignKey("items.id"), nullable=False)
    slot = Column(Enum(SlotType), nullable=False)

    user = relationship("User", back_populates="_equipped_items")
    item = relationship("Item")

    def __repr__(self):
        return f"<EquippedItem(slot={self.slot}, item={self.item.name})>"


class InventoryItem(SimpleBase):
    __tablename__ = "inventory_items"

    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    item_id = Column(Integer, ForeignKey("items.id"), nullable=False)
    quantity = Column(Integer, default=1)

    user = relationship("User", back_populates="_inventory_items")
    item = relationship("Item")

    def __repr__(self):
        return f"<InventoryItem(item={self.item.name}, quantity={self.quantity})>"
