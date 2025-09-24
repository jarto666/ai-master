from datetime import datetime
from pydantic import BaseModel, Field
from typing import Literal


class JobCreateRequest(BaseModel):
    object_key: str = Field(..., description="S3 object key of the input file")
    reference_object_key: str | None = Field(
        None, description="S3 object key of the reference file"
    )


class Job(BaseModel):
    id: str = Field(..., alias="_id")
    object_key: str
    reference_object_key: str | None = None
    status: Literal["queued", "processing", "done", "failed"] = "queued"
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        populate_by_name = True
        json_encoders = {datetime: lambda v: v.isoformat()}
