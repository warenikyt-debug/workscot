from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select
from app.api.deps import Database
from app.models.user import User
from app.core.security import verify_password, get_password_hash, create_access_token, create_refresh_token, decode_token
from app.schemas.auth import RegisterRequest, LoginRequest, TokenResponse
from jose import JWTError

router = APIRouter(prefix="/auth", tags=["auth"])

@router.post("/register", response_model=TokenResponse, status_code=201)
async def register(request: RegisterRequest, db: Database):
    if request.password != request.password_confirm:
        raise HTTPException(400, "Passwords do not match")
    existing = await db.execute(select(User).where(User.email == request.email))
    if existing.scalar_one_or_none():
        raise HTTPException(409, "Email already registered")
    user = User(email=request.email, hashed_password=get_password_hash(request.password))
    db.add(user)
    await db.flush()
    return TokenResponse(access_token=create_access_token(user.id, user.role.value), refresh_token=create_refresh_token(user.id, user.role.value))

@router.post("/login", response_model=TokenResponse)
async def login(request: LoginRequest, db: Database):
    result = await db.execute(select(User).where(User.email == request.email))
    user = result.scalar_one_or_none()
    if not user or not verify_password(request.password, user.hashed_password):
        raise HTTPException(401, "Invalid credentials")
    if not user.is_active:
        raise HTTPException(403, "Account blocked")
    return TokenResponse(access_token=create_access_token(user.id, user.role.value), refresh_token=create_refresh_token(user.id, user.role.value))

@router.post("/refresh", response_model=TokenResponse)
async def refresh(refresh_token: str, db: Database):
    try:
        payload = decode_token(refresh_token)
        if payload.get("type") != "refresh":
            raise HTTPException(401)
        user_id = int(payload.get("sub"))
        role = payload.get("role")
    except (JWTError, ValueError):
        raise HTTPException(401, "Invalid refresh token")
    user = await db.get(User, user_id)
    if not user or not user.is_active:
        raise HTTPException(401)
    return TokenResponse(access_token=create_access_token(user.id, user.role.value), refresh_token=create_refresh_token(user.id, user.role.value))
