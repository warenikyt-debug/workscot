from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy import select
from app.api.deps import Database, CurrentUser, require_role
from app.models.user import User, UserRole
from app.models.order import Order, OrderStatus, OrderStatusHistory

router = APIRouter(prefix="/moderation", tags=["moderation"])

@router.get("/orders")
async def get_orders(db: Database, moderator: User = Depends(require_role(UserRole.MODERATOR, UserRole.ADMIN))):
    result = await db.execute(select(Order).where(Order.status == OrderStatus.ON_MODERATION).order_by(Order.created_at.asc()))
    return result.scalars().all()

@router.post("/orders/{order_id}/approve")
async def approve(order_id: int, db: Database, moderator: User = Depends(require_role(UserRole.MODERATOR, UserRole.ADMIN))):
    order = await db.get(Order, order_id)
    if not order or order.status != OrderStatus.ON_MODERATION:
        raise HTTPException(400)
    order.status = OrderStatus.PUBLISHED
    db.add(OrderStatusHistory(order_id=order.id, old_status=OrderStatus.ON_MODERATION, new_status=OrderStatus.PUBLISHED, changed_by=moderator.id))
    return {"message": "Approved"}

@router.post("/orders/{order_id}/reject")
async def reject(order_id: int, reason: str, db: Database, moderator: User = Depends(require_role(UserRole.MODERATOR, UserRole.ADMIN))):
    order = await db.get(Order, order_id)
    if not order or order.status != OrderStatus.ON_MODERATION:
        raise HTTPException(400)
    order.status = OrderStatus.REJECTED
    order.rejection_reason = reason
    db.add(OrderStatusHistory(order_id=order.id, old_status=OrderStatus.ON_MODERATION, new_status=OrderStatus.REJECTED, changed_by=moderator.id))
    return {"message": "Rejected"}
