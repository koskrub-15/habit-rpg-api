from fastapi import Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.deps import get_current_user
from apps.api.router_generator import RouterFactory
from apps.CRUD.from_models.task import sub_task_crud, task_crud
from apps.CRUD.from_models.user import user_crud
from apps.db.session import get_db
from apps.models.user import User
from apps.schemas.task import (
    SubTaskCreate,
    SubTaskResponse,
    SubTaskResponseShort,
    SubTaskUpdate,
    TaskCreate,
    TaskResponse,
    TaskResponseShort,
    TaskUpdate,
)
from apps.schemas.user import CompleteActivityResponse, SubTaskCompleteResponse

task_factory = RouterFactory(
    crud=task_crud,
    create_schema=TaskCreate,
    update_schema=TaskUpdate,
    response_schema=TaskResponse,
    response_short_schema=TaskResponseShort,
    resource_name="task",
    resource_name_plural="tasks",
    tag="Tasks",
    prefix="/tasks",
    current_user_dependency=Depends(get_current_user),
    owner_field="user_id",
)

sub_task_factory = RouterFactory(
    crud=sub_task_crud,
    create_schema=SubTaskCreate,
    update_schema=SubTaskUpdate,
    response_schema=SubTaskResponse,
    response_short_schema=SubTaskResponseShort,
    resource_name="sub_task",
    resource_name_plural="sub_tasks",
    tag="Tasks",
    prefix="/sub_tasks",
    current_user_dependency=Depends(get_current_user),
    owner_parent={"crud": task_crud, "fk_field": "task_id", "owner_field": "user_id"},
)

task_router = task_factory.create_router()
sub_task_router = sub_task_factory.create_router()


@task_router.post(
    "/{task_id}/complete",
    response_model=CompleteActivityResponse,
    summary="Complete a task",
)
async def complete_task(
    task_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Mark a task as completed, awarding experience and gold to its owner.
    """
    task = await task_crud.get(db, task_id, raise_not_found=True)

    if task.user_id != current_user.id and not current_user.is_superuser:  # type: ignore[union-attr]
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions to complete another user's task",
        )

    return await user_crud.complete_activity(
        db,
        user_id=task.user_id,  # type: ignore
        activity_type="task",
        activity_id=task_id,
    )


@sub_task_router.post(
    "/{sub_task_id}/complete",
    response_model=SubTaskCompleteResponse,
    summary="Complete a sub-task",
)
async def complete_sub_task(
    sub_task_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Mark a sub-task as completed. When every sub-task of the parent task is done,
    the parent task is auto-completed and its owner is rewarded.
    """
    sub_task = await sub_task_crud.get(db, sub_task_id, raise_not_found=True)
    parent = await task_crud.get(db, sub_task.task_id, raise_not_found=True)  # type: ignore

    if parent.user_id != current_user.id and not current_user.is_superuser:  # type: ignore[union-attr]
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions to complete another user's sub-task",
        )

    return await user_crud.complete_sub_task(db, sub_task_id=sub_task_id)
