import asyncio
import os
import signal
from contextlib import asynccontextmanager

import app.core.entities_hub  # noqa: F401
from app.features.assets.router import router as assets_router
from app.features.auth.router import router as auth_router
from app.features.health.router import router as health_router
from app.features.mastering.router import router as mastering_router
from app.features.realtime.events import start_events_consumer, stop_events_consumer
from app.features.realtime.websocket import router as websocket_router
from dotenv import load_dotenv
from fastapi import FastAPI

load_dotenv()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: start events consumer (DB migrations handled via Alembic)

    start_events_consumer(_handle_event_broadcast)

    # Optional signal handlers (guarded to avoid clobbering server handlers like Uvicorn)
    loop = asyncio.get_running_loop()
    installed_signals: list[int] = []

    async def _pre_shutdown() -> None:
        try:
            stop_events_consumer()
        except Exception:
            pass

    if os.getenv("APP_HANDLE_SIGNALS", "0") == "1":
        candidate_signals = [
            getattr(signal, name, None) for name in ("SIGINT", "SIGTERM", "SIGHUP")
        ]
        for sig in candidate_signals:
            if sig is None:
                continue
            try:
                loop.add_signal_handler(
                    sig, lambda s=sig: loop.create_task(_pre_shutdown())
                )
                installed_signals.append(sig)
            except (NotImplementedError, RuntimeError):
                # Not supported on this platform or in this context
                pass

    try:
        yield
    finally:
        for sig in installed_signals:
            try:
                loop.remove_signal_handler(sig)
            except Exception:
                pass
        # Ensure events consumer is stopped on shutdown
        stop_events_consumer()


app = FastAPI(title="Mastering API", version="0.1.0", lifespan=lifespan)

app.include_router(auth_router)
app.include_router(assets_router)
app.include_router(mastering_router)
app.include_router(health_router)
app.include_router(websocket_router)


async def _handle_event_broadcast(job_id: str, job_doc: dict) -> None:
    """Delegate to realtime feature's broadcaster.

    Kept as a thin wrapper to avoid coupling main to implementation details.
    """
    try:
        from app.features.realtime.websocket import broadcast_job_update_to_user

        user_id = str(job_doc.get("userId") or "")
        if not user_id:
            return
        await broadcast_job_update_to_user(user_id, job_doc)
    except Exception:
        pass
