from sqlalchemy import Column, Enum, Integer
from sqlalchemy.orm import relationship

from apps.core.enums import ItemTheme, ItemType, Rarity
from apps.db.base import Base
from apps.models.achievement import reward_item_table


class Item(Base):
    __tablename__ = "items"

    defense = Column(Integer, default=0)
    attack = Column(Integer, default=0)
    pet_power = Column(Integer, default=0)
    heal_amount = Column(Integer, default=0)
    required_level = Column(Integer, default=0)
    rarity = Column(Enum(Rarity), default=Rarity.COMMON)
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
