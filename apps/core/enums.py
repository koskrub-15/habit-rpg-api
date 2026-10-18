import enum


class TaskStatus(enum.Enum):
    TODO = "TODO"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"


class TaskType(enum.Enum):
    DAILY = "DAILY"
    REGULAR = "REGULAR"


class Size(enum.Enum):
    SMALL = "SMALL"
    MEDIUM = "MEDIUM"
    BIG = "BIG"
    LARGE = "LARGE"


class HabitType(enum.Enum):
    POSITIVE = "POSITIVE"
    NEGATIVE = "NEGATIVE"
    NEUTRAL = "NEUTRAL"


class HabitStatus(enum.Enum):
    TODO = "TODO"
    FAILED = "FAILED"
    COMPLETED = "COMPLETED"


class Rarity(enum.Enum):
    COMMON = "COMMON"
    UNCOMMON = "UNCOMMON"
    RARE = "RARE"
    EPIC = "EPIC"
    LEGENDARY = "LEGENDARY"


class ItemType(enum.Enum):
    WEAPON = "WEAPON"
    ARMOR = "ARMOR"
    ACCESSORY = "ACCESSORY"
    PET = "PET"
    CONSUMABLE = "CONSUMABLE"
    MISC = "MISC"


class ItemTheme(enum.Enum):
    COMMON = "COMMON"
    WINTER = "WINTER"
    SUMMER = "SUMMER"
    SPRING = "SPRING"
    FALL = "FALL"
    ASIAN = "ASIAN"
    MEDIEVAL = "MEDIEVAL"
    HALLOWEEN = "HALLOWEEN"
    CHRISTMAS = "CHRISTMAS"


class SlotType(enum.Enum):
    HELMET = "HELMET"
    ARMOR = "ARMOR"
    ACCESSORY = "ACCESSORY"
    WEAPON = "WEAPON"
    PET = "PET"


class FriendshipStatus(enum.Enum):
    PENDING = "PENDING"
    ACCEPTED = "ACCEPTED"
    DECLINED = "DECLINED"


class NotificationType(enum.Enum):
    TASK_REMINDER = "TASK_REMINDER"
    STREAK_REMINDER = "STREAK_REMINDER"
    NEWS = "NEWS"
    FRIEND_REQUEST = "FRIEND_REQUEST"
    SYSTEM = "SYSTEM"


class ActivityType(enum.Enum):
    TASK_COMPLETED = "TASK_COMPLETED"
    HABIT_COMPLETED = "HABIT_COMPLETED"
    ITEM_PURCHASED = "ITEM_PURCHASED"
    ITEM_SOLD = "ITEM_SOLD"
    ITEM_USED = "ITEM_USED"
    ACHIEVEMENT_UNLOCKED = "ACHIEVEMENT_UNLOCKED"
    LEVEL_UP = "LEVEL_UP"
    DEATH = "DEATH"
    DAILY_MISSED = "DAILY_MISSED"
    BOSS_DEFEATED = "BOSS_DEFEATED"


class BossFightStatus(enum.Enum):
    ACTIVE = "ACTIVE"
    WON = "WON"
    LOST = "LOST"
