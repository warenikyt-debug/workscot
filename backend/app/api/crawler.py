from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy import select
from app.api.deps import Database, CurrentUser, require_role
from app.models.user import User, UserRole
from app.models.crawler_source import CrawlerSource, SourceStatus
from app.models.crawler_log import CrawlerLog
from app.services.crawler_service import crawl_source

router = APIRouter(prefix="/crawler", tags=["crawler"])

@router.get("/sources")
async def get_sources(db: Database, admin: User = Depends(require_role(UserRole.ADMIN))):
    result = await db.execute(select(CrawlerSource).order_by(CrawlerSource.created_at.desc()))
    return result.scalars().all()

@router.post("/sources")
async def add_source(name: str, base_url: str, db: Database, admin: User = Depends(require_role(UserRole.ADMIN))):
    source = CrawlerSource(name=name, base_url=base_url)
    db.add(source)
    await db.flush()
    await db.refresh(source)
    return source

@router.get("/logs")
async def get_logs(db: Database, admin: User = Depends(require_role(UserRole.ADMIN))):
    result = await db.execute(select(CrawlerLog).order_by(CrawlerLog.created_at.desc()).limit(50))
    return result.scalars().all()

@router.post("/run/{source_id}")
async def run_crawler(source_id: int, admin: User = Depends(require_role(UserRole.ADMIN))):
    result = await crawl_source(source_id)
    return result
