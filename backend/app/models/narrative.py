from sqlalchemy import Column,Integer,String, DateTime, JSON, func, Text
from sqlalchemy.orm import relationship
from app.db.base import Base

class Narrative(Base):
    __tablename__ = "narrative"

    id = Column(Integer, primary_key=True, index=True)
    text = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    actions = relationship("DetectedAction", back_populates="narrative", cascade="all, delete-orphan")