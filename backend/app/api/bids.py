from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select
from app.api.deps import Database, CurrentUser, require_role
from app.models.user import UserRole
from app.models.order import Order, OrderStatus, OrderStatusHistory
from app.models.bid import Bid, BidStatus
from app.schemas.bid import BidCreate, BidResponse

router = APIRouter(prefix="/bids", tags=["bids"])


@router.post("/orders/{order_id}", response_model=BidResponse, status_code=status.HTTP_201_CREATED)
async def create_bid(order_id: int, request: BidCreate, db: Database, current_user: CurrentUser):
    if current_user.role != UserRole.FREELANCER:
        raise HTTPException(status_code=403, detail="Только фрилансеры могут отправлять отклики")

    order = await db.get(Order, order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Заказ не найден")
    if order.status != OrderStatus.PUBLISHED:
        raise HTTPException(status_code=400, detail="Заказ недоступен для откликов")

    existing = await db.execute(
        select(Bid).where(
            Bid.order_id == order_id,
            Bid.freelancer_id == current_user.id,
            Bid.status.in_([BidStatus.SENT, BidStatus.VIEWED, BidStatus.ACCEPTED])
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Вы уже отправили отклик")

    bid = Bid(order_id=order_id, freelancer_id=current_user.id, **request.model_dump())
    db.add(bid)
    await db.flush()
    await db.refresh(bid)
    return bid


@router.get("/orders/{order_id}", response_model=list[BidResponse])
async def get_order_bids(order_id: int, db: Database, current_user: CurrentUser):
    order = await db.get(Order, order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Заказ не найден")
    if order.customer_id != current_user.id and current_user.role not in [UserRole.MODERATOR, UserRole.ADMIN]:
        raise HTTPException(status_code=403, detail="Недостаточно прав")

    result = await db.execute(
        select(Bid).where(Bid.order_id == order_id).order_by(Bid.created_at.desc())
    )
    return result.scalars().all()


@router.patch("/{bid_id}/accept")
async def accept_bid(bid_id: int, db: Database, current_user: CurrentUser):
    bid = await db.get(Bid, bid_id)
    if not bid:
        raise HTTPException(status_code=404, detail="Отклик не найден")

    order = await db.get(Order, bid.order_id)
    if order.customer_id != current_user.id:
        raise HTTPException(status_code=403, detail="Недостаточно прав")

    bid.status = BidStatus.ACCEPTED
    order.status = OrderStatus.IN_PROGRESS

    # Добавляем запись в историю статусов
    db.add(OrderStatusHistory(
        order_id=order.id,
        old_status=OrderStatus.PUBLISHED,
        new_status=OrderStatus.IN_PROGRESS,
        changed_by=current_user.id,
    ))

    # Отклоняем остальные отклики
    other_bids = await db.execute(
        select(Bid).where(Bid.order_id == order.id, Bid.id != bid_id)
    )
    for b in other_bids.scalars().all():
        b.status = BidStatus.REJECTED

    return {"message": "Отклик принят, заказ в работе"}


@router.patch("/{bid_id}/reject")
async def reject_bid(bid_id: int, db: Database, current_user: CurrentUser):
    bid = await db.get(Bid, bid_id)
    if not bid:
        raise HTTPException(status_code=404, detail="Отклик не найден")

    order = await db.get(Order, bid.order_id)
    if order.customer_id != current_user.id:
        raise HTTPException(status_code=403, detail="Недостаточно прав")

    bid.status = BidStatus.REJECTED
    return {"message": "Отклик отклонён"}
