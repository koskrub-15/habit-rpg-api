import pytest_asyncio
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from apps.models.notification import UserNotificationPreference, NotificationType
from apps.models.user import User
from apps.schemas.notification import (
    UserNotificationPreferenceCreate,
    UserNotificationPreferenceUpdate,
)
from apps.schemas.user import UserCreate


@pytest_asyncio.fixture
async def create_test_user_for_notification_prefs(db_session: AsyncSession):
    """
    Fixture to create a test user for user notification preference-related tests.
    """
    user_data = UserCreate(
        name="Pref User",
        email="pref@example.com",
        password="prefpassword",
        description="User for notification preferences",
    )
    user = User(**user_data.model_dump(mode="json"))
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest_asyncio.fixture
async def create_test_user_notification_preference_payload(
    create_test_user_for_notification_prefs: User,
):
    """
    Fixture providing data for creating a user notification preference (payload).
    """
    return UserNotificationPreferenceCreate(
        name="System Notification Pref",
        user_id=create_test_user_for_notification_prefs.id,
        notification_type=NotificationType.SYSTEM,
        is_enabled=True,
    )


@pytest_asyncio.fixture
async def create_another_test_user_notification_preference_payload(
    create_test_user_for_notification_prefs: User,
):
    """
    Fixture providing data for creating a second user notification preference.
    """
    return UserNotificationPreferenceCreate(
        name="Task Reminder Pref",
        user_id=create_test_user_for_notification_prefs.id,
        notification_type=NotificationType.TASK_REMINDER,
        is_enabled=False,
    )


@pytest_asyncio.fixture
async def create_update_user_notification_preference_payload():
    """
    Fixture providing data for updating a user notification preference.
    """
    return UserNotificationPreferenceUpdate(
        name="Updated System Pref", is_enabled=False
    )


@pytest.mark.asyncio
async def test_create_user_notification_preference(
    client: AsyncClient,
    db_session: AsyncSession,
    create_test_user_for_notification_prefs: User,
    create_test_user_notification_preference_payload: UserNotificationPreferenceCreate,
):
    """Tests the POST /api/v1/user_notification_preferences/ endpoint for creating a new preference."""
    response = await client.post(
        "/api/v1/user_notification_preferences/",
        json=create_test_user_notification_preference_payload.model_dump(mode="json"),
    )

    assert response.status_code == 201
    response_data = response.json()

    assert "id" in response_data
    assert (
        response_data["name"] == create_test_user_notification_preference_payload.name
    )
    assert response_data["user_id"] == create_test_user_for_notification_prefs.id
    assert (
        response_data["notification_type"]
        == create_test_user_notification_preference_payload.notification_type.value
    )
    assert (
        response_data["is_enabled"]
        == create_test_user_notification_preference_payload.is_enabled
    )

    created_pref = await db_session.get(UserNotificationPreference, response_data["id"])
    assert created_pref is not None
    assert created_pref.name == create_test_user_notification_preference_payload.name
    assert created_pref.user_id == create_test_user_for_notification_prefs.id


@pytest.mark.asyncio
async def test_get_user_notification_preferences(
    client: AsyncClient,
    db_session: AsyncSession,
    create_test_user_for_notification_prefs: User,
    create_test_user_notification_preference_payload: UserNotificationPreferenceCreate,
    create_another_test_user_notification_preference_payload: UserNotificationPreferenceCreate,
):
    """Tests the GET /api/v1/user_notification_preferences/ endpoint for retrieving a list of preferences."""
    await client.post(
        "/api/v1/user_notification_preferences/",
        json=create_test_user_notification_preference_payload.model_dump(mode="json"),
    )
    await client.post(
        "/api/v1/user_notification_preferences/",
        json=create_another_test_user_notification_preference_payload.model_dump(
            mode="json"
        ),
    )

    response = await client.get("/api/v1/user_notification_preferences/")

    assert response.status_code == 200
    response_data = response.json()

    assert isinstance(response_data, list)
    assert len(response_data) == 2

    assert "id" in response_data[0]
    assert "name" in response_data[0]
    assert "user_id" in response_data[0]


@pytest.mark.asyncio
async def test_get_user_notification_preferences_pagination(
    client: AsyncClient,
    create_test_user_for_notification_prefs: User,
):
    """Tests pagination for the GET /api/v1/user_notification_preferences/ endpoint."""
    user = create_test_user_for_notification_prefs
    notification_types = list(NotificationType)
    for i in range(5):
        pref_payload = UserNotificationPreferenceCreate(
            name=f"Pref {i}",
            user_id=user.id,
            notification_type=notification_types[i % len(notification_types)],
            is_enabled=(i % 2 == 0),
        )
        await client.post(
            "/api/v1/user_notification_preferences/",
            json=pref_payload.model_dump(mode="json"),
        )

    response = await client.get(
        "/api/v1/user_notification_preferences/?skip=1&limit=2&order_by=created_at"
    )
    assert response.status_code == 200
    response_data = response.json()
    assert len(response_data) == 2
    assert response_data[0]["name"] == "Pref 1"
    assert response_data[1]["name"] == "Pref 2"


@pytest.mark.asyncio
async def test_get_user_notification_preferences_filter_by_name(
    client: AsyncClient,
    create_test_user_for_notification_prefs: User,
    create_test_user_notification_preference_payload: UserNotificationPreferenceCreate,
    create_another_test_user_notification_preference_payload: UserNotificationPreferenceCreate,
):
    """Tests name filtering for the GET /api/v1/user_notification_preferences/ endpoint."""
    await client.post(
        "/api/v1/user_notification_preferences/",
        json=create_test_user_notification_preference_payload.model_dump(mode="json"),
    )
    await client.post(
        "/api/v1/user_notification_preferences/",
        json=create_another_test_user_notification_preference_payload.model_dump(
            mode="json"
        ),
    )

    response = await client.get("/api/v1/user_notification_preferences/?name=System")
    assert response.status_code == 200
    response_data = response.json()
    assert len(response_data) == 1
    assert response_data[0]["name"] == "System Notification Pref"


@pytest.mark.asyncio
async def test_get_user_notification_preference_by_id(
    client: AsyncClient,
    db_session: AsyncSession,
    create_test_user_for_notification_prefs: User,
    create_test_user_notification_preference_payload: UserNotificationPreferenceCreate,
):
    """Tests the GET /api/v1/user_notification_preferences/{id} endpoint for retrieving a preference by ID."""
    create_response = await client.post(
        "/api/v1/user_notification_preferences/",
        json=create_test_user_notification_preference_payload.model_dump(mode="json"),
    )
    pref_id = create_response.json()["id"]

    response = await client.get(f"/api/v1/user_notification_preferences/{pref_id}")
    assert response.status_code == 200
    response_data = response.json()

    assert response_data["id"] == pref_id
    assert (
        response_data["name"] == create_test_user_notification_preference_payload.name
    )
    assert response_data["user_id"] == create_test_user_for_notification_prefs.id

    response_not_found = await client.get("/api/v1/user_notification_preferences/99999")
    assert response_not_found.status_code == 404
    assert "detail" in response_not_found.json()
    assert (
        "User_notification_preference with id 99999 not found"
        in response_not_found.json()["detail"]
    )


@pytest.mark.asyncio
async def test_update_user_notification_preference(
    client: AsyncClient,
    db_session: AsyncSession,
    create_test_user_for_notification_prefs: User,
    create_test_user_notification_preference_payload: UserNotificationPreferenceCreate,
    create_update_user_notification_preference_payload: UserNotificationPreferenceUpdate,
):
    """Tests the PATCH /api/v1/user_notification_preferences/{id} endpoint for updating an existing preference."""
    create_response = await client.post(
        "/api/v1/user_notification_preferences/",
        json=create_test_user_notification_preference_payload.model_dump(mode="json"),
    )
    pref_id = create_response.json()["id"]

    response = await client.patch(
        f"/api/v1/user_notification_preferences/{pref_id}",
        json=create_update_user_notification_preference_payload.model_dump(
            mode="json", exclude_unset=True
        ),
    )
    assert response.status_code == 200
    response_data = response.json()

    assert response_data["id"] == pref_id
    assert (
        response_data["name"] == create_update_user_notification_preference_payload.name
    )
    assert (
        response_data["is_enabled"]
        == create_update_user_notification_preference_payload.is_enabled
    )

    updated_pref = await db_session.get(UserNotificationPreference, pref_id)
    assert updated_pref.name == create_update_user_notification_preference_payload.name
    assert (
        updated_pref.is_enabled
        == create_update_user_notification_preference_payload.is_enabled
    )

    response_not_found = await client.patch(
        "/api/v1/user_notification_preferences/99999",
        json=create_update_user_notification_preference_payload.model_dump(
            mode="json", exclude_unset=True
        ),
    )
    assert response_not_found.status_code == 404
    assert "detail" in response_not_found.json()


@pytest.mark.asyncio
async def test_delete_user_notification_preference(
    client: AsyncClient,
    db_session: AsyncSession,
    create_test_user_for_notification_prefs: User,
    create_test_user_notification_preference_payload: UserNotificationPreferenceCreate,
):
    """Tests the DELETE /api/v1/user_notification_preferences/{id} endpoint for deleting a preference."""
    create_response = await client.post(
        "/api/v1/user_notification_preferences/",
        json=create_test_user_notification_preference_payload.model_dump(mode="json"),
    )
    pref_id = create_response.json()["id"]

    response = await client.delete(f"/api/v1/user_notification_preferences/{pref_id}")
    assert response.status_code == 204

    deleted_pref = await db_session.get(UserNotificationPreference, pref_id)
    assert deleted_pref is None

    response_not_found = await client.delete(
        "/api/v1/user_notification_preferences/99999"
    )
    assert response_not_found.status_code == 404
    assert "detail" in response_not_found.json()


@pytest.mark.asyncio
async def test_get_user_notification_preference_count(
    client: AsyncClient,
    db_session: AsyncSession,
    create_test_user_for_notification_prefs: User,
    create_test_user_notification_preference_payload: UserNotificationPreferenceCreate,
):
    """Tests the GET /api/v1/user_notification_preferences/count endpoint for retrieving the preference count."""
    response_initial = await client.get("/api/v1/user_notification_preferences/count")
    assert response_initial.status_code == 200
    assert response_initial.json()["count"] == 0

    await client.post(
        "/api/v1/user_notification_preferences/",
        json=create_test_user_notification_preference_payload.model_dump(mode="json"),
    )

    response_after_create = await client.get(
        "/api/v1/user_notification_preferences/count"
    )
    assert response_after_create.status_code == 200
    assert response_after_create.json()["count"] == 1


@pytest.mark.asyncio
async def test_check_user_notification_preference_exists(
    client: AsyncClient,
    db_session: AsyncSession,
    create_test_user_for_notification_prefs: User,
    create_test_user_notification_preference_payload: UserNotificationPreferenceCreate,
):
    """Tests the GET /api/v1/user_notification_preferences/{id}/exists endpoint for checking preference existence."""
    create_response = await client.post(
        "/api/v1/user_notification_preferences/",
        json=create_test_user_notification_preference_payload.model_dump(mode="json"),
    )
    pref_id = create_response.json()["id"]

    response_exists = await client.get(
        f"/api/v1/user_notification_preferences/{pref_id}/exists"
    )
    assert response_exists.status_code == 200
    assert response_exists.json()["exists"] is True

    response_not_exists = await client.get(
        "/api/v1/user_notification_preferences/99999/exists"
    )
    assert response_not_exists.status_code == 200
    assert response_not_exists.json()["exists"] is False


@pytest.mark.asyncio
async def test_bulk_create_user_notification_preferences(
    client: AsyncClient,
    db_session: AsyncSession,
    create_test_user_for_notification_prefs: User,
    create_test_user_notification_preference_payload: UserNotificationPreferenceCreate,
    create_another_test_user_notification_preference_payload: UserNotificationPreferenceCreate,
):
    """Tests the POST /api/v1/user_notification_preferences/bulk endpoint for bulk creating preferences."""
    user = create_test_user_for_notification_prefs

    prefs_payload = [
        create_test_user_notification_preference_payload.model_dump(mode="json"),
        create_another_test_user_notification_preference_payload.model_dump(
            mode="json"
        ),
    ]
    for payload in prefs_payload:
        payload["user_id"] = user.id

    response = await client.post(
        "/api/v1/user_notification_preferences/bulk", json=prefs_payload
    )
    assert response.status_code == 201
    response_data = response.json()
    assert isinstance(response_data, list)
    assert len(response_data) == 2

    for pref_data in response_data:
        created_pref = await db_session.get(UserNotificationPreference, pref_data["id"])
        assert created_pref is not None
        assert created_pref.name == pref_data["name"]

    large_prefs_payload = [
        UserNotificationPreferenceCreate(
            name=f"Bulk Pref {i}",
            user_id=user.id,
            notification_type=NotificationType.SYSTEM,
            is_enabled=(i % 2 == 0),
        ).model_dump(mode="json")
        for i in range(101)
    ]
    response_limit_exceeded = await client.post(
        "/api/v1/user_notification_preferences/bulk", json=large_prefs_payload
    )
    assert response_limit_exceeded.status_code == 400
    assert (
        "Cannot create more than 100 user_notification_preferences at once"
        in response_limit_exceeded.json()["detail"]
    )
