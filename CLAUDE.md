# Habit RPG API — CLAUDE.md

Habitica-подобный RPG бэкенд: задачи и привычки дают опыт и золото, есть инвентарь, экипировка, магазин, достижения, друзья.

## Как запустить

```bash
uv run uvicorn apps.main:app --reload   # dev server → http://localhost:8000
uv run pytest tests/ -v                  # 173 теста, SQLite in-memory
```

Swagger UI: `http://localhost:8000/docs`

---

## Git workflow

Коммиты прямо в `main` заблокированы хуком `no-commit-to-branch`. Работаем в ветках:

```bash
git checkout -b feature/my-feature   # новая ветка
git add . && git commit              # pre-commit запустится автоматически
git push origin feature/my-feature
# → PR на GitHub → merge в main
```

Текущая рабочая ветка: **`opus_magnum`**

### Pre-commit хуки

| Хук | Статус | Что делает |
|-----|--------|------------|
| `uv-lock` | ✅ | Проверяет актуальность `uv.lock` |
| `pre-commit-update` | ✅ | Обновляет версии хуков |
| `ruff` | ✅ | Линтер Python (автофикс) |
| `ruff-format` | ✅ | Форматтер Python |
| `mypy` | ✅ | Статическая типизация |
| `prettier` | ✅ | Форматтер YAML/MD/JSON |
| `trailing-whitespace` | ✅ | Убирает пробелы в конце строк |
| `check-yaml` / `check-toml` | ✅ | Валидация конфигов |
| `debug-statements` | ✅ | Нет print/breakpoint в коде |
| `sourcery` | 💤 | Закомментирован — нужен токен (`sourcery login`) |
| `format-justfile` | 💤 | Закомментирован — нужен `just` (`sudo dnf install just`) |

### Включить sourcery

```bash
# 1. Раскомментировать в .pre-commit-config.yaml
# 2. Залогиниться:
sourcery login
```

## Стек

- **FastAPI** + **SQLAlchemy 2.0 async** + **Pydantic v2**
- **aiosqlite** (тесты) / **asyncpg** (прод PostgreSQL)
- **JWT** (python-jose) + **Argon2** (хеширование паролей)
- **uv** как менеджер пакетов (аналог pip + venv в одном)

---

## Архитектура

```
apps/
├── models/      ← SQLAlchemy ORM-модели (таблицы БД)
├── schemas/     ← Pydantic схемы (валидация входа/выхода)
├── CRUD/        ← логика работы с БД
│   ├── base.py              ← BaseCRUD (универсальный)
│   └── from_models/         ← конкретные CRUD для каждой модели
├── api/
│   ├── router_generator.py  ← RouterFactory (генератор эндпоинтов)
│   ├── deps.py              ← get_current_user dependency
│   └── v1/endpoints/        ← HTTP маршруты
├── db/
│   ├── base.py              ← MinimalBase / SimpleBase / Base
│   └── session.py           ← get_db dependency
└── core/
    ├── config.py            ← настройки через pydantic-settings
    └── security.py          ← JWT + хеширование паролей
```

Поток запроса: `HTTP → endpoint → CRUD → SQLAlchemy → DB`

---

## BaseCRUD (`apps/CRUD/base.py`)

`BaseCRUD[Model, CreateSchema, UpdateSchema]` — дженерик-класс. Ты передаёшь SQLAlchemy-модель и Pydantic-схемы один раз, и получаешь готовые методы для работы с БД.

### Использование

```python
from apps.CRUD.base import BaseCRUD
from apps.models.habit import Habit
from apps.schemas.habit import HabitCreate, HabitUpdate

class CRUDHabit(BaseCRUD[Habit, HabitCreate, HabitUpdate]):
    def __init__(self):
        super().__init__(model=Habit)

habit_crud = CRUDHabit()
```

### Методы

| Метод                                                                         | Что делает                                                      |
| ----------------------------------------------------------------------------- | --------------------------------------------------------------- |
| `create(db, obj_in)`                                                          | Создать запись (принимает схему или dict), делает commit        |
| `get(db, id, relationships=[...])`                                            | Получить по ID, опционально загружая связи через `selectinload` |
| `get_multi(db, skip, limit, filters, search_fields, order_by, relationships)` | Список с пагинацией, фильтрами, LIKE-поиском, сортировкой       |
| `update(db, id, obj_in)`                                                      | Обновить — только переданные поля (`exclude_unset=True`)        |
| `delete(db, id)`                                                              | Удалить по ID                                                   |
| `count(db, filters)`                                                          | Подсчёт записей                                                 |
| `bulk_create(db, objs_in)`                                                    | Массовое создание                                               |
| `get_or_create(db, **kwargs)`                                                 | Найти или создать, возвращает `(объект, был_создан)`            |

### Расширение через override

Чтобы добавить бизнес-логику поверх стандартного CRUD — переопредели метод:

```python
class CRUDTask(BaseCRUD[Task, TaskCreate, TaskUpdate]):
    async def update(self, db, *, id, obj_in, commit=True):
        task = await super().update(db, id=id, obj_in=obj_in, commit=commit)
        # Создаём запись в логе при завершении задачи
        if update_data.get("status") == "COMPLETED":
            db.add(ActivityLog(user_id=task.user_id, ...))
            await db.commit()
        return task
```

### Загрузка связей

```python
# Загрузить задачу вместе с подзадачами
task = await task_crud.get(db, task_id, relationships=["sub_tasks"])

# Вложенные связи (через точку)
user = await user_crud.get(db, user_id, relationships=["tasks.sub_tasks"])
```

---

## RouterFactory (`apps/api/router_generator.py`)

Фабрика, которая генерирует **8 стандартных CRUD-эндпоинтов** за один вызов. Без неё пришлось бы вручную писать одинаковый код для каждого ресурса.

### Использование

```python
from apps.api.router_generator import RouterFactory

factory = RouterFactory(
    crud=habit_crud,                          # экземпляр BaseCRUD
    create_schema=HabitCreate,                # Pydantic схема для POST
    update_schema=HabitUpdate,                # Pydantic схема для PATCH
    response_schema=HabitResponse,            # полный ответ (с вложенными объектами)
    response_short_schema=HabitResponseShort, # краткий ответ (для списков)
    resource_name="habit",
    resource_name_plural="habits",
    tag="Habits",
    prefix="/habits",
    current_user_dependency=Depends(get_current_user),
    # with_relations_method="get_user_with_relations"  # кастомный метод загрузки, если нужен
)
router = factory.create_router()
```

### Что генерируется

| Метод  | Путь                  | Описание                                                                |
| ------ | --------------------- | ----------------------------------------------------------------------- |
| POST   | `/habits/`            | Создать                                                                 |
| GET    | `/habits/`            | Список (пагинация, фильтр `?name=`, сортировка `?order_by=-created_at`) |
| GET    | `/habits/count`       | Количество                                                              |
| GET    | `/habits/{id}`        | Получить по ID                                                          |
| PATCH  | `/habits/{id}`        | Обновить (только переданные поля)                                       |
| DELETE | `/habits/{id}`        | Удалить                                                                 |
| GET    | `/habits/{id}/exists` | Проверить существование                                                 |
| POST   | `/habits/bulk`        | Массовое создание (до 100 шт.)                                          |

### Как RouterFactory загружает связи автоматически

RouterFactory смотрит на поля `response_schema` — если поле аннотировано как Pydantic `BaseModel` (не `str`/`int`/etc.), он считает его связанной сущностью и загружает через `selectinload`. Поэтому достаточно добавить поле в Response-схему:

```python
class ShopItemResponse(ShopItemResponseShort):
    item: Optional[ItemResponseShort] = None  # ← RouterFactory автоматически сделает selectinload
```

### Добавление кастомных эндпоинтов поверх RouterFactory

```python
router = factory.create_router()

@router.post("/{habit_id}/complete")  # добавляем свой эндпоинт
async def complete_habit(habit_id: int, ...):
    ...
```

### Безопасность

RouterFactory **не делает** проверок владельца — это чисто механический CRUD. Security-логика пишется вручную только в специфических эндпоинтах (например, `complete_activity` проверяет что пользователь completает своё задание).

---

## Иерархия базовых моделей (`apps/db/base.py`)

```
MinimalBase   ← id, created_at, updated_at
    └── SimpleBase  ← + name (NOT NULL), description (nullable)
            └── Base  ← алиас SimpleBase (для совместимости)
```

**Правило выбора:**

- `MinimalBase` → таблицы-связки и логи, у которых нет смыслового "имени":
  - `Friendship`, `InventoryItem`, `EquippedItem`, `ActivityLog`
- `SimpleBase` / `Base` → доменные сущности с именем:
  - `User`, `Task`, `Habit`, `Item`, `Achievement`, `Notification`, `ShopItem`, `Reward`...

Ошибка `NOT NULL constraint failed: *.name` означает что junction-таблица ошибочно наследует `SimpleBase`.

---

## Схемы Pydantic (`apps/schemas/`)

Паттерн для каждого ресурса — 4 класса:

```python
class HabitCreate(SimpleBaseSchemaCreate):   # для POST — name обязателен
    habit_type: HabitType = HabitType.NEUTRAL
    user_id: Optional[int] = None            # RouterFactory подставит из токена если None

class HabitUpdate(BaseModel):                # для PATCH — всё Optional
    name: Optional[str] = None
    habit_type: Optional[HabitType] = None
    model_config = ConfigDict(from_attributes=True)

class HabitResponseShort(BaseSchemaResponse):  # для списков — минимум полей
    habit_type: HabitType
    streak: int

class HabitResponse(HabitResponseShort):     # полный ответ — добавляем вложенные объекты
    user: Optional[UserResponseShort] = None
```

**Обязательно** используй `model_config = ConfigDict(from_attributes=True)` — без этого Pydantic не умеет читать из ORM-объектов SQLAlchemy.

Исключение: если модель без `name` (использует `MinimalBase`) — наследуй от `BaseModel` напрямую, а не от `BaseSchemaResponse`.

---

## Аутентификация

- `apps/api/deps.py` — `get_current_user`: читает JWT из `Authorization: Bearer <token>` заголовка, возвращает объект `User`
- `apps/core/security.py` — `create_access_token`, `verify_password`, `get_password_hash`
- RouterFactory принимает `current_user_dependency=Depends(get_current_user)` и пробрасывает его в каждый эндпоинт

Если `current_user_dependency=None` — эндпоинты публичные (без аутентификации).

---

## Тесты (`tests/`)

Все тесты используют SQLite in-memory — никакой реальной БД не нужно.

### Фикстуры (`conftest.py`)

| Фикстура                     | Что даёт                                                              |
| ---------------------------- | --------------------------------------------------------------------- |
| `db_session`                 | Async SQLite сессия, откатывается после каждого теста                 |
| `client`                     | FastAPI TestClient с тестовой БД                                      |
| `test_user`                  | Создан пользователь в БД                                              |
| `auth_client`                | TestClient с `Authorization: Bearer <jwt>` заголовком для `test_user` |
| `create_test_user_for_tasks` | Отдельный пользователь (не `test_user`) для тестирования ресурсов     |

### Паттерн тестов

Тесты создают ресурсы с `user_id` другого пользователя (`create_test_user_for_X`), но делают запросы через `auth_client` (от `test_user`). RouterFactory это разрешает — он не проверяет владельца.

```python
def test_create_habit(auth_client, create_test_user_for_habits):
    response = auth_client.post("/api/v1/habits/", json={
        "name": "Exercise",
        "user_id": create_test_user_for_habits.id,  # другой пользователь!
    })
    assert response.status_code == 201
```

### Запуск

```bash
uv run pytest tests/ -v          # все тесты
uv run pytest tests/api/v1/test_habits_endpoints.py -v  # конкретный файл
uv run pytest -k "test_create"   # по названию
```
