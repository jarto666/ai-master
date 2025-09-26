from __future__ import annotations

import mimetypes
from datetime import datetime, timezone

from app.core.db import SessionLocal
from app.core.s3 import s3
from app.core.settings import settings
from app.core.utils.assets import (
    ALLOWED_MIME_TYPES,
    MAX_FILE_SIZE_BYTES,
)
from app.features.assets.entities import Asset
from fastapi import HTTPException, status
from sqlalchemy import insert, select, update

from . import dto


async def list_assets(*, user_id: str) -> list[dto.Asset]:
    async with SessionLocal() as session:
        stmt = (
            select(Asset)
            .where(Asset.user_id == user_id)
            .order_by(Asset.created_at.desc())
        )
        res = await session.execute(stmt)
        rows = res.scalars().all()
        return [
            dto.Asset.model_validate(
                {
                    "id": str(a.id),
                    "userId": str(a.user_id),
                    "object_key": a.s3_key,
                    "mimeType": a.mime_type,
                    "fileSize": a.file_size,
                    "durationSeconds": a.duration_seconds,
                    "status": a.status,
                    "etag": a.etag,
                    "created_at": a.created_at,
                    "updated_at": a.updated_at,
                }
            )
            for a in rows
        ]


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
    req: dto.AssetCreateRequest,
    user_id: str,
) -> dto.AssetCreateResponse:
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

    # Pre-generate id to embed into object key (UUID from DB)
    ext = _extension_from_mime_or_name(req.file_type, req.file_name)
    # We'll create a temporary UUID by inserting first with a placeholder S3 key, then update

    async with SessionLocal() as session:
        now = datetime.now(timezone.utc)
        ins = (
            insert(Asset)
            .values(
                user_id=user_id,
                s3_key="__pending__",
                mime_type=req.file_type,
                file_size=req.file_size,
                duration_seconds=req.duration_seconds,
                status="created",
                etag=None,
                created_at=now,
                updated_at=now,
            )
            .returning(Asset)
        )
        res = await session.execute(ins)
        created: Asset = res.scalar_one()
        # now that we have id, build key and update
        object_key = f"assets/{user_id}/{created.id}/original.{ext}"
        await session.execute(
            update(Asset)
            .where(Asset.id == created.id)
            .values(s3_key=object_key, updated_at=datetime.now(timezone.utc))
        )
        await session.commit()

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

    asset = dto.Asset.model_validate(
        {
            "id": str(created.id),
            "userId": str(created.user_id),
            "object_key": object_key,
            "mimeType": created.mime_type,
            "fileSize": created.file_size,
            "durationSeconds": created.duration_seconds,
            "status": "created",
            "etag": None,
            "created_at": now,
            "updated_at": now,
        }
    )
    upload = dto.PresignedPost(url=presigned["url"], fields=presigned["fields"])
    return dto.AssetCreateResponse(asset=asset, upload=upload)


async def confirm_upload(
    *, asset_id: str, user_id: str, req: dto.AssetConfirmRequest
) -> dto.Asset:
    async with SessionLocal() as session:
        # fetch
        res = await session.execute(
            select(Asset).where(Asset.id == asset_id, Asset.user_id == user_id)
        )
        asset_row: Asset | None = res.scalar_one_or_none()
        if not asset_row:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Asset not found"
            )

        object_key: str = asset_row.s3_key
        etag: str | None = None
        file_size_val = asset_row.file_size
        try:
            head = s3.head_object(Bucket=settings.S3_BUCKET, Key=object_key)
            etag = (head.get("ETag") or "").strip('"') or None
            # Trust S3 size if available
            content_length = head.get("ContentLength")
            if isinstance(content_length, int) and content_length > 0:
                file_size_val = content_length
        except Exception:
            pass

        await session.execute(
            update(Asset)
            .where(Asset.id == asset_id, Asset.user_id == user_id)
            .values(
                status="uploaded",
                etag=etag,
                file_size=file_size_val,
                duration_seconds=req.duration_seconds
                if req.duration_seconds is not None
                else asset_row.duration_seconds,
                updated_at=datetime.now(timezone.utc),
            )
        )
        await session.commit()

        # reload
        res2 = await session.execute(select(Asset).where(Asset.id == asset_id))
        a: Asset = res2.scalar_one()
        return dto.Asset.model_validate(
            {
                "id": str(a.id),
                "userId": str(a.user_id),
                "object_key": a.s3_key,
                "mimeType": a.mime_type,
                "fileSize": a.file_size,
                "durationSeconds": a.duration_seconds,
                "status": a.status,
                "etag": a.etag,
                "created_at": a.created_at,
                "updated_at": a.updated_at,
            }
        )


async def get_asset(*, asset_id: str, user_id: str) -> dto.Asset:
    async with SessionLocal() as session:
        res = await session.execute(
            select(Asset).where(Asset.id == asset_id, Asset.user_id == user_id)
        )
        a: Asset | None = res.scalar_one_or_none()
        if not a:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Asset not found"
            )
        return dto.Asset.model_validate(
            {
                "id": str(a.id),
                "userId": str(a.user_id),
                "object_key": a.s3_key,
                "mimeType": a.mime_type,
                "fileSize": a.file_size,
                "durationSeconds": a.duration_seconds,
                "status": a.status,
                "etag": a.etag,
                "created_at": a.created_at,
                "updated_at": a.updated_at,
            }
        )
