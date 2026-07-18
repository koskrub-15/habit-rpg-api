from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.deps import get_current_user
from apps.api.router_generator import RouterFactory
from apps.CRUD.from_models.user import user_crud
from apps.db.session import get_db
from apps.models.user import User
from apps.schemas.achievement import AchievementResponse
from apps.schemas.user import (
    CompleteActivityRequest,
    CompleteActivityResponse,
    DailyCronResponse,
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
    current_user_dependency=Depends(get_current_user),
    owner_field="id",
    write_requires_superuser=True,
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
    current_user: User = Depends(get_current_user),
):
    """
    Mark a task as completed or record a habit performance.
    Awards experience and gold to the user.
    """
    if user_id != current_user.id and not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions to modify another user's data",
        )

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
@router.post(
    "/{user_id}/reset-daily-tasks",
    status_code=status.HTTP_200_OK,
    include_in_schema=False,
)
async def reset_daily(
    user_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Reset the status of all daily tasks for a specific user to 'TODO'.
    """
    if user_id != current_user.id and not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions to modify another user's data",
        )

    await user_crud.reset_daily_tasks(db, user_id=user_id)
    return


@router.post(
    "/{user_id}/cron",
    response_model=DailyCronResponse,
    status_code=status.HTTP_200_OK,
    summary="Run the daily rollover for a user",
)
async def run_cron(
    user_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Roll the user's day over: reset daily tasks and habits, and apply HP damage for
    any daily tasks left un-completed. Idempotent — running it twice the same day is
    a no-op.
    """
    if user_id != current_user.id and not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions to modify another user's data",
        )

    return await user_crud.run_daily_cron(db, user_id=user_id)


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
    current_user: User = Depends(get_current_user),
):
    """
    Add a specified quantity of an item to a user's inventory.
    """
    if user_id != current_user.id and not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions to modify another user's inventory",
        )

    inventory_item = await user_crud.add_to_inventory(
        db, user_id=user_id, item_id=body.item_id, quantity=body.quantity
    )
    return inventory_item


@router.get(
    "/{user_id}/inventory",
    response_model=List[InventoryItemResponse],
    summary="Get user's inventory",
)
async def get_inventory(
    user_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Get all items in a user's inventory.
    """
    if user_id != current_user.id and not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions to view another user's inventory",
        )

    return await user_crud.get_inventory(db, user_id=user_id)


@router.post(
    "/{user_id}/equip",
    response_model=EquippedItemResponse,
    summary="Equip an item from inventory",
)
async def equip_item(
    user_id: int,
    body: EquipItemRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Equip an item from the user's inventory into a specific slot.
    """
    if user_id != current_user.id and not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions to modify another user's equipment",
        )

    return await user_crud.equip_item(
        db, user_id=user_id, item_id=body.item_id, slot=body.slot
    )


@router.post(
    "/{user_id}/unequip",
    status_code=status.HTTP_200_OK,
    summary="Unequip an item",
)
async def unequip_item(
    user_id: int,
    body: UnequipItemRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Unequip an item from a specific slot.
    """
    if user_id != current_user.id and not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions to modify another user's equipment",
        )

    await user_crud.unequip_item(db, user_id=user_id, slot=body.slot)
    return {"detail": "Item unequipped successfully"}


@router.get(
    "/{user_id}/equipped",
    response_model=List[EquippedItemResponse],
    summary="Get user's equipped items",
)
async def get_equipped(
    user_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Get all currently equipped items for a user.
    """
    if user_id != current_user.id and not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions to view another user's equipment",
        )

    return await user_crud.get_equipped_items(db, user_id=user_id)


@router.delete(
    "/{user_id}/inventory/{item_id}",
    status_code=status.HTTP_200_OK,
    summary="Remove item from user's inventory",
)
async def remove_from_inventory(
    user_id: int,
    item_id: int,
    quantity: int = 1,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Remove a specified quantity of an item from the user's inventory.
    """
    if user_id != current_user.id and not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions to modify another user's inventory",
        )

    await user_crud.remove_from_inventory(
        db, user_id=user_id, item_id=item_id, quantity=quantity
    )
    return {"detail": "Item removed successfully"}


@router.post(
    "/{user_id}/achievements/{achievement_id}",
    status_code=status.HTTP_200_OK,
    response_model=AchievementResponse,
    summary="Grant an achievement to a user",
)
async def grant_achievement(
    user_id: int,
    achievement_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Manually grant an achievement to a user.
    """
    if not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Superuser privileges required",
        )

    return await user_crud.grant_achievement(
        db, user_id=user_id, achievement_id=achievement_id
    )


@router.get(
    "/{user_id}/details",
    response_model=UserResponse,
    summary="Get user with all related data",
)
async def get_user_details(
    user_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Get detailed user information including all related tasks, habits, achievements, etc.
    """
    if user_id != current_user.id and not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions to view another user's data",
        )

    return await user_crud.get_user_with_relations(db, user_id)
