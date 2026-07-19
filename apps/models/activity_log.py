import enum

from sqlalchemy import Column, Enum, ForeignKey, Integer, String
from sqlalchemy.orm import relationship

from apps.db.base import MinimalBase


class ActivityType(enum.Enum):
    TASK_COMPLETED = "TASK_COMPLETED"
    HABIT_COMPLETED = "HABIT_COMPLETED"
    ITEM_PURCHASED = "ITEM_PURCHASED"
    ITEM_SOLD = "ITEM_SOLD"
    ITEM_USED = "ITEM_USED"
    ACHIEVEMENT_UNLOCKED = "ACHIEVEMENT_UNLOCKED"
    LEVEL_UP = "LEVEL_UP"
    DEATH = "DEATH"
    DAILY_MISSED = "DAILY_MISSED"


class ActivityLog(MinimalBase):
    __tablename__ = "activity_logs"

    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    activity_type = Column(Enum(ActivityType), nullable=False)
    description = Column(String(555), nullable=True)
    task_id = Column(Integer, ForeignKey("tasks.id"), nullable=True)
    habit_id = Column(Integer, ForeignKey("habits.id"), nullable=True)
    item_id = Column(Integer, ForeignKey("items.id"), nullable=True)
    achievement_id = Column(Integer, ForeignKey("achievements.id"), nullable=True)

    user = relationship("User")

    def __repr__(self):
        return f"<ActivityLog(user_id={self.user_id}, type={self.activity_type})>"
