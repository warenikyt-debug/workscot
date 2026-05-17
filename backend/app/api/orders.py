from fastapi import APIRouter, HTTPException, status, Depends
from sqlalchemy import select, or_
from app.api.deps import Database, CurrentUser, require_role
from app.models.user import UserRole
from app.models.order import Order, OrderStatus, OrderStatusHistory
from app.schemas.order import OrderCreate, OrderUpdate, OrderResponse, OrderSearchParams

router = APIRouter(prefix="/orders", tags=["orders"])


@router.post("/", response_model=OrderResponse, status_code=status.HTTP_201_CREATED)
async def create_order(request: OrderCreate, db: Database, current_user: CurrentUser):
    if current_user.role not in [UserRole.CUSTOMER, UserRole.ADMIN]:
        raise HTTPException(status_code=403, detail="Только заказчики могут создавать заказы")

    order = Order(**request.model_dump(), customer_id=current_user.id, status=OrderStatus.DRAFT)
    db.add(order)
    await db.flush()

    history = OrderStatusHistory(order_id=order.id, new_status=OrderStatus.DRAFT, changed_by=current_user.id)
    db.add(history)
    await db.refresh(order)
    return order


@router.get("/", response_model=list[OrderResponse])
async def search_orders(db: Database, category: str = None, keywords: str = None, skills: str = None, budget_from: float = None, budget_to: float = None, payment_format: str = None, sort_by: str = "created_at", sort_order: str = "desc", page: int = 1, page_size: int = 20):
    query = select(Order).where(Order.status == OrderStatus.PUBLISHED)

    if category:
        query = query.where(Order.category == category)
    if keywords:
        query = query.where(or_(Order.title.ilike(f"%{keywords}%"), Order.description.ilike(f"%{keywords}%")))
    if skills:
        query = query.where(Order.required_skills.ilike(f"%{skills}%"))
    if budget_from is not None:
        query = query.where(Order.budget_max >= budget_from)
    if budget_to is not None:
        query = query.where(Order.budget_min <= budget_to)
    if payment_format:
        query = query.where(Order.payment_format == payment_format)

    sort_col = getattr(Order, sort_by, Order.created_at)
    query = query.order_by(sort_col.desc() if sort_order == "desc" else sort_col.asc())
    query = query.offset((page - 1) * page_size).limit(page_size)

    result = await db.execute(query)
    return result.scalars().all()


@router.get("/my", response_model=list[OrderResponse])
async def get_my_orders(db: Database, current_user: CurrentUser):
    query = select(Order).where(Order.customer_id == current_user.id).order_by(Order.created_at.desc())
    result = await db.execute(query)
    return result.scalars().all()


@router.get("/{order_id}", response_model=OrderResponse)
async def get_order(order_id: int, db: Database):
    result = await db.execute(select(Order).where(Order.id == order_id))
    order = result.scalar_one_or_none()
    if not order:
        raise HTTPException(status_code=404, detail="Заказ не найден")
    return order


@router.patch("/{order_id}", response_model=OrderResponse)
async def update_order(order_id: int, request: OrderUpdate, db: Database, current_user: CurrentUser):
    result = await db.execute(select(Order).where(Order.id == order_id))
    order = result.scalar_one_or_none()
    if not order:
        raise HTTPException(status_code=404, detail="Заказ не найден")
    if order.customer_id != current_user.id and current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Недостаточно прав")

    for field, value in request.model_dump(exclude_unset=True).items():
        setattr(order, field, value)
    await db.refresh(order)
    return order


@router.post("/{order_id}/submit")
async def submit_for_moderation(order_id: int, db: Database, current_user: CurrentUser):
    result = await db.execute(select(Order).where(Order.id == order_id))
    order = result.scalar_one_or_none()
    if not order:
        raise HTTPException(status_code=404, detail="Заказ не найден")
    if order.customer_id != current_user.id:
        raise HTTPException(status_code=403, detail="Недостаточно прав")
    if order.status != OrderStatus.DRAFT:
        raise HTTPException(status_code=400, detail="Нельзя отправить на модерацию")

    old_status = order.status
    order.status = OrderStatus.ON_MODERATION
    db.add(OrderStatusHistory(order_id=order.id, old_status=old_status, new_status=OrderStatus.ON_MODERATION, changed_by=current_user.id))
    return {"message": "Заказ отправлен на модерацию"}
