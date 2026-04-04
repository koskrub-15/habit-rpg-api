import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from apps.db.base import Base as DBBase
from apps.main import app

from apps.db.session import get_db

SQLALCHEMY_DATABASE_URL = "sqlite+aiosqlite:///./test.db"
engine = create_async_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)
TestingSessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


@pytest_asyncio.fixture(name="db_session")
async def db_session_fixture() -> AsyncSession:
    """
    Creates an independent AsyncSession for each test.
    After each test, the transaction is rolled back and the session is closed.
    This ensures that each test runs with a clean database,
    isolating tests from each other.

    Yields:
        AsyncSession: Database session for use in tests.
    """
    async with engine.begin() as connection:
        await connection.run_sync(DBBase.metadata.drop_all)
        await connection.run_sync(DBBase.metadata.create_all)

    async with TestingSessionLocal() as session:
        yield session
        await session.rollback()


@pytest_asyncio.fixture(name="client")
async def client_fixture(db_session: AsyncSession) -> AsyncClient:
    """
    Creates a FastAPI test client that uses a mocked database session.
    This allows sending requests to your API in a test environment without
    actual interaction with a real database.

    Args:
        db_session (AsyncSession): Fixture providing the mocked DB session.

    Yields:
        httpx.AsyncClient: Asynchronous FastAPI test client.
    """

    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        yield client

    app.dependency_overrides.clear()
