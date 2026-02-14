import asyncio
import logging

from fastapi import FastAPI

from apps.api.v1.router import api_router
from apps.core.config import settings

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)


app = FastAPI(
    title=settings.PROJECT_NAME,
    debug=settings.DEBUG,
)


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
