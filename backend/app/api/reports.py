from fastapi import APIRouter, Depends
from sqlalchemy import select, func
from app.api.deps import Database, require_role
from app.models.user import User, UserRole
from app.models.order import Order, OrderStatus
from app.models.bid import Bid
from app.models.external_order import ExternalOrder, ExternalOrderStatus
from app.models.crawler_source import CrawlerSource, SourceStatus
from app.models.crawler_log import CrawlerLog

router = APIRouter(prefix="/reports", tags=["reports"])


@router.get("/summary")
async def get_summary(
    db: Database,
    admin: User = Depends(require_role(UserRole.MODERATOR, UserRole.ADMIN)),
):
    published = await db.scalar(select(func.count(Order.id)).where(Order.status == OrderStatus.PUBLISHED))
    on_moderation = await db.scalar(select(func.count(Order.id)).where(Order.status == OrderStatus.ON_MODERATION))
    in_progress = await db.scalar(select(func.count(Order.id)).where(Order.status == OrderStatus.IN_PROGRESS))
    completed = await db.scalar(select(func.count(Order.id)).where(Order.status == OrderStatus.COMPLETED))
    total_bids = await db.scalar(select(func.count(Bid.id)))
    external_new = await db.scalar(select(func.count(ExternalOrder.id)).where(ExternalOrder.status == ExternalOrderStatus.NEW))
    external_active = await db.scalar(select(func.count(ExternalOrder.id)).where(ExternalOrder.status == ExternalOrderStatus.ACTIVE))
    active_sources = await db.scalar(select(func.count(CrawlerSource.id)).where(CrawlerSource.status == SourceStatus.ACTIVE))
    crawler_errors = await db.scalar(select(func.count(CrawlerLog.id)).where(CrawlerLog.status == "error"))

    categories_query = await db.execute(
        select(Order.category, func.count(Order.id).label("count"))
        .where(Order.status == OrderStatus.PUBLISHED)
        .group_by(Order.category)
        .order_by(func.count(Order.id).desc())
        .limit(10)
    )
    popular_categories = [{"category": row[0], "count": row[1]} for row in categories_query.all()]

    return {
        "orders": {
            "published": published or 0,
            "on_moderation": on_moderation or 0,
            "in_progress": in_progress or 0,
            "completed": completed or 0,
        },
        "bids": {"total": total_bids or 0},
        "external_orders": {"new": external_new or 0, "active": external_active or 0},
        "crawler": {"active_sources": active_sources or 0, "errors": crawler_errors or 0},
        "popular_categories": popular_categories,
    }
