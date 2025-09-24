import asyncio
import json
from typing import Mapping, Any

import aio_pika
import aio_pika.abc
from .settings import settings

_connection: aio_pika.abc.AbstractRobustConnection | None = None
_channel: aio_pika.abc.AbstractChannel | None = None
_exchange: aio_pika.abc.AbstractExchange | None = None

_init_lock = asyncio.Lock()


async def get_channel() -> tuple[aio_pika.abc.AbstractChannel, aio_pika.abc.AbstractExchange]:
    """
    Return an open channel and declared exchange. Lazy-initialize connection and topology once.
    Safe for concurrent calls via an initialization lock.
    """
    global _connection, _channel, _exchange

    if _channel and not _channel.is_closed and _exchange is not None:
        return _channel, _exchange

    async with _init_lock:
        # Re-check inside the lock to avoid duplicate init
        if _channel and not _channel.is_closed and _exchange is not None:
            return _channel, _exchange

        if _connection is None or _connection.is_closed:
            _connection = await aio_pika.connect_robust(settings.RABBITMQ_URL)

        _channel = await _connection.channel()
        await _channel.set_qos(prefetch_count=10)

        _exchange = await _channel.declare_exchange(
            settings.RMQ_EXCHANGE,
            type=aio_pika.ExchangeType.DIRECT,
            durable=True,
        )
        queue = await _channel.declare_queue(settings.RMQ_QUEUE, durable=True)
        await queue.bind(_exchange, routing_key=settings.RMQ_ROUTING_KEY)

        return _channel, _exchange


async def publish_job(message: Mapping[str, Any], routing_key: str | None = None) -> None:
    """
    Publish a job message to the configured exchange with persistent delivery.
    Optionally override the routing key.
    """
    _, exchange = await get_channel()
    await exchange.publish(
        aio_pika.Message(
            body=json.dumps(message).encode(),
            content_type="application/json",
            delivery_mode=aio_pika.DeliveryMode.PERSISTENT,
            correlation_id=str(message.get("jobId", "")) or None,
        ),
        routing_key=routing_key or settings.RMQ_ROUTING_KEY,
    )


async def close() -> None:
    """Close channel and connection for graceful shutdown."""
    global _connection, _channel, _exchange
    if _channel and not _channel.is_closed:
        await _channel.close()
    _channel = None
    _exchange = None
    if _connection and not _connection.is_closed:
        await _connection.close()
    _connection = None