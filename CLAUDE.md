# Habit RPG API — CLAUDE.md

A Habitica-style RPG backend: tasks and habits grant experience and gold; there is an inventory, equipment, a shop, achievements, and friends.

## Project goals

- **Open pet project** — bring it to a public repo: clean code, documentation, everything understandable to an outsider.
- **Master the stack** — deeply understand everything in use: FastAPI, SQLAlchemy async, Pydantic v2, JWT, testing, linters, git workflow.

## How to run

```bash
uv run uvicorn apps.main:app --reload   # dev server → http://localhost:8000
uv run pytest tests/ -v                  # 217 tests, SQLite in-memory
```

Swagger UI: `http://localhost:8000/docs`

### Docker (dev)

```bash
cp compose.override.dev.yaml compose.override.yaml   # once, locally
docker compose up --build                             # bring up app + PostgreSQL
docker compose watch                                  # hot-reload on changes
```

`compose.override.yaml` is in `.gitignore` — not committed. Based on `compose.override.dev.yaml`.

---

## Git workflow

Commits straight to `main` are blocked by the `no-commit-to-branch` hook. We work in branches:

```bash
git checkout -b feature/my-feature   # new branch
git add . && git commit              # pre-commit runs automatically
git push origin feature/my-feature
# → PR on GitHub → merge into main
```

Current working branch: **`opus_magnum`**

### CI (GitHub Actions)

`.github/workflows/ci.yml` runs on every push to `main` and on every pull request. Two parallel jobs:

- **`test`** — `setup-uv` (cache keyed on `uv.lock`) → `uv sync --frozen` → `pytest`.
- **`lint`** — `pre-commit/action` runs all hooks (installs itself independently of `uv sync`).

### Pre-commit hooks

| Hook                        | Status | What it does                                           |
| --------------------------- | ------ | ------------------------------------------------------ |
| `uv-lock`                   | ✅     | Checks that `uv.lock` is up to date                    |
| `pre-commit-update`         | ✅     | Updates hook versions                                  |
| `ruff`                      | ✅     | Python linter (autofix)                                |
| `ruff-format`               | ✅     | Python formatter                                       |
| `mypy`                      | ✅     | Static typing                                          |
| `prettier`                  | ✅     | YAML/MD/JSON formatter                                 |
| `trailing-whitespace`       | ✅     | Strips trailing whitespace                             |
| `check-yaml` / `check-toml` | ✅     | Config validation                                      |
| `debug-statements`          | ✅     | No print/breakpoint in code                            |
| `sourcery`                  | 💤     | Commented out — needs a token (`sourcery login`)       |
| `format-justfile`           | 💤     | Commented out — needs `just` (`sudo dnf install just`) |

### Enable sourcery

```bash
# 1. Uncomment it in .pre-commit-config.yaml
# 2. Log in:
sourcery login
```

## Stack

- **FastAPI** + **SQLAlchemy 2.0 async** + **Pydantic v2**
- **aiosqlite** (tests) / **asyncpg** (production PostgreSQL)
- **JWT** (python-jose) + **Argon2** (password hashing)
- **uv** as the package manager (pip + venv rolled into one)

---

## Architecture

```
apps/
├── models/      ← SQLAlchemy ORM models (DB tables)
├── schemas/     ← Pydantic schemas (input/output validation)
├── CRUD/        ← database logic
│   ├── base.py              ← BaseCRUD (generic)
│   └── from_models/         ← concrete CRUD for each model
├── api/
│   ├── router_generator.py  ← RouterFactory (endpoint generator)
│   ├── deps.py              ← get_current_user dependency
│   └── v1/endpoints/        ← HTTP routes
├── db/
│   ├── base.py              ← MinimalBase / SimpleBase / Base
│   └── session.py           ← get_db dependency
└── core/
    ├── config.py            ← settings via pydantic-settings
    └── security.py          ← JWT + password hashing
```

Request flow: `HTTP → endpoint → CRUD → SQLAlchemy → DB`

---

## BaseCRUD (`apps/CRUD/base.py`)

`BaseCRUD[Model, CreateSchema, UpdateSchema]` is a generic class. You pass the SQLAlchemy model and Pydantic schemas once and get ready-made methods for working with the DB.

### Usage

```python
from apps.CRUD.base import BaseCRUD
from apps.models.habit import Habit
from apps.schemas.habit import HabitCreate, HabitUpdate

class CRUDHabit(BaseCRUD[Habit, HabitCreate, HabitUpdate]):
    def __init__(self):
        super().__init__(model=Habit)

habit_crud = CRUDHabit()
```

### Methods

| Method                                                                        | What it does                                                     |
| ----------------------------------------------------------------------------- | ---------------------------------------------------------------- |
| `create(db, obj_in)`                                                          | Create a record (accepts a schema or dict), commits              |
| `get(db, id, relationships=[...])`                                            | Get by ID, optionally eager-loading relations via `selectinload` |
| `get_multi(db, skip, limit, filters, search_fields, order_by, relationships)` | List with pagination, filters, LIKE search, sorting              |
| `update(db, id, obj_in)`                                                      | Update — only the passed fields (`exclude_unset=True`)           |
| `delete(db, id)`                                                              | Delete by ID                                                     |
| `count(db, filters)`                                                          | Count records                                                    |
| `bulk_create(db, objs_in)`                                                    | Bulk create                                                      |
| `get_or_create(db, **kwargs)`                                                 | Find or create, returns `(object, was_created)`                  |

### Extending via override

To add business logic on top of the standard CRUD, override the method:

```python
class CRUDTask(BaseCRUD[Task, TaskCreate, TaskUpdate]):
    async def update(self, db, *, id, obj_in, commit=True):
        task = await super().update(db, id=id, obj_in=obj_in, commit=commit)
        # Write a log entry when the task is completed
        if update_data.get("status") == "COMPLETED":
            db.add(ActivityLog(user_id=task.user_id, ...))
            await db.commit()
        return task
```

### Loading relations

```python
# Load a task together with its sub-tasks
task = await task_crud.get(db, task_id, relationships=["sub_tasks"])

# Nested relations (via dot notation)
user = await user_crud.get(db, user_id, relationships=["tasks.sub_tasks"])
```

---

## RouterFactory (`apps/api/router_generator.py`)

A factory that generates **8 standard CRUD endpoints** in a single call. Without it you would have to hand-write the same boilerplate for every resource.

### Usage

```python
from apps.api.router_generator import RouterFactory

factory = RouterFactory(
    crud=habit_crud,                          # BaseCRUD instance
    create_schema=HabitCreate,                # Pydantic schema for POST
    update_schema=HabitUpdate,                # Pydantic schema for PATCH
    response_schema=HabitResponse,            # full response (with nested objects)
    response_short_schema=HabitResponseShort, # short response (for lists)
    resource_name="habit",
    resource_name_plural="habits",
    tag="Habits",
    prefix="/habits",
    current_user_dependency=Depends(get_current_user),
    # with_relations_method="get_user_with_relations"  # custom loading method, if needed
)
router = factory.create_router()
```

### What gets generated

| Method | Path                  | Description                                                         |
| ------ | --------------------- | ------------------------------------------------------------------- |
| POST   | `/habits/`            | Create                                                              |
| GET    | `/habits/`            | List (pagination, filter `?name=`, sorting `?order_by=-created_at`) |
| GET    | `/habits/count`       | Count                                                               |
| GET    | `/habits/{id}`        | Get by ID                                                           |
| PATCH  | `/habits/{id}`        | Update (only the passed fields)                                     |
| DELETE | `/habits/{id}`        | Delete                                                              |
| GET    | `/habits/{id}/exists` | Check existence                                                     |
| POST   | `/habits/bulk`        | Bulk create (up to 100)                                             |

### How RouterFactory loads relations automatically

RouterFactory inspects the fields of `response_schema` — if a field is annotated as a Pydantic `BaseModel` (not `str`/`int`/etc.), it treats it as a related entity and loads it via `selectinload`. So it is enough to add the field to the Response schema:

```python
class ShopItemResponse(ShopItemResponseShort):
    item: Optional[ItemResponseShort] = None  # ← RouterFactory will selectinload automatically
```

### Adding custom endpoints on top of RouterFactory

```python
router = factory.create_router()

@router.post("/{habit_id}/complete")  # add your own endpoint
async def complete_habit(habit_id: int, ...):
    ...
```

### Security

RouterFactory does **not** perform ownership checks — it is purely mechanical CRUD. Security logic is written by hand only in specific endpoints (for example, `complete_activity` checks that the user is completing their own task).

---

## Base model hierarchy (`apps/db/base.py`)

```
MinimalBase   ← id, created_at, updated_at
    └── SimpleBase  ← + name (NOT NULL), description (nullable)
            └── Base  ← alias of SimpleBase (for compatibility)
```

**Choosing rule:**

- `MinimalBase` → junction tables and logs that have no meaningful "name":
  - `Friendship`, `InventoryItem`, `EquippedItem`, `ActivityLog`
- `SimpleBase` / `Base` → domain entities with a name:
  - `User`, `Task`, `Habit`, `Item`, `Achievement`, `Notification`, `ShopItem`, `Reward`...

A `NOT NULL constraint failed: *.name` error means a junction table wrongly inherits from `SimpleBase`.

---

## Pydantic schemas (`apps/schemas/`)

The pattern for each resource is 4 classes:

```python
class HabitCreate(SimpleBaseSchemaCreate):   # for POST — name is required
    habit_type: HabitType = HabitType.NEUTRAL
    user_id: Optional[int] = None            # RouterFactory fills it from the token if None

class HabitUpdate(BaseModel):                # for PATCH — everything Optional
    name: Optional[str] = None
    habit_type: Optional[HabitType] = None
    model_config = ConfigDict(from_attributes=True)

class HabitResponseShort(BaseSchemaResponse):  # for lists — minimal fields
    habit_type: HabitType
    streak: int

class HabitResponse(HabitResponseShort):     # full response — add nested objects
    user: Optional[UserResponseShort] = None
```

**Always** use `model_config = ConfigDict(from_attributes=True)` — without it Pydantic cannot read from SQLAlchemy ORM objects.

Exception: if a model has no `name` (uses `MinimalBase`), inherit from `BaseModel` directly instead of `BaseSchemaResponse`.

---

## Authentication

- `apps/api/deps.py` — `get_current_user`: reads the JWT from the `Authorization: Bearer <token>` header and returns a `User` object
- `apps/core/security.py` — `create_access_token`, `verify_password`, `get_password_hash`
- RouterFactory accepts `current_user_dependency=Depends(get_current_user)` and passes it into every endpoint

If `current_user_dependency=None`, the endpoints are public (no authentication).

---

## Tests (`tests/`)

All tests use SQLite in-memory — no real database needed.

### Fixtures (`conftest.py`)

| Fixture                      | What it provides                                                        |
| ---------------------------- | ----------------------------------------------------------------------- |
| `db_session`                 | Async SQLite session, rolled back after each test                       |
| `client`                     | FastAPI TestClient with the test DB                                     |
| `test_user`                  | A user created in the DB                                                |
| `auth_client`                | TestClient with an `Authorization: Bearer <jwt>` header for `test_user` |
| `create_test_user_for_tasks` | A separate user (not `test_user`) for testing resources                 |

### Test pattern

Tests create resources with another user's `user_id` (`create_test_user_for_X`) but make requests through `auth_client` (as `test_user`). RouterFactory allows this — it does not check ownership.

```python
def test_create_habit(auth_client, create_test_user_for_habits):
    response = auth_client.post("/api/v1/habits/", json={
        "name": "Exercise",
        "user_id": create_test_user_for_habits.id,  # a different user!
    })
    assert response.status_code == 201
```

### Running

```bash
uv run pytest tests/ -v          # all tests
uv run pytest tests/api/v1/test_habits_endpoints.py -v  # a specific file
uv run pytest -k "test_create"   # by name
```
