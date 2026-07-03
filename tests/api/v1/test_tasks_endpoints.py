import pytest_asyncio
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from apps.models.task import Task, TaskType, TaskStatus, Size
from apps.models.user import User
from apps.schemas.task import TaskCreate, TaskUpdate
from apps.schemas.user import UserCreate


@pytest_asyncio.fixture
async def create_test_user_for_tasks(db_session: AsyncSession):
    """
    Fixture to create a test user for task-related tests.
    Tasks are linked to users.
    """
    user_data = UserCreate(
        name="Task User",
        email="task@example.com",
        password="taskpassword",
        description="User for tasks",
    )
    user = User(**user_data.model_dump(mode="json"))
    db_session.add(user)
    await db_session.commit()
    return user


@pytest_asyncio.fixture
async def create_test_task_payload(create_test_user_for_tasks: User):
    """
    Fixture providing data for creating a task (payload).
    """
    return TaskCreate(
        name="Finish Project",
        description="Complete the habit API project.",
        user_id=create_test_user_for_tasks.id,
        task_type=TaskType.REGULAR,
        task_size=Size.LARGE,
    )


@pytest_asyncio.fixture
async def create_another_test_task_payload(create_test_user_for_tasks: User):
    """
    Fixture providing data for creating a second task.
    """
    return TaskCreate(
        name="Daily Standup",
        description="Participate in daily team standup.",
        user_id=create_test_user_for_tasks.id,
        task_type=TaskType.DAILY,
        task_size=Size.SMALL,
    )


@pytest_asyncio.fixture
async def create_update_task_payload():
    """
    Fixture providing data for updating a task.
    """
    return TaskUpdate(name="Refactor Code", status=TaskStatus.IN_PROGRESS)


@pytest.mark.asyncio
async def test_create_task(
    auth_client: AsyncClient,
    db_session: AsyncSession,
    create_test_user_for_tasks: User,
    create_test_task_payload: TaskCreate,
):
    """Tests the POST /api/v1/tasks/ endpoint for creating a new task."""
    response = await auth_client.post(
        "/api/v1/tasks/", json=create_test_task_payload.model_dump(mode="json")
    )

    assert response.status_code == 201
    response_data = response.json()

    assert "id" in response_data
    assert response_data["name"] == create_test_task_payload.name
    assert response_data["user_id"] == create_test_user_for_tasks.id
    assert response_data["task_type"] == create_test_task_payload.task_type.value
    assert response_data["task_size"] == create_test_task_payload.task_size.value

    created_task = await db_session.get(Task, response_data["id"])
    assert created_task is not None
    assert created_task.name == create_test_task_payload.name
    assert created_task.user_id == create_test_user_for_tasks.id


@pytest.mark.asyncio
async def test_get_tasks(
    auth_client: AsyncClient,
    db_session: AsyncSession,
    create_test_user_for_tasks: User,
    create_test_task_payload: TaskCreate,
    create_another_test_task_payload: TaskCreate,
):
    """Tests the GET /api/v1/tasks/ endpoint for retrieving a list of tasks."""
    await auth_client.post(
        "/api/v1/tasks/", json=create_test_task_payload.model_dump(mode="json")
    )
    await auth_client.post(
        "/api/v1/tasks/", json=create_another_test_task_payload.model_dump(mode="json")
    )

    response = await auth_client.get("/api/v1/tasks/")

    assert response.status_code == 200
    response_data = response.json()

    assert isinstance(response_data, list)
    assert len(response_data) == 2

    assert "id" in response_data[0]
    assert "name" in response_data[0]
    assert "user_id" in response_data[0]


@pytest.mark.asyncio
async def test_get_tasks_pagination(
    auth_client: AsyncClient,
    create_test_user_for_tasks: User,
):
    """Tests pagination for the GET /api/v1/tasks/ endpoint."""
    user = create_test_user_for_tasks
    for i in range(5):
        task_payload = TaskCreate(
            name=f"Task {i}",
            description=f"Description {i}",
            user_id=user.id,
            task_type=TaskType.REGULAR,
            task_size=Size.SMALL,
        )
        await auth_client.post("/api/v1/tasks/", json=task_payload.model_dump(mode="json"))

    response = await auth_client.get("/api/v1/tasks/?skip=1&limit=2&order_by=created_at")
    assert response.status_code == 200
    response_data = response.json()
    assert len(response_data) == 2
    assert response_data[0]["name"] == "Task 1"
    assert response_data[1]["name"] == "Task 2"


@pytest.mark.asyncio
async def test_get_tasks_filter_by_name(
    auth_client: AsyncClient,
    create_test_user_for_tasks: User,
    create_test_task_payload: TaskCreate,
    create_another_test_task_payload: TaskCreate,
):
    """Tests name filtering for the GET /api/v1/tasks/ endpoint."""
    await auth_client.post(
        "/api/v1/tasks/", json=create_test_task_payload.model_dump(mode="json")
    )
    await auth_client.post(
        "/api/v1/tasks/", json=create_another_test_task_payload.model_dump(mode="json")
    )

    response = await auth_client.get("/api/v1/tasks/?name=Project")
    assert response.status_code == 200
    response_data = response.json()
    assert len(response_data) == 1
    assert response_data[0]["name"] == "Finish Project"


@pytest.mark.asyncio
async def test_get_task_by_id(
    auth_client: AsyncClient,
    db_session: AsyncSession,
    create_test_user_for_tasks: User,
    create_test_task_payload: TaskCreate,
):
    """Tests the GET /api/v1/tasks/{id} endpoint for retrieving a task by ID."""
    create_response = await auth_client.post(
        "/api/v1/tasks/", json=create_test_task_payload.model_dump(mode="json")
    )
    task_id = create_response.json()["id"]

    response = await auth_client.get(f"/api/v1/tasks/{task_id}")
    assert response.status_code == 200
    response_data = response.json()

    assert response_data["id"] == task_id
    assert response_data["name"] == create_test_task_payload.name
    assert response_data["user_id"] == create_test_user_for_tasks.id

    response_not_found = await auth_client.get("/api/v1/tasks/99999")
    assert response_not_found.status_code == 404
    assert "detail" in response_not_found.json()
    assert "Task with id 99999 not found" in response_not_found.json()["detail"]


@pytest.mark.asyncio
async def test_update_task(
    auth_client: AsyncClient,
    db_session: AsyncSession,
    create_test_user_for_tasks: User,
    create_test_task_payload: TaskCreate,
    create_update_task_payload: TaskUpdate,
):
    """Tests the PATCH /api/v1/tasks/{id} endpoint for updating an existing task."""
    create_response = await auth_client.post(
        "/api/v1/tasks/", json=create_test_task_payload.model_dump(mode="json")
    )
    task_id = create_response.json()["id"]

    response = await auth_client.patch(
        f"/api/v1/tasks/{task_id}",
        json=create_update_task_payload.model_dump(mode="json", exclude_unset=True),
    )
    assert response.status_code == 200
    response_data = response.json()

    assert response_data["id"] == task_id
    assert response_data["name"] == create_update_task_payload.name
    assert response_data["status"] == create_update_task_payload.status.value

    updated_task = await db_session.get(Task, task_id)
    assert updated_task.name == create_update_task_payload.name
    assert updated_task.status == create_update_task_payload.status

    response_not_found = await auth_client.patch(
        "/api/v1/tasks/99999",
        json=create_update_task_payload.model_dump(mode="json", exclude_unset=True),
    )
    assert response_not_found.status_code == 404
    assert "detail" in response_not_found.json()


@pytest.mark.asyncio
async def test_delete_task(
    auth_client: AsyncClient,
    db_session: AsyncSession,
    create_test_user_for_tasks: User,
    create_test_task_payload: TaskCreate,
):
    """Tests the DELETE /api/v1/tasks/{id} endpoint for deleting a task."""
    create_response = await auth_client.post(
        "/api/v1/tasks/", json=create_test_task_payload.model_dump(mode="json")
    )
    task_id = create_response.json()["id"]

    response = await auth_client.delete(f"/api/v1/tasks/{task_id}")
    assert response.status_code == 204

    deleted_task = await db_session.get(Task, task_id)
    assert deleted_task is None

    response_not_found = await auth_client.delete("/api/v1/tasks/99999")
    assert response_not_found.status_code == 404
    assert "detail" in response_not_found.json()


@pytest.mark.asyncio
async def test_get_task_count(
    auth_client: AsyncClient,
    db_session: AsyncSession,
    create_test_user_for_tasks: User,
    create_test_task_payload: TaskCreate,
):
    """Tests the GET /api/v1/tasks/count endpoint for retrieving the task count."""
    response_initial = await auth_client.get("/api/v1/tasks/count")
    assert response_initial.status_code == 200
    assert response_initial.json()["count"] == 0

    await auth_client.post(
        "/api/v1/tasks/", json=create_test_task_payload.model_dump(mode="json")
    )

    response_after_create = await auth_client.get("/api/v1/tasks/count")
    assert response_after_create.status_code == 200
    assert response_after_create.json()["count"] == 1


@pytest.mark.asyncio
async def test_check_task_exists(
    auth_client: AsyncClient,
    db_session: AsyncSession,
    create_test_user_for_tasks: User,
    create_test_task_payload: TaskCreate,
):
    """Tests the GET /api/v1/tasks/{id}/exists endpoint for checking task existence."""
    create_response = await auth_client.post(
        "/api/v1/tasks/", json=create_test_task_payload.model_dump(mode="json")
    )
    task_id = create_response.json()["id"]

    response_exists = await auth_client.get(f"/api/v1/tasks/{task_id}/exists")
    assert response_exists.status_code == 200
    assert response_exists.json()["exists"] is True

    response_not_exists = await auth_client.get("/api/v1/tasks/99999/exists")
    assert response_not_exists.status_code == 200
    assert response_not_exists.json()["exists"] is False


@pytest.mark.asyncio
async def test_bulk_create_tasks(
    auth_client: AsyncClient,
    db_session: AsyncSession,
    create_test_user_for_tasks: User,
    create_test_task_payload: TaskCreate,
    create_another_test_task_payload: TaskCreate,
):
    """Tests the POST /api/v1/tasks/bulk endpoint for bulk creating tasks."""
    user = create_test_user_for_tasks

    tasks_payload = [
        create_test_task_payload.model_dump(mode="json"),
        create_another_test_task_payload.model_dump(mode="json"),
    ]
    for payload in tasks_payload:
        payload["user_id"] = user.id

    response = await auth_client.post("/api/v1/tasks/bulk", json=tasks_payload)
    assert response.status_code == 201
    response_data = response.json()
    assert isinstance(response_data, list)
    assert len(response_data) == 2

    for task_data in response_data:
        created_task = await db_session.get(Task, task_data["id"])
        assert created_task is not None
        assert created_task.name == task_data["name"]

    large_tasks_payload = [
        TaskCreate(
            name=f"Bulk Task {i}",
            description=f"Description {i}",
            user_id=user.id,
            task_type=TaskType.REGULAR,
            task_size=Size.SMALL,
        ).model_dump(mode="json")
        for i in range(101)
    ]
    response_limit_exceeded = await auth_client.post(
        "/api/v1/tasks/bulk", json=large_tasks_payload
    )
    assert response_limit_exceeded.status_code == 400
    assert (
        "Cannot create more than 100 tasks at once"
        in response_limit_exceeded.json()["detail"]
    )
