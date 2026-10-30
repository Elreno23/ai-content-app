from app.db.base import Base
from sqlalchemy import String,DateTime,ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func
from datetime import datetime

class DetectedAction(Base):
    __tablename__="detected_action"

    id:Mapped[int]=mapped_column(primary_key=True, index=True)
    type:Mapped[str]=mapped_column(String(50),nullable=False)
    target:Mapped[str]=mapped_column(String(50),nullable=True)
    created_at:Mapped[datetime]=mapped_column(DateTime(timezone=True),server_default=func.now())

    narrative_id:Mapped[int]=mapped_column(ForeignKey("narrative.id"),nullable=False)
    narrative_relationship:Mapped["Narrative"]=relationship(
        back_populates="actions_relationship"
    )