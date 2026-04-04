from typing import Any, Dict, Optional, Union

from sqlalchemy.ext.asyncio import AsyncSession

from apps.CRUD.base import BaseCRUD
from apps.CRUD.from_models.activity_log import activity_log_crud
from apps.models.activity_log import ActivityType
from apps.models.task import SubTask, Task, TaskStatus
from apps.schemas.activity_log import ActivityLogCreate
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
    ) -> Optional[Task]:
        # Get object before update to check status change
        db_obj = await self.get(db, id)
        if not db_obj:
            return None

        old_status = db_obj.status
        updated_obj = await super().update(db, id=id, obj_in=obj_in, commit=commit)

        if (
            updated_obj
            and old_status != TaskStatus.COMPLETED
            and updated_obj.status == TaskStatus.COMPLETED
        ):
            # Auto-log task completion
            await activity_log_crud.create(
                db,
                obj_in=ActivityLogCreate(
                    user_id=updated_obj.user_id,
                    activity_type=ActivityType.TASK_COMPLETED,
                    description=f"Completed task: {updated_obj.name}",
                    task_id=updated_obj.id,
                ),
                commit=commit,
            )

        return updated_obj


class CRUDSubTask(BaseCRUD[SubTask, SubTaskCreate, SubTaskUpdate]):
    def __init__(self):
        super().__init__(model=SubTask)


task_crud = CRUDTask()
sub_task_crud = CRUDSubTask()
