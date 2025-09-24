from typing import Literal
from pydantic import BaseModel, Field


class PresignRequest(BaseModel):
    file_name: str = Field(..., description="Original file name")
    file_type: str = Field(..., description="MIME type of the file")
    file_size: int = Field(..., description="File size in bytes", gt=0)
    upload_type: Literal["input", "reference"] = Field(
        "input", description="Type of upload"
    )
