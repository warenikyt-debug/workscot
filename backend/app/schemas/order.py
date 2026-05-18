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
    created_at: datetime
    updated_at: datetime
    class Config:
        from_attributes = True
