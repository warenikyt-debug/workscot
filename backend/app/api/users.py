from fastapi import APIRouter, HTTPException, status, Depends
from sqlalchemy import select
from app.api.deps import Database, CurrentUser, require_role
from app.models.user import User, UserRole
from app.schemas.user import UserResponse

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/me", response_model=UserResponse)
async def get_me(current_user: CurrentUser):
    return current_user


@router.get("/{user_id}", response_model=UserResponse)
async def get_user(user_id: int, db: Database):
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="Пользователь не найден")
    return user


@router.patch("/{user_id}/role")
async def set_user_role(
    user_id: int,
    role: UserRole,
    db: Database,
    admin: User = Depends(require_role(UserRole.ADMIN)),
):
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="Пользователь не найден")

    old_role = user.role
    user.role = role
    return {"message": f"Роль изменена с {old_role.value} на {role.value}"}


@router.patch("/{user_id}/block")
async def toggle_user_block(
    user_id: int,
    db: Database,
    admin: User = Depends(require_role(UserRole.ADMIN)),
):
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="Пользователь не найден")

    user.is_active = not user.is_active
    state = "заблокирован" if not user.is_active else "разблокирован"
    return {"message": f"Пользователь {user.email} {state}"}
