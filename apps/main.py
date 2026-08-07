import logging

from typing import Any

from fastapi import FastAPI
from fastapi.encoders import jsonable_encoder
from fastapi.middleware.cors import CORSMiddleware
from starlette.responses import JSONResponse

from apps.api.v1.router import api_router
from apps.core.config import settings

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)


class CustomJSONResponse(JSONResponse):
    def render(self, content: Any) -> bytes:
        return super().render(jsonable_encoder(content))


API_DESCRIPTION = """
A **Habitica-style RPG backend**: complete real-life tasks and habits to earn
experience and gold, then spend them on gear in a rotating shop.

### Features

- 🔐 **JWT auth** with access/refresh rotation, token revocation, and Argon2 hashing
- ✅ **Tasks & habits** with streaks, sizes, and daily reset
- 🛒 **Shop** with time-based rotations, stock, and themed items
- 🎒 **Inventory & equipment** across weapon / armor / accessory / pet slots
- 🏆 **Achievements & rewards** and an automatic **activity log**
- 🤝 **Friends** (request / accept / decline / remove)

Built with FastAPI, async SQLAlchemy 2.0, and Pydantic v2.
"""

TAGS_METADATA = [
    {"name": "Auth", "description": "Register, login, and refresh/revoke tokens."},
    {
        "name": "Users",
        "description": "User accounts, progression, inventory, equipment.",
    },
    {"name": "Tasks", "description": "One-off and daily tasks, with sub-tasks."},
    {"name": "Habits", "description": "Positive/negative habits and streak tracking."},
    {"name": "Items", "description": "The item catalog (gear, pets, consumables)."},
    {"name": "Shop", "description": "Buy items with earned gold."},
    {
        "name": "Store",
        "description": "Shop inventory, rotations, and themed offerings.",
    },
    {"name": "Achievements", "description": "Achievements and reward bundles."},
    {"name": "Notifications", "description": "Notifications and per-user preferences."},
    {"name": "Friends", "description": "Friend requests and the friends list."},
    {"name": "Activity Log", "description": "Automatic history of important actions."},
    {"name": "Health", "description": "Liveness probe for load balancers."},
]

app = FastAPI(
    title=settings.PROJECT_NAME,
    description=API_DESCRIPTION,
    summary="Gamified habit tracking and task management API.",
    version="0.1.0",
    debug=settings.DEBUG,
    default_response_class=CustomJSONResponse,
    openapi_tags=TAGS_METADATA,
    contact={
        "name": "Konstantin Bevz",
        "url": "https://github.com/koskrub-15/habit-rpg-api",
    },
    license_info={"name": "MIT", "url": "https://opensource.org/licenses/MIT"},
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health", tags=["Health"], summary="Liveness probe")
async def health() -> dict[str, str]:
    """Return service liveness status for load balancers and uptime checks."""
    return {"status": "ok"}


app.include_router(api_router, prefix="/api/v1")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        reload=settings.DEBUG,
        log_level="info",
    )
