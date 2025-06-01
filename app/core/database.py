from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from app.core.config import settings
from contextlib import asynccontextmanager

# Configuration SQLite
engine = create_async_engine(
    settings.DB_URL,
    connect_args={"check_same_thread": False},  # Nécessaire pour SQLite
    echo=settings.DEBUG
)

async_session = sessionmaker(
    engine,
    expire_on_commit=False,
    class_=AsyncSession
)

@asynccontextmanager
async def get_db():
    """Gestionnaire de contexte asynchrone pour les sessions de base de données"""
    async with async_session() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
