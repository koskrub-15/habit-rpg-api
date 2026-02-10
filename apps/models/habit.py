import enum
from datetime import datetime

from sqlalchemy import Column, DateTime, Enum, ForeignKey, Integer, String
from sqlalchemy.orm import relationship

from apps.db.base import Base
from apps.models.task import Size


class HabitType(enum.Enum):
    POSITIVE = "POSITIVE"
    NEGATIVE = "NEGATIVE"
    NEUTRAL = "NEUTRAL"


class HabitStatus(enum.Enum):
    TODO = "TODO"
    FAILED = "FAILED"
    COMPLETED = "COMPLETED"


class Habit(Base):
    __tablename__ = "habits"

    description = Column(String(500), nullable=True)

    habit_type = Column(Enum(HabitType), default="NEUTRAL")
    habit_size = Column(Enum(Size), default=Size.SMALL)
    overfullfillment = Column(Integer, default=0)
    status = Column(Enum(HabitStatus), default=HabitStatus.TODO)
    streak = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, onupdate=datetime.utcnow)

    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    user = relationship("User", back_populates="habits")

    def __repr__(self):
        return f"<Habit(title={self.name}, habit_type={self.habit_type}, status={self.status})>"
