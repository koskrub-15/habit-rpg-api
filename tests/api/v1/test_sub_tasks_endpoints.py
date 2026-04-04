import pytest_asyncio
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from apps.models.task import SubTask, Task, TaskStatus, Size
from apps.models.user import User
from apps.schemas.task import SubTaskCreate, SubTaskUpdate, TaskCreate
from apps.schemas.user import UserCreate


@pytest_asyncio.fixture
async def create_test_user_for_subtasks(db_session: AsyncSession):
    """
    Fixture to create a test user for subtask-related tests.
    Subtasks are linked to tasks, which are linked to users.
    """
    user_data = UserCreate(
        name="SubTask User",
        email="subtask@example.com",
        password="subtaskpassword",
        description="User for subtasks",
    )
    user = User(**user_data.model_dump(mode="json"))
    db_session.add(user)
    await db_session.commit()
    return user


@pytest_asyncio.fixture
async def create_test_task_for_subtasks(
    db_session: AsyncSession, create_test_user_for_subtasks: User
):
    """
    Fixture to create a test task for subtask-related tests.
    """
    task_data = TaskCreate(
        name="Parent Task for Subtasks",
        description="A task to hold subtasks.",
        user_id=create_test_user_for_subtasks.id,
        task_size=Size.MEDIUM,
    )
    task = Task(**task_data.model_dump(mode="json"))
    db_session.add(task)
    await db_session.commit()
    return task


@pytest_asyncio.fixture
async def create_test_sub_task_payload(create_test_task_for_subtasks: Task):
    """
    Fixture providing data for creating a subtask (payload).
    """
    return SubTaskCreate(
        name="Subtask 1",
        description="First subtask.",
        task_id=create_test_task_for_subtasks.id,
    )


@pytest_asyncio.fixture
async def create_another_test_sub_task_payload(create_test_task_for_subtasks: Task):
    """
    Fixture providing data for creating a second subtask.
    """
    return SubTaskCreate(
        name="Subtask 2",
        description="Second subtask.",
        task_id=create_test_task_for_subtasks.id,
    )


@pytest_asyncio.fixture
async def create_update_sub_task_payload():
    """
    Fixture providing data for updating a subtask.
    """
    return SubTaskUpdate(name="Updated Subtask 1", status=TaskStatus.COMPLETED)


@pytest.mark.asyncio
async def test_create_sub_task(
    client: AsyncClient,
    db_session: AsyncSession,
    create_test_task_for_subtasks: Task,
    create_test_sub_task_payload: SubTaskCreate,
):
    """Tests the POST /api/v1/sub_tasks/ endpoint for creating a new subtask."""
    response = await client.post(
        "/api/v1/sub_tasks/", json=create_test_sub_task_payload.model_dump(mode="json")
    )

    assert response.status_code == 201
    response_data = response.json()

    assert "id" in response_data
    assert response_data["name"] == create_test_sub_task_payload.name
    assert response_data["task_id"] == create_test_task_for_subtasks.id

    created_sub_task = await db_session.get(SubTask, response_data["id"])
    assert created_sub_task is not None
    assert created_sub_task.name == create_test_sub_task_payload.name
    assert created_sub_task.task_id == create_test_task_for_subtasks.id


@pytest.mark.asyncio
async def test_get_sub_tasks(
    client: AsyncClient,
    db_session: AsyncSession,
    create_test_task_for_subtasks: Task,
    create_test_sub_task_payload: SubTaskCreate,
    create_another_test_sub_task_payload: SubTaskCreate,
):
    """Tests the GET /api/v1/sub_tasks/ endpoint for retrieving a list of subtasks."""
    await client.post(
        "/api/v1/sub_tasks/", json=create_test_sub_task_payload.model_dump(mode="json")
    )
    await client.post(
        "/api/v1/sub_tasks/",
        json=create_another_test_sub_task_payload.model_dump(mode="json"),
    )

    response = await client.get("/api/v1/sub_tasks/")

    assert response.status_code == 200
    response_data = response.json()

    assert isinstance(response_data, list)
    assert len(response_data) == 2

    assert "id" in response_data[0]
    assert "name" in response_data[0]
    assert "task_id" in response_data[0]


@pytest.mark.asyncio
async def test_get_sub_tasks_pagination(
    client: AsyncClient,
    create_test_task_for_subtasks: Task,
):
    """Tests pagination for the GET /api/v1/sub_tasks/ endpoint."""
    task_id = create_test_task_for_subtasks.id
    for i in range(5):
        sub_task_payload = SubTaskCreate(
            name=f"Subtask {i}",
            description=f"Description {i}",
            task_id=task_id,
        )
        await client.post(
            "/api/v1/sub_tasks/", json=sub_task_payload.model_dump(mode="json")
        )

    response = await client.get("/api/v1/sub_tasks/?skip=1&limit=2&order_by=created_at")
    assert response.status_code == 200
    response_data = response.json()
    assert len(response_data) == 2
    assert response_data[0]["name"] == "Subtask 1"
    assert response_data[1]["name"] == "Subtask 2"


@pytest.mark.asyncio
async def test_get_sub_tasks_filter_by_name(
    client: AsyncClient,
    create_test_task_for_subtasks: Task,
    create_test_sub_task_payload: SubTaskCreate,
    create_another_test_sub_task_payload: SubTaskCreate,
):
    """Tests name filtering for the GET /api/v1/sub_tasks/ endpoint."""
    await client.post(
        "/api/v1/sub_tasks/", json=create_test_sub_task_payload.model_dump(mode="json")
    )
    await client.post(
        "/api/v1/sub_tasks/",
        json=create_another_test_sub_task_payload.model_dump(mode="json"),
    )

    response = await client.get("/api/v1/sub_tasks/?name=Subtask 1")
    assert response.status_code == 200
    response_data = response.json()
    assert len(response_data) == 1
    assert response_data[0]["name"] == "Subtask 1"


@pytest.mark.asyncio
async def test_get_sub_task_by_id(
    client: AsyncClient,
    db_session: AsyncSession,
    create_test_task_for_subtasks: Task,
    create_test_sub_task_payload: SubTaskCreate,
):
    """Tests the GET /api/v1/sub_tasks/{id} endpoint for retrieving a subtask by ID."""
    create_response = await client.post(
        "/api/v1/sub_tasks/", json=create_test_sub_task_payload.model_dump(mode="json")
    )
    sub_task_id = create_response.json()["id"]

    response = await client.get(f"/api/v1/sub_tasks/{sub_task_id}")
    assert response.status_code == 200
    response_data = response.json()

    assert response_data["id"] == sub_task_id
    assert response_data["name"] == create_test_sub_task_payload.name
    assert response_data["task_id"] == create_test_task_for_subtasks.id

    response_not_found = await client.get("/api/v1/sub_tasks/99999")
    assert response_not_found.status_code == 404
    assert "detail" in response_not_found.json()
    assert "Sub_task with id 99999 not found" in response_not_found.json()["detail"]


@pytest.mark.asyncio
async def test_update_sub_task(
    client: AsyncClient,
    db_session: AsyncSession,
    create_test_task_for_subtasks: Task,
    create_test_sub_task_payload: SubTaskCreate,
    create_update_sub_task_payload: SubTaskUpdate,
):
    """Tests the PATCH /api/v1/sub_tasks/{id} endpoint for updating an existing subtask."""
    create_response = await client.post(
        "/api/v1/sub_tasks/", json=create_test_sub_task_payload.model_dump(mode="json")
    )
    sub_task_id = create_response.json()["id"]

    response = await client.patch(
        f"/api/v1/sub_tasks/{sub_task_id}",
        json=create_update_sub_task_payload.model_dump(mode="json", exclude_unset=True),
    )
    assert response.status_code == 200
    response_data = response.json()

    assert response_data["id"] == sub_task_id
    assert response_data["name"] == create_update_sub_task_payload.name
    assert response_data["status"] == create_update_sub_task_payload.status.value

    updated_sub_task = await db_session.get(SubTask, sub_task_id)
    assert updated_sub_task.name == create_update_sub_task_payload.name
    assert updated_sub_task.status == create_update_sub_task_payload.status

    response_not_found = await client.patch(
        "/api/v1/sub_tasks/99999",
        json=create_update_sub_task_payload.model_dump(mode="json", exclude_unset=True),
    )
    assert response_not_found.status_code == 404
    assert "detail" in response_not_found.json()


@pytest.mark.asyncio
async def test_delete_sub_task(
    client: AsyncClient,
    db_session: AsyncSession,
    create_test_task_for_subtasks: Task,
    create_test_sub_task_payload: SubTaskCreate,
):
    """Tests the DELETE /api/v1/sub_tasks/{id} endpoint for deleting a subtask."""
    create_response = await client.post(
        "/api/v1/sub_tasks/", json=create_test_sub_task_payload.model_dump(mode="json")
    )
    sub_task_id = create_response.json()["id"]

    response = await client.delete(f"/api/v1/sub_tasks/{sub_task_id}")
    assert response.status_code == 204

    deleted_sub_task = await db_session.get(SubTask, sub_task_id)
    assert deleted_sub_task is None

    response_not_found = await client.delete("/api/v1/sub_tasks/99999")
    assert response_not_found.status_code == 404
    assert "detail" in response_not_found.json()


@pytest.mark.asyncio
async def test_get_sub_task_count(
    client: AsyncClient,
    db_session: AsyncSession,
    create_test_task_for_subtasks: Task,
    create_test_sub_task_payload: SubTaskCreate,
):
    """Tests the GET /api/v1/sub_tasks/count endpoint for retrieving the subtask count."""
    response_initial = await client.get("/api/v1/sub_tasks/count")
    assert response_initial.status_code == 200
    assert response_initial.json()["count"] == 0

    await client.post(
        "/api/v1/sub_tasks/", json=create_test_sub_task_payload.model_dump(mode="json")
    )

    response_after_create = await client.get("/api/v1/sub_tasks/count")
    assert response_after_create.status_code == 200
    assert response_after_create.json()["count"] == 1


@pytest.mark.asyncio
async def test_check_sub_task_exists(
    client: AsyncClient,
    db_session: AsyncSession,
    create_test_task_for_subtasks: Task,
    create_test_sub_task_payload: SubTaskCreate,
):
    """Tests the GET /api/v1/sub_tasks/{id}/exists endpoint for checking subtask existence."""
    create_response = await client.post(
        "/api/v1/sub_tasks/", json=create_test_sub_task_payload.model_dump(mode="json")
    )
    sub_task_id = create_response.json()["id"]

    response_exists = await client.get(f"/api/v1/sub_tasks/{sub_task_id}/exists")
    assert response_exists.status_code == 200
    assert response_exists.json()["exists"] is True

    response_not_exists = await client.get("/api/v1/sub_tasks/99999/exists")
    assert response_not_exists.status_code == 200
    assert response_not_exists.json()["exists"] is False


@pytest.mark.asyncio
async def test_bulk_create_sub_tasks(
    client: AsyncClient,
    db_session: AsyncSession,
    create_test_task_for_subtasks: Task,
    create_test_sub_task_payload: SubTaskCreate,
    create_another_test_sub_task_payload: SubTaskCreate,
):
    """Tests the POST /api/v1/sub_tasks/bulk endpoint for bulk creating subtasks."""
    task = create_test_task_for_subtasks

    sub_tasks_payload = [
        create_test_sub_task_payload.model_dump(mode="json"),
        create_another_test_sub_task_payload.model_dump(mode="json"),
    ]
    for payload in sub_tasks_payload:
        payload["task_id"] = task.id

    response = await client.post("/api/v1/sub_tasks/bulk", json=sub_tasks_payload)
    assert response.status_code == 201
    response_data = response.json()
    assert isinstance(response_data, list)
    assert len(response_data) == 2

    for sub_task_data in response_data:
        created_sub_task = await db_session.get(SubTask, sub_task_data["id"])
        assert created_sub_task is not None
        assert created_sub_task.name == sub_task_data["name"]

    large_sub_tasks_payload = [
        SubTaskCreate(
            name=f"Bulk Subtask {i}",
            description=f"Description {i}",
            task_id=task.id,
        ).model_dump(mode="json")
        for i in range(101)
    ]
    response_limit_exceeded = await client.post(
        "/api/v1/sub_tasks/bulk", json=large_sub_tasks_payload
    )
    assert response_limit_exceeded.status_code == 400
    assert (
        "Cannot create more than 100 sub_tasks at once"
        in response_limit_exceeded.json()["detail"]
    )
