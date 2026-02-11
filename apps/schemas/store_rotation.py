from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel

from apps.db.base import BaseSchemaResponse, SimpleBaseSchemaCreate
from apps.models.item import ItemTheme, Rarity

# Import specific models to access enums if needed
# from apps.models.store import ShopItem, ShopRotation, ShopRotationItem


# --- ShopItem Schemas ---
class ShopItemCreate(SimpleBaseSchemaCreate):
    # SimpleBaseSchemaCreate provides 'name'
    item_id: int
    price: int
    rarity: Optional[Rarity] = Rarity.COMMON  # Default from model
    stock: Optional[int] = 1  # Default from model
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
    # BaseSchemaResponse provides id, name, created_at, updated_at
    price: int
    rarity: Rarity


class ShopItemResponse(ShopItemResponseShort):
    item: "ItemResponseShort"  # Forward reference to Item schema
    stock: Optional[int] = None
    available_from: Optional[datetime] = None
    available_until: Optional[datetime] = None
    shop_rotation_items: List["ShopRotationItemResponseShort"] = []


# --- ShopRotation Schemas ---
class ShopRotationCreate(SimpleBaseSchemaCreate):
    # SimpleBaseSchemaCreate provides 'name'
    start_date: datetime
    end_date: datetime
    theme: Optional[ItemTheme] = None


class ShopRotationUpdate(BaseModel):
    name: Optional[str] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    theme: Optional[ItemTheme] = None


class ShopRotationResponseShort(BaseSchemaResponse):
    # BaseSchemaResponse provides id, name, created_at, updated_at
    start_date: datetime
    end_date: datetime
    theme: Optional[ItemTheme] = None


class ShopRotationResponse(ShopRotationResponseShort):
    rotation_items: List["ShopRotationItemResponseShort"] = []


# --- ShopRotationItem Schemas ---
# Note: ShopRotationItem model inherits SimpleBase, meaning it has a 'name'.
# If you didn't intend for it to have a name, consider using a plain BaseModel
# for creation or altering your ORM model. Assuming 'name' is desired.
class ShopRotationItemCreate(SimpleBaseSchemaCreate):
    # SimpleBaseSchemaCreate provides 'name'
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
    # BaseSchemaResponse provides id, name, created_at, updated_at
    rotation_id: int
    shop_item_id: int


class ShopRotationItemResponse(ShopRotationItemResponseShort):
    is_random_common: bool
    is_themed: bool
    slot_in_display: Optional[int] = None
    shop_rotation: "ShopRotationResponseShort"
    shop_item: "ShopItemResponseShort"
