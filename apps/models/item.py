import enum
from datetime import datetime

from sqlalchemy import Column, DateTime, Enum, Integer, String, Text
from sqlalchemy.orm import relationship

from apps.db.base import Base


class ItemType(enum.Enum):
    WEAPON = "WEAPON"
    ARMOR = "ARMOR"
    ACCESSORY = "ACCESSORY"
    PET = "PET"
    CONSUMABLE = "CONSUMABLE"
    MISC = "MISC"


class Item(Base):
    __tablename__ = "items"

    description = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    item_type = Column(Enum(ItemType), nullable=False)
    defense = Column(Integer, default=0)
    attack = Column(Integer, default=0)
    pet_power = Column(Integer, default=0)

    def __repr__(self):
        return f"<Item(name={self.name}, type={self.item_type})>"
