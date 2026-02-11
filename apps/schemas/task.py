from typing import List, Optional

from pydantic import BaseModel

from apps.db.base import BaseSchemaCreate, BaseSchemaResponse, SimpleBaseSchemaCreate
from apps.models.task import Size, SubTask, TaskStatus, TaskType


class TaskCreate(BaseSchemaCreate):
    task_type: Optional[TaskType] = TaskType.REGULAR
    task_size: Optional[Size] = Size.MEDIUM
    user_id: Optional[int] = None
    sub_tasks: Optional[List["SubTaskCreate"]] = None


class TaskUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    status: Optional[TaskStatus] = None
    task_size: Optional[Size] = None
    sub_tasks: Optional[List["SubTaskUpdate"]] = None


class TaskResponseShort(BaseSchemaResponse):
    user_id: int
    task_type: TaskType
    task_size: Size
    status: TaskStatus


class TaskResponse(TaskResponseShort):
    sub_tasks: Optional[List["SubTaskResponseShort"]] = None
    user: "UserResponseShort"


class SubTaskCreate(SimpleBaseSchemaCreate):
    task_id: int


class SubTaskUpdate(BaseModel):
    name: Optional[str] = None
    status: Optional[TaskStatus] = None


class SubTaskResponseShort(BaseSchemaResponse):
    task_id: int
    status: TaskStatus


class SubTaskResponse(SubTaskResponseShort):
    task: TaskResponseShort
