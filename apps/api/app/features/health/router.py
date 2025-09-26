from __future__ import annotations

from app.core.db import get_db_session
from fastapi import APIRouter
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter()


@router.get("/health")
async def health() -> dict:
    return {"status": "ok"}


@router.get("/healthz")
async def healthz() -> dict:
    gen = get_db_session()
    session: AsyncSession = await gen.__anext__()
    try:
        await session.execute(text("select 1"))
        db_ok = True
    except Exception:
        db_ok = False
    finally:
        try:
            await gen.aclose()
        except Exception:
            pass
    return {"ok": True, "db": db_ok}
