from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, Literal

from pydantic import BaseModel, Field


class PresignedPost(BaseModel):
    url: str
    fields: Dict[str, Any]


class AssetCreateRequest(BaseModel):
    file_name: str = Field(..., alias="fileName")
    file_type: str = Field(..., alias="fileType")
    file_size: int = Field(..., alias="fileSize")
    duration_seconds: float | None = Field(None, alias="durationSeconds")


class AssetConfirmRequest(BaseModel):
    duration_seconds: float | None = Field(None, alias="durationSeconds")


class Asset(BaseModel):
    id: str = Field(...)
    user_id: str = Field(..., alias="userId")
    object_key: str = Field(..., alias="objectKey")
    mime_type: str = Field(..., alias="mimeType")
    file_size: int = Field(..., alias="fileSize")
    file_name: str = Field(..., alias="fileName")
    duration_seconds: float | None = Field(None, alias="durationSeconds")
    status: Literal["created", "uploaded"] = Field("created")
    etag: str | None = None
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc), alias="createdAt"
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc), alias="updatedAt"
    )

    class Config:
        populate_by_name = True
        json_encoders = {datetime: lambda v: v.isoformat()}


class AssetCreateResponse(BaseModel):
    asset: Asset
    upload: PresignedPost


class AssetDownloadUrl(BaseModel):
    url: str
