from fastapi import APIRouter, HTTPException
from sqlalchemy import select
from app.api.deps import Database, CurrentUser
from app.models.notification import Notification

router = APIRouter(prefix="/notifications", tags=["notifications"])


@router.get("/")
async def get_notifications(db: Database, current_user: CurrentUser, unread_only: bool = False):
    query = select(Notification).where(Notification.user_id == current_user.id)
    if unread_only:
        query = query.where(Notification.is_read == False)
    query = query.order_by(Notification.created_at.desc()).limit(50)
    result = await db.execute(query)
    return result.scalars().all()


@router.post("/{notification_id}/read")
async def mark_as_read(notification_id: int, db: Database, current_user: CurrentUser):
    notification = await db.get(Notification, notification_id)
    if not notification or notification.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Уведомление не найдено")
    notification.is_read = True
    return {"message": "Отмечено как прочитанное"}


@router.post("/read-all")
async def mark_all_as_read(db: Database, current_user: CurrentUser):
    result = await db.execute(
        select(Notification).where(Notification.user_id == current_user.id, Notification.is_read == False)
    )
    for notification in result.scalars().all():
        notification.is_read = True
    return {"message": "Все уведомления отмечены как прочитанные"}
