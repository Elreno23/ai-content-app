from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.beat import Beat
    from app.models.chapter import Chapter


class Scene(Base):
    __tablename__ = "scenes"
    __table_args__ = (
        CheckConstraint("number >= 1", name="ck_scenes_number_positive"),
        UniqueConstraint("chapter_id", "number", name="uq_scenes_chapter_number"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    chapter_id: Mapped[int] = mapped_column(
        ForeignKey("chapters.id", ondelete="CASCADE"), nullable=False
    )
    number: Mapped[int] = mapped_column(nullable=False)
    title: Mapped[str | None] = mapped_column(String(200), nullable=True)
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    chapter: Mapped["Chapter"] = relationship(back_populates="scenes", lazy="selectin")
    beats: Mapped[list["Beat"]] = relationship(
        back_populates="scene", lazy="selectin", passive_deletes="all"
    )
