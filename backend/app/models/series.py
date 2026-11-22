from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, DateTime, String, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.season import Season


class Series(Base):
    __tablename__ = "series"
    __table_args__ = (
        CheckConstraint(
            "max_chapters_per_season IS NULL OR max_chapters_per_season > 0",
            name="ck_series_max_chapters_positive",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    bible: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    max_chapters_per_season: Mapped[int | None] = mapped_column(nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    seasons: Mapped[list["Season"]] = relationship(
        back_populates="series", lazy="selectin", passive_deletes=True
    )
