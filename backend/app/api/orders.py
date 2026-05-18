from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy import select, or_
from app.api.deps import Database, CurrentUser, require_role
from app.models.user import UserRole
from app.models.order import Order, OrderStatus, OrderStatusHistory
from app.schemas.order import OrderCreate, OrderResponse

router = APIRouter(prefix="/orders", tags=["orders"])

@router.post("/", response_model=OrderResponse, status_code=201)
async def create_order(request: OrderCreate, db: Database, current_user: CurrentUser):
    if current_user.role not in [UserRole.CUSTOMER, UserRole.ADMIN]:
        raise HTTPException(403, "Only customers can create orders")
    order = Order(**request.model_dump(), customer_id=current_user.id, status=OrderStatus.DRAFT)
    db.add(order)
    await db.flush()
    db.add(OrderStatusHistory(order_id=order.id, new_status=OrderStatus.DRAFT, changed_by=current_user.id))
    await db.refresh(order)
    return order

@router.get("/", response_model=list[OrderResponse])
async def search_orders(db: Database, category: str = None, keywords: str = None, skills: str = None, budget_from: float = None, budget_to: float = None, sort_by: str = "created_at", sort_order: str = "desc", page: int = 1, page_size: int = 20):
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
    sort_col = getattr(Order, sort_by, Order.created_at)
    query = query.order_by(sort_col.desc() if sort_order == "desc" else sort_col.asc())
    query = query.offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(query)
    return result.scalars().all()

@router.get("/my", response_model=list[OrderResponse])
async def my_orders(db: Database, current_user: CurrentUser):
    result = await db.execute(select(Order).where(Order.customer_id == current_user.id).order_by(Order.created_at.desc()))
    return result.scalars().all()

@router.get("/{order_id}", response_model=OrderResponse)
async def get_order(order_id: int, db: Database):
    order = await db.get(Order, order_id)
    if not order:
        raise HTTPException(404, "Order not found")
    return order

@router.post("/{order_id}/submit")
async def submit_order(order_id: int, db: Database, current_user: CurrentUser):
    order = await db.get(Order, order_id)
    if not order or order.customer_id != current_user.id:
        raise HTTPException(404, "Order not found")
    if order.status != OrderStatus.DRAFT:
        raise HTTPException(400, "Cannot submit")
    order.status = OrderStatus.ON_MODERATION
    db.add(OrderStatusHistory(order_id=order.id, old_status=OrderStatus.DRAFT, new_status=OrderStatus.ON_MODERATION, changed_by=current_user.id))
    return {"message": "Submitted"}
