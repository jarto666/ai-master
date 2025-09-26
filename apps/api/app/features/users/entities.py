from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from app.core.db import Base
from app.core.utils.time import utcnow

if TYPE_CHECKING:
    from app.features.assets.entities import Asset
    from app.features.mastering.entities import Job
    from app.features.tracks.entities import Track
from sqlalchemy import DateTime, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    email: Mapped[str] = mapped_column(String(320), nullable=False, unique=True)
    name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=False), default=utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=False), default=utcnow, onupdate=utcnow, nullable=False
    )

    assets: Mapped[list[Asset]] = relationship(back_populates="user")
    tracks: Mapped[list[Track]] = relationship(back_populates="user")
    jobs: Mapped[list[Job]] = relationship(back_populates="user")
