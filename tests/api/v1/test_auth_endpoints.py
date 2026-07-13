import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession


@pytest.mark.asyncio
async def test_register_user(client: AsyncClient, db_session: AsyncSession):
    """
    Tests user registration.
    """
    payload = {
        "name": "New User",
        "email": "newuser@example.com",
        "password": "strongpassword",
        "description": "I am new here",
    }
    response = await client.post("/api/v1/auth/register", json=payload)

    assert response.status_code == 201
    data = response.json()
    assert data["email"] == payload["email"]
    assert "id" in data
    assert "password" not in data


@pytest.mark.asyncio
async def test_login_returns_tokens(client: AsyncClient, db_session: AsyncSession):
    """
    Tests that login returns access and refresh tokens.
    """
    # First, register a user
    user_payload = {
        "name": "Login User",
        "email": "login@example.com",
        "password": "password123",
        "description": "User for login test",
    }
    await client.post("/api/v1/auth/register", json=user_payload)

    # Try to login (Use data= for form-data, and key 'username')
    login_payload = {"username": "login@example.com", "password": "password123"}
    response = await client.post("/api/v1/auth/login", data=login_payload)

    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["token_type"] == "bearer"


@pytest.mark.asyncio
async def test_login_wrong_password_returns_401(
    client: AsyncClient, db_session: AsyncSession
):
    """
    Tests login failure with wrong password.
    """
    user_payload = {
        "name": "Wrong Pass User",
        "email": "wrongpass@example.com",
        "password": "correct_password",
        "description": "User for wrong pass test",
    }
    await client.post("/api/v1/auth/register", json=user_payload)

    login_payload = {
        "username": "wrongpass@example.com",
        "password": "incorrect_password",
    }
    response = await client.post("/api/v1/auth/login", data=login_payload)

    assert response.status_code == 401
    assert response.json()["detail"] == "Incorrect email or password"


@pytest.mark.asyncio
async def test_login_nonexistent_user_returns_401(
    client: AsyncClient, db_session: AsyncSession
):
    """
    Tests login failure for a user that doesn't exist.
    """
    login_payload = {"username": "nonexistent@example.com", "password": "any_password"}
    response = await client.post("/api/v1/auth/login", data=login_payload)

    assert response.status_code == 401
    assert response.json()["detail"] == "Incorrect email or password"


@pytest.mark.asyncio
async def test_refresh_token_returns_new_access_token(
    client: AsyncClient, db_session: AsyncSession
):
    """
    Tests obtaining a new access token using a refresh token.
    """
    user_payload = {
        "name": "Refresh User",
        "email": "refresh@example.com",
        "password": "password123",
        "description": "User for refresh test",
    }
    await client.post("/api/v1/auth/register", json=user_payload)

    login_response = await client.post(
        "/api/v1/auth/login",
        data={"username": "refresh@example.com", "password": "password123"},
    )
    refresh_token = login_response.json()["refresh_token"]

    # Send refresh token as JSON body {"refresh_token": "..."}
    response = await client.post(
        "/api/v1/auth/refresh", json={"refresh_token": refresh_token}
    )

    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    # Rotation check: should return new refresh token too
    assert "refresh_token" in data
    assert data["refresh_token"] != refresh_token


@pytest.mark.asyncio
async def test_refresh_with_invalid_token_returns_401(
    client: AsyncClient, db_session: AsyncSession
):
    """
    Tests refresh failure with an invalid token.
    """
    response = await client.post(
        "/api/v1/auth/refresh", json={"refresh_token": "invalid_token"}
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_logout_invalidates_token(client: AsyncClient, db_session: AsyncSession):
    """
    Tests logout (token invalidation/blacklist).
    For MVP, we check successful logout response.
    """
    user_payload = {
        "name": "Logout User",
        "email": "logout@example.com",
        "password": "password123",
        "description": "User for logout test",
    }
    await client.post("/api/v1/auth/register", json=user_payload)

    login_response = await client.post(
        "/api/v1/auth/login",
        data={"username": "logout@example.com", "password": "password123"},
    )
    login_response.json()["access_token"]
    refresh_token = login_response.json()["refresh_token"]

    response = await client.post(
        "/api/v1/auth/logout", json={"refresh_token": refresh_token}
    )
    assert response.status_code == 200

    # Revoked refresh token must not produce a new access token
    refresh_response = await client.post(
        "/api/v1/auth/refresh", json={"refresh_token": refresh_token}
    )
    assert refresh_response.status_code == 401
