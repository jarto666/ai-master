from __future__ import annotations

import asyncio
import json
from datetime import datetime, timezone
from typing import Awaitable, Callable

import aio_pika
from app.core.db import SessionLocal
from app.core.settings import settings
from app.features.mastering.entities import Job
from sqlalchemy import select
from sqlalchemy import update as sa_update

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

                update: dict = {"updated_at": datetime.now(timezone.utc)}
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
                        update["last_error"] = str(data["error"])[:500]
                try:
                    async with SessionLocal() as session:
                        await session.execute(
                            sa_update(Job).where(Job.id == job_id).values(**update)
                        )
                        await session.commit()
                        # Reload full job to include necessary fields for UI
                        res = await session.execute(select(Job).where(Job.id == job_id))
                        j: Job | None = res.scalar_one_or_none()
                        if j is None:
                            continue
                        job_doc = {
                            "id": str(j.id),
                            "userId": str(j.user_id),
                            "inputAssetId": str(j.input_asset_id),
                            "referenceAssetId": str(j.reference_asset_id)
                            if j.reference_asset_id
                            else None,
                            "object_key": j.object_key,
                            "reference_object_key": j.reference_object_key,
                            "status": j.status,
                            "result_object_key": j.result_object_key,
                            "preview_object_key": j.preview_object_key,
                            "lastError": j.last_error,
                            "created_at": j.created_at,
                            "updated_at": j.updated_at,
                        }
                    # Notify handler for broadcast with full job document
                    await handler(job_id, job_doc)
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
