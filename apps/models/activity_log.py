from sqlalchemy import Column, Enum, ForeignKey, Integer, String
from sqlalchemy.orm import relationship

from apps.core.enums import ActivityType
from apps.db.base import MinimalBase


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
