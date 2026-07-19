from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, ConfigDict, Field

from apps.models.item import ItemTheme, ItemType, Rarity
from apps.schemas.base import BaseSchemaResponse, SimpleBaseSchemaCreate


class ItemCreate(SimpleBaseSchemaCreate):
    item_type: ItemType
    defense: int = Field(default=0, ge=0)
    attack: int = Field(default=0, ge=0)
    pet_power: int = Field(default=0, ge=0)
    heal_amount: int = Field(default=0, ge=0)
    required_level: int = Field(default=0, ge=0)
    rarity: Rarity = Rarity.COMMON
    available_in_shop: bool = False
    theme: ItemTheme = ItemTheme.COMMON


class ItemUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    item_type: Optional[ItemType] = None
    defense: Optional[int] = None
    attack: Optional[int] = None
    pet_power: Optional[int] = None
    heal_amount: Optional[int] = None
    required_level: Optional[int] = None
    rarity: Optional[Rarity] = None
    available_in_shop: Optional[bool] = None
    theme: Optional[ItemTheme] = None
    model_config = ConfigDict(from_attributes=True)


class ItemResponseShort(BaseSchemaResponse):
    item_type: ItemType
    rarity: Rarity
    attack: int = 0
    defense: int = 0


class ItemResponse(ItemResponseShort):
    pet_power: int = 0
    heal_amount: int = 0
    required_level: int = 0
    available_in_shop: bool = False
    theme: ItemTheme = ItemTheme.COMMON


class UseItemResponse(BaseModel):
    item_id: int
    health_restored: int
    current_health: int
    model_config = ConfigDict(from_attributes=True)


class SellItemResponse(BaseModel):
    item_id: int
    gold_earned: int
    new_gold: int
    model_config = ConfigDict(from_attributes=True)
