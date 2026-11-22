from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.season import Season


class Chapter(Base):
    __tablename__ = "chapters"
    __table_args__ = (
        CheckConstraint("number >= 1", name="ck_chapters_number_positive"),
        UniqueConstraint("season_id", "number", name="uq_chapters_season_number"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    season_id: Mapped[int] = mapped_column(
        ForeignKey("seasons.id", ondelete="CASCADE"), nullable=False
    )
    number: Mapped[int] = mapped_column(nullable=False)
    title: Mapped[str | None] = mapped_column(String(200), nullable=True)
    logline: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="planned")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    season: Mapped["Season"] = relationship(back_populates="chapters", lazy="selectin")
