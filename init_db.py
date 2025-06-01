import asyncio
from app.core.database import engine
from app.models.base import Base

async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print("Base de données créée avec succès!")

if __name__ == "__main__":
    asyncio.run(init_db())
