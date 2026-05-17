from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, Float, DateTime, ForeignKey
from app.core.database import Base


class SavedSearch(Base):
    __tablename__ = "saved_searches"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    name = Column(String(255), nullable=False)
    categories = Column(Text)
    keywords = Column(String(500))
    skills = Column(Text)
    budget_min = Column(Float)
    budget_max = Column(Float)
    source_type = Column(String(50))
    created_at = Column(DateTime, default=datetime.utcnow)
