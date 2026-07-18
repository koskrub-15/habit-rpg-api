from fastapi import Depends

from apps.api.deps import get_current_user
from apps.api.router_generator import RouterFactory
from apps.CRUD.from_models.task import sub_task_crud, task_crud
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
