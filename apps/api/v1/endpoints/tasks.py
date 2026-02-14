from apps.CRUD.from_models.task import task_crud, sub_task_crud
from apps.schemas.task import (
    TaskCreate,
    TaskUpdate,
    TaskResponse,
    TaskResponseShort,
    SubTaskCreate,
    SubTaskUpdate,
    SubTaskResponse,
    SubTaskResponseShort,
)
from apps.api.router_generator import RouterFactory

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
)

task_router = task_factory.create_router()
sub_task_router = sub_task_factory.create_router()
