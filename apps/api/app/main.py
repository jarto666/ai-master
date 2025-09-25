import asyncio
import json

import aio_pika
from app.core.db import db
from app.core.settings import settings
from app.features.assets.router import router as assets_router
from app.features.auth.router import router as auth_router
from app.features.jobs.router import router as jobs_router
from app.features.mastering.router import router as mastering_router
from app.features.uploads.router import router as uploads_router
from dotenv import load_dotenv
from fastapi import FastAPI

load_dotenv()

app = FastAPI(title="Mastering API", version="0.1.0")

app.include_router(auth_router)
app.include_router(uploads_router)
app.include_router(assets_router)
app.include_router(mastering_router)
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


_events_task: asyncio.Task | None = None


async def _consume_events() -> None:
    # Safety: never consume from the jobs queue
    if settings.RMQ_EVENTS_QUEUE == settings.RMQ_QUEUE:
        print(
            "[api] WARNING: RMQ_EVENTS_QUEUE equals RMQ_QUEUE; refusing to start events consumer to avoid draining jobs queue",
        )
        return

    print(
        "[api] starting events consumer",
        {
            "url": settings.RABBITMQ_URL,
            "events_exchange": settings.RMQ_EVENTS_EXCHANGE,
            "events_queue": settings.RMQ_EVENTS_QUEUE,
            "events_rk": settings.RMQ_EVENTS_ROUTING_KEY,
        },
    )

    connection = await aio_pika.connect_robust(settings.RABBITMQ_URL)
    channel = await connection.channel()
    await channel.set_qos(prefetch_count=50)
    exchange = await channel.declare_exchange(
        settings.RMQ_EVENTS_EXCHANGE,
        type=aio_pika.ExchangeType.TOPIC,
        durable=True,
    )
    queue = await channel.declare_queue(settings.RMQ_EVENTS_QUEUE, durable=True)
    await queue.bind(exchange, routing_key=settings.RMQ_EVENTS_ROUTING_KEY)

    async with queue.iterator() as queue_iter:
        async for message in queue_iter:  # runs until connection closes
            async with message.process():
                try:
                    payload = json.loads(message.body.decode())
                except Exception:
                    continue
                job_id = payload.get("jobId")
                event_type = payload.get("type")
                data = payload.get("data", {})
                if not job_id or not event_type:
                    continue
                update: dict = {"updated_at": __import__("datetime").datetime.utcnow()}
                if event_type == "job.processing":
                    update["status"] = "processing"
                elif event_type == "job.done":
                    update["status"] = "done"
                    if "result_object_key" in data:
                        update["result_object_key"] = data["result_object_key"]
                    if "preview_object_key" in data:
                        update["preview_object_key"] = data["preview_object_key"]
                elif event_type == "job.failed":
                    update["status"] = "failed"
                    if "error" in data:
                        update["lastError"] = str(data["error"])[:500]
                try:
                    from bson import ObjectId

                    await db.jobs.update_one(
                        {"_id": ObjectId(job_id)}, {"$set": update}
                    )
                except Exception:
                    # Swallow to keep consumer running
                    pass


@app.on_event("startup")
async def startup() -> None:
    # Ensure a unique email index for users collection
    try:
        await db.users.create_index("email", unique=True)
    except Exception:
        # Index may already exist or DB not reachable at startup; ignore here
        pass

    # Start events consumer
    global _events_task
    if _events_task is None or _events_task.done():
        _events_task = asyncio.create_task(_consume_events())


@app.on_event("shutdown")
async def shutdown() -> None:
    # Let the events task cancel on shutdown
    global _events_task
    if _events_task and not _events_task.done():
        _events_task.cancel()
