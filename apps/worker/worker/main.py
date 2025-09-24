import asyncio
import json
import signal
from contextlib import asynccontextmanager
from typing import Awaitable, Callable, AsyncIterator

import aio_pika
import aio_pika.abc
from .core.settings import settings

StopCallback = Callable[[], Awaitable[None]]


@asynccontextmanager
async def _lifecycle() -> AsyncIterator[StopCallback]:
    loop = asyncio.get_running_loop()
    stop_event = asyncio.Event()

    def _request_shutdown(*_: int) -> None:
        stop_event.set()

    # Register signals
    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, _request_shutdown)
        except NotImplementedError:
            # Windows fallback
            pass

    async def _wait_stop() -> None:
        await stop_event.wait()

    try:
        yield _wait_stop
    finally:
        # cleanup hook if needed later
        pass


async def handle_message(msg: aio_pika.abc.AbstractIncomingMessage):
    async with msg.process():
        try:
            payload = json.loads(msg.body.decode())
            job_id = payload.get("jobId")
            print(f"[worker] received job {job_id}: {payload}")
            # TODO: download from S3, analyze, render, upload, update DB/API
            await asyncio.sleep(1.0)
            print(f"[worker] done job {job_id}")
        except Exception as e:
            print("[worker] error:", e)
            raise


async def main() -> None:
    async with _lifecycle() as wait_stop:
        connection = await aio_pika.connect_robust(settings.RABBITMQ_URL)
        try:
            channel = await connection.channel()
            await channel.set_qos(prefetch_count=5)

            exchange = await channel.declare_exchange(
                settings.RMQ_EXCHANGE,
                type=aio_pika.ExchangeType.DIRECT,
                durable=True,
            )
            queue = await channel.declare_queue(settings.RMQ_QUEUE, durable=True)
            await queue.bind(exchange, routing_key=settings.RMQ_ROUTING_KEY)

            await queue.consume(handle_message)
            print("[worker] waiting for messages… (Ctrl+C to stop)")

            await wait_stop()
        finally:
            await connection.close()


if __name__ == "__main__":
    asyncio.run(main())