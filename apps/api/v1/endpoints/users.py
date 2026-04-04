from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.router_generator import RouterFactory
from apps.CRUD.from_models.user import user_crud
from apps.db.session import get_db
from apps.schemas.user import (
    CompleteActivityRequest,
    CompleteActivityResponse,
    EquipItemRequest,
    EquippedItemResponse,
    InventoryItemResponse,
    UnequipItemRequest,
    UpdateInventoryRequest,
    UserCreate,
    UserResponse,
    UserResponseShort,
    UserUpdate,
)

router = APIRouter(prefix="/users", tags=["Users"])

user_factory = RouterFactory(
    crud=user_crud,
    create_schema=UserCreate,
    update_schema=UserUpdate,
    response_schema=UserResponse,
    response_short_schema=UserResponseShort,
    resource_name="user",
    resource_name_plural="users",
    tag="Users",
    prefix="",
    with_relations_method="get_user_with_relations",
)

# Generate standard CRUD endpoints
user_crud_router = user_factory.create_router()
router.include_router(user_crud_router)


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
    Mark a task as completed or record a habit performance.
    Awards experience and gold to the user.
    """
    return await user_crud.complete_activity(
        db,
        user_id=user_id,
        activity_type=body.activity_type,
        activity_id=body.activity_id,
        performed=body.performed,
    )


@router.post(
    "/{user_id}/reset-daily",
    status_code=status.HTTP_200_OK,
    summary="Reset all daily tasks for a user",
)
async def reset_daily(user_id: int, db: AsyncSession = Depends(get_db)):
    """
    Reset the status of all daily tasks and habits for a specific user to 'TODO'.
    """
    await user_crud.reset_daily_tasks(db, user_id=user_id)
    return


@router.post(
    "/{user_id}/inventory",
    response_model=InventoryItemResponse,
    status_code=status.HTTP_201_CREATED,
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
    inventory_item = await user_crud.add_to_inventory(
        db, user_id=user_id, item_id=body.item_id, quantity=body.quantity
    )
    return inventory_item


@router.delete(
    "/{user_id}/inventory/{item_id}",
    status_code=status.HTTP_200_OK,
    summary="Remove an item from user's inventory",
)
async def remove_from_inventory(
    user_id: int,
    item_id: int,
    quantity: int = 1,
    db: AsyncSession = Depends(get_db),
):
    """
    Remove a specified quantity of an item from a user's inventory.
    """
    await user_crud.remove_from_inventory(
        db, user_id=user_id, item_id=item_id, quantity=quantity
    )
    return


@router.post(
    "/{user_id}/equip",
    summary="Equip an item to a slot",
    response_model=EquippedItemResponse,
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
    equipped = await user_crud.equip_item(
        db, user_id=user_id, item_id=body.item_id, slot=body.slot
    )
    return equipped


@router.post(
    "/{user_id}/unequip",
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


@router.get(
    "/{user_id}/details",
    response_model=UserResponse,
    summary="Get user details with relations",
)
async def get_user_details(user_id: int, db: AsyncSession = Depends(get_db)):
    """
    Get detailed information about a user, including habits, tasks, and inventory.
    """
    return await user_crud.get_user_with_relations(db, user_id)


@router.post("/{user_id}/achievements/{achievement_id}")
async def grant_achievement(
    user_id: int, achievement_id: int, db: AsyncSession = Depends(get_db)
):
    """Grant an achievement to a user manually."""
    return await user_crud.grant_achievement(db, user_id, achievement_id)
