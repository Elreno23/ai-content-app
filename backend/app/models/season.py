from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.chapter import Chapter
    from app.models.series import Series


class Season(Base):
    __tablename__ = "seasons"
    __table_args__ = (
        CheckConstraint("number >= 1", name="ck_seasons_number_positive"),
        UniqueConstraint("series_id", "number", name="uq_seasons_series_number"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    series_id: Mapped[int] = mapped_column(
        ForeignKey("series.id", ondelete="CASCADE"), nullable=False
    )
    number: Mapped[int] = mapped_column(nullable=False)
    title: Mapped[str | None] = mapped_column(String(200), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    series: Mapped["Series"] = relationship(back_populates="seasons", lazy="selectin")
    chapters: Mapped[list["Chapter"]] = relationship(
        back_populates="season", lazy="selectin", passive_deletes=True
    )
