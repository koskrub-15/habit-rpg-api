"""Authorization tests for RouterFactory-generated endpoints.

These cover the ownership and superuser rules that plain CRUD mechanics tests
(run as a superuser) do not exercise:

- Owned resources (owner_field, e.g. habits): a user only sees and mutates
  their own rows; cross-user access returns 403; new rows are forced to the
  caller; superusers bypass all of it.
- Catalog resources (write_requires_superuser, e.g. items): everyone can read,
  only superusers can write.
- Users: each user only sees/edits themselves; only superusers list everyone
  or create users through the factory endpoint.
"""

import pytest
from httpx import AsyncClient

from apps.models.user import User

HABITS = "/api/v1/habits"
ITEMS = "/api/v1/items"
USERS = "/api/v1/users"


def _habit_payload(name: str = "Read", user_id: int | None = None) -> dict:
    body: dict = {"name": name, "habit_type": "POSITIVE", "habit_size": "MEDIUM"}
    if user_id is not None:
        body["user_id"] = user_id
    return body


async def _create_habit_as(client: AsyncClient, headers: dict, **kwargs) -> dict:
    resp = await client.post(
        f"{HABITS}/", json=_habit_payload(**kwargs), headers=headers
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


# --- Owned resource: habits ------------------------------------------------


@pytest.mark.asyncio
async def test_create_forces_owner_to_caller(
    client: AsyncClient, normal_user: User, create_test_user, auth_headers
):
    """A regular user cannot create a habit owned by someone else."""
    other = await create_test_user()
    habit = await _create_habit_as(client, auth_headers(normal_user), user_id=other.id)
    assert habit["user_id"] == normal_user.id


@pytest.mark.asyncio
async def test_list_only_returns_own_rows(
    client: AsyncClient, normal_user: User, create_test_user, auth_headers
):
    other = await create_test_user()
    await _create_habit_as(client, auth_headers(other), name="Theirs")
    await _create_habit_as(client, auth_headers(normal_user), name="Mine")

    resp = await client.get(f"{HABITS}/", headers=auth_headers(normal_user))
    assert resp.status_code == 200
    names = {h["name"] for h in resp.json()}
    assert names == {"Mine"}


@pytest.mark.asyncio
async def test_count_only_counts_own_rows(
    client: AsyncClient, normal_user: User, create_test_user, auth_headers
):
    other = await create_test_user()
    await _create_habit_as(client, auth_headers(other), name="Theirs")
    await _create_habit_as(client, auth_headers(normal_user), name="Mine")

    resp = await client.get(f"{HABITS}/count", headers=auth_headers(normal_user))
    assert resp.json() == {"count": 1}


@pytest.mark.asyncio
async def test_get_others_row_is_forbidden(
    client: AsyncClient, normal_user: User, create_test_user, auth_headers
):
    other = await create_test_user()
    habit = await _create_habit_as(client, auth_headers(other), name="Theirs")

    resp = await client.get(
        f"{HABITS}/{habit['id']}", headers=auth_headers(normal_user)
    )
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_update_others_row_is_forbidden(
    client: AsyncClient, normal_user: User, create_test_user, auth_headers
):
    other = await create_test_user()
    habit = await _create_habit_as(client, auth_headers(other), name="Theirs")

    resp = await client.patch(
        f"{HABITS}/{habit['id']}",
        json={"name": "Hacked"},
        headers=auth_headers(normal_user),
    )
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_delete_others_row_is_forbidden(
    client: AsyncClient, normal_user: User, create_test_user, auth_headers
):
    other = await create_test_user()
    habit = await _create_habit_as(client, auth_headers(other), name="Theirs")

    resp = await client.delete(
        f"{HABITS}/{habit['id']}", headers=auth_headers(normal_user)
    )
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_exists_hides_others_row(
    client: AsyncClient, normal_user: User, create_test_user, auth_headers
):
    other = await create_test_user()
    habit = await _create_habit_as(client, auth_headers(other), name="Theirs")

    resp = await client.get(
        f"{HABITS}/{habit['id']}/exists", headers=auth_headers(normal_user)
    )
    assert resp.json() == {"exists": False}


@pytest.mark.asyncio
async def test_superuser_can_access_any_row(
    client: AsyncClient, test_user: User, normal_user: User, auth_headers
):
    """test_user is a superuser and bypasses ownership checks."""
    habit = await _create_habit_as(client, auth_headers(normal_user), name="Theirs")

    resp = await client.get(f"{HABITS}/{habit['id']}", headers=auth_headers(test_user))
    assert resp.status_code == 200
    assert resp.json()["user_id"] == normal_user.id


# --- Catalog resource: items -----------------------------------------------


@pytest.mark.asyncio
async def test_catalog_read_is_open_to_regular_users(
    client: AsyncClient, normal_user: User, auth_headers
):
    resp = await client.get(f"{ITEMS}/", headers=auth_headers(normal_user))
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_catalog_write_requires_superuser(
    client: AsyncClient, normal_user: User, auth_headers
):
    payload = {"name": "Sword", "item_type": "WEAPON"}
    resp = await client.post(
        f"{ITEMS}/", json=payload, headers=auth_headers(normal_user)
    )
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_superuser_can_write_catalog(
    client: AsyncClient, test_user: User, auth_headers
):
    payload = {"name": "Sword", "item_type": "WEAPON"}
    resp = await client.post(f"{ITEMS}/", json=payload, headers=auth_headers(test_user))
    assert resp.status_code == 201


# --- Users -----------------------------------------------------------------


@pytest.mark.asyncio
async def test_user_list_shows_only_self(
    client: AsyncClient, normal_user: User, create_test_user, auth_headers
):
    await create_test_user()
    resp = await client.get(f"{USERS}/", headers=auth_headers(normal_user))
    assert resp.status_code == 200
    ids = {u["id"] for u in resp.json()}
    assert ids == {normal_user.id}


@pytest.mark.asyncio
async def test_superuser_lists_all_users(
    client: AsyncClient, test_user: User, normal_user: User, auth_headers
):
    resp = await client.get(f"{USERS}/", headers=auth_headers(test_user))
    ids = {u["id"] for u in resp.json()}
    assert {test_user.id, normal_user.id} <= ids


@pytest.mark.asyncio
async def test_user_cannot_read_other_user(
    client: AsyncClient, normal_user: User, create_test_user, auth_headers
):
    other = await create_test_user()
    resp = await client.get(f"{USERS}/{other.id}", headers=auth_headers(normal_user))
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_user_cannot_create_via_factory(
    client: AsyncClient, normal_user: User, auth_headers
):
    payload = {
        "name": "Intruder",
        "email": "intruder@example.com",
        "password": "password123",
    }
    resp = await client.post(
        f"{USERS}/", json=payload, headers=auth_headers(normal_user)
    )
    assert resp.status_code == 403


# --- Hand-written user endpoints -------------------------------------------


@pytest.mark.asyncio
async def test_cannot_reset_another_users_dailies(
    client: AsyncClient, normal_user: User, create_test_user, auth_headers
):
    other = await create_test_user()
    resp = await client.post(
        f"{USERS}/{other.id}/reset-daily", headers=auth_headers(normal_user)
    )
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_cannot_read_another_users_details(
    client: AsyncClient, normal_user: User, create_test_user, auth_headers
):
    other = await create_test_user()
    resp = await client.get(
        f"{USERS}/{other.id}/details", headers=auth_headers(normal_user)
    )
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_grant_achievement_requires_superuser(
    client: AsyncClient, normal_user: User, auth_headers
):
    """Granting achievements is a superuser-only action, even to oneself."""
    resp = await client.post(
        f"{USERS}/{normal_user.id}/achievements/1", headers=auth_headers(normal_user)
    )
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_superuser_can_grant_achievement(
    client: AsyncClient, test_user: User, normal_user: User, auth_headers
):
    ach = await client.post(
        "/api/v1/achievements/",
        json={"name": "First Steps", "condition_type": "streak", "condition_value": 1},
        headers=auth_headers(test_user),
    )
    assert ach.status_code == 201, ach.text
    resp = await client.post(
        f"{USERS}/{normal_user.id}/achievements/{ach.json()['id']}",
        headers=auth_headers(test_user),
    )
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_cannot_complete_another_users_habit(
    client: AsyncClient, normal_user: User, create_test_user, auth_headers
):
    other = await create_test_user()
    habit = await _create_habit_as(client, auth_headers(other), name="Theirs")

    resp = await client.post(
        f"{HABITS}/{habit['id']}/complete", headers=auth_headers(normal_user)
    )
    assert resp.status_code == 403
