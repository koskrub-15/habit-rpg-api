from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship

from apps.db.base import SimpleBase
from apps.models.item import Item, ItemTheme, Rarity


class ShopItem(SimpleBase):
    __tablename__ = "shop_items"
    item_id = Column(Integer, ForeignKey(Item.id))
    price = Column(Integer)
    rarity = Column(Enum(Rarity), default=Rarity.COMMON)
    stock = Column(Integer, nullable=True, default=1)
    # required_level = Column(Integer, default=0)
    # is_available = Column(Boolean, default=True)
    available_from = Column(DateTime, nullable=True)
    available_until = Column(DateTime, nullable=True)

    item = relationship(Item, back_populates="shop_items")
    shop_rotation_items = relationship(
        "ShopRotationItem", back_populates="shop_item", cascade="all, delete-orphan"
    )

    def __repr__(self):
        return f"<ShopItem(id={self.id}, item_id={self.item_id}, price={self.price}, rarity={self.rarity}, stock={self.stock}, available_from={self.available_from}, available_until={self.available_until}, created_at={self.created_at}, updated_at={self.updated_at})>"


class ShopRotation(SimpleBase):
    __tablename__ = "shop_rotations"
    start_date = Column(DateTime, nullable=False)
    end_date = Column(DateTime, nullable=False)
    theme = Column(Enum(ItemTheme), nullable=True)
    rotation_items = relationship(
        "ShopRotationItem", back_populates="shop_rotation", cascade="all, delete-orphan"
    )

    def __repr__(self):
        return f"<ShopRotation(id={self.id}, start_date={self.start_date}, end_date={self.end_date}, theme={self.theme})>"


class ShopRotationItem(SimpleBase):
    __tablename__ = "shop_rotation_items"
    rotation_id = Column(Integer, ForeignKey("shop_rotations.id"), nullable=False)
    shop_item_id = Column(Integer, ForeignKey("shop_items.id"), nullable=False)
    is_random_common = Column(Boolean, default=True)
    is_themed = Column(Boolean, default=False)

    __table_args__ = (
        UniqueConstraint(
            "rotation_id", "shop_item_id", name="unique_rotation_shop_item"
        ),
    )
    shop_rotation = relationship("ShopRotation", back_populates="rotation_items")
    shop_item = relationship("ShopItem", back_populates="shop_rotation_items")

    def __repr__(self):
        return f"<ShopRotationItem(id={self.id}, rotation_id={self.rotation_id}, shop_item_id={self.shop_item_id}, is_random_common={self.is_random_common}, is_themed={self.is_themed})>"
