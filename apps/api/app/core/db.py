from __future__ import annotations

from typing import AsyncGenerator, AsyncIterator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import declarative_base

from .settings import settings

Base = declarative_base()

# Create async engine (psycopg3 async)
engine = create_async_engine(settings.DATABASE_URL, echo=False, future=True)

# Async session factory (aka DB context)
db_sessionmaker = async_sessionmaker(
    bind=engine, expire_on_commit=False, class_=AsyncSession
)

# Back-compat alias (will be removed later)
SessionLocal = db_sessionmaker


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    async with db_sessionmaker() as session:
        yield session


# Back-compat alias (previous name)
async def get_db_session() -> AsyncIterator[AsyncSession]:
    async for s in get_session():
        yield s
