from sqlalchemy import Column, ForeignKey, Integer, String, Table
from sqlalchemy.orm import relationship

from apps.db.base import Base, SimpleBase


class Achievement(Base):
    __tablename__ = "achievements"
    condition_type = Column(String(50), nullable=False)
    condition_value = Column(Integer, nullable=False)

    users = relationship(
        "User", secondary="user_achievements", back_populates="achievements"
    )
    rewards = relationship(
        "Reward", secondary="reward_achievement", back_populates="achievements"
    )


# how to work with achievements:
# def check_achievement(user, achievement):
#     if achievement.condition_type == "points":
#         return user.points >= achievement.condition_value
#     elif achievement.condition_type == "streak":
#         return user.streak >= achievement.condition_value
#     elif achievement.condition_type == "days":
#         return user.days >= achievement.condition_value
#     else:
#         raise ValueError(f"Unknown condition type: {achievement.condition_type}")


user_achievement_table = Table(
    "user_achievements",
    Base.metadata,
    Column("user_id", Integer, ForeignKey("users.id"), primary_key=True),
    Column("achievement_id", Integer, ForeignKey("achievements.id"), primary_key=True),
)


class Reward(SimpleBase):
    __tablename__ = "rewards"
    gold = Column(Integer, nullable=False)
    experience = Column(Integer, nullable=False)
    health_points = Column(Integer, nullable=False)

    items = relationship("Item", secondary="reward_item", back_populates="rewards")
    achievements = relationship(
        "Achievement", secondary="reward_achievement", back_populates="rewards"
    )


reward_item_table = Table(
    "reward_item",
    Base.metadata,
    Column("reward_id", Integer, ForeignKey("rewards.id"), primary_key=True),
    Column("item_id", Integer, ForeignKey("items.id"), primary_key=True),
)

reward_achievement_table = Table(
    "reward_achievement",
    Base.metadata,
    Column("reward_id", Integer, ForeignKey("rewards.id"), primary_key=True),
    Column("achievement_id", Integer, ForeignKey("achievements.id"), primary_key=True),
)
