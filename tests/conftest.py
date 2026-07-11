import asyncio
import pytest
import pytest_asyncio
from typing import AsyncGenerator
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlmodel import SQLModel
from httpx import AsyncClient, ASGITransport

from app.config import settings
from app.database import get_session
from app.main import app

# Define test database URL by replacing the main database name with defaultdb_test
TEST_DATABASE_URL = settings.DATABASE_URL.replace("/defaultdb", "/defaultdb_test")

@pytest_asyncio.fixture(scope="session", autouse=True)
async def setup_test_db():
    """Session-scoped database table setup. Executed once at start."""
    # 1. Create the test database if it doesn't exist
    admin_engine = create_async_engine(
        settings.DATABASE_URL,
        isolation_level="AUTOCOMMIT",
        connect_args={"ssl": True} if "cockroachlabs.cloud" in settings.DATABASE_URL else {}
    )
    async with admin_engine.connect() as conn:
        await conn.execute(text("CREATE DATABASE IF NOT EXISTS defaultdb_test"))
    await admin_engine.dispose()
    
    # 2. Connect and create all tables once
    init_engine = create_async_engine(
        TEST_DATABASE_URL,
        connect_args={"ssl": True} if "cockroachlabs.cloud" in settings.DATABASE_URL else {}
    )
    async with init_engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.drop_all)
        await conn.run_sync(SQLModel.metadata.create_all)
    await init_engine.dispose()
    
    yield

@pytest_asyncio.fixture
async def db_engine():
    """Function-scoped database engine. Prevents event loop mismatch by binding to the active test loop."""
    engine = create_async_engine(
        TEST_DATABASE_URL,
        connect_args={"ssl": True} if "cockroachlabs.cloud" in settings.DATABASE_URL else {}
    )
    yield engine
    await engine.dispose()

@pytest_asyncio.fixture
async def db_session(db_engine) -> AsyncGenerator[AsyncSession, None]:
    """Provide a clean session and truncate tables to guarantee clean test separation without re-creating schemas."""
    session_local = async_sessionmaker(
        bind=db_engine,
        class_=AsyncSession,
        expire_on_commit=False
    )
    
    # Clean database tables prior to each test (child first due to FK constraints)
    async with db_engine.begin() as conn:
        await conn.execute(text("TRUNCATE TABLE applications, jobs, candidate_profiles, companies, users CASCADE"))
        
    async with session_local() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()

@pytest_asyncio.fixture
async def client(db_engine, db_session) -> AsyncGenerator[AsyncClient, None]:
    """Provide an HTTPX AsyncClient for testing FastAPI routes, binding requests to the active session."""
    
    # Dependency override yields the clean, active test session
    async def override_get_session():
        yield db_session

    app.dependency_overrides[get_session] = override_get_session
    
    # Create client using ASGITransport
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac
        
    app.dependency_overrides.clear()
