from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.season import Season
    from app.models.scene import Scene

NARRATIVE_STATUSES = ("planned", "drafting", "narrative_complete", "narrative_approved")
VISUAL_STATUSES = ("not_started", "visualizing", "visual_complete")


class Chapter(Base):
    __tablename__ = "chapters"
    __table_args__ = (
        CheckConstraint("number >= 1", name="ck_chapters_number_positive"),
        CheckConstraint(
            "narrative_status IN ('planned', 'drafting', 'narrative_complete', 'narrative_approved')",
            name="ck_chapters_narrative_status",
        ),
        CheckConstraint(
            "visual_status IN ('not_started', 'visualizing', 'visual_complete')",
            name="ck_chapters_visual_status",
        ),
        UniqueConstraint("season_id", "number", name="uq_chapters_season_number"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    season_id: Mapped[int] = mapped_column(
        ForeignKey("seasons.id", ondelete="CASCADE"), nullable=False
    )
    number: Mapped[int] = mapped_column(nullable=False)
    title: Mapped[str | None] = mapped_column(String(200), nullable=True)
    logline: Mapped[str | None] = mapped_column(Text, nullable=True)
    narrative_status: Mapped[str] = mapped_column(
        String(50), nullable=False, default="planned", server_default="planned", index=True
    )
    visual_status: Mapped[str] = mapped_column(
        String(50), nullable=False, default="not_started", server_default="not_started"
    )
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
    scenes: Mapped[list["Scene"]] = relationship(
        back_populates="chapter", lazy="selectin", passive_deletes="all"
    )
