from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, ConfigDict, Field

from apps.models.boss import BossFightStatus
from apps.schemas.base import BaseSchemaResponse, SimpleBaseSchemaCreate


class BossCreate(SimpleBaseSchemaCreate):
    max_health: int = Field(default=100, gt=0)
    attack: int = Field(default=0, ge=0)
    defense: int = Field(default=0, ge=0)
    required_level: int = Field(default=0, ge=0)
    reward_gold: int = Field(default=0, ge=0)
    reward_experience: int = Field(default=0, ge=0)


class BossUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    max_health: Optional[int] = None
    attack: Optional[int] = None
    defense: Optional[int] = None
    required_level: Optional[int] = None
    reward_gold: Optional[int] = None
    reward_experience: Optional[int] = None
    model_config = ConfigDict(from_attributes=True)


class BossResponseShort(BaseSchemaResponse):
    max_health: int
    attack: int
    defense: int
    required_level: int


class BossResponse(BossResponseShort):
    reward_gold: int
    reward_experience: int


class BossFightResponse(BaseModel):
    id: int
    boss_id: int
    boss_health: int
    rounds: int
    status: BossFightStatus
    model_config = ConfigDict(from_attributes=True)


class BossAttackResponse(BaseModel):
    boss_id: int
    player_damage: int
    boss_damage: int
    boss_health: int
    player_health: int
    rounds: int
    status: BossFightStatus
    died: bool = False
    reward_gold: int = 0
    reward_experience: int = 0
    new_level: int
    model_config = ConfigDict(from_attributes=True)
