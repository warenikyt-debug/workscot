from fastapi import APIRouter, Depends
from sqlalchemy import select, func
from app.api.deps import Database, require_role
from app.models.user import User, UserRole
from app.models.order import Order, OrderStatus
from app.models.bid import Bid

router = APIRouter(prefix="/reports", tags=["reports"])

@router.get("/summary")
async def summary(db: Database, user: User = Depends(require_role(UserRole.MODERATOR, UserRole.ADMIN))):
    published = await db.scalar(select(func.count(Order.id)).where(Order.status == OrderStatus.PUBLISHED))
    on_moderation = await db.scalar(select(func.count(Order.id)).where(Order.status == OrderStatus.ON_MODERATION))
    in_progress = await db.scalar(select(func.count(Order.id)).where(Order.status == OrderStatus.IN_PROGRESS))
    completed = await db.scalar(select(func.count(Order.id)).where(Order.status == OrderStatus.COMPLETED))
    total_bids = await db.scalar(select(func.count(Bid.id)))
    cats = await db.execute(select(Order.category, func.count(Order.id)).where(Order.status == OrderStatus.PUBLISHED).group_by(Order.category).order_by(func.count(Order.id).desc()).limit(10))
    return {
        "orders": {"published": published or 0, "on_moderation": on_moderation or 0, "in_progress": in_progress or 0, "completed": completed or 0},
        "bids": {"total": total_bids or 0},
        "popular_categories": [{"category": row[0], "count": row[1]} for row in cats.all()]
    }
