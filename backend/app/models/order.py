import enum
from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, Float, DateTime, Enum, ForeignKey
from sqlalchemy.orm import relationship
from app.core.database import Base

class OrderStatus(str, enum.Enum):
    DRAFT = "draft"
    ON_MODERATION = "on_moderation"
    PUBLISHED = "published"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    REJECTED = "rejected"

class PaymentFormat(str, enum.Enum):
    FIXED = "fixed"
    HOURLY = "hourly"
    BY_AGREEMENT = "by_agreement"

class Order(Base):
    __tablename__ = "orders"
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=False)
    category = Column(String(100), nullable=False)
    required_skills = Column(Text)
    budget_min = Column(Float)
    budget_max = Column(Float)
    deadline = Column(DateTime)
    payment_format = Column(Enum(PaymentFormat), default=PaymentFormat.FIXED)
    attachments = Column(Text)
    status = Column(Enum(OrderStatus), default=OrderStatus.DRAFT)
    customer_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    rejection_reason = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    customer = relationship("User", backref="orders")
    bids = relationship("Bid", back_populates="order", cascade="all, delete-orphan")

class OrderStatusHistory(Base):
    __tablename__ = "order_status_history"
    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(Integer, ForeignKey("orders.id"), nullable=False)
    old_status = Column(Enum(OrderStatus))
    new_status = Column(Enum(OrderStatus), nullable=False)
    changed_by = Column(Integer, ForeignKey("users.id"))
    comment = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
