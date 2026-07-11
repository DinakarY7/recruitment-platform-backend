from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from app.config import settings

# Create the async engine for CockroachDB
connect_args = {}
if "cockroachlabs.cloud" in settings.DATABASE_URL:
    connect_args["ssl"] = True

engine = create_async_engine(
    settings.DATABASE_URL,
    echo=False,  # Set to True for SQL logging in development
    future=True,
    # CockroachDB recommends connection pool settings
    pool_size=20,
    max_overflow=10,
    pool_recycle=1800,
    connect_args=connect_args,
)

# Async session factory
AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)

async def init_db():
    """Initializes the database, creating all tables defined in models.py."""
    from sqlmodel import SQLModel
    # Import models here to ensure they are registered with SQLModel.metadata
    from app.models import User, Company, CandidateProfile, Job, Application
    
    async with engine.begin() as conn:
        # Create all tables if they don't exist
        await conn.run_sync(SQLModel.metadata.create_all)

async def get_session() -> AsyncSession:
    """Dependency for retrieving database session in FastAPI endpoints."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
