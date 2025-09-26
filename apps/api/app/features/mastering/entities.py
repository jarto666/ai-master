from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from app.core.db import Base
from app.core.utils.time import utcnow

if TYPE_CHECKING:
    from app.features.assets.entities import Asset
    from app.features.users.entities import User
from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship


class Job(Base):
    __tablename__ = "jobs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    input_asset_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("assets.id", ondelete="CASCADE"), nullable=False
    )
    reference_asset_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("assets.id", ondelete="SET NULL"), nullable=True
    )
    object_key: Mapped[str] = mapped_column(Text, nullable=False)
    reference_object_key: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="queued")
    result_object_key: Mapped[str | None] = mapped_column(Text, nullable=True)
    preview_object_key: Mapped[str | None] = mapped_column(Text, nullable=True)
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=False), default=utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=False), default=utcnow, onupdate=utcnow, nullable=False
    )

    user: Mapped[User] = relationship(back_populates="jobs")
    input_asset: Mapped[Asset] = relationship(foreign_keys=[input_asset_id])
    reference_asset: Mapped[Asset | None] = relationship(
        foreign_keys=[reference_asset_id]
    )

    __table_args__ = (
        CheckConstraint(
            "status in ('queued','processing','done','failed')", name="ck_jobs_status"
        ),
        UniqueConstraint("id", name="uq_jobs_id"),
    )
