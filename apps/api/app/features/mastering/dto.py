from __future__ import annotations

from datetime import datetime, timezone
from typing import Literal

from pydantic import BaseModel, Field


class StartMasteringRequest(BaseModel):
    asset_id: str = Field(..., alias="assetId")
    reference_asset_id: str | None = Field(None, alias="referenceAssetId")


class MasteringJob(BaseModel):
    id: str = Field(...)
    user_id: str = Field(..., alias="userId")
    input_asset_id: str = Field(..., alias="inputAssetId")
    reference_asset_id: str | None = Field(None, alias="referenceAssetId")
    object_key: str = Field(..., alias="objectKey")
    reference_object_key: str | None = Field(None, alias="referenceObjectKey")
    status: Literal["queued", "processing", "done", "failed"] = "queued"
    result_object_key: str | None = Field(None, alias="resultObjectKey")
    preview_object_key: str | None = Field(None, alias="previewObjectKey")
    file_name: str | None = Field(None, alias="fileName")
    last_error: str | None = Field(None, alias="lastError")
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc), alias="createdAt"
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc), alias="updatedAt"
    )

    class Config:
        populate_by_name = True
        json_encoders = {datetime: lambda v: v.isoformat()}
