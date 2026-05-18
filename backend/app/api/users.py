from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy import select
from app.api.deps import Database, CurrentUser, require_role
from app.models.user import User, UserRole

router = APIRouter(prefix="/users", tags=["users"])

@router.get("/me")
async def get_me(current_user: CurrentUser):
    return {"id": current_user.id, "email": current_user.email, "role": current_user.role.value, "is_active": current_user.is_active}

@router.patch("/{user_id}/role")
async def set_role(user_id: int, role: str, db: Database, admin: User = Depends(require_role(UserRole.ADMIN))):
    user = await db.get(User, user_id)
    if not user:
        raise HTTPException(404, "User not found")
    user.role = UserRole(role)
    return {"message": f"Role changed to {role}"}

@router.patch("/{user_id}/block")
async def toggle_block(user_id: int, db: Database, admin: User = Depends(require_role(UserRole.ADMIN))):
    user = await db.get(User, user_id)
    if not user:
        raise HTTPException(404, "User not found")
    user.is_active = not user.is_active
    return {"message": "Toggled"}
