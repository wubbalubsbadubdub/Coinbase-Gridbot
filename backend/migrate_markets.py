from app.db.session import engine
from sqlalchemy import text
import asyncio

async def migrate():
    async with engine.begin() as conn:
        try:
            await conn.execute(text("ALTER TABLE markets ADD COLUMN is_favorite BOOLEAN DEFAULT 0"))
            print("Added is_favorite")
        except Exception as e:
            print(f"Skipped is_favorite: {e}")
            
        try:
            await conn.execute(text("ALTER TABLE markets ADD COLUMN market_rank INTEGER DEFAULT 999999"))
            print("Added market_rank")
        except Exception as e:
            print(f"Skipped market_rank: {e}")

        try:
            await conn.execute(text("ALTER TABLE markets ADD COLUMN volume_24h FLOAT DEFAULT 0.0"))
            print("Added volume_24h")
        except Exception as e:
            print(f"Skipped volume_24h: {e}")

if __name__ == "__main__":
    asyncio.run(migrate())
