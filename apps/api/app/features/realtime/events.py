from __future__ import annotations

import asyncio
import json
from typing import Awaitable, Callable

import aio_pika
from app.core.db import db
from app.core.settings import settings

_events_task: asyncio.Task | None = None


async def _consume_events(handler: Callable[[str, dict], Awaitable[None]]) -> None:
    print(
        "[api] starting events consumer",
        {
            "url": settings.RABBITMQ_URL,
            "events_exchange": settings.RMQ_EVENTS_EXCHANGE,
            "events_rk": settings.RMQ_EVENTS_ROUTING_KEY,
            "exclusive_ephemeral_queue": True,
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
    # Declare a per-instance, server-named exclusive queue so every API instance
    # receives a copy of each event (pub/sub fanout via topic binding).
    queue = await channel.declare_queue(
        "", exclusive=True, durable=False, auto_delete=True
    )
    rk = settings.RMQ_EVENTS_ROUTING_KEY or "#"
    await queue.bind(exchange, routing_key=rk)

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

                # Persist basic job status updates
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
                    # Notify handler for broadcast
                    await handler(job_id, update)
                except Exception:
                    # Swallow to keep consumer running
                    pass


def start_events_consumer(handler: Callable[[str, dict], Awaitable[None]]) -> None:
    global _events_task
    if _events_task is None or _events_task.done():
        _events_task = asyncio.create_task(_consume_events(handler))


def stop_events_consumer() -> None:
    global _events_task
    if _events_task and not _events_task.done():
        _events_task.cancel()
