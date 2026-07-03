import enum
from datetime import datetime, timezone

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship

from apps.db.base import Base


class NotificationType(enum.Enum):
    TASK_REMINDER = "TASK_REMINDER"
    STREAK_REMINDER = "STREAK_REMINDER"
    NEWS = "NEWS"
    FRIEND_REQUEST = "FRIEND_REQUEST"
    SYSTEM = "SYSTEM"


class Notification(Base):
    __tablename__ = "notifications"

    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    notification_type = Column(Enum(NotificationType), nullable=False)
    message = Column(String(500), nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    user = relationship("User", back_populates="notifications")

    def __repr__(self):
        return f"<Notification(id={self.id}, user_id={self.user_id}, type={self.notification_type}, created_at={self.created_at})>"


class UserNotificationPreference(Base):
    __tablename__ = "user_notification_preferences"

    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    notification_type = Column(Enum(NotificationType), nullable=False)
    is_enabled = Column(Boolean, default=False)

    user = relationship("User", back_populates="notification_preferences")

    __table_args__ = (
        UniqueConstraint(
            "user_id", "notification_type", name="_user_notification_type_uc"
        ),
    )

    def __repr__(self):
        return f"<UserNotificationPreference(user_id={self.user_id}, type={self.notification_type}, enabled={self.is_enabled})>"
