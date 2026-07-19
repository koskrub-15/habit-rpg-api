import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from apps.models.achievement import Achievement, Reward
from apps.models.notification import (
    Notification,
    NotificationType,
    UserNotificationPreference,
)
from apps.models.task import Size, Task, TaskStatus, TaskType
from apps.models.user import User


async def _notifications(db_session, user_id, notification_type=None):
    stmt = select(Notification).where(Notification.user_id == user_id)
    if notification_type is not None:
        stmt = stmt.where(Notification.notification_type == notification_type)
    result = await db_session.execute(stmt)
    return list(result.scalars().all())


@pytest.mark.asyncio
async def test_friend_request_notifies_recipient(
    client: AsyncClient, db_session: AsyncSession, auth_headers
):
    """Sending a friend request creates a FRIEND_REQUEST notification for the recipient."""
    sender = User(name="Sender", email="s@example.com", password="password")
    recipient = User(name="Recipient", email="r@example.com", password="password")
    db_session.add_all([sender, recipient])
    await db_session.commit()

    resp = await client.post(
        f"/api/v1/friends/request/{recipient.id}", headers=auth_headers(sender)
    )
    assert resp.status_code == 201

    notifs = await _notifications(db_session, recipient.id)
    assert len(notifs) == 1
    assert notifs[0].notification_type == NotificationType.FRIEND_REQUEST


@pytest.mark.asyncio
async def test_friend_request_notification_suppressed_by_optout(
    client: AsyncClient, db_session: AsyncSession, auth_headers
):
    """An explicit disabled preference suppresses the notification."""
    sender = User(name="Sender", email="s@example.com", password="password")
    recipient = User(name="Recipient", email="r@example.com", password="password")
    db_session.add_all([sender, recipient])
    await db_session.commit()
    db_session.add(
        UserNotificationPreference(
            name="Friend request preference",
            user_id=recipient.id,
            notification_type=NotificationType.FRIEND_REQUEST,
            is_enabled=False,
        )
    )
    await db_session.commit()

    await client.post(
        f"/api/v1/friends/request/{recipient.id}", headers=auth_headers(sender)
    )

    notifs = await _notifications(db_session, recipient.id)
    assert notifs == []


@pytest.mark.asyncio
async def test_level_up_notifies_user(
    auth_client: AsyncClient, db_session: AsyncSession, test_user: User
):
    """Crossing a level threshold creates a SYSTEM notification."""
    task = Task(
        name="Level task",
        user_id=test_user.id,
        task_type=TaskType.REGULAR,
        task_size=Size.MEDIUM,
        status=TaskStatus.TODO,
    )
    db_session.add(task)
    await db_session.commit()
    await db_session.refresh(task)

    response = await auth_client.post(
        f"/api/v1/users/{test_user.id}/complete-activity",
        json={"activity_type": "task", "activity_id": task.id},
    )
    assert response.status_code == 200

    notifs = await _notifications(db_session, test_user.id, NotificationType.SYSTEM)
    assert any("level" in n.message.lower() for n in notifs)


@pytest.mark.asyncio
async def test_achievement_unlock_notifies_user(
    auth_client: AsyncClient, db_session: AsyncSession, test_user: User
):
    """Granting an achievement creates a SYSTEM notification."""
    reward = Reward(name="R", gold=0, experience=0, health_points=0)
    achievement = Achievement(
        name="First Steps", condition_type="manual", condition_value=0, rewards=[reward]
    )
    db_session.add(achievement)
    await db_session.commit()
    await db_session.refresh(achievement)

    response = await auth_client.post(
        f"/api/v1/users/{test_user.id}/achievements/{achievement.id}"
    )
    assert response.status_code == 200

    notifs = await _notifications(db_session, test_user.id, NotificationType.SYSTEM)
    assert any("achievement" in n.message.lower() for n in notifs)
