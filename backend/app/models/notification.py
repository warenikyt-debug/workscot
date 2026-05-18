import enum
from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, Enum, ForeignKey
from app.core.database import Base

class NotificationType(str, enum.Enum):
    ORDER_PUBLISHED = "order_published"
    NEW_BID = "new_bid"
    BID_ACCEPTED = "bid_accepted"
    SYSTEM = "system"

class Notification(Base):
    __tablename__ = "notifications"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    type = Column(Enum(NotificationType), nullable=False)
    title = Column(String(255), nullable=False)
    message = Column(Text)
    is_read = Column(Boolean, default=False)
    link = Column(String(500))
    created_at = Column(DateTime, default=datetime.utcnow)
