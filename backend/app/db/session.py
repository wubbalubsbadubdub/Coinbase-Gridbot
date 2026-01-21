from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from app.config import settings
import os

# Ensure the directory for the SQLite database exists
os.makedirs("data", exist_ok=True)

# Use SQLite for local development
DATABASE_URL = "sqlite+aiosqlite:///data/gridbot.db"

engine = create_async_engine(
    DATABASE_URL,
    echo=settings.ENV == "dev",  # Log SQL in dev mode
)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    expire_on_commit=False,
)

async def get_db():
    async with AsyncSessionLocal() as session:
        yield session
