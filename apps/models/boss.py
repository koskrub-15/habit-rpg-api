import enum

from sqlalchemy import Column, Enum, ForeignKey, Integer
from sqlalchemy.orm import relationship

from apps.db.base import MinimalBase, SimpleBase


class BossFightStatus(enum.Enum):
    ACTIVE = "ACTIVE"
    WON = "WON"
    LOST = "LOST"


class Boss(SimpleBase):
    __tablename__ = "bosses"

    max_health = Column(Integer, nullable=False, default=100)
    attack = Column(Integer, nullable=False, default=0)
    defense = Column(Integer, nullable=False, default=0)
    required_level = Column(Integer, nullable=False, default=0)
    reward_gold = Column(Integer, nullable=False, default=0)
    reward_experience = Column(Integer, nullable=False, default=0)

    fights = relationship(
        "BossFight", back_populates="boss", cascade="all, delete-orphan"
    )

    def __repr__(self):
        return f"<Boss(name={self.name}, max_health={self.max_health})>"


class BossFight(MinimalBase):
    __tablename__ = "boss_fights"

    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    boss_id = Column(Integer, ForeignKey("bosses.id"), nullable=False)
    boss_health = Column(Integer, nullable=False)
    rounds = Column(Integer, nullable=False, default=0)
    status = Column(
        Enum(BossFightStatus), nullable=False, default=BossFightStatus.ACTIVE
    )

    boss = relationship("Boss", back_populates="fights")
    user = relationship("User")

    def __repr__(self):
        return f"<BossFight(user_id={self.user_id}, boss_id={self.boss_id}, status={self.status})>"
