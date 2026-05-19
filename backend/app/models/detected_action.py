from sqlalchemy import Column, Integer, String, DateTime, JSON, func, ForeignKey
from sqlalchemy.orm import relationship
from app.db.base import Base

class DetectedAction(Base):
    __tablename__ = "detected_action"

    id = Column(Integer, primary_key=True,index=True)
    type =  Column(String(50), nullable=False)
    target = Column(String(100), nullable=False)
    created_at = Column(DateTime(timezone=True),server_default=func.now())
    narrative_id = Column(Integer, ForeignKey("narrative.id"), nullable=False)
    narrative = relationship("Narrative", back_populates="actions")