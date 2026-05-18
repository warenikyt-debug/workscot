from fastapi import APIRouter, HTTPException
from sqlalchemy import select
from app.api.deps import Database, CurrentUser
from app.models.user import UserRole
from app.models.order import Order, OrderStatus, OrderStatusHistory
from app.models.bid import Bid, BidStatus
from app.schemas.bid import BidCreate, BidResponse

router = APIRouter(prefix="/bids", tags=["bids"])

@router.post("/orders/{order_id}", response_model=BidResponse, status_code=201)
async def create_bid(order_id: int, request: BidCreate, db: Database, current_user: CurrentUser):
    if current_user.role != UserRole.FREELANCER:
        raise HTTPException(403, "Only freelancers can bid")
    order = await db.get(Order, order_id)
    if not order or order.status != OrderStatus.PUBLISHED:
        raise HTTPException(400, "Order not available")
    existing = await db.execute(select(Bid).where(Bid.order_id == order_id, Bid.freelancer_id == current_user.id, Bid.status.in_([BidStatus.SENT, BidStatus.VIEWED, BidStatus.ACCEPTED])))
    if existing.scalar_one_or_none():
        raise HTTPException(409, "Already bid")
    bid = Bid(order_id=order_id, freelancer_id=current_user.id, **request.model_dump())
    db.add(bid)
    await db.flush()
    await db.refresh(bid)
    return bid

@router.get("/orders/{order_id}", response_model=list[BidResponse])
async def get_bids(order_id: int, db: Database, current_user: CurrentUser):
    order = await db.get(Order, order_id)
    if not order:
        raise HTTPException(404)
    if order.customer_id != current_user.id and current_user.role not in [UserRole.MODERATOR, UserRole.ADMIN]:
        raise HTTPException(403)
    result = await db.execute(select(Bid).where(Bid.order_id == order_id).order_by(Bid.created_at.desc()))
    return result.scalars().all()

@router.patch("/{bid_id}/accept")
async def accept_bid(bid_id: int, db: Database, current_user: CurrentUser):
    bid = await db.get(Bid, bid_id)
    if not bid:
        raise HTTPException(404)
    order = await db.get(Order, bid.order_id)
    if order.customer_id != current_user.id:
        raise HTTPException(403)
    bid.status = BidStatus.ACCEPTED
    order.status = OrderStatus.IN_PROGRESS
    db.add(OrderStatusHistory(order_id=order.id, old_status=OrderStatus.PUBLISHED, new_status=OrderStatus.IN_PROGRESS, changed_by=current_user.id))
    other = await db.execute(select(Bid).where(Bid.order_id == order.id, Bid.id != bid_id))
    for b in other.scalars().all():
        b.status = BidStatus.REJECTED
    return {"message": "Accepted"}
