import random
from datetime import datetime, timezone
from typing import List, Optional

from fastapi import HTTPException, status
from sqlalchemy import func, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from apps.CRUD.base import BaseCRUD
from apps.models.achievement import Achievement, Reward
from apps.models.activity_log import ActivityLog, ActivityType
from apps.models.boss import Boss, BossFight, BossFightStatus
from apps.models.habit import Habit, HabitStatus, HabitType
from apps.models.item import Item, ItemType
from apps.models.notification import (
    Notification,
    NotificationType,
    UserNotificationPreference,
)
from apps.models.store_rotation import ShopItem, ShopRotation, ShopRotationItem
from apps.models.task import Size, SubTask, Task, TaskStatus, TaskType
from apps.models.user import (
    EquippedItem,
    Friendship,
    FriendshipStatus,
    InventoryItem,
    SlotType,
    User,
)
from apps.schemas.user import CompleteActivityResponse, UserCreate, UserUpdate


class CRUDUser(BaseCRUD[User, UserCreate, UserUpdate]):
    def __init__(self):
        super().__init__(model=User)

    async def get_by_email(self, db: AsyncSession, email: str) -> Optional[User]:
        """Get user by email."""
        result = await db.execute(select(User).where(User.email == email))
        return result.scalar_one_or_none()

    async def reset_daily_tasks(self, db: AsyncSession, *, user_id: int):
        """Reset all daily tasks and habits for a user to 'TODO'."""
        from sqlalchemy import update
        from apps.models.task import Task, TaskStatus, TaskType
        from apps.models.habit import Habit, HabitStatus

        # Reset daily tasks
        await db.execute(
            update(Task)
            .where(Task.user_id == user_id, Task.task_type == TaskType.DAILY)
            .values(status=TaskStatus.TODO)
        )
        # Reset habits
        await db.execute(
            update(Habit)
            .where(Habit.user_id == user_id)
            .values(status=HabitStatus.TODO)
        )
        await db.commit()
        return

    async def _enforce_rotation_availability(
        self, db: AsyncSession, shop_item_id: int, now: datetime
    ) -> None:
        """Rotation-exclusive items may only be bought while their rotation is live.

        Items never attached to any rotation are always buyable (subject to the
        item's own availability window).
        """
        is_rotation_item = (
            await db.execute(
                select(ShopRotationItem.id).where(
                    ShopRotationItem.shop_item_id == shop_item_id
                )
            )
        ).first()
        if is_rotation_item is None:
            return

        is_featured_now = (
            await db.execute(
                select(ShopRotationItem.id)
                .join(ShopRotation, ShopRotationItem.rotation_id == ShopRotation.id)
                .where(
                    ShopRotationItem.shop_item_id == shop_item_id,
                    ShopRotation.start_date <= now,
                    ShopRotation.end_date > now,
                )
            )
        ).first()
        if is_featured_now is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="This item is only available during its shop rotation",
            )

    async def buy_item(self, db: AsyncSession, user_id: int, shop_item_id: int):
        """Buy item from the shop."""
        result = await db.execute(
            select(ShopItem)
            .where(ShopItem.id == shop_item_id)
            .options(selectinload(ShopItem.item))
        )
        shop_item = result.scalar_one_or_none()

        if not shop_item:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Shop item not found"
            )

        user = await self.get(db, user_id, raise_not_found=True)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        now = datetime.now(timezone.utc)
        if shop_item.available_from and now < shop_item.available_from:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Item not currently available. It will be available only from {shop_item.available_from}",
            )

        if shop_item.available_until and now > shop_item.available_until:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Item not currently available. Offer has expired",
            )

        if shop_item.stock == 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Out of stock",
            )

        await self._enforce_rotation_availability(db, shop_item_id, now)

        if user.gold < shop_item.price:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Not enough gold on the balance",
            )

        user.gold -= shop_item.price
        shop_item.stock -= 1

        await self.add_to_inventory(db, user_id, shop_item.item_id)

        item_name = shop_item.item.name if shop_item.item else "item"
        db.add(
            ActivityLog(
                user_id=user_id,  # type: ignore
                activity_type=ActivityType.ITEM_PURCHASED,  # type: ignore
                item_id=shop_item.item_id,  # type: ignore
                description=f"Purchased item: {item_name}",  # type: ignore
            )
        )

        await db.commit()
        await self.check_and_award_achievements(db, user_id)
        return {"message": "Purchase successful", "new_gold": user.gold}

    # Friends methods
    async def send_friend_request(
        self, db: AsyncSession, user_id: int, friend_id: int
    ) -> Friendship:
        """Send a friend request."""
        if user_id == friend_id:
            raise HTTPException(status_code=400, detail="Cannot add yourself as friend")

        # Check if recipient exists
        friend = await self.get(db, friend_id)
        if not friend:
            raise HTTPException(status_code=404, detail="User not found")

        # Check for existing friendship or request
        result = await db.execute(
            select(Friendship).where(
                or_(
                    (Friendship.user_id == user_id)
                    & (Friendship.friend_id == friend_id),
                    (Friendship.user_id == friend_id)
                    & (Friendship.friend_id == user_id),
                )
            )
        )
        existing = result.scalar_one_or_none()
        if existing:
            raise HTTPException(
                status_code=409, detail="Friendship already exists or pending"
            )

        friendship = Friendship(
            user_id=user_id, friend_id=friend_id, status=FriendshipStatus.PENDING
        )  # type: ignore
        db.add(friendship)
        await self._notify(
            db,
            friend_id,
            NotificationType.FRIEND_REQUEST,
            "Friend request",
            "You have a new friend request",
        )
        await db.commit()
        await db.refresh(friendship)
        return friendship

    async def accept_friend_request(
        self, db: AsyncSession, user_id: int, request_id: int
    ) -> Friendship:
        """Accept a friend request."""
        result = await db.execute(
            select(Friendship).where(
                Friendship.id == request_id,
                Friendship.friend_id == user_id,
                Friendship.status == FriendshipStatus.PENDING,
            )
        )
        friendship = result.scalar_one_or_none()
        if not friendship:
            raise HTTPException(status_code=404, detail="Friend request not found")

        friendship.status = FriendshipStatus.ACCEPTED
        await db.commit()
        await db.refresh(friendship)
        await self.check_and_award_achievements(db, user_id)
        await self.check_and_award_achievements(db, friendship.user_id)
        return friendship

    async def decline_friend_request(
        self, db: AsyncSession, user_id: int, request_id: int
    ) -> Friendship:
        """Decline a friend request."""
        result = await db.execute(
            select(Friendship).where(
                Friendship.id == request_id,
                Friendship.friend_id == user_id,
                Friendship.status == FriendshipStatus.PENDING,
            )
        )
        friendship = result.scalar_one_or_none()
        if not friendship:
            raise HTTPException(status_code=404, detail="Friend request not found")

        friendship.status = FriendshipStatus.DECLINED
        await db.commit()
        await db.refresh(friendship)
        return friendship

    async def get_friends(self, db: AsyncSession, user_id: int) -> List[User]:
        """Get list of friends (ACCEPTED status)."""
        result = await db.execute(
            select(Friendship).where(
                ((Friendship.user_id == user_id) | (Friendship.friend_id == user_id))
                & (Friendship.status == FriendshipStatus.ACCEPTED)
            )
        )
        friendships = result.scalars().all()

        friend_ids = []
        for f in friendships:
            if f.user_id == user_id:
                friend_ids.append(f.friend_id)
            else:
                friend_ids.append(f.user_id)

        if not friend_ids:
            return []

        result = await db.execute(select(User).where(User.id.in_(friend_ids)))
        return list(result.scalars().all())

    async def get_incoming_friend_requests(
        self, db: AsyncSession, user_id: int
    ) -> List[Friendship]:
        """Return pending friend requests received by the user, with sender loaded.

        Exposes the ``request_id`` (Friendship.id) that /friends/accept and
        /friends/decline expect — otherwise a recipient has no way to obtain it.
        """
        result = await db.execute(
            select(Friendship)
            .where(
                Friendship.friend_id == user_id,
                Friendship.status == FriendshipStatus.PENDING,
            )
            .options(selectinload(Friendship.user))
        )
        return list(result.scalars().all())

    async def remove_friend(
        self, db: AsyncSession, user_id: int, friend_id: int
    ) -> None:
        """Remove a friend."""
        result = await db.execute(
            select(Friendship).where(
                or_(
                    (Friendship.user_id == user_id)
                    & (Friendship.friend_id == friend_id),
                    (Friendship.user_id == friend_id)
                    & (Friendship.friend_id == user_id),
                )
            )
        )
        friendship = result.scalar_one_or_none()
        if not friendship:
            raise HTTPException(status_code=404, detail="Friendship not found")

        await db.delete(friendship)
        await db.commit()

    # Achievements methods
    async def grant_achievement(
        self, db: AsyncSession, user_id: int, achievement_id: int
    ) -> Achievement:
        """Grant an achievement to a user manually."""
        user = await self.get(
            db, user_id, raise_not_found=True, relationships=["achievements"]
        )
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        result = await db.execute(
            select(Achievement)
            .where(Achievement.id == achievement_id)
            .options(selectinload(Achievement.rewards).selectinload(Reward.items))
        )
        achievement = result.scalar_one_or_none()
        if not achievement:
            raise HTTPException(status_code=404, detail="Achievement not found")

        if achievement in user.achievements:
            raise HTTPException(
                status_code=409, detail="User already has this achievement"
            )

        level_before = self._calculate_level(user.experience)
        user.achievements.append(achievement)
        await self._apply_achievement_rewards(db, user, achievement)

        db.add(
            ActivityLog(
                user_id=user.id,  # type: ignore
                activity_type=ActivityType.ACHIEVEMENT_UNLOCKED,  # type: ignore
                achievement_id=achievement.id,  # type: ignore
                description=f"Unlocked achievement: {achievement.name}",  # type: ignore
            )
        )
        await self._notify(
            db,
            user.id,
            NotificationType.SYSTEM,
            "Achievement unlocked",
            f"Achievement unlocked: {achievement.name}",
        )
        await self._handle_level_up(db, user, level_before)

        await db.commit()
        await db.refresh(user)
        return achievement

    async def check_and_award_achievements(
        self, db: AsyncSession, user_id: int
    ) -> List[Achievement]:
        """Check all achievements and award those where conditions are met."""
        user = await self.get(
            db, user_id, relationships=["achievements", "tasks", "habits"]
        )
        if not user:
            return []

        result = await db.execute(
            select(Achievement).options(
                selectinload(Achievement.rewards).selectinload(Reward.items)
            )
        )
        all_achievements = result.scalars().all()

        friends_count = (
            await db.execute(
                select(func.count())
                .select_from(Friendship)
                .where(
                    or_(
                        Friendship.user_id == user_id,
                        Friendship.friend_id == user_id,
                    ),
                    Friendship.status == FriendshipStatus.ACCEPTED,
                )
            )
        ).scalar_one()
        items_purchased = (
            await db.execute(
                select(func.count())
                .select_from(ActivityLog)
                .where(
                    ActivityLog.user_id == user_id,
                    ActivityLog.activity_type == ActivityType.ITEM_PURCHASED,
                )
            )
        ).scalar_one()
        bosses_defeated = (
            await db.execute(
                select(func.count())
                .select_from(BossFight)
                .where(
                    BossFight.user_id == user_id,
                    BossFight.status == BossFightStatus.WON,
                )
            )
        ).scalar_one()

        awarded = []
        for ach in all_achievements:
            if ach in user.achievements:
                continue

            current_value = {
                "tasks_completed": sum(
                    1 for t in user.tasks if t.status == TaskStatus.COMPLETED
                ),
                "habit_streak": max((h.streak for h in user.habits), default=0),
                "level": self._calculate_level(user.experience),
                "gold": user.gold,
                "experience": user.experience,
                "friends_count": friends_count,
                "items_purchased": items_purchased,
                "bosses_defeated": bosses_defeated,
            }.get(ach.condition_type)

            condition_met = (
                current_value is not None and current_value >= ach.condition_value
            )

            if condition_met:
                level_before = self._calculate_level(user.experience)
                user.achievements.append(ach)
                await self._apply_achievement_rewards(db, user, ach)
                db.add(
                    ActivityLog(
                        user_id=user.id,  # type: ignore
                        activity_type=ActivityType.ACHIEVEMENT_UNLOCKED,  # type: ignore
                        achievement_id=ach.id,  # type: ignore
                        description=f"Unlocked achievement: {ach.name}",  # type: ignore
                    )
                )
                await self._notify(
                    db,
                    user.id,
                    NotificationType.SYSTEM,
                    "Achievement unlocked",
                    f"Achievement unlocked: {ach.name}",
                )
                await self._handle_level_up(db, user, level_before)
                awarded.append(ach)

        if awarded:
            await db.commit()
        return awarded

    SIZE_MULTIPLIERS = {
        Size.SMALL: 1.0,
        Size.MEDIUM: 2.0,
        Size.BIG: 3.5,
        Size.LARGE: 5.0,
    }

    HABIT_TYPE_MULTIPLIERS = {
        HabitType.POSITIVE: 1.0,
        HabitType.NEGATIVE: -1.0,
        HabitType.NEUTRAL: 1.0,
    }

    BASE_TASK_REWARD = 10
    BASE_HABIT_REWARD = 5
    HABIT_OVERFULFILL_DECAY = 0.7
    DAILY_MISS_PENALTY = 10
    SELL_RATE = 0.5
    SELL_FLOOR = 1

    @staticmethod
    def _to_utc(dt: datetime) -> datetime:
        """Coerce a stored datetime to timezone-aware UTC.

        SQLite round-trips ``DateTime(timezone=True)`` as naive values that
        already hold UTC wall-clock time, so treat naive datetimes as UTC.
        """
        return dt if dt.tzinfo is not None else dt.replace(tzinfo=timezone.utc)

    def _completed_today(
        self, last_completed_at: Optional[datetime], now: datetime
    ) -> bool:
        """Whether the last rewarded completion happened on the current UTC day."""
        return (
            last_completed_at is not None
            and self._to_utc(last_completed_at).date() == now.date()
        )

    def _daily_overfulfillment_decay(self, habit: Habit, now: datetime) -> float:
        """Grow or reset the daily repeat counter and return the reward multiplier.

        The first rewarded completion of a UTC day resets ``overfulfillment`` to 0
        (full reward); each further completion the same day increments it, shrinking
        the reward by ``HABIT_OVERFULFILL_DECAY ** overfulfillment``. This caps daily
        farming while still granting diminishing rewards for extra effort.
        """
        if self._completed_today(habit.last_completed_at, now):
            habit.overfulfillment += 1
        else:
            habit.overfulfillment = 0
        habit.last_completed_at = now
        return self.HABIT_OVERFULFILL_DECAY**habit.overfulfillment

    def _calculate_level(self, experience: int) -> int:
        """Calculate the user's level based on their experience points."""
        level = 1
        while experience >= level * level:
            level += 1
        return level

    async def _notify(
        self,
        db: AsyncSession,
        user_id: int,
        notification_type: NotificationType,
        title: str,
        message: str,
    ) -> None:
        """Create a notification unless the user has explicitly opted out of its type.

        Notifications default to on: a preference row is only consulted to suppress
        a type the user has switched off (``is_enabled=False``). The caller commits.
        """
        result = await db.execute(
            select(UserNotificationPreference).where(
                UserNotificationPreference.user_id == user_id,
                UserNotificationPreference.notification_type == notification_type,
            )
        )
        preference = result.scalar_one_or_none()
        if preference is not None and not preference.is_enabled:
            return
        db.add(
            Notification(
                user_id=user_id,  # type: ignore
                notification_type=notification_type,  # type: ignore
                name=title,  # type: ignore
                message=message,  # type: ignore
            )
        )

    async def _handle_level_up(
        self, db: AsyncSession, user: User, level_before: int
    ) -> None:
        """Heal to full, log LEVEL_UP and notify when a level threshold is crossed."""
        level_after = self._calculate_level(user.experience)
        if level_after > level_before:
            user.health_points = 100
            db.add(
                ActivityLog(
                    user_id=user.id,  # type: ignore
                    activity_type=ActivityType.LEVEL_UP,  # type: ignore
                    description=f"Reached level {level_after}",  # type: ignore
                )
            )
            await self._notify(
                db,
                user.id,
                NotificationType.SYSTEM,
                "Level up",
                f"You reached level {level_after}!",
            )

    async def _apply_death_penalty(self, db: AsyncSession, user: User) -> bool:
        """Apply the Habitica-style death penalty when health hits zero.

        Losing all health costs one level (experience drops to the floor of the new
        level, resetting the XP bar), all gold, and one random equipped item; health
        is then restored to full. Returns True if the user died. (Habitica also
        removes a random stat point — not modelled here, so it is skipped.)
        """
        if user.health_points > 0:
            return False

        level = self._calculate_level(user.experience)
        new_level = max(1, level - 1)
        user.experience = (new_level - 1) ** 2
        user.gold = 0
        user.health_points = 100

        result = await db.execute(
            select(EquippedItem).where(EquippedItem.user_id == user.id)
        )
        equipped = result.scalars().all()
        if equipped:
            await db.delete(random.choice(equipped))

        db.add(
            ActivityLog(
                user_id=user.id,  # type: ignore
                activity_type=ActivityType.DEATH,  # type: ignore
                description=f"Died and dropped to level {new_level}",  # type: ignore
            )
        )
        return True

    async def _apply_achievement_rewards(
        self, db: AsyncSession, user: User, achievement: Achievement
    ) -> None:
        """Grant every reward attached to an achievement (gold, exp, health, items).

        An achievement may carry several rewards (M2M), so contributions are summed.
        Health stays clamped to [0, 100]. Items land in the user's inventory.
        Caller is responsible for committing.
        """
        for reward in achievement.rewards:
            user.gold += reward.gold
            user.experience += reward.experience
            user.health_points = max(
                0, min(100, user.health_points + reward.health_points)
            )
            for item in reward.items:
                await self.add_to_inventory(db, user.id, item.id)

    def _apply_task_reward(self, user: User, task: Task) -> dict:
        """Apply reward for completed task to user and task objects in memory."""
        now = datetime.now(timezone.utc)
        if task.status == TaskStatus.COMPLETED:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="Task already completed"
            )
        if self._completed_today(task.last_completed_at, now):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Task already completed today",
            )

        task.status = TaskStatus.COMPLETED
        task.last_completed_at = now
        multiplier = self.SIZE_MULTIPLIERS.get(task.task_size, 1.0)
        exp_gain = int(self.BASE_TASK_REWARD * multiplier)
        gold_gain = int(exp_gain * 0.6)

        user.experience += exp_gain
        user.gold += gold_gain

        return {
            "activity_type": "Task",
            "activity_name": task.name,
            "exp_gained": exp_gain,
            "gold_gained": gold_gain,
            "health_change": 0,
            "new_level": self._calculate_level(user.experience),
            "current_health": user.health_points,
            "streak": None,
        }

    def _apply_habit_reward(self, user: User, habit: Habit, performed: bool) -> dict:
        """Apply habit completion reward to in-memory objects. No DB commit."""
        now = datetime.now(timezone.utc)
        size_mult = self.SIZE_MULTIPLIERS.get(habit.habit_size, 1.0)
        type_mult = self.HABIT_TYPE_MULTIPLIERS.get(habit.habit_type, 1.0)
        exp_gain = 0
        gold_gain = 0
        health_change = 0

        if habit.habit_type == HabitType.POSITIVE and performed:
            decay = self._daily_overfulfillment_decay(habit, now)
            habit.streak += 1
            habit.status = HabitStatus.COMPLETED
            exp_gain = int(self.BASE_HABIT_REWARD * size_mult * type_mult * decay)
            gold_gain = int(exp_gain * 0.5)

        elif habit.habit_type == HabitType.POSITIVE and not performed:
            if habit.overfulfillment > 0:
                habit.overfulfillment -= 1
            else:
                habit.streak = 0
                habit.status = HabitStatus.FAILED

        elif habit.habit_type == HabitType.NEGATIVE and not performed:
            # Successfully avoided the bad habit: reward and grow the streak.
            decay = self._daily_overfulfillment_decay(habit, now)
            habit.streak += 1
            exp_gain = int(self.BASE_HABIT_REWARD * size_mult * abs(type_mult) * decay)
            gold_gain = int(exp_gain * 0.4)
            health_change = 0
            habit.status = HabitStatus.COMPLETED

        elif habit.habit_type == HabitType.NEGATIVE and performed:
            # Gave in to the bad habit: lose health, no reward, streak resets.
            habit.streak = 0
            exp_gain = 0
            gold_gain = 0
            health_change = int(-10 * size_mult)
            habit.status = HabitStatus.FAILED

        else:  # NEUTRAL
            if performed:
                decay = self._daily_overfulfillment_decay(habit, now)
                exp_gain = int(self.BASE_HABIT_REWARD * size_mult * type_mult * decay)
                gold_gain = int(exp_gain * 0.3)
            else:
                if habit.overfulfillment > 0:
                    habit.overfulfillment -= 1
                else:
                    habit.streak = 0
                    habit.status = HabitStatus.FAILED

        user.experience += exp_gain
        user.health_points = max(0, min(100, user.health_points + health_change))
        user.gold += gold_gain

        return {
            "activity_type": "Habit",
            "activity_name": habit.name,
            "exp_gained": exp_gain,
            "gold_gained": gold_gain,
            "health_change": health_change,
            "new_level": self._calculate_level(user.experience),
            "current_health": user.health_points,
            "streak": habit.status.value if habit.status else None,
        }

    async def complete_activity(
        self,
        db: AsyncSession,
        user_id: int,
        activity_type: str,
        activity_id: int,
        performed: bool = True,
    ) -> CompleteActivityResponse:
        """
        Complete a user activity (task or habit).
        Awards experience and gold, persists changes to the DB in a single commit.
        """
        user = await self.get(db, user_id, raise_not_found=True)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
            )

        level_before = self._calculate_level(user.experience)

        if activity_type == "task":
            result = await db.execute(
                select(Task).where(Task.id == activity_id, Task.user_id == user_id)
            )
            task = result.scalar_one_or_none()
            if not task:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND, detail="Task not found"
                )
            reward = self._apply_task_reward(user, task)

            db.add(
                ActivityLog(
                    user_id=user_id,  # type: ignore
                    activity_type=ActivityType.TASK_COMPLETED,  # type: ignore
                    task_id=activity_id,  # type: ignore
                    description=f"Completed task: {task.name}",  # type: ignore
                )
            )

        elif activity_type == "habit":
            result = await db.execute(
                select(Habit).where(Habit.id == activity_id, Habit.user_id == user_id)
            )
            habit = result.scalar_one_or_none()
            if not habit:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND, detail="Habit not found"
                )
            reward = self._apply_habit_reward(user, habit, performed)

            db.add(
                ActivityLog(
                    user_id=user_id,  # type: ignore
                    activity_type=ActivityType.HABIT_COMPLETED,  # type: ignore
                    habit_id=activity_id,  # type: ignore
                    description=f"Recorded habit: {habit.name} (performed={performed})",  # type: ignore
                )
            )

        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="activity_type must be 'task' or 'habit'",
            )

        await self._handle_level_up(db, user, level_before)
        died = await self._apply_death_penalty(db, user)

        # Reflect the final user state after level-up heal / death penalty.
        reward["current_health"] = user.health_points
        reward["new_level"] = self._calculate_level(user.experience)
        reward["died"] = died

        await db.commit()

        # Trigger achievement check after activity completion
        await self.check_and_award_achievements(db, user_id)

        return CompleteActivityResponse(**reward)

    async def complete_sub_task(self, db: AsyncSession, sub_task_id: int) -> dict:
        """Mark a sub-task done and auto-complete its parent once all are done.

        Sub-tasks are checklist steps of a parent task. Completing the final
        outstanding one finishes the parent task through the normal reward path
        (experience, gold, level-up), so a checklist actually pays out. If the
        parent is already completed (or completed earlier today) only the sub-task
        state changes.
        """
        now = datetime.now(timezone.utc)
        result = await db.execute(
            select(SubTask)
            .where(SubTask.id == sub_task_id)
            .options(selectinload(SubTask.task).selectinload(Task.sub_tasks))
        )
        sub_task = result.scalar_one_or_none()
        if sub_task is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Sub-task not found"
            )

        task = sub_task.task
        sub_task.status = TaskStatus.COMPLETED
        await db.flush()

        all_done = all(st.status == TaskStatus.COMPLETED for st in task.sub_tasks)
        task_reward = None
        if (
            all_done
            and task.status != TaskStatus.COMPLETED
            and not self._completed_today(task.last_completed_at, now)
        ):
            task_reward = await self.complete_activity(
                db,
                user_id=task.user_id,
                activity_type="task",
                activity_id=task.id,
            )
        else:
            await db.commit()

        return {
            "sub_task_id": sub_task_id,
            "task_id": task.id,
            "task_completed": task_reward is not None,
            "task_reward": task_reward,
        }

    def _rank_users(self, users: List[User]) -> List[dict]:
        """Turn an already-sorted list of users into ranked leaderboard rows."""
        return [
            {
                "rank": index,
                "user_id": user.id,
                "name": user.name,
                "level": self._calculate_level(user.experience),
                "experience": user.experience,
            }
            for index, user in enumerate(users, start=1)
        ]

    async def get_leaderboard(self, db: AsyncSession, *, limit: int = 10) -> List[dict]:
        """Top users ranked by experience (ties broken by id)."""
        result = await db.execute(
            select(User).order_by(User.experience.desc(), User.id).limit(limit)
        )
        return self._rank_users(list(result.scalars().all()))

    async def get_friends_leaderboard(
        self, db: AsyncSession, user_id: int
    ) -> List[dict]:
        """The user and their accepted friends ranked by experience."""
        me = await self.get(db, user_id, raise_not_found=True)
        assert me is not None  # raise_not_found=True raises 404 before returning None
        friends = await self.get_friends(db, user_id)
        everyone = [me, *friends]
        everyone.sort(key=lambda u: (-u.experience, u.id))
        return self._rank_users(everyone)

    async def run_daily_cron(self, db: AsyncSession, *, user_id: int) -> dict:
        """Roll the user's day over: reset dailies/habits and damage HP for misses.

        Idempotent per UTC day — a second call the same day is a no-op. Every DAILY
        task left un-completed costs HP (scaled by size, like giving in to a negative
        habit); dropping to 0 HP triggers the death penalty. Dailies and habits are
        then reset to TODO for the new day.
        """
        user = await self.get(db, user_id, raise_not_found=True)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
            )
        now = datetime.now(timezone.utc)

        if (
            user.last_cron_at is not None
            and self._to_utc(user.last_cron_at).date() >= now.date()
        ):
            return {
                "ran": False,
                "missed_dailies": 0,
                "health_lost": 0,
                "current_health": user.health_points,
                "died": False,
            }

        result = await db.execute(
            select(Task)
            .where(Task.user_id == user_id, Task.task_type == TaskType.DAILY)
            .options(selectinload(Task.sub_tasks))
        )
        dailies = result.scalars().all()

        missed = 0
        health_lost = 0
        for task in dailies:
            if task.status != TaskStatus.COMPLETED:
                missed += 1
                health_lost += int(
                    self.DAILY_MISS_PENALTY
                    * self.SIZE_MULTIPLIERS.get(task.task_size, 1.0)
                )
            task.reset_daily_task()

        await db.execute(
            update(Habit)
            .where(Habit.user_id == user_id)
            .values(status=HabitStatus.TODO)
        )

        if health_lost:
            user.health_points = max(0, user.health_points - health_lost)
        died = await self._apply_death_penalty(db, user)

        if missed:
            db.add(
                ActivityLog(
                    user_id=user_id,  # type: ignore
                    activity_type=ActivityType.DAILY_MISSED,  # type: ignore
                    description=f"Missed {missed} daily task(s), lost {health_lost} HP",  # type: ignore
                )
            )

        user.last_cron_at = now
        await db.commit()

        return {
            "ran": True,
            "missed_dailies": missed,
            "health_lost": health_lost,
            "current_health": user.health_points,
            "died": died,
        }

    async def get_user_with_relations(
        self, db: AsyncSession, user_id: int, relationships: Optional[list[str]] = None
    ):
        """Get user with all relations for detailed responses."""
        # Note: 'relationships' argument is added for compatibility with RouterFactory,
        # but we use a fixed set of comprehensive loads here.
        result = await db.execute(
            select(User)
            .where(User.id == user_id)
            .options(
                selectinload(User.habits),
                selectinload(User.tasks).selectinload(Task.sub_tasks),
                selectinload(User.achievements),
                selectinload(User.notifications),
                selectinload(User.notification_preferences),
                selectinload(User._equipped_items).selectinload(EquippedItem.item),
                selectinload(User._inventory_items).selectinload(InventoryItem.item),
            )
        )
        user = result.scalar_one_or_none()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"User with id {user_id} not found",
            )
        return user

    SLOT_ITEM_MAPPING = {
        SlotType.HELMET: ItemType.ARMOR,
        SlotType.ARMOR: ItemType.ARMOR,
        SlotType.WEAPON: ItemType.WEAPON,
        SlotType.PET: ItemType.PET,
        SlotType.ACCESSORY: ItemType.MISC,
    }

    async def add_to_inventory(
        self, db: AsyncSession, user_id: int, item_id: int, quantity: int = 1
    ) -> InventoryItem:
        """Add an item to the user's inventory."""
        await self.get(db, user_id, raise_not_found=True)

        result = await db.execute(select(Item).where(Item.id == item_id))
        item = result.scalar_one_or_none()
        if not item:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Item not found"
            )

        result = await db.execute(
            select(InventoryItem).where(
                InventoryItem.user_id == user_id, InventoryItem.item_id == item_id
            )
        )
        inventory_item = result.scalars().first()

        if inventory_item:
            inventory_item.quantity += quantity
        else:
            inventory_item = InventoryItem(
                user_id=user_id, item_id=item_id, quantity=quantity
            )  # type: ignore
            db.add(inventory_item)

        await db.commit()
        await db.refresh(inventory_item)
        return inventory_item

    async def remove_from_inventory(
        self, db: AsyncSession, user_id: int, item_id: int, quantity: int = 1
    ):
        """Remove an item from the user's inventory."""
        user = await self.get(
            db, user_id, raise_not_found=True, relationships=["_inventory_items"]
        )
        assert user is not None  # raise_not_found=True raises 404 before returning None

        inventory_item = next(
            (
                inv_item
                for inv_item in user._inventory_items
                if inv_item.item_id == item_id
            ),
            None,
        )

        if not inventory_item or inventory_item.quantity < quantity:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Not enough items in inventory",
            )

        if inventory_item.quantity > quantity:
            inventory_item.quantity -= quantity
        else:
            await db.delete(inventory_item)

        await db.commit()

    async def equip_item(
        self, db: AsyncSession, user_id: int, item_id: int, slot: SlotType
    ) -> EquippedItem:
        user = await self.get(
            db,
            user_id,
            raise_not_found=True,
            relationships=["_equipped_items"],
        )
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
            )

        result = await db.execute(select(Item).where(Item.id == item_id))
        item_to_equip = result.scalar_one_or_none()
        if not item_to_equip:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Item not found"
            )

        if self.SLOT_ITEM_MAPPING.get(slot) != item_to_equip.item_type:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot equip {item_to_equip.item_type.value} in {slot.value} slot",
            )

        required_level = item_to_equip.required_level or 0
        user_level = self._calculate_level(user.experience)
        if required_level > user_level:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Requires level {required_level}, you are level {user_level}",
            )

        result = await db.execute(
            select(InventoryItem).where(
                InventoryItem.user_id == user_id, InventoryItem.item_id == item_id
            )
        )
        inventory_item = result.scalars().first()
        if not inventory_item:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Item not in inventory",
            )

        existing_equipped = next(
            (eq for eq in user._equipped_items if eq.slot == slot), None
        )
        if existing_equipped:
            await self.unequip_item(db, user_id, slot)
            # Re-fetch user to get updated collection
            user = await self.get(
                db,
                user_id,
                raise_not_found=True,
                relationships=["_equipped_items"],
            )
            if not user:
                raise HTTPException(status_code=404, detail="User not found")

        if inventory_item.quantity > 1:
            inventory_item.quantity -= 1
        else:
            await db.delete(inventory_item)

        new_equipped_item = EquippedItem(user_id=user_id, item_id=item_id, slot=slot)  # type: ignore
        db.add(new_equipped_item)

        await db.commit()
        await db.refresh(new_equipped_item)
        await self.check_and_award_achievements(db, user_id)
        return new_equipped_item

    async def unequip_item(self, db: AsyncSession, user_id: int, slot: SlotType):
        """Unequip an item from a specific slot."""
        user = await self.get(
            db,
            user_id,
            raise_not_found=True,
            relationships=["_equipped_items"],
        )
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
            )

        equipped_item_to_remove = next(
            (eq for eq in user._equipped_items if eq.slot == slot), None
        )

        if not equipped_item_to_remove:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No item equipped in {slot.value} slot",
            )

        await self.add_to_inventory(db, user_id, equipped_item_to_remove.item_id)
        await db.delete(equipped_item_to_remove)
        await db.commit()

    async def get_inventory(
        self, db: AsyncSession, user_id: int
    ) -> List[InventoryItem]:
        """Get all inventory items for a user."""
        result = await db.execute(
            select(InventoryItem)
            .where(InventoryItem.user_id == user_id)
            .options(selectinload(InventoryItem.item))
        )
        return list(result.scalars().all())

    async def get_equipped_items(
        self, db: AsyncSession, user_id: int
    ) -> List[EquippedItem]:
        """Get all equipped items for a user."""
        result = await db.execute(
            select(EquippedItem)
            .where(EquippedItem.user_id == user_id)
            .options(selectinload(EquippedItem.item))
        )
        return list(result.scalars().all())

    async def use_item(self, db: AsyncSession, user_id: int, item_id: int) -> dict:
        """Consume one CONSUMABLE item from the user's inventory and apply its effect.

        Consumables restore HP by their ``heal_amount`` (clamped to 100). One unit is
        removed from the inventory. Non-consumables and items not owned are rejected.
        """
        user = await self.get(db, user_id, raise_not_found=True)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
            )

        result = await db.execute(select(Item).where(Item.id == item_id))
        item = result.scalar_one_or_none()
        if not item:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Item not found"
            )
        if item.item_type != ItemType.CONSUMABLE:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Item is not consumable",
            )

        result = await db.execute(
            select(InventoryItem).where(
                InventoryItem.user_id == user_id, InventoryItem.item_id == item_id
            )
        )
        inventory_item = result.scalars().first()
        if not inventory_item:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Item not in inventory",
            )

        before = user.health_points
        user.health_points = min(100, before + (item.heal_amount or 0))
        health_restored = user.health_points - before

        if inventory_item.quantity > 1:
            inventory_item.quantity -= 1
        else:
            await db.delete(inventory_item)

        db.add(
            ActivityLog(
                user_id=user_id,  # type: ignore
                activity_type=ActivityType.ITEM_USED,  # type: ignore
                item_id=item_id,  # type: ignore
                description=f"Used item: {item.name} (+{health_restored} HP)",  # type: ignore
            )
        )
        await db.commit()

        return {
            "item_id": item_id,
            "health_restored": health_restored,
            "current_health": user.health_points,
        }

    async def _sell_value(self, db: AsyncSession, item_id: int) -> int:
        """Gold refunded for selling one unit: half the cheapest shop price.

        Items never sold in any shop refund a flat ``SELL_FLOOR``.
        """
        cheapest = (
            await db.execute(
                select(func.min(ShopItem.price)).where(ShopItem.item_id == item_id)
            )
        ).scalar_one_or_none()
        if not cheapest:
            return self.SELL_FLOOR
        return max(self.SELL_FLOOR, int(cheapest * self.SELL_RATE))

    async def sell_item(self, db: AsyncSession, user_id: int, item_id: int) -> dict:
        """Sell one unit of an inventory item back for gold.

        Removes one unit from the inventory and credits the user with the item's
        sell value. Items not owned are rejected.
        """
        user = await self.get(db, user_id, raise_not_found=True)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
            )

        result = await db.execute(select(Item).where(Item.id == item_id))
        item = result.scalar_one_or_none()
        if not item:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Item not found"
            )

        result = await db.execute(
            select(InventoryItem).where(
                InventoryItem.user_id == user_id, InventoryItem.item_id == item_id
            )
        )
        inventory_item = result.scalars().first()
        if not inventory_item:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Item not in inventory",
            )

        gold_earned = await self._sell_value(db, item_id)
        user.gold += gold_earned

        if inventory_item.quantity > 1:
            inventory_item.quantity -= 1
        else:
            await db.delete(inventory_item)

        db.add(
            ActivityLog(
                user_id=user_id,  # type: ignore
                activity_type=ActivityType.ITEM_SOLD,  # type: ignore
                item_id=item_id,  # type: ignore
                description=f"Sold item: {item.name} (+{gold_earned} gold)",  # type: ignore
            )
        )
        await db.commit()
        await self.check_and_award_achievements(db, user_id)

        return {
            "item_id": item_id,
            "gold_earned": gold_earned,
            "new_gold": user.gold,
        }

    async def get_user_stats(self, db: AsyncSession, user_id: int) -> dict:
        """Derive the character's combat stats from currently equipped items.

        Sums the attack/defense/pet_power of every equipped item so the item
        stats actually influence the character sheet.
        """
        user = await self.get(db, user_id, raise_not_found=True)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
            )
        equipped = await self.get_equipped_items(db, user_id)
        return {
            "level": self._calculate_level(user.experience),
            "health_points": user.health_points,
            "attack": sum(e.item.attack for e in equipped if e.item),
            "defense": sum(e.item.defense for e in equipped if e.item),
            "pet_power": sum(e.item.pet_power for e in equipped if e.item),
        }

    async def get_active_boss_fight(
        self, db: AsyncSession, user_id: int, boss_id: int
    ) -> Optional[BossFight]:
        """Return the user's in-progress fight against a boss, if any."""
        result = await db.execute(
            select(BossFight).where(
                BossFight.user_id == user_id,
                BossFight.boss_id == boss_id,
                BossFight.status == BossFightStatus.ACTIVE,
            )
        )
        return result.scalar_one_or_none()

    async def attack_boss(self, db: AsyncSession, user_id: int, boss_id: int) -> dict:
        """Fight a boss for one round using the character's equipped combat stats.

        Player damage is ``attack + pet_power`` of equipped items minus the boss's
        defense (a chip of at least 1 always lands). If the blow does not finish the
        boss, it strikes back for ``attack`` minus the player's equipped defense;
        dropping to 0 HP triggers the usual death penalty and loses the fight.

        A fresh fight starts automatically at the boss's full health and persists
        between rounds. Defeating a boss grants its gold/experience once — a boss
        already beaten cannot be farmed again, though a lost fight may be retried.
        """
        user = await self.get(db, user_id, raise_not_found=True)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
            )

        boss = (
            await db.execute(select(Boss).where(Boss.id == boss_id))
        ).scalar_one_or_none()
        if not boss:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Boss not found"
            )

        user_level = self._calculate_level(user.experience)
        if boss.required_level > user_level:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Requires level {boss.required_level}, you are level {user_level}",
            )

        already_won = (
            await db.execute(
                select(BossFight.id).where(
                    BossFight.user_id == user_id,
                    BossFight.boss_id == boss_id,
                    BossFight.status == BossFightStatus.WON,
                )
            )
        ).first()
        if already_won is not None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Boss already defeated",
            )

        fight = await self.get_active_boss_fight(db, user_id, boss_id)
        if fight is None:
            fight = BossFight(
                user_id=user_id,  # type: ignore
                boss_id=boss_id,  # type: ignore
                boss_health=boss.max_health,  # type: ignore
                rounds=0,  # type: ignore
                status=BossFightStatus.ACTIVE,  # type: ignore
            )
            db.add(fight)

        equipped = await self.get_equipped_items(db, user_id)
        attack = sum(e.item.attack + e.item.pet_power for e in equipped if e.item)
        defense = sum(e.item.defense for e in equipped if e.item)

        player_damage = max(1, attack - boss.defense)
        fight.boss_health = max(0, fight.boss_health - player_damage)
        fight.rounds += 1

        boss_damage = 0
        died = False
        reward_gold = 0
        reward_experience = 0
        level_before = self._calculate_level(user.experience)

        if fight.boss_health == 0:
            fight.status = BossFightStatus.WON
            reward_gold = boss.reward_gold
            reward_experience = boss.reward_experience
            user.gold += reward_gold
            user.experience += reward_experience
            db.add(
                ActivityLog(
                    user_id=user_id,  # type: ignore
                    activity_type=ActivityType.BOSS_DEFEATED,  # type: ignore
                    description=f"Defeated boss: {boss.name}",  # type: ignore
                )
            )
            await self._notify(
                db,
                user_id,
                NotificationType.SYSTEM,
                "Boss defeated",
                f"You defeated {boss.name}!",
            )
            await self._handle_level_up(db, user, level_before)
        else:
            boss_damage = max(0, boss.attack - defense)
            user.health_points = max(0, user.health_points - boss_damage)
            died = await self._apply_death_penalty(db, user)
            if died:
                fight.status = BossFightStatus.LOST

        await db.commit()
        await db.refresh(fight)

        if fight.status == BossFightStatus.WON:
            await self.check_and_award_achievements(db, user_id)

        return {
            "boss_id": boss_id,
            "player_damage": player_damage,
            "boss_damage": boss_damage,
            "boss_health": fight.boss_health,
            "player_health": user.health_points,
            "rounds": fight.rounds,
            "status": fight.status,
            "died": died,
            "reward_gold": reward_gold,
            "reward_experience": reward_experience,
            "new_level": self._calculate_level(user.experience),
        }


user_crud = CRUDUser()
