from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, Literal

from pydantic import BaseModel, Field, field_validator


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
    id: str = Field(..., alias="_id")
    user_id: str = Field(..., alias="userId")
    object_key: str = Field(..., description="S3 key for the original upload")
    mime_type: str = Field(..., alias="mimeType")
    file_size: int = Field(..., alias="fileSize")
    duration_seconds: float | None = Field(None, alias="durationSeconds")
    status: Literal["created", "uploaded"] = Field("created")
    etag: str | None = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        populate_by_name = True
        json_encoders = {datetime: lambda v: v.isoformat()}

    @field_validator("id", mode="before")
    @classmethod
    def cast_id_to_str(cls, v):
        try:
            return str(v) if v is not None else v
        except Exception:
            return v


class AssetCreateResponse(BaseModel):
    asset: Asset
    upload: PresignedPost
