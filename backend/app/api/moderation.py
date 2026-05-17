from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy import select
from app.api.deps import Database, CurrentUser, require_role
from app.models.user import User, UserRole
from app.models.order import Order, OrderStatus, OrderStatusHistory
from app.models.external_order import ExternalOrder, ExternalOrderStatus

router = APIRouter(prefix="/moderation", tags=["moderation"])


@router.get("/orders")
async def get_orders_for_moderation(
    db: Database,
    moderator: User = Depends(require_role(UserRole.MODERATOR, UserRole.ADMIN)),
):
    query = select(Order).where(Order.status == OrderStatus.ON_MODERATION).order_by(Order.created_at.asc())
    result = await db.execute(query)
    return result.scalars().all()


@router.post("/orders/{order_id}/approve")
async def approve_order(
    order_id: int,
    db: Database,
    moderator: User = Depends(require_role(UserRole.MODERATOR, UserRole.ADMIN)),
):
    order = await db.get(Order, order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Заказ не найден")
    if order.status != OrderStatus.ON_MODERATION:
        raise HTTPException(status_code=400, detail="Заказ не на модерации")

    old_status = order.status
    order.status = OrderStatus.PUBLISHED
    db.add(OrderStatusHistory(order_id=order.id, old_status=old_status, new_status=OrderStatus.PUBLISHED, changed_by=moderator.id, comment="Одобрен модератором"))
    return {"message": "Заказ опубликован"}


@router.post("/orders/{order_id}/reject")
async def reject_order(
    order_id: int,
    reason: str,
    db: Database,
    moderator: User = Depends(require_role(UserRole.MODERATOR, UserRole.ADMIN)),
):
    order = await db.get(Order, order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Заказ не найден")
    if order.status != OrderStatus.ON_MODERATION:
        raise HTTPException(status_code=400, detail="Заказ не на модерации")

    old_status = order.status
    order.status = OrderStatus.REJECTED
    order.rejection_reason = reason
    db.add(OrderStatusHistory(order_id=order.id, old_status=old_status, new_status=OrderStatus.REJECTED, changed_by=moderator.id, comment=reason))
    return {"message": "Заказ отклонён"}


@router.get("/external-orders")
async def get_suspicious_external(
    db: Database,
    moderator: User = Depends(require_role(UserRole.MODERATOR, UserRole.ADMIN)),
):
    query = select(ExternalOrder).where(ExternalOrder.status == ExternalOrderStatus.NEW).order_by(ExternalOrder.discovered_at.desc())
    result = await db.execute(query)
    return result.scalars().all()


@router.post("/external-orders/{order_id}/approve")
async def approve_external_order(
    order_id: int,
    db: Database,
    moderator: User = Depends(require_role(UserRole.MODERATOR, UserRole.ADMIN)),
):
    ext_order = await db.get(ExternalOrder, order_id)
    if not ext_order:
        raise HTTPException(status_code=404, detail="Внешний заказ не найден")
    ext_order.status = ExternalOrderStatus.ACTIVE
    return {"message": "Внешний заказ активирован"}


@router.post("/external-orders/{order_id}/archive")
async def archive_external_order(
    order_id: int,
    db: Database,
    moderator: User = Depends(require_role(UserRole.MODERATOR, UserRole.ADMIN)),
):
    ext_order = await db.get(ExternalOrder, order_id)
    if not ext_order:
        raise HTTPException(status_code=404, detail="Внешний заказ не найден")
    ext_order.status = ExternalOrderStatus.ARCHIVED
    return {"message": "Внешний заказ перемещён в архив"}
