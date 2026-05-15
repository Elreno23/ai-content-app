from sqlalchemy import Column,Integer,String, DateTime, JSON, func
from app.db.base import Base


class Simulation(Base):
    __tablename__ = "simulation"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    payload = Column(JSON, nullable=True)