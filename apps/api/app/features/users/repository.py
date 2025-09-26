from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from app.features.users.entities import User
from sqlalchemy import insert, select, update
from sqlalchemy.ext.asyncio import AsyncSession


async def upsert_user(
    session: AsyncSession, *, email: str, name: Optional[str] = None
) -> User:
    res = await session.execute(select(User).where(User.email == email))
    user: User | None = res.scalar_one_or_none()
    if user:
        if name and user.name != name:
            await session.execute(
                update(User)
                .where(User.id == user.id)
                .values(name=name, updated_at=datetime.now(timezone.utc))
            )
            await session.commit()
            user.name = name
        return user
    stmt = (
        insert(User)
        .values(
            email=email,
            name=name,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        .returning(User)
    )
    res = await session.execute(stmt)
    user = res.scalar_one()
    await session.commit()
    return user


async def get_user_by_email(session: AsyncSession, *, email: str) -> User | None:
    res = await session.execute(select(User).where(User.email == email))
    return res.scalar_one_or_none()
