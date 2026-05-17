from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
from app.models.bid import BidStatus


class BidCreate(BaseModel):
    message: str = Field(min_length=10)
    proposed_price: float = Field(gt=0)
    proposed_deadline: Optional[datetime] = None


class BidResponse(BaseModel):
    id: int
    order_id: int
    freelancer_id: int
    message: str
    proposed_price: float
    proposed_deadline: Optional[datetime]
    status: BidStatus
    created_at: datetime

    class Config:
        from_attributes = True
