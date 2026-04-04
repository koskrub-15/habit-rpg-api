import pytest_asyncio
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from apps.models.notification import Notification, NotificationType
from apps.models.user import User
from apps.schemas.notification import NotificationCreate, NotificationUpdate
from apps.schemas.user import UserCreate


@pytest_asyncio.fixture
async def create_test_user_for_notifications(db_session: AsyncSession):
    """
    Fixture to create a test user for notification-related tests.
    Notifications are linked to users.
    """
    user_data = UserCreate(
        name="Notification User",
        email="notify@example.com",
        password="notifypassword",
        description="User for notifications",
    )
    user = User(**user_data.model_dump(mode="json"))
    db_session.add(user)
    await db_session.commit()
    return user


@pytest_asyncio.fixture
async def create_test_notification_payload(create_test_user_for_notifications: User):
    """
    Fixture providing data for creating a notification (payload).
    """
    return NotificationCreate(
        name="Welcome Notification",
        description="A welcome message.",
        user_id=create_test_user_for_notifications.id,
        notification_type=NotificationType.SYSTEM,
        message="Welcome to the platform!",
    )


@pytest_asyncio.fixture
async def create_another_test_notification_payload(
    create_test_user_for_notifications: User,
):
    """
    Fixture providing data for creating a second notification.
    """
    return NotificationCreate(
        name="Task Reminder",
        description="Don't forget your tasks.",
        user_id=create_test_user_for_notifications.id,
        notification_type=NotificationType.TASK_REMINDER,
        message="You have pending tasks!",
    )


@pytest_asyncio.fixture
async def create_update_notification_payload():
    """
    Fixture providing data for updating a notification.
    """
    return NotificationUpdate(
        name="Updated Welcome", message="Updated welcome message."
    )


@pytest.mark.asyncio
async def test_create_notification(
    client: AsyncClient,
    db_session: AsyncSession,
    create_test_user_for_notifications: User,
    create_test_notification_payload: NotificationCreate,
):
    """Tests the POST /api/v1/notifications/ endpoint for creating a new notification."""
    response = await client.post(
        "/api/v1/notifications/",
        json=create_test_notification_payload.model_dump(mode="json"),
    )

    assert response.status_code == 201
    response_data = response.json()

    assert "id" in response_data
    assert response_data["name"] == create_test_notification_payload.name
    assert response_data["user_id"] == create_test_user_for_notifications.id
    assert (
        response_data["notification_type"]
        == create_test_notification_payload.notification_type.value
    )
    assert response_data["message"] == create_test_notification_payload.message

    created_notification = await db_session.get(Notification, response_data["id"])
    assert created_notification is not None
    assert created_notification.name == create_test_notification_payload.name
    assert created_notification.user_id == create_test_user_for_notifications.id


@pytest.mark.asyncio
async def test_get_notifications(
    client: AsyncClient,
    db_session: AsyncSession,
    create_test_user_for_notifications: User,
    create_test_notification_payload: NotificationCreate,
    create_another_test_notification_payload: NotificationCreate,
):
    """Tests the GET /api/v1/notifications/ endpoint for retrieving a list of notifications."""
    await client.post(
        "/api/v1/notifications/",
        json=create_test_notification_payload.model_dump(mode="json"),
    )
    await client.post(
        "/api/v1/notifications/",
        json=create_another_test_notification_payload.model_dump(mode="json"),
    )

    response = await client.get("/api/v1/notifications/")

    assert response.status_code == 200
    response_data = response.json()

    assert isinstance(response_data, list)
    assert len(response_data) == 2

    assert "id" in response_data[0]
    assert "name" in response_data[0]
    assert "user_id" in response_data[0]


@pytest.mark.asyncio
async def test_get_notifications_pagination(
    client: AsyncClient,
    create_test_user_for_notifications: User,
):
    """Tests pagination for the GET /api/v1/notifications/ endpoint."""
    user = create_test_user_for_notifications
    for i in range(5):
        notification_payload = NotificationCreate(
            name=f"Notif {i}",
            description=f"Description {i}",
            user_id=user.id,
            notification_type=NotificationType.SYSTEM,
            message=f"Message {i}",
        )
        await client.post(
            "/api/v1/notifications/", json=notification_payload.model_dump(mode="json")
        )

    response = await client.get(
        "/api/v1/notifications/?skip=1&limit=2&order_by=created_at"
    )
    assert response.status_code == 200
    response_data = response.json()
    assert len(response_data) == 2
    assert response_data[0]["name"] == "Notif 1"
    assert response_data[1]["name"] == "Notif 2"


@pytest.mark.asyncio
async def test_get_notifications_filter_by_name(
    client: AsyncClient,
    create_test_user_for_notifications: User,
    create_test_notification_payload: NotificationCreate,
    create_another_test_notification_payload: NotificationCreate,
):
    """Tests name filtering for the GET /api/v1/notifications/ endpoint."""
    await client.post(
        "/api/v1/notifications/",
        json=create_test_notification_payload.model_dump(mode="json"),
    )
    await client.post(
        "/api/v1/notifications/",
        json=create_another_test_notification_payload.model_dump(mode="json"),
    )

    response = await client.get("/api/v1/notifications/?name=Welcome")
    assert response.status_code == 200
    response_data = response.json()
    assert len(response_data) == 1
    assert response_data[0]["name"] == "Welcome Notification"


@pytest.mark.asyncio
async def test_get_notification_by_id(
    client: AsyncClient,
    db_session: AsyncSession,
    create_test_user_for_notifications: User,
    create_test_notification_payload: NotificationCreate,
):
    """Tests the GET /api/v1/notifications/{id} endpoint for retrieving a notification by ID."""
    create_response = await client.post(
        "/api/v1/notifications/",
        json=create_test_notification_payload.model_dump(mode="json"),
    )
    notification_id = create_response.json()["id"]

    response = await client.get(f"/api/v1/notifications/{notification_id}")
    assert response.status_code == 200
    response_data = response.json()

    assert response_data["id"] == notification_id
    assert response_data["name"] == create_test_notification_payload.name
    assert response_data["user_id"] == create_test_user_for_notifications.id

    response_not_found = await client.get("/api/v1/notifications/99999")
    assert response_not_found.status_code == 404
    assert "detail" in response_not_found.json()
    assert "Notification with id 99999 not found" in response_not_found.json()["detail"]


@pytest.mark.asyncio
async def test_update_notification(
    client: AsyncClient,
    db_session: AsyncSession,
    create_test_user_for_notifications: User,
    create_test_notification_payload: NotificationCreate,
    create_update_notification_payload: NotificationUpdate,
):
    """Tests the PATCH /api/v1/notifications/{id} endpoint for updating an existing notification."""
    create_response = await client.post(
        "/api/v1/notifications/",
        json=create_test_notification_payload.model_dump(mode="json"),
    )
    notification_id = create_response.json()["id"]

    response = await client.patch(
        f"/api/v1/notifications/{notification_id}",
        json=create_update_notification_payload.model_dump(
            mode="json", exclude_unset=True
        ),
    )
    assert response.status_code == 200
    response_data = response.json()

    assert response_data["id"] == notification_id
    assert response_data["name"] == create_update_notification_payload.name
    assert response_data["message"] == create_update_notification_payload.message

    updated_notification = await db_session.get(Notification, notification_id)
    assert updated_notification.name == create_update_notification_payload.name
    assert updated_notification.message == create_update_notification_payload.message

    response_not_found = await client.patch(
        "/api/v1/notifications/99999",
        json=create_update_notification_payload.model_dump(
            mode="json", exclude_unset=True
        ),
    )
    assert response_not_found.status_code == 404
    assert "detail" in response_not_found.json()


@pytest.mark.asyncio
async def test_delete_notification(
    client: AsyncClient,
    db_session: AsyncSession,
    create_test_user_for_notifications: User,
    create_test_notification_payload: NotificationCreate,
):
    """Tests the DELETE /api/v1/notifications/{id} endpoint for deleting a notification."""
    create_response = await client.post(
        "/api/v1/notifications/",
        json=create_test_notification_payload.model_dump(mode="json"),
    )
    notification_id = create_response.json()["id"]

    response = await client.delete(f"/api/v1/notifications/{notification_id}")
    assert response.status_code == 204

    deleted_notification = await db_session.get(Notification, notification_id)
    assert deleted_notification is None

    response_not_found = await client.delete("/api/v1/notifications/99999")
    assert response_not_found.status_code == 404
    assert "detail" in response_not_found.json()


@pytest.mark.asyncio
async def test_get_notification_count(
    client: AsyncClient,
    db_session: AsyncSession,
    create_test_user_for_notifications: User,
    create_test_notification_payload: NotificationCreate,
):
    """Tests the GET /api/v1/notifications/count endpoint for retrieving the notification count."""
    response_initial = await client.get("/api/v1/notifications/count")
    assert response_initial.status_code == 200
    assert response_initial.json()["count"] == 0

    await client.post(
        "/api/v1/notifications/",
        json=create_test_notification_payload.model_dump(mode="json"),
    )

    response_after_create = await client.get("/api/v1/notifications/count")
    assert response_after_create.status_code == 200
    assert response_after_create.json()["count"] == 1


@pytest.mark.asyncio
async def test_check_notification_exists(
    client: AsyncClient,
    db_session: AsyncSession,
    create_test_user_for_notifications: User,
    create_test_notification_payload: NotificationCreate,
):
    """Tests the GET /api/v1/notifications/{id}/exists endpoint for checking notification existence."""
    create_response = await client.post(
        "/api/v1/notifications/",
        json=create_test_notification_payload.model_dump(mode="json"),
    )
    notification_id = create_response.json()["id"]

    response_exists = await client.get(
        f"/api/v1/notifications/{notification_id}/exists"
    )
    assert response_exists.status_code == 200
    assert response_exists.json()["exists"] is True

    response_not_exists = await client.get("/api/v1/notifications/99999/exists")
    assert response_not_exists.status_code == 200
    assert response_not_exists.json()["exists"] is False


@pytest.mark.asyncio
async def test_bulk_create_notifications(
    client: AsyncClient,
    db_session: AsyncSession,
    create_test_user_for_notifications: User,
    create_test_notification_payload: NotificationCreate,
    create_another_test_notification_payload: NotificationCreate,
):
    """Tests the POST /api/v1/notifications/bulk endpoint for bulk creating notifications."""
    user = create_test_user_for_notifications

    notifications_payload = [
        create_test_notification_payload.model_dump(mode="json"),
        create_another_test_notification_payload.model_dump(mode="json"),
    ]
    for payload in notifications_payload:
        payload["user_id"] = user.id

    response = await client.post(
        "/api/v1/notifications/bulk", json=notifications_payload
    )
    assert response.status_code == 201
    response_data = response.json()
    assert isinstance(response_data, list)
    assert len(response_data) == 2

    for notification_data in response_data:
        created_notification = await db_session.get(
            Notification, notification_data["id"]
        )
        assert created_notification is not None
        assert created_notification.name == notification_data["name"]

    large_notifications_payload = [
        NotificationCreate(
            name=f"Bulk Notif {i}",
            description=f"Bulk description {i}",
            user_id=user.id,
            notification_type=NotificationType.SYSTEM,
            message=f"Message {i}",
        ).model_dump(mode="json")
        for i in range(101)
    ]
    response_limit_exceeded = await client.post(
        "/api/v1/notifications/bulk", json=large_notifications_payload
    )
    assert response_limit_exceeded.status_code == 400
    assert (
        "Cannot create more than 100 notifications at once"
        in response_limit_exceeded.json()["detail"]
    )
