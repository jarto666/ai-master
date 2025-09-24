from fastapi import FastAPI
from dotenv import load_dotenv
from app.core.db import db
from app.features.uploads.router import router as uploads_router
from app.features.jobs.router import router as jobs_router
from app.features.auth.router import router as auth_router

load_dotenv()

app = FastAPI(title="Mastering API", version="0.1.0")

app.include_router(auth_router)
app.include_router(uploads_router)
app.include_router(jobs_router)


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.get("/healthz")
async def healthz():
    # quick smoke: ping db
    try:
        await db.command("ping")
        db_ok = True
    except Exception:
        db_ok = False
    return {"ok": True, "db": db_ok}