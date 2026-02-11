import enum

from sqlalchemy import Boolean, Column, Enum, Integer
from sqlalchemy.orm import relationship

from apps.db.base import Base
from apps.models.achievement import reward_item_table


class Rarity(enum.Enum):
    COMMON = "COMMON"
    UNCOMMON = "UNCOMMON"
    RARE = "RARE"
    EPIC = "EPIC"
    LEGENDARY = "LEGENDARY"


class ItemType(enum.Enum):
    WEAPON = "WEAPON"
    ARMOR = "ARMOR"
    ACCESSORY = "ACCESSORY"
    PET = "PET"
    CONSUMABLE = "CONSUMABLE"
    MISC = "MISC"


class ItemTheme(enum.Enum):
    COMMON = "COMMON"
    WINTER = "WINTER"
    SUMMER = "SUMMER"
    SPRING = "SPRING"
    FALL = "FALL"
    ASIAN = "ASIAN"
    MEDIEVAL = "MEDIEVAL"
    HALLOWEEN = "HALLOWEEN"
    CHRISTMAS = "CHRISTMAS"
    # another


class Item(Base):
    __tablename__ = "items"

    defense = Column(Integer, default=0)
    attack = Column(Integer, default=0)
    pet_power = Column(Integer, default=0)
    required_level = Column(Integer, default=0)
    rarity = Column(Enum(Rarity), default=Rarity.COMMON)
    available_in_shop = Column(Boolean, default=False)
    theme = Column(Enum(ItemTheme), default=ItemTheme.COMMON)
    item_type = Column(Enum(ItemType), nullable=False)

    rewards = relationship(
        "Reward", secondary=reward_item_table, back_populates="items"
    )

    shop_items = relationship(
        "ShopItem", back_populates="item", cascade="all, delete-orphan"
    )

    def __repr__(self):
        return f"<Item(name={self.name}, type={self.item_type})>"
