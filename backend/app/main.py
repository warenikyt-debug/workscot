from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from app.core.config import settings
import os

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    docs_url="/api/docs",
    redoc_url="/api/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health_check():
    return {"status": "ok", "project": settings.PROJECT_NAME, "version": settings.VERSION}


from app.api.auth import router as auth_router
from app.api.users import router as users_router
from app.api.orders import router as orders_router
from app.api.bids import router as bids_router
from app.api.moderation import router as moderation_router
from app.api.crawler import router as crawler_router
from app.api.notifications import router as notifications_router
from app.api.reports import router as reports_router

app.include_router(auth_router, prefix="/api")
app.include_router(users_router, prefix="/api")
app.include_router(orders_router, prefix="/api")
app.include_router(bids_router, prefix="/api")
app.include_router(moderation_router, prefix="/api")
app.include_router(crawler_router, prefix="/api")
app.include_router(notifications_router, prefix="/api")
app.include_router(reports_router, prefix="/api")

# Статика — путь относительно backend/
static_dir = os.path.join(os.path.dirname(__file__), "..", "static")
if os.path.exists(static_dir):
    app.mount("/", StaticFiles(directory=static_dir, html=True), name="static")
