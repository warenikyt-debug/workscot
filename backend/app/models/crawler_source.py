import enum
from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, DateTime, Enum
from app.core.database import Base

class SourceStatus(str, enum.Enum):
    ACTIVE = "active"
    DISABLED = "disabled"
    ERROR = "error"

class CrawlerSource(Base):
    __tablename__ = "crawler_sources"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    base_url = Column(String(500), nullable=False)
    crawl_rules = Column(Text)
    extract_rules = Column(Text)
    interval_minutes = Column(Integer, default=60)
    status = Column(Enum(SourceStatus), default=SourceStatus.ACTIVE)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
