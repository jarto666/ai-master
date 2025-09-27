from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from app.core.db import Base
from app.core.utils.time import utcnow

if TYPE_CHECKING:
    from app.features.mastering.entities import Job
    from app.features.tracks.entities import Track
    from app.features.users.entities import User

from sqlalchemy import BigInteger, CheckConstraint, DateTime, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship


class Asset(Base):
    __tablename__ = "assets"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    s3_key: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    file_name: Mapped[str] = mapped_column(Text, nullable=False)
    mime_type: Mapped[str] = mapped_column(String(100), nullable=False)
    file_size: Mapped[int] = mapped_column(BigInteger, nullable=False)
    duration_seconds: Mapped[float | None] = mapped_column(nullable=True)
    etag: Mapped[str | None] = mapped_column(String(128), nullable=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="created")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=False), default=utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=False), default=utcnow, onupdate=utcnow, nullable=False
    )

    user: Mapped["User"] = relationship(back_populates="assets")
    tracks: Mapped[list["Track"]] = relationship(back_populates="original_asset")
    jobs_input: Mapped[list["Job"]] = relationship(
        foreign_keys="Job.input_asset_id", back_populates="input_asset"
    )

    __table_args__ = (
        CheckConstraint("status in ('created','uploaded')", name="ck_assets_status"),
    )
