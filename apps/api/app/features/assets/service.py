from __future__ import annotations

import mimetypes
from datetime import datetime
from typing import Any, Dict

from app.core.db import db
from app.core.s3 import s3
from app.core.settings import settings
from app.core.utils.assets import (
    ALLOWED_MIME_TYPES,
    MAX_FILE_SIZE_BYTES,
)
from bson import ObjectId
from fastapi import HTTPException, status

from . import schemas


async def list_assets(*, user_id: str) -> list[schemas.Asset]:
    cursor = db.assets.find({"userId": user_id}).sort("created_at", -1)
    results: list[schemas.Asset] = []
    async for doc in cursor:
        try:
            results.append(schemas.Asset.model_validate(doc))
        except Exception:
            # Skip docs that fail validation
            continue
    return results


def _extension_from_mime_or_name(file_type: str, file_name: str) -> str:
    # Try to deduce extension from mime; fallback to file name; default to 'bin'
    if "/" in file_type:
        guessed = mimetypes.guess_extension(file_type)
        if guessed:
            return guessed.lstrip(".")
    if "." in file_name:
        return file_name.rsplit(".", 1)[-1]
    # Common audio fallbacks
    if file_type in ("audio/wav",):
        return "wav"
    if file_type in ("audio/mpeg",):
        return "mp3"
    if file_type in ("audio/aiff", "audio/x-aiff"):
        return "aiff"
    return "bin"


async def create_asset(
    *,
    req: schemas.AssetCreateRequest,
    user_id: str,
) -> schemas.AssetCreateResponse:
    # Validate mime and size
    if req.file_type not in ALLOWED_MIME_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File type {req.file_type} not allowed.",
        )
    if req.file_size > MAX_FILE_SIZE_BYTES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File size {req.file_size} exceeds max of {MAX_FILE_SIZE_BYTES}",
        )

    # Pre-generate id to embed into object key
    asset_id = ObjectId()
    ext = _extension_from_mime_or_name(req.file_type, req.file_name)
    object_key = f"assets/{user_id}/{asset_id}/original.{ext}"

    now = datetime.utcnow()
    doc: Dict[str, Any] = {
        "_id": asset_id,
        "userId": user_id,
        "object_key": object_key,
        "mimeType": req.file_type,
        "fileSize": req.file_size,
        "durationSeconds": req.duration_seconds,
        "status": "created",
        "etag": None,
        "created_at": now,
        "updated_at": now,
    }

    await db.assets.insert_one(doc)

    # Create presigned POST for client direct upload
    conditions = [
        ["content-length-range", 1, MAX_FILE_SIZE_BYTES],
        {"Content-Type": req.file_type},
    ]
    fields = {"Content-Type": req.file_type}
    presigned = s3.generate_presigned_post(
        Bucket=settings.S3_BUCKET,
        Key=object_key,
        Fields=fields,
        Conditions=conditions,
        ExpiresIn=3600,
    )

    asset = schemas.Asset.model_validate(doc)
    upload = schemas.PresignedPost(url=presigned["url"], fields=presigned["fields"])
    return schemas.AssetCreateResponse(asset=asset, upload=upload)


async def confirm_upload(
    *, asset_id: str, user_id: str, req: schemas.AssetConfirmRequest
) -> schemas.Asset:
    try:
        oid = ObjectId(asset_id)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Asset not found"
        )

    doc = await db.assets.find_one({"_id": oid, "userId": user_id})
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Asset not found"
        )

    object_key: str = doc.get("object_key")
    etag: str | None = None
    try:
        head = s3.head_object(Bucket=settings.S3_BUCKET, Key=object_key)
        etag = (head.get("ETag") or "").strip('"') or None
        # Trust S3 size if available
        content_length = head.get("ContentLength")
        if isinstance(content_length, int) and content_length > 0:
            doc["fileSize"] = content_length
    except Exception:
        # If HEAD fails, still allow confirmation
        pass

    update: Dict[str, Any] = {
        "status": "uploaded",
        "etag": etag,
        "updated_at": datetime.utcnow(),
    }
    if req.duration_seconds is not None:
        update["durationSeconds"] = req.duration_seconds

    await db.assets.update_one({"_id": oid, "userId": user_id}, {"$set": update})
    updated = await db.assets.find_one({"_id": oid})
    return schemas.Asset.model_validate(updated)


async def get_asset(*, asset_id: str, user_id: str) -> schemas.Asset:
    try:
        oid = ObjectId(asset_id)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Asset not found"
        )
    doc = await db.assets.find_one({"_id": oid, "userId": user_id})
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Asset not found"
        )
    return schemas.Asset.model_validate(doc)
