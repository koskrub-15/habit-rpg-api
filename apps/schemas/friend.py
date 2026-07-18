from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict

from apps.models.user import FriendshipStatus
from apps.schemas.user import UserResponseShort


class FriendRequestResponse(BaseModel):
    id: int  # the request_id to pass to /friends/accept|decline
    user_id: int  # id of the user who sent the request
    friend_id: int  # id of the recipient (the current user)
    status: FriendshipStatus
    created_at: Optional[datetime] = None
    user: Optional[UserResponseShort] = None  # the sender
    model_config = ConfigDict(from_attributes=True)
