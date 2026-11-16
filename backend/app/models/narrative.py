from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import DateTime
from sqlalchemy.sql import func
from datetime import datetime
from app.db.base import Base
from sqlalchemy.dialects.postgresql import JSONB

class Narrative(Base):
    __tablename__="narrative"

    id:Mapped[int]=mapped_column(primary_key=True,index=True)
    episode_number:Mapped[int]=mapped_column(unique=True,index=True,nullable=False)
    payload:Mapped[dict]=mapped_column(JSONB,nullable=False)
    create_at:Mapped[datetime]=mapped_column(DateTime(timezone=True),server_default=func.now())
   