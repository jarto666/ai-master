from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, Optional

from app.core.db import SessionLocal
from app.features.users.entities import User
from sqlalchemy import insert, select, update
from sqlalchemy.ext.asyncio import AsyncSession


async def get_or_create_user(
    *, email: str, name: Optional[str] = None, session: AsyncSession | None = None
) -> Dict[str, Any]:
    """Return a plain dict representing the user, creating it if not exists."""
    external_session = session is not None
    if external_session and session is not None:
        res = await session.execute(select(User).where(User.email == email))
        existing: User | None = res.scalar_one_or_none()
        if existing:
            if name and existing.name != name:
                await session.execute(
                    update(User)
                    .where(User.id == existing.id)
                    .values(name=name, updated_at=datetime.now(timezone.utc))
                )
                await session.commit()
                existing.name = name
        else:
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
            existing = res.scalar_one()
            await session.commit()
        return {"id": str(existing.id), "email": existing.email, "name": existing.name}
    else:
        async with SessionLocal() as session2:
            res = await session2.execute(select(User).where(User.email == email))
            existing2: User | None = res.scalar_one_or_none()
            if existing2:
                if name and existing2.name != name:
                    await session2.execute(
                        update(User)
                        .where(User.id == existing2.id)
                        .values(name=name, updated_at=datetime.now(timezone.utc))
                    )
                    await session2.commit()
                    existing2.name = name
            else:
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
                res = await session2.execute(stmt)
                existing2 = res.scalar_one()
                await session2.commit()
            return {
                "id": str(existing2.id),
                "email": existing2.email,
                "name": existing2.name,
            }
