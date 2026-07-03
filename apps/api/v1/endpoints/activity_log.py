from fastapi import Depends

from apps.api.deps import get_current_user
from apps.api.router_generator import RouterFactory
from apps.CRUD.from_models.activity_log import activity_log_crud
from apps.schemas.activity_log import (
    ActivityLogCreate,
    ActivityLogResponse,
    ActivityLogUpdate,
)

activity_log_factory = RouterFactory(
    crud=activity_log_crud,
    create_schema=ActivityLogCreate,
    update_schema=ActivityLogUpdate,
    response_schema=ActivityLogResponse,
    response_short_schema=ActivityLogResponse,
    resource_name="activity_log",
    resource_name_plural="activity_logs",
    tag="Activity Log",
    prefix="/activity-log",
    current_user_dependency=Depends(get_current_user),
)

router = activity_log_factory.create_router()
