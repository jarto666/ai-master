from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, Literal

from pydantic import BaseModel, Field


class PresignedPost(BaseModel):
    url: str
    fields: Dict[str, Any]


class AssetCreateRequest(BaseModel):
    file_name: str = Field(..., description="Original client file name")
    file_type: str = Field(..., description="MIME type, e.g. audio/wav")
    file_size: int = Field(..., description="File size in bytes")
    duration_seconds: float | None = Field(
        None, description="Optional known duration in seconds"
    )


class AssetConfirmRequest(BaseModel):
    duration_seconds: float | None = Field(
        None, description="Optional known duration in seconds"
    )


class Asset(BaseModel):
    id: str = Field(...)
    user_id: str = Field(..., alias="userId")
    object_key: str = Field(..., description="S3 key for the original upload")
    mime_type: str = Field(..., alias="mimeType")
    file_size: int = Field(..., alias="fileSize")
    duration_seconds: float | None = Field(None, alias="durationSeconds")
    status: Literal["created", "uploaded"] = Field("created")
    etag: str | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    class Config:
        populate_by_name = True
        json_encoders = {datetime: lambda v: v.isoformat()}


class AssetCreateResponse(BaseModel):
    asset: Asset
    upload: PresignedPost
