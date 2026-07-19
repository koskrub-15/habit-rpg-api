from fastapi import Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.deps import get_current_user
from apps.api.router_generator import RouterFactory
from apps.CRUD.from_models.boss import boss_crud
from apps.CRUD.from_models.user import user_crud
from apps.db.session import get_db
from apps.models.user import User
from apps.schemas.boss import (
    BossAttackResponse,
    BossCreate,
    BossFightResponse,
    BossResponse,
    BossResponseShort,
    BossUpdate,
)

boss_factory = RouterFactory(
    crud=boss_crud,
    create_schema=BossCreate,
    update_schema=BossUpdate,
    response_schema=BossResponse,
    response_short_schema=BossResponseShort,
    resource_name="boss",
    resource_name_plural="bosses",
    tag="Bosses",
    prefix="/bosses",
    write_requires_superuser=True,
    current_user_dependency=Depends(get_current_user),
)

router = boss_factory.create_router()


@router.post(
    "/{boss_id}/attack",
    response_model=BossAttackResponse,
    summary="Attack a boss with your equipped combat stats",
)
async def attack_boss(
    boss_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Fight a boss for one round. Player damage comes from equipped attack and
    pet power; the boss strikes back against equipped defense. Starts a fresh
    fight automatically and rewards gold/experience on the finishing blow.
    """
    return await user_crud.attack_boss(db, user_id=current_user.id, boss_id=boss_id)


@router.get(
    "/{boss_id}/fight",
    response_model=BossFightResponse,
    summary="Get your in-progress fight against a boss",
)
async def get_boss_fight(
    boss_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Return the current active fight against this boss, or 404 if none is open."""
    fight = await user_crud.get_active_boss_fight(
        db, user_id=current_user.id, boss_id=boss_id
    )
    if fight is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="No active fight"
        )
    return fight
