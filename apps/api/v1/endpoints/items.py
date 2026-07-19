from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.deps import get_current_user
from apps.CRUD.from_models.item import item_crud
from apps.CRUD.from_models.user import user_crud
from apps.db.session import get_db
from apps.models.user import User
from apps.schemas.item import (
    ItemCreate,
    ItemResponse,
    ItemResponseShort,
    ItemUpdate,
    SellItemResponse,
    UseItemResponse,
)
from apps.api.router_generator import RouterFactory

item_factory = RouterFactory(
    crud=item_crud,
    create_schema=ItemCreate,
    update_schema=ItemUpdate,
    response_schema=ItemResponse,
    response_short_schema=ItemResponseShort,
    resource_name="item",
    resource_name_plural="items",
    tag="Items",
    prefix="/items",
    write_requires_superuser=True,
    current_user_dependency=Depends(get_current_user),
)

router = item_factory.create_router()


@router.post(
    "/{item_id}/use",
    response_model=UseItemResponse,
    summary="Use a consumable item from your inventory",
)
async def use_item(
    item_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Consume one unit of a CONSUMABLE item from the current user's inventory and
    apply its effect (restores HP by the item's heal_amount).
    """
    return await user_crud.use_item(db, user_id=current_user.id, item_id=item_id)


@router.post(
    "/{item_id}/sell",
    response_model=SellItemResponse,
    summary="Sell an item from your inventory for gold",
)
async def sell_item(
    item_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Sell one unit of an item from the current user's inventory. Refunds half the
    item's cheapest shop price as gold (a flat minimum for items sold nowhere).
    """
    return await user_crud.sell_item(db, user_id=current_user.id, item_id=item_id)
