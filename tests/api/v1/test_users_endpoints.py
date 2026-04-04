import pytest_asyncio
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from apps.models.user import User
from apps.schemas.user import UserCreate, UserUpdate


@pytest_asyncio.fixture
async def create_test_user_payload():
    """
    Fixture providing data for creating a user (payload).
    This allows easy reuse of user creation data in various tests.
    """
    return UserCreate(
        name="Test User",
        email="test@example.com",
        password="testpassword",
        description="A test user account",
    )


@pytest_asyncio.fixture
async def create_another_test_user_payload():
    """
    Fixture providing data for creating a second user.
    Used for tests where multiple users are required,
    for example, to check pagination or filtering.
    """
    return UserCreate(
        name="Another User",
        email="another@example.com",
        password="anotherpassword",
        description="Another test user account",
    )


@pytest_asyncio.fixture
async def create_update_user_payload():
    """
    Fixture providing data for updating a user.
    """
    return UserUpdate(name="Updated User", email="updated@example.com")


@pytest.mark.asyncio
async def test_create_user(
    client: AsyncClient, db_session: AsyncSession, create_test_user_payload: UserCreate
):
    """
    Tests the POST /api/v1/users/ endpoint for creating a new user.

    Verifies:
    - Successful response status (HTTP 201 Created).
    - Returned data matches the UserResponse schema.
    - User is correctly created in the database.
    - Password is not returned in the response.
    """
    response = await client.post(
        "/api/v1/users/", json=create_test_user_payload.model_dump(mode="json")
    )

    assert response.status_code == 201
    response_data = response.json()

    assert "id" in response_data
    assert response_data["name"] == create_test_user_payload.name
    assert response_data["email"] == create_test_user_payload.email
    assert "password" not in response_data

    created_user = await db_session.get(User, response_data["id"])
    assert created_user is not None
    assert created_user.name == create_test_user_payload.name
    assert created_user.email == create_test_user_payload.email


@pytest.mark.asyncio
async def test_create_user_duplicate_email(
    client: AsyncClient, db_session: AsyncSession, create_test_user_payload: UserCreate
):
    """
    Tests an attempt to create a user with an already existing email.

    Verifies:
    - HTTP 400 Bad Request error is returned.
    - Error message contains information about email uniqueness.
    """
    await client.post(
        "/api/v1/users/", json=create_test_user_payload.model_dump(mode="json")
    )

    response = await client.post(
        "/api/v1/users/", json=create_test_user_payload.model_dump(mode="json")
    )

    assert response.status_code == 400
    response_data = response.json()
    assert "detail" in response_data
    assert "Database integrity error" in response_data["detail"]


@pytest.mark.asyncio
async def test_get_users(
    client: AsyncClient,
    db_session: AsyncSession,
    create_test_user_payload: UserCreate,
    create_another_test_user_payload: UserCreate,
):
    """
    Tests the GET /api/v1/users/ endpoint for retrieving a list of users.

    Verifies:
    - Successful response status (HTTP 200 OK).
    - A list of users is returned.
    - The number of returned users matches the expectation.
    - User data matches the UserResponseShort schema.
    """
    await client.post(
        "/api/v1/users/", json=create_test_user_payload.model_dump(mode="json")
    )
    await client.post(
        "/api/v1/users/", json=create_another_test_user_payload.model_dump(mode="json")
    )

    response = await client.get("/api/v1/users/")

    assert response.status_code == 200
    response_data = response.json()

    assert isinstance(response_data, list)
    assert len(response_data) == 2

    assert "id" in response_data[0]
    assert "name" in response_data[0]
    assert "email" in response_data[0]
    assert "password" not in response_data[0]


@pytest.mark.asyncio
async def test_get_users_pagination(
    client: AsyncClient,
    db_session: AsyncSession,
    create_test_user_payload: UserCreate,
    create_another_test_user_payload: UserCreate,
):
    """
    Tests pagination for the GET /api/v1/users/ endpoint.

    Verifies:
    - Correct functioning of skip and limit parameters.
    """
    users_to_create = [
        UserCreate(
            name=f"User {i}",
            email=f"user{i}@example.com",
            password="password",
            description="desc",
        )
        for i in range(5)
    ]
    for user_payload in users_to_create:
        await client.post("/api/v1/users/", json=user_payload.model_dump(mode="json"))

    response = await client.get("/api/v1/users/?skip=1&limit=2&order_by=created_at")
    assert response.status_code == 200
    response_data = response.json()
    assert len(response_data) == 2
    assert response_data[0]["name"] == "User 1"
    assert response_data[1]["name"] == "User 2"


@pytest.mark.asyncio
async def test_get_users_filter_by_name(
    client: AsyncClient,
    db_session: AsyncSession,
    create_test_user_payload: UserCreate,
    create_another_test_user_payload: UserCreate,
):
    """
    Tests filtering by name for the GET /api/v1/users/ endpoint.

    Verifies:
    - Correct functioning of the 'name' parameter for partial matching.
    """
    await client.post(
        "/api/v1/users/", json=create_test_user_payload.model_dump(mode="json")
    )
    await client.post(
        "/api/v1/users/", json=create_another_test_user_payload.model_dump(mode="json")
    )

    response = await client.get("/api/v1/users/?name=Test")
    assert response.status_code == 200
    response_data = response.json()
    assert len(response_data) == 1
    assert response_data[0]["name"] == "Test User"


@pytest.mark.asyncio
async def test_get_user_by_id(
    client: AsyncClient, db_session: AsyncSession, create_test_user_payload: UserCreate
):
    """
    Tests the GET /api/v1/users/{id} endpoint for retrieving a user by ID.

    Verifies:
    - Successful response status (HTTP 200 OK).
    - Returned data matches the UserResponse schema.
    - HTTP 404 Not Found error is returned if the user is not found.
    """
    create_response = await client.post(
        "/api/v1/users/", json=create_test_user_payload.model_dump(mode="json")
    )
    user_id = create_response.json()["id"]

    response = await client.get(f"/api/v1/users/{user_id}")
    assert response.status_code == 200
    response_data = response.json()

    assert response_data["id"] == user_id
    assert response_data["name"] == create_test_user_payload.name
    assert response_data["email"] == create_test_user_payload.email

    response_not_found = await client.get("/api/v1/users/99999")
    assert response_not_found.status_code == 404
    assert "detail" in response_not_found.json()
    assert "User with id 99999 not found" in response_not_found.json()["detail"]


@pytest.mark.asyncio
async def test_update_user(
    client: AsyncClient,
    db_session: AsyncSession,
    create_test_user_payload: UserCreate,
    create_update_user_payload: UserUpdate,
):
    """
    Tests the PATCH /api/v1/users/{id} endpoint for updating an existing user.

    Verifies:
    - Successful response status (HTTP 200 OK).
    - User is correctly updated in the database.
    - Updated data is returned.
    - HTTP 404 Not Found error is returned if the user is not found.
    """
    create_response = await client.post(
        "/api/v1/users/", json=create_test_user_payload.model_dump(mode="json")
    )
    user_id = create_response.json()["id"]

    response = await client.patch(
        f"/api/v1/users/{user_id}",
        json=create_update_user_payload.model_dump(mode="json", exclude_unset=True),
    )
    assert response.status_code == 200
    response_data = response.json()

    assert response_data["id"] == user_id
    assert response_data["name"] == create_update_user_payload.name
    assert response_data["email"] == create_update_user_payload.email

    updated_user = await db_session.get(User, user_id)
    assert updated_user.name == create_update_user_payload.name
    assert updated_user.email == create_update_user_payload.email

    response_not_found = await client.patch(
        "/api/v1/users/99999",
        json=create_update_user_payload.model_dump(mode="json", exclude_unset=True),
    )
    assert response_not_found.status_code == 404
    assert "detail" in response_not_found.json()


@pytest.mark.asyncio
async def test_delete_user(
    client: AsyncClient, db_session: AsyncSession, create_test_user_payload: UserCreate
):
    """
    Tests the DELETE /api/v1/users/{id} endpoint for deleting a user.

    Verifies:
    - Successful response status (HTTP 204 No Content).
    - User is deleted from the database.
    - HTTP 404 Not Found error is returned if the user is not found.
    """
    create_response = await client.post(
        "/api/v1/users/", json=create_test_user_payload.model_dump(mode="json")
    )
    user_id = create_response.json()["id"]

    response = await client.delete(f"/api/v1/users/{user_id}")
    assert response.status_code == 204

    deleted_user = await db_session.get(User, user_id)
    assert deleted_user is None

    response_not_found = await client.delete("/api/v1/users/99999")
    assert response_not_found.status_code == 404
    assert "detail" in response_not_found.json()


@pytest.mark.asyncio
async def test_get_user_count(
    client: AsyncClient, db_session: AsyncSession, create_test_user_payload: UserCreate
):
    """
    Tests the GET /api/v1/users/count endpoint for retrieving the number of users.

    Verifies:
    - Successful response status (HTTP 200 OK).
    - Correct number of users.
    """
    response_initial = await client.get("/api/v1/users/count")
    assert response_initial.status_code == 200
    assert response_initial.json()["count"] == 0

    await client.post(
        "/api/v1/users/", json=create_test_user_payload.model_dump(mode="json")
    )

    response_after_create = await client.get("/api/v1/users/count")
    assert response_after_create.status_code == 200
    assert response_after_create.json()["count"] == 1


@pytest.mark.asyncio
async def test_check_user_exists(
    client: AsyncClient, db_session: AsyncSession, create_test_user_payload: UserCreate
):
    """
    Tests the GET /api/v1/users/{id}/exists endpoint for checking user existence.

    Verifies:
    - Returns {'exists': True} for an existing user.
    - Returns {'exists': False} for a non-existent user.
    """
    create_response = await client.post(
        "/api/v1/users/", json=create_test_user_payload.model_dump(mode="json")
    )
    user_id = create_response.json()["id"]

    response_exists = await client.get(f"/api/v1/users/{user_id}/exists")
    assert response_exists.status_code == 200
    assert response_exists.json()["exists"] is True

    response_not_exists = await client.get("/api/v1/users/99999/exists")
    assert response_not_exists.status_code == 200
    assert response_not_exists.json()["exists"] is False


@pytest.mark.asyncio
async def test_bulk_create_users(
    client: AsyncClient,
    db_session: AsyncSession,
    create_test_user_payload: UserCreate,
    create_another_test_user_payload: UserCreate,
):
    """
    Tests the POST /api/v1/users/bulk endpoint for bulk user creation.

    Verifies:
    - Successful response status (HTTP 201 Created).
    - All users are correctly created.
    - Limitation on the number of users for bulk creation.
    """
    users_payload = [
        create_test_user_payload.model_dump(mode="json"),
        create_another_test_user_payload.model_dump(mode="json"),
    ]

    response = await client.post("/api/v1/users/bulk", json=users_payload)
    assert response.status_code == 201
    response_data = response.json()
    assert isinstance(response_data, list)
    assert len(response_data) == 2

    for user_data in response_data:
        created_user = await db_session.get(User, user_data["id"])
        assert created_user is not None
        assert created_user.email == user_data["email"]

    large_users_payload = [
        UserCreate(
            name=f"Bulk User {i}",
            email=f"bulk{i}@example.com",
            password="password",
            description="desc",
        ).model_dump(mode="json")
        for i in range(101)
    ]
    response_limit_exceeded = await client.post(
        "/api/v1/users/bulk", json=large_users_payload
    )
    assert response_limit_exceeded.status_code == 400
    assert (
        "Cannot create more than 100 users at once"
        in response_limit_exceeded.json()["detail"]
    )
