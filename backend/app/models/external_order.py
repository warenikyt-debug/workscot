import enum
from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, Float, DateTime, Enum
from app.core.database import Base

class ExternalOrderStatus(str, enum.Enum):
    NEW = "new"
    ACTIVE = "active"
    ARCHIVED = "archived"
    ERROR = "error"

class ExternalOrder(Base):
    __tablename__ = "external_orders"
    id = Column(Integer, primary_key=True, index=True)
    external_id = Column(String(255), unique=True, index=True, nullable=False)
    title = Column(String(500), nullable=False)
    description = Column(Text)
    category = Column(String(100))
    required_skills = Column(Text)
    budget = Column(String(255))
    budget_min = Column(Float)
    budget_max = Column(Float)
    deadline = Column(String(255))
    source_url = Column(Text)
    source_name = Column(String(255))
    status = Column(Enum(ExternalOrderStatus), default=ExternalOrderStatus.NEW)
    discovered_at = Column(DateTime, default=datetime.utcnow)
    last_updated = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
