from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from apps.CRUD.from_models.user import user_crud
from apps.db.session import get_db

router = APIRouter(prefix="/friends", tags=["Friends"])


@router.post("/request/{friend_id}", status_code=status.HTTP_201_CREATED)
async def send_friend_request(
    friend_id: int, user_id: int, db: AsyncSession = Depends(get_db)
):
    """Send a friend request to another user."""
    return await user_crud.send_friend_request(db, user_id, friend_id)


@router.post("/accept/{request_id}")
async def accept_friend_request(
    request_id: int, user_id: int, db: AsyncSession = Depends(get_db)
):
    """Accept a pending friend request."""
    return await user_crud.accept_friend_request(db, user_id, request_id)


@router.post("/decline/{request_id}")
async def decline_friend_request(
    request_id: int, user_id: int, db: AsyncSession = Depends(get_db)
):
    """Decline a pending friend request."""
    return await user_crud.decline_friend_request(db, user_id, request_id)


@router.get("/")
async def list_friends(user_id: int, db: AsyncSession = Depends(get_db)):
    """Get the list of friends for a user."""
    return await user_crud.get_friends(db, user_id)


@router.delete("/{friend_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_friend(
    friend_id: int, user_id: int, db: AsyncSession = Depends(get_db)
):
    """Remove a user from the friends list."""
    await user_crud.remove_friend(db, user_id, friend_id)
