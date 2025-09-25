import asyncio
import json
import os
import signal
import tempfile
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import Awaitable, Callable, AsyncIterator

import aio_pika
import aio_pika.abc

from worker.core.settings import settings
from worker.providers import files as files_provider

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


 


async def _run_ffmpeg_normalize(input_path: str, output_path: str) -> None:
    """
    Apply basic loudness normalization using ffmpeg loudnorm filter.
    Target: I=-14 LUFS, TP=-1.5 dB, LRA=11.
    """
    process = await asyncio.create_subprocess_exec(
        "ffmpeg",
        "-y",
        "-i",
        input_path,
        "-af",
        "loudnorm=I=-14:TP=-1.5:LRA=11",
        "-ar",
        "44100",
        "-ac",
        "2",
        "-c:a",
        "pcm_s16le",
        output_path,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    _, stderr = await process.communicate()
    if process.returncode != 0:
        raise RuntimeError(f"ffmpeg loudnorm failed: {stderr.decode(errors='ignore')[:500]}")


async def _run_ffmpeg_preview(input_path: str, output_path: str, duration_seconds: int = 60) -> None:
    """
    Create an mp3 preview clip of the mastered audio.
    """
    process = await asyncio.create_subprocess_exec(
        "ffmpeg",
        "-y",
        "-t",
        str(duration_seconds),
        "-i",
        input_path,
        "-vn",
        "-c:a",
        "libmp3lame",
        "-b:a",
        "192k",
        output_path,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    _, stderr = await process.communicate()
    if process.returncode != 0:
        raise RuntimeError(f"ffmpeg preview failed: {stderr.decode(errors='ignore')[:500]}")


async def _publish_event(exchange: aio_pika.abc.AbstractExchange, routing_key: str, payload: dict) -> None:
    await exchange.publish(
        aio_pika.Message(
            body=json.dumps(payload).encode(),
            content_type="application/json",
            delivery_mode=aio_pika.DeliveryMode.PERSISTENT,
            correlation_id=str(payload.get("jobId", "")) or None,
        ),
        routing_key=routing_key,
    )


async def handle_message(events_exchange: aio_pika.abc.AbstractExchange, msg: aio_pika.abc.AbstractIncomingMessage):
    async with msg.process():
        try:
            payload = json.loads(msg.body.decode())
        except Exception:
            return

        job_id = payload.get("jobId")
        object_key = payload.get("object_key")
        if not job_id or not object_key:
            return

        print(f"[worker] start job {job_id}")

        # Notify processing
        await _publish_event(
            events_exchange,
            settings.RMQ_EVENTS_ROUTING_KEY_PROCESSING,
            {
                "type": "job.processing",
                "occurredAt": datetime.now(timezone.utc).isoformat(),
                "jobId": job_id,
                "data": {},
                "version": 1,
            },
        )

        try:
            result_key = f"jobs/{job_id}/master.wav"
            preview_key = f"jobs/{job_id}/preview.mp3"

            with tempfile.TemporaryDirectory() as tmpdir:
                input_path = os.path.join(tmpdir, "input")
                mastered_path = os.path.join(tmpdir, "master.wav")
                preview_path = os.path.join(tmpdir, "preview.mp3")

                await files_provider.download_file(object_key, input_path)
                await _run_ffmpeg_normalize(input_path, mastered_path)
                await _run_ffmpeg_preview(mastered_path, preview_path)
                await files_provider.upload_file(mastered_path, result_key, "audio/wav")
                await files_provider.upload_file(preview_path, preview_key, "audio/mpeg")

            # Notify done
            await _publish_event(
                events_exchange,
                settings.RMQ_EVENTS_ROUTING_KEY_DONE,
                {
                    "type": "job.done",
                    "occurredAt": datetime.now(timezone.utc).isoformat(),
                    "jobId": job_id,
                    "data": {
                        "result_object_key": result_key,
                        "preview_object_key": preview_key,
                    },
                    "version": 1,
                },
            )
            print(f"[worker] done job {job_id}")
        except Exception as e:
            # Notify failed
            await _publish_event(
                events_exchange,
                settings.RMQ_EVENTS_ROUTING_KEY_FAILED,
                {
                    "type": "job.failed",
                    "occurredAt": datetime.now(timezone.utc).isoformat(),
                    "jobId": job_id,
                    "data": {"error": str(e)[:500]},
                    "version": 1,
                },
            )
            print(f"[worker] failed job {job_id}: {e}")


async def main() -> None:
    async with _lifecycle() as wait_stop:
        connection = await aio_pika.connect_robust(settings.RABBITMQ_URL)
        try:
            channel = await connection.channel()
            await channel.set_qos(prefetch_count=5)

            # Jobs input (direct)
            exchange = await channel.declare_exchange(
                settings.RMQ_EXCHANGE,
                type=aio_pika.ExchangeType.DIRECT,
                durable=True,
            )
            queue = await channel.declare_queue(settings.RMQ_QUEUE, durable=True)
            await queue.bind(exchange, routing_key=settings.RMQ_ROUTING_KEY)

            # Events output (topic)
            events_exchange = await channel.declare_exchange(
                settings.RMQ_EVENTS_EXCHANGE,
                type=aio_pika.ExchangeType.TOPIC,
                durable=True,
            )

            await queue.consume(lambda m: handle_message(events_exchange, m))
            print("[worker] waiting for messages… (Ctrl+C to stop)")

            await wait_stop()
        finally:
            await connection.close()


if __name__ == "__main__":
    asyncio.run(main())