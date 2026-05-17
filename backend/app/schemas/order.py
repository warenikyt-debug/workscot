from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
from app.models.order import OrderStatus, PaymentFormat


class OrderCreate(BaseModel):
    title: str = Field(min_length=5, max_length=255)
    description: str = Field(min_length=20)
    category: str
    required_skills: Optional[str] = None
    budget_min: Optional[float] = None
    budget_max: Optional[float] = None
    deadline: Optional[datetime] = None
    payment_format: PaymentFormat = PaymentFormat.FIXED
    attachments: Optional[str] = None


class OrderUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    category: Optional[str] = None
    required_skills: Optional[str] = None
    budget_min: Optional[float] = None
    budget_max: Optional[float] = None
    deadline: Optional[datetime] = None
    payment_format: Optional[PaymentFormat] = None
    attachments: Optional[str] = None


class OrderResponse(BaseModel):
    id: int
    title: str
    description: str
    category: str
    required_skills: Optional[str]
    budget_min: Optional[float]
    budget_max: Optional[float]
    deadline: Optional[datetime]
    payment_format: PaymentFormat
    status: OrderStatus
    customer_id: int
    rejection_reason: Optional[str]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class OrderSearchParams(BaseModel):
    category: Optional[str] = None
    keywords: Optional[str] = None
    skills: Optional[str] = None
    budget_from: Optional[float] = None
    budget_to: Optional[float] = None
    payment_format: Optional[PaymentFormat] = None
    date_from: Optional[datetime] = None
    date_to: Optional[datetime] = None
    sort_by: str = "created_at"
    sort_order: str = "desc"
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)
