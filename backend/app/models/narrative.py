from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import DateTime, Text
from typing import List
from sqlalchemy.sql import func
from datetime import datetime
from app.db.base import Base

class Narrative(Base):
    __tablename__="narrative"

    id:Mapped[int]=mapped_column(primary_key=True,index=True)
    episode_number:Mapped[int]=mapped_column(unique=True,index=True,nullable=False)
    text:Mapped[str]=mapped_column(Text,nullable=False)
    create_at:Mapped[datetime]=mapped_column(DateTime(timezone=True),server_default=func.now())
    actions_relationship:Mapped[List["DetectedAction"]]=relationship(
        back_populates="narrative_relationship",
        cascade="all,delete-orphan"
    )