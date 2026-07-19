from datetime import datetime, timezone
from typing import List, Optional, Tuple

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from apps.CRUD.base import BaseCRUD
from apps.models.store_rotation import ShopItem, ShopRotation, ShopRotationItem
from apps.schemas.store_rotation import (
    ShopItemCreate,
    ShopItemUpdate,
    ShopRotationCreate,
    ShopRotationItemCreate,
    ShopRotationItemUpdate,
    ShopRotationUpdate,
)


class CRUDShopItem(BaseCRUD[ShopItem, ShopItemCreate, ShopItemUpdate]):
    def __init__(self):
        super().__init__(model=ShopItem)


class CRUDShopRotation(BaseCRUD[ShopRotation, ShopRotationCreate, ShopRotationUpdate]):
    def __init__(self):
        super().__init__(model=ShopRotation)

    async def get_active(
        self, db: AsyncSession, *, at: Optional[datetime] = None
    ) -> Optional[ShopRotation]:
        """Return the rotation active at ``at`` (now by default).

        If several rotations overlap, the one that started most recently wins.
        """
        at = at or datetime.now(timezone.utc)
        result = await db.execute(
            select(ShopRotation)
            .where(ShopRotation.start_date <= at, ShopRotation.end_date > at)
            .order_by(ShopRotation.start_date.desc())
        )
        return result.scalars().first()

    async def get_current_shop(
        self, db: AsyncSession, *, at: Optional[datetime] = None
    ) -> Tuple[Optional[ShopRotation], List[ShopRotationItem]]:
        """Return the active rotation and its featured items (ordered by slot)."""
        at = at or datetime.now(timezone.utc)
        rotation = await self.get_active(db, at=at)
        if rotation is None:
            return None, []
        result = await db.execute(
            select(ShopRotationItem)
            .where(ShopRotationItem.rotation_id == rotation.id)
            .options(
                selectinload(ShopRotationItem.shop_item).selectinload(ShopItem.item)
            )
            .order_by(
                ShopRotationItem.slot_in_display.is_(None),
                ShopRotationItem.slot_in_display,
                ShopRotationItem.id,
            )
        )
        return rotation, list(result.scalars().all())


class CRUDShopRotationItem(
    BaseCRUD[ShopRotationItem, ShopRotationItemCreate, ShopRotationItemUpdate]
):
    def __init__(self):
        super().__init__(model=ShopRotationItem)


shop_item_crud = CRUDShopItem()
shop_rotation_crud = CRUDShopRotation()
shop_rotation_item_crud = CRUDShopRotationItem()
