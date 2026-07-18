from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict

from apps.models.task import Size, TaskStatus, TaskType
from apps.schemas.base import BaseSchemaResponse, SimpleBaseSchemaCreate


class SubTaskCreate(SimpleBaseSchemaCreate):
    task_id: Optional[int] = None
    status: TaskStatus = TaskStatus.TODO


class SubTaskUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    status: Optional[TaskStatus] = None
    model_config = ConfigDict(from_attributes=True)


class SubTaskResponseShort(BaseSchemaResponse):
    task_id: int
    status: TaskStatus


class SubTaskResponse(SubTaskResponseShort):
    pass


class TaskCreate(SimpleBaseSchemaCreate):
    user_id: Optional[int] = None
    task_type: TaskType = TaskType.REGULAR
    task_size: Size = Size.SMALL
    status: TaskStatus = TaskStatus.TODO


class TaskUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    status: Optional[TaskStatus] = None
    task_type: Optional[TaskType] = None
    task_size: Optional[Size] = None
    model_config = ConfigDict(from_attributes=True)


class TaskResponseShort(BaseSchemaResponse):
    user_id: int
    status: TaskStatus
    task_type: TaskType
    task_size: Size
    last_completed_at: Optional[datetime] = None


class TaskResponse(TaskResponseShort):
    sub_tasks: List[SubTaskResponseShort] = []
