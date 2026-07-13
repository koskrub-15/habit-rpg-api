from typing import Any, Dict, Union

from sqlalchemy.ext.asyncio import AsyncSession

from apps.CRUD.base import BaseCRUD
from apps.models.task import SubTask, Task, TaskStatus
from apps.schemas.task import SubTaskCreate, SubTaskUpdate, TaskCreate, TaskUpdate


class CRUDTask(BaseCRUD[Task, TaskCreate, TaskUpdate]):
    def __init__(self):
        super().__init__(model=Task)

    async def update(
        self,
        db: AsyncSession,
        *,
        id: Any,
        obj_in: Union[TaskUpdate, Dict[str, Any]],
        commit: bool = True,
    ) -> Task:
        if isinstance(obj_in, dict):
            update_data = obj_in
        else:
            update_data = obj_in.model_dump(exclude_unset=True)

        task = await super().update(db, id=id, obj_in=update_data, commit=commit)
        assert task is not None  # super().update() raises 404 before returning None

        if (
            update_data.get("status") == TaskStatus.COMPLETED
            or update_data.get("status") == "COMPLETED"
        ):
            from apps.models.activity_log import ActivityLog, ActivityType

            db.add(
                ActivityLog(
                    user_id=task.user_id,
                    activity_type=ActivityType.TASK_COMPLETED,
                    task_id=task.id,
                    description=f"Completed task: {task.name}",
                )
            )
            if commit:
                await db.commit()

        return task


class CRUDSubTask(BaseCRUD[SubTask, SubTaskCreate, SubTaskUpdate]):
    def __init__(self):
        super().__init__(model=SubTask)


task_crud = CRUDTask()
sub_task_crud = CRUDSubTask()
