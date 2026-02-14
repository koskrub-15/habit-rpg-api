from apps.CRUD.base import BaseCRUD
from apps.models.task import Task, SubTask
from apps.schemas.task import TaskCreate, TaskUpdate, SubTaskCreate, SubTaskUpdate


class CRUDTask(BaseCRUD[Task, TaskCreate, TaskUpdate]):
    def __init__(self):
        super().__init__(model=Task)


class CRUDSubTask(BaseCRUD[SubTask, SubTaskCreate, SubTaskUpdate]):
    def __init__(self):
        super().__init__(model=SubTask)


task_crud = CRUDTask()
sub_task_crud = CRUDSubTask()
