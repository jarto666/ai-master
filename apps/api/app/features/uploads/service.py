from fastapi import HTTPException, status
import uuid
from app.core.s3 import s3
from app.core.settings import settings

# 500 MB
MAX_FILE_SIZE_BYTES = 500 * 1024 * 1024
ALLOWED_MIME_TYPES = ["audio/wav", "audio/x-aiff", "audio/aiff", "audio/mpeg"]


def create_presigned_post(
    *, file_name: str, file_type: str, file_size: int, upload_type: str
) -> dict:
    # TODO: add user id to path
    if file_type not in ALLOWED_MIME_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File type {file_type} not allowed.",
        )
    if file_size > MAX_FILE_SIZE_BYTES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File size {file_size} exceeds max of {MAX_FILE_SIZE_BYTES}",
        )

    object_key = f"{upload_type}/{uuid.uuid4()}/{file_name}"

    conditions = [
        ["content-length-range", 1, MAX_FILE_SIZE_BYTES],
        {"Content-Type": file_type},
    ]

    fields = {
        "Content-Type": file_type,
    }

    return s3.generate_presigned_post(
        Bucket=settings.S3_BUCKET,
        Key=object_key,
        Fields=fields,
        Conditions=conditions,
        ExpiresIn=3600,  # 1 hour
    )
