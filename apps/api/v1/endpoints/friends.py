from typing import List

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.deps import get_current_user
from apps.CRUD.from_models.user import user_crud
from apps.db.session import get_db
from apps.models.user import User
from apps.schemas.friend import FriendRequestResponse

router = APIRouter(prefix="/friends", tags=["Friends"])


@router.get("/requests", response_model=List[FriendRequestResponse])
async def list_incoming_requests(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List incoming pending friend requests for the current user."""
    return await user_crud.get_incoming_friend_requests(db, current_user.id)


@router.post("/request/{friend_id}", status_code=status.HTTP_201_CREATED)
async def send_friend_request(
    friend_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Send a friend request to another user."""
    return await user_crud.send_friend_request(db, current_user.id, friend_id)


@router.post("/accept/{request_id}")
async def accept_friend_request(
    request_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Accept a pending friend request."""
    return await user_crud.accept_friend_request(db, current_user.id, request_id)


@router.post("/decline/{request_id}")
async def decline_friend_request(
    request_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Decline a pending friend request."""
    return await user_crud.decline_friend_request(db, current_user.id, request_id)


@router.get("/")
async def list_friends(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get the list of friends for a user."""
    return await user_crud.get_friends(db, current_user.id)


@router.delete("/{friend_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_friend(
    friend_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Remove a user from the friends list."""
    await user_crud.remove_friend(db, current_user.id, friend_id)
