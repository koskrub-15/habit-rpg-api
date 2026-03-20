from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.router_generator import RouterFactory
from apps.CRUD.from_models.user import user_crud
from apps.db.session import get_db
from apps.models.user import EquippedItem
from apps.schemas.user import (
    CompleteActivityRequest,
    CompleteActivityResponse,
    EquipItemRequest,
    UnequipItemRequest,
    UpdateInventoryRequest,
    UserCreate,
    UserResponse,
    UserResponseShort,
    UserUpdate,
)

user_factory = RouterFactory(
    crud=user_crud,
    create_schema=UserCreate,
    update_schema=UserUpdate,
    response_schema=UserResponse,
    response_short_schema=UserResponseShort,
    resource_name="user",
    resource_name_plural="users",
    tag="Users",
    prefix="/users",
    with_relations_method="get_user_with_relations",
)

router = user_factory.create_router()


@router.post(
    "/{user_id}/complete-activity",
    response_model=CompleteActivityResponse,
    summary="Complete a task or habit",
)
async def complete_activity(
    user_id: int,
    body: CompleteActivityRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Mark a task or habit as complete for a user, applying rewards and effects.
    """
    return await user_crud.complete_activity(
        db,
        user_id=user_id,
        activity_type=body.activity_type,
        activity_id=body.activity_id,
        performed=body.performed,
    )


@router.post(
    "/{user_id}/reset-daily-tasks",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Reset all daily tasks for a user",
)
async def reset_daily_tasks(user_id: int, db: AsyncSession = Depends(get_db)):
    """
    Reset the status of all daily tasks for a specific user to 'TODO'.
    """
    await user_crud.reset_daily_tasks(db, user_id=user_id)
    return


@router.post(
    "/{user_id}/inventory/add",
    summary="Add an item to user's inventory",
)
async def add_to_inventory(
    user_id: int,
    body: UpdateInventoryRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Add a specified quantity of an item to a user's inventory.
    """
    await user_crud.add_to_inventory(
        db, user_id=user_id, item_id=body.item_id, quantity=body.quantity
    )
    return {"message": "Inventory updated"}


@router.post(
    "/{user_id}/inventory/remove",
    summary="Remove an item from user's inventory",
)
async def remove_from_inventory(
    user_id: int,
    body: UpdateInventoryRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Remove a specified quantity of an item from a user's inventory.
    """
    await user_crud.remove_from_inventory(
        db, user_id=user_id, item_id=body.item_id, quantity=body.quantity
    )
    return {"message": "Inventory updated"}


@router.post(
    "/{user_id}/equip-item",
    summary="Equip an item to a slot",
    response_model=UserResponse,
)
async def equip_item(
    user_id: int,
    body: EquipItemRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Equip an item from the user's inventory to a specified equipment slot.
    If an item is already in the slot, it will be unequipped and returned to the inventory.
    """
    await user_crud.equip_item(
        db, user_id=user_id, item_id=body.item_id, slot=body.slot
    )
    return await user_crud.get_user_with_relations(db, user_id)


@router.post(
    "/{user_id}/unequip-item",
    summary="Unequip an item from a slot",
    response_model=UserResponse,
)
async def unequip_item(
    user_id: int,
    body: UnequipItemRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Unequip an item from a specified equipment slot and return it to the inventory.
    """
    await user_crud.unequip_item(db, user_id=user_id, slot=body.slot)
    return await user_crud.get_user_with_relations(db, user_id)
