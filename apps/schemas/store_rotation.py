from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel

from apps.db.base import BaseSchemaResponse, SimpleBaseSchemaCreate
from apps.models.item import ItemTheme, Rarity


class ShopItemCreate(SimpleBaseSchemaCreate):
    item_id: int
    price: int
    rarity: Optional[Rarity] = Rarity.COMMON
    stock: Optional[int] = 1
    available_from: Optional[datetime] = None
    available_until: Optional[datetime] = None


class ShopItemUpdate(BaseModel):
    name: Optional[str] = None
    item_id: Optional[int] = None
    price: Optional[int] = None
    rarity: Optional[Rarity] = None
    stock: Optional[int] = None
    available_from: Optional[datetime] = None
    available_until: Optional[datetime] = None


class ShopItemResponseShort(BaseSchemaResponse):
    price: int
    rarity: Rarity


class ShopItemResponse(ShopItemResponseShort):
    item: "ItemResponseShort"
    stock: Optional[int] = None
    available_from: Optional[datetime] = None
    available_until: Optional[datetime] = None
    shop_rotation_items: List["ShopRotationItemResponseShort"] = []


class ShopRotationCreate(SimpleBaseSchemaCreate):
    start_date: datetime
    end_date: datetime
    theme: Optional[ItemTheme] = None


class ShopRotationUpdate(BaseModel):
    name: Optional[str] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    theme: Optional[ItemTheme] = None


class ShopRotationResponseShort(BaseSchemaResponse):
    start_date: datetime
    end_date: datetime
    theme: Optional[ItemTheme] = None


class ShopRotationResponse(ShopRotationResponseShort):
    rotation_items: List["ShopRotationItemResponseShort"] = []


class ShopRotationItemCreate(SimpleBaseSchemaCreate):
    rotation_id: int
    shop_item_id: int
    is_random_common: Optional[bool] = False
    is_themed: Optional[bool] = False
    slot_in_display: Optional[int] = None


class ShopRotationItemUpdate(BaseModel):
    name: Optional[str] = None
    rotation_id: Optional[int] = None
    shop_item_id: Optional[int] = None
    is_random_common: Optional[bool] = None
    is_themed: Optional[bool] = None
    slot_in_display: Optional[int] = None


class ShopRotationItemResponseShort(BaseSchemaResponse):
    rotation_id: int
    shop_item_id: int


class ShopRotationItemResponse(ShopRotationItemResponseShort):
    is_random_common: bool
    is_themed: bool
    slot_in_display: Optional[int] = None
    shop_rotation: "ShopRotationResponseShort"
    shop_item: "ShopItemResponseShort"
