from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, field_validator


class StartMasteringRequest(BaseModel):
    asset_id: str = Field(..., alias="assetId")
    reference_asset_id: str | None = Field(None, alias="referenceAssetId")


class MasteringJob(BaseModel):
    id: str = Field(..., alias="_id")
    user_id: str = Field(..., alias="userId")
    input_asset_id: str = Field(..., alias="inputAssetId")
    reference_asset_id: str | None = Field(None, alias="referenceAssetId")
    object_key: str
    reference_object_key: str | None = None
    status: Literal["queued", "processing", "done", "failed"] = "queued"
    result_object_key: str | None = None
    preview_object_key: str | None = None
    last_error: str | None = Field(None, alias="lastError")
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
