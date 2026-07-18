import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from apps.main import app
from apps.db.session import get_db
from apps.core.security import create_access_token
from apps.models.user import User
from apps.CRUD.from_models.user import user_crud
from typing import Optional
from apps.schemas.user import UserCreate

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
    """
    async with engine.begin() as connection:
        from apps.db.base import mapper_registry

        await connection.run_sync(mapper_registry.metadata.drop_all)
        await connection.run_sync(mapper_registry.metadata.create_all)

    async with TestingSessionLocal() as session:
        yield session
        await session.rollback()


@pytest_asyncio.fixture(name="client")
async def client_fixture(db_session: AsyncSession) -> AsyncClient:
    """
    Creates a FastAPI test client that uses a mocked database session.
    """

    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        yield client

    app.dependency_overrides.clear()


@pytest_asyncio.fixture(name="test_user")
async def test_user_fixture(db_session: AsyncSession) -> User:
    """
    Creates a superuser used by the bulk of the CRUD tests.

    The default authenticated user is a superuser so that the existing tests,
    which exercise CRUD mechanics across resources owned by other users, keep
    passing. Ownership enforcement for regular users is covered separately in
    test_authorization.py via the `normal_user` / `normal_client` fixtures.
    """
    user_in = UserCreate(
        email="test@example.com", password="password123", name="Test User"
    )
    user = await user_crud.create(db_session, obj_in=user_in)
    user.is_superuser = True
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest_asyncio.fixture(name="normal_user")
async def normal_user_fixture(db_session: AsyncSession) -> User:
    """Creates a regular (non-superuser) user for authorization tests."""
    user_in = UserCreate(
        email="normal@example.com", password="password123", name="Normal User"
    )
    return await user_crud.create(db_session, obj_in=user_in)


@pytest_asyncio.fixture(name="normal_client")
async def normal_client_fixture(client: AsyncClient, normal_user: User) -> AsyncClient:
    """Returns a client authenticated as a regular (non-superuser) user."""
    access_token = create_access_token(subject=normal_user.id)
    client.headers.update({"Authorization": f"Bearer {access_token}"})
    return client


@pytest_asyncio.fixture(name="auth_client")
async def auth_client_fixture(client: AsyncClient, test_user: User) -> AsyncClient:
    """
    Returns a client with an Authorization header for the test user.
    """
    access_token = create_access_token(subject=test_user.id)
    client.headers.update({"Authorization": f"Bearer {access_token}"})
    return client


@pytest.fixture
def auth_headers():
    """
    Returns a callable that builds an Authorization header for an arbitrary user,
    for tests that need to act as several different authenticated users.
    """

    def _headers(user: User) -> dict:
        access_token = create_access_token(subject=user.id)
        return {"Authorization": f"Bearer {access_token}"}

    return _headers


@pytest_asyncio.fixture
async def create_test_user(db_session: AsyncSession):
    """
    Fixture to create test users dynamically within tests.
    It returns a callable that can be used to create users with unique emails.
    """
    user_counter = 0

    async def _create_user(
        email: Optional[str] = None,
        name: str = "Test User",
        password: str = "password123",
    ) -> User:
        nonlocal user_counter
        if email is None:
            email = f"test_user_{user_counter}@example.com"
            user_counter += 1

        user_in = UserCreate(email=email, password=password, name=name)
        user = await user_crud.create(db_session, obj_in=user_in)
        return user

    return _create_user
