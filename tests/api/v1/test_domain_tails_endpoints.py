import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from apps.models.notification import Notification, NotificationType
from apps.models.task import Size, SubTask, Task, TaskStatus, TaskType
from apps.models.user import Friendship, FriendshipStatus, User


# --- Notifications: read state -------------------------------------------------


async def _notify(db, user_id, message="hello"):
    n = Notification(
        user_id=user_id,
        notification_type=NotificationType.SYSTEM,
        name="Note",
        message=message,
    )
    db.add(n)
    await db.flush()
    return n


@pytest.mark.asyncio
async def test_mark_notification_read_and_unread_count(
    client: AsyncClient, db_session: AsyncSession, auth_headers
):
    user = User(name="Reader", email="reader@example.com", password="pw")
    db_session.add(user)
    await db_session.flush()
    n1 = await _notify(db_session, user.id, "one")
    await _notify(db_session, user.id, "two")
    await db_session.commit()

    before = await client.get(
        "/api/v1/notifications/unread/count", headers=auth_headers(user)
    )
    assert before.json()["unread"] == 2

    read = await client.post(
        f"/api/v1/notifications/{n1.id}/read", headers=auth_headers(user)
    )
    assert read.status_code == 200
    assert read.json()["is_read"] is True

    after = await client.get(
        "/api/v1/notifications/unread/count", headers=auth_headers(user)
    )
    assert after.json()["unread"] == 1


@pytest.mark.asyncio
async def test_mark_all_notifications_read(
    client: AsyncClient, db_session: AsyncSession, auth_headers
):
    user = User(name="Clearer", email="clearer@example.com", password="pw")
    db_session.add(user)
    await db_session.flush()
    await _notify(db_session, user.id, "a")
    await _notify(db_session, user.id, "b")
    await _notify(db_session, user.id, "c")
    await db_session.commit()

    response = await client.post(
        "/api/v1/notifications/read-all", headers=auth_headers(user)
    )
    assert response.status_code == 200
    assert response.json()["unread"] == 0

    count = await client.get(
        "/api/v1/notifications/unread/count", headers=auth_headers(user)
    )
    assert count.json()["unread"] == 0


@pytest.mark.asyncio
async def test_cannot_mark_another_users_notification_read(
    client: AsyncClient, db_session: AsyncSession, auth_headers
):
    owner = User(name="Owner", email="owner@example.com", password="pw")
    intruder = User(name="Intruder", email="intruder@example.com", password="pw")
    db_session.add_all([owner, intruder])
    await db_session.flush()
    note = await _notify(db_session, owner.id, "private")
    await db_session.commit()

    response = await client.post(
        f"/api/v1/notifications/{note.id}/read", headers=auth_headers(intruder)
    )
    assert response.status_code == 404


# --- Sub-tasks: auto-complete parent ------------------------------------------


async def _task_with_subtasks(db, user_id, n=2):
    task = Task(
        name="Checklist",
        user_id=user_id,
        task_type=TaskType.REGULAR,
        task_size=Size.SMALL,
        status=TaskStatus.TODO,
    )
    db.add(task)
    await db.flush()
    subs = [
        SubTask(name=f"step {i}", task_id=task.id, status=TaskStatus.TODO)
        for i in range(n)
    ]
    db.add_all(subs)
    await db.flush()
    return task, subs


@pytest.mark.asyncio
async def test_completing_last_subtask_auto_completes_parent(
    client: AsyncClient, db_session: AsyncSession, auth_headers
):
    user = User(name="Doer", email="doer@example.com", password="pw", experience=0)
    db_session.add(user)
    await db_session.flush()
    task, subs = await _task_with_subtasks(db_session, user.id, n=2)
    await db_session.commit()

    first = await client.post(
        f"/api/v1/sub_tasks/{subs[0].id}/complete", headers=auth_headers(user)
    )
    assert first.status_code == 200
    assert first.json()["task_completed"] is False

    second = await client.post(
        f"/api/v1/sub_tasks/{subs[1].id}/complete", headers=auth_headers(user)
    )
    body = second.json()
    assert body["task_completed"] is True
    assert body["task_reward"]["exp_gained"] == 10

    await db_session.refresh(task)
    await db_session.refresh(user)
    assert task.status == TaskStatus.COMPLETED
    assert user.experience == 10


@pytest.mark.asyncio
async def test_completing_non_final_subtask_leaves_parent_open(
    client: AsyncClient, db_session: AsyncSession, auth_headers
):
    user = User(name="Halfway", email="halfway@example.com", password="pw")
    db_session.add(user)
    await db_session.flush()
    task, subs = await _task_with_subtasks(db_session, user.id, n=3)
    await db_session.commit()

    response = await client.post(
        f"/api/v1/sub_tasks/{subs[0].id}/complete", headers=auth_headers(user)
    )
    assert response.json()["task_completed"] is False

    await db_session.refresh(task)
    assert task.status == TaskStatus.TODO


# --- Leaderboards --------------------------------------------------------------


@pytest.mark.asyncio
async def test_global_leaderboard_ranks_by_experience(
    client: AsyncClient, db_session: AsyncSession, auth_headers
):
    low = User(name="Low", email="low@example.com", password="pw", experience=5)
    high = User(name="High", email="high@example.com", password="pw", experience=500)
    mid = User(name="Mid", email="mid@example.com", password="pw", experience=100)
    db_session.add_all([low, high, mid])
    await db_session.commit()

    response = await client.get("/api/v1/users/leaderboard", headers=auth_headers(low))
    assert response.status_code == 200
    board = response.json()
    names = [entry["name"] for entry in board]
    assert names[:3] == ["High", "Mid", "Low"]
    assert board[0]["rank"] == 1


@pytest.mark.asyncio
async def test_friends_leaderboard_scoped_to_self_and_friends(
    client: AsyncClient, db_session: AsyncSession, auth_headers
):
    me = User(name="Me", email="me@example.com", password="pw", experience=50)
    friend = User(name="Buddy", email="buddy@example.com", password="pw", experience=90)
    stranger = User(
        name="Stranger", email="stranger@example.com", password="pw", experience=999
    )
    db_session.add_all([me, friend, stranger])
    await db_session.flush()
    db_session.add(
        Friendship(user_id=me.id, friend_id=friend.id, status=FriendshipStatus.ACCEPTED)
    )
    await db_session.commit()

    response = await client.get("/api/v1/friends/leaderboard", headers=auth_headers(me))
    assert response.status_code == 200
    board = response.json()
    names = [entry["name"] for entry in board]
    assert names == ["Buddy", "Me"]
    assert "Stranger" not in names
