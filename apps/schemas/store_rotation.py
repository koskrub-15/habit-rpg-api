from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, model_validator

from apps.models.item import ItemTheme, Rarity
from apps.schemas.base import BaseSchemaResponse, SimpleBaseSchemaCreate
from apps.schemas.item import ItemResponseShort


class ShopItemCreate(SimpleBaseSchemaCreate):
    item_id: int
    price: int
    rarity: Rarity = Rarity.COMMON
    stock: Optional[int] = 1
    available_from: Optional[datetime] = None
    available_until: Optional[datetime] = None


class ShopItemUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    item_id: Optional[int] = None
    price: Optional[int] = None
    rarity: Optional[Rarity] = None
    stock: Optional[int] = None
    available_from: Optional[datetime] = None
    available_until: Optional[datetime] = None
    model_config = ConfigDict(from_attributes=True)


class ShopItemResponseShort(BaseSchemaResponse):
    item_id: int
    price: int
    rarity: Rarity
    stock: Optional[int] = None


class ShopItemResponse(ShopItemResponseShort):
    item: Optional[ItemResponseShort] = None
    available_from: Optional[datetime] = None
    available_until: Optional[datetime] = None


class ShopRotationCreate(SimpleBaseSchemaCreate):
    start_date: datetime
    end_date: datetime
    theme: Optional[ItemTheme] = None

    @model_validator(mode="after")
    def validate_dates(self) -> "ShopRotationCreate":
        if self.end_date <= self.start_date:
            raise ValueError("end_date must be after start_date")
        return self


class ShopRotationUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    theme: Optional[ItemTheme] = None
    model_config = ConfigDict(from_attributes=True)


class ShopRotationResponseShort(BaseSchemaResponse):
    start_date: datetime
    end_date: datetime
    theme: Optional[ItemTheme] = None


class ShopRotationResponse(ShopRotationResponseShort):
    pass


class ShopRotationItemCreate(SimpleBaseSchemaCreate):
    rotation_id: int
    shop_item_id: int
    is_random_common: bool = True
    is_themed: bool = False
    slot_in_display: Optional[int] = None


class ShopRotationItemUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    is_random_common: Optional[bool] = None
    is_themed: Optional[bool] = None
    slot_in_display: Optional[int] = None
    model_config = ConfigDict(from_attributes=True)


class ShopRotationItemResponseShort(BaseSchemaResponse):
    rotation_id: int
    shop_item_id: int
    is_random_common: bool
    is_themed: bool
    slot_in_display: Optional[int] = None


class ShopRotationItemResponse(ShopRotationItemResponseShort):
    pass


class CurrentShopItem(BaseModel):
    slot_in_display: Optional[int] = None
    is_random_common: bool
    is_themed: bool
    shop_item: Optional[ShopItemResponse] = None
    model_config = ConfigDict(from_attributes=True)


class CurrentShopResponse(BaseModel):
    rotation: Optional[ShopRotationResponseShort] = None
    items: List[CurrentShopItem] = []
    model_config = ConfigDict(from_attributes=True)
