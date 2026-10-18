from sqlalchemy import Column, DateTime, Enum, ForeignKey, Integer
from sqlalchemy.orm import relationship

from apps.core.enums import Size, TaskStatus, TaskType
from apps.db.base import Base, SimpleBase


class Task(Base):
    __tablename__ = "tasks"

    status = Column(Enum(TaskStatus), default=TaskStatus.TODO)
    task_type = Column(Enum(TaskType), default=TaskType.REGULAR)
    task_size = Column(Enum(Size), default=Size.SMALL)
    last_completed_at = Column(DateTime(timezone=True), nullable=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    user = relationship("User", back_populates="tasks")

    sub_tasks = relationship(
        "SubTask", back_populates="task", cascade="all, delete-orphan"
    )

    def reset_daily_task(self):
        """Reset this task if it's a daily task."""
        if self.task_type == TaskType.DAILY:
            self.status = TaskStatus.TODO
            for sub_task in self.sub_tasks:
                sub_task.status = TaskStatus.TODO

    def __repr__(self) -> str:
        return f"<Task(title={self.name}, status={self.status})>"


class SubTask(SimpleBase):
    __tablename__ = "sub_tasks"

    status = Column(Enum(TaskStatus), default=TaskStatus.TODO)

    task_id = Column(Integer, ForeignKey("tasks.id"), nullable=False)
    task = relationship("Task", back_populates="sub_tasks")

    def __repr__(self) -> str:
        return f"<SubTask(title={self.name}, status={self.status})>"
