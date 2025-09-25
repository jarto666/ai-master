import asyncio

from worker.core.s3 import s3
from worker.core.settings import settings


async def download_file(object_key: str, dest_path: str) -> None:
    """Download an object from S3 to a local destination path."""
    await asyncio.to_thread(s3.download_file, settings.S3_BUCKET, object_key, dest_path)


async def upload_file(src_path: str, object_key: str, content_type: str) -> None:
    """Upload a local file to S3 with provided content type."""
    await asyncio.to_thread(
        s3.upload_file,
        src_path,
        settings.S3_BUCKET,
        object_key,
        ExtraArgs={"ContentType": content_type},
    )


