import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from apps.models.user import User


@pytest.mark.asyncio
async def test_send_friend_request(auth_client: AsyncClient, db_session: AsyncSession):
    """
    Tests sending a friend request from one user to another.
    """
    user1 = User(name="User1", email="u1@example.com", password="password")
    user2 = User(name="User2", email="u2@example.com", password="password")
    db_session.add_all([user1, user2])
    await db_session.commit()

    response = await auth_client.post(
        f"/api/v1/friends/request/{user2.id}", params={"user_id": user1.id}
    )
    assert response.status_code == 201
    assert response.json()["status"] == "PENDING"


@pytest.mark.asyncio
async def test_send_friend_request_to_nonexistent_user_returns_404(
    auth_client: AsyncClient, db_session: AsyncSession
):
    """
    Tests failure when sending a friend request to a non-existent user.
    """
    user = User(name="User", email="u@example.com", password="password")
    db_session.add(user)
    await db_session.commit()

    response = await auth_client.post(
        "/api/v1/friends/request/9999", params={"user_id": user.id}
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_send_duplicate_friend_request_returns_409(
    auth_client: AsyncClient, db_session: AsyncSession
):
    """
    Tests that a user cannot send a second friend request to the same user.
    """
    user1 = User(name="U1", email="u1@example.com", password="password")
    user2 = User(name="U2", email="u2@example.com", password="password")
    db_session.add_all([user1, user2])
    await db_session.commit()

    # Send first request
    await auth_client.post(
        f"/api/v1/friends/request/{user2.id}", params={"user_id": user1.id}
    )

    # Send second request
    response = await auth_client.post(
        f"/api/v1/friends/request/{user2.id}", params={"user_id": user1.id}
    )
    assert response.status_code == 409


@pytest.mark.asyncio
async def test_accept_friend_request(auth_client: AsyncClient, db_session: AsyncSession):
    """
    Tests accepting a friend request.
    """
    user1 = User(name="U1", email="u1@example.com", password="password")
    user2 = User(name="U2", email="u2@example.com", password="password")
    db_session.add_all([user1, user2])
    await db_session.commit()

    # Send request
    req_response = await auth_client.post(
        f"/api/v1/friends/request/{user2.id}", params={"user_id": user1.id}
    )
    request_id = req_response.json()["id"]

    # Accept request
    response = await auth_client.post(
        f"/api/v1/friends/accept/{request_id}", params={"user_id": user2.id}
    )
    assert response.status_code == 200
    assert response.json()["status"] == "ACCEPTED"

    # Check if they are friends (Assuming list_friends endpoint)
    list_resp = await auth_client.get("/api/v1/friends/", params={"user_id": user1.id})
    assert len(list_resp.json()) == 1
    assert list_resp.json()[0]["id"] == user2.id


@pytest.mark.asyncio
async def test_decline_friend_request(auth_client: AsyncClient, db_session: AsyncSession):
    """
    Tests declining a friend request.
    """
    user1 = User(name="U1", email="u1@example.com", password="password")
    user2 = User(name="U2", email="u2@example.com", password="password")
    db_session.add_all([user1, user2])
    await db_session.commit()

    req_response = await auth_client.post(
        f"/api/v1/friends/request/{user2.id}", params={"user_id": user1.id}
    )
    request_id = req_response.json()["id"]

    # Decline
    response = await auth_client.post(
        f"/api/v1/friends/decline/{request_id}", params={"user_id": user2.id}
    )
    assert response.status_code == 200
    assert response.json()["status"] == "DECLINED"


@pytest.mark.asyncio
async def test_get_friends_list(auth_client: AsyncClient, db_session: AsyncSession):
    """
    Tests retrieving the list of friends for a user.
    """
    # Create several users and make some of them friends with user1
    user1 = User(name="U1", email="u1@example.com", password="password")
    user2 = User(name="U2", email="u2@example.com", password="password")
    user3 = User(name="U3", email="u3@example.com", password="password")
    db_session.add_all([user1, user2, user3])
    await db_session.commit()

    # user1 sends to user2, user2 accepts
    req1 = await auth_client.post(
        f"/api/v1/friends/request/{user2.id}", params={"user_id": user1.id}
    )
    await auth_client.post(
        f"/api/v1/friends/accept/{req1.json()['id']}", params={"user_id": user2.id}
    )

    # user3 sends to user1, user1 accepts
    req2 = await auth_client.post(
        f"/api/v1/friends/request/{user1.id}", params={"user_id": user3.id}
    )
    await auth_client.post(
        f"/api/v1/friends/accept/{req2.json()['id']}", params={"user_id": user1.id}
    )

    response = await auth_client.get("/api/v1/friends/", params={"user_id": user1.id})
    assert response.status_code == 200
    assert len(response.json()) == 2


@pytest.mark.asyncio
async def test_remove_friend(auth_client: AsyncClient, db_session: AsyncSession):
    """
    Tests removing a friend.
    """
    user1 = User(name="U1", email="u1@example.com", password="password")
    user2 = User(name="U2", email="u2@example.com", password="password")
    db_session.add_all([user1, user2])
    await db_session.commit()

    # Setup friendship
    req = await auth_client.post(
        f"/api/v1/friends/request/{user2.id}", params={"user_id": user1.id}
    )
    await auth_client.post(
        f"/api/v1/friends/accept/{req.json()['id']}", params={"user_id": user2.id}
    )

    # Remove
    response = await auth_client.delete(
        f"/api/v1/friends/{user2.id}", params={"user_id": user1.id}
    )
    assert response.status_code == 204

    # Verify removal
    list_resp = await auth_client.get("/api/v1/friends/", params={"user_id": user1.id})
    assert len(list_resp.json()) == 0
