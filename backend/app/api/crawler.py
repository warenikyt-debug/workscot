from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy import select
from app.api.deps import Database, CurrentUser, require_role
from app.models.user import User, UserRole
from app.models.crawler_source import CrawlerSource, SourceStatus
from app.models.crawler_log import CrawlerLog

router = APIRouter(prefix="/crawler", tags=["crawler"])


@router.get("/sources")
async def get_sources(
    db: Database,
    admin: User = Depends(require_role(UserRole.ADMIN)),
):
    result = await db.execute(select(CrawlerSource).order_by(CrawlerSource.created_at.desc()))
    return result.scalars().all()


@router.post("/sources")
async def add_source(
    name: str,
    base_url: str,
    crawl_rules: str = None,
    extract_rules: str = None,
    interval_minutes: int = 60,
    db: Database = None,
    admin: User = Depends(require_role(UserRole.ADMIN)),
):
    source = CrawlerSource(
        name=name,
        base_url=base_url,
        crawl_rules=crawl_rules,
        extract_rules=extract_rules,
        interval_minutes=interval_minutes,
    )
    db.add(source)
    await db.flush()
    await db.refresh(source)
    return source


@router.patch("/sources/{source_id}")
async def update_source(
    source_id: int,
    name: str = None,
    base_url: str = None,
    crawl_rules: str = None,
    extract_rules: str = None,
    interval_minutes: int = None,
    status: SourceStatus = None,
    db: Database = None,
    admin: User = Depends(require_role(UserRole.ADMIN)),
):
    source = await db.get(CrawlerSource, source_id)
    if not source:
        raise HTTPException(status_code=404, detail="Источник не найден")

    if name is not None:
        source.name = name
    if base_url is not None:
        source.base_url = base_url
    if crawl_rules is not None:
        source.crawl_rules = crawl_rules
    if extract_rules is not None:
        source.extract_rules = extract_rules
    if interval_minutes is not None:
        source.interval_minutes = interval_minutes
    if status is not None:
        source.status = status

    await db.refresh(source)
    return source


@router.get("/logs")
async def get_logs(
    source_id: int = None,
    limit: int = 50,
    db: Database = None,
    admin: User = Depends(require_role(UserRole.ADMIN)),
):
    query = select(CrawlerLog).order_by(CrawlerLog.created_at.desc()).limit(limit)
    if source_id:
        query = query.where(CrawlerLog.source_id == source_id)
    result = await db.execute(query)
    return result.scalars().all()


@router.post("/run/{source_id}")
async def run_crawler(
    source_id: int,
    db: Database,
    admin: User = Depends(require_role(UserRole.ADMIN)),
):
    source = await db.get(CrawlerSource, source_id)
    if not source:
        raise HTTPException(status_code=404, detail="Источник не найден")
    return {"message": f"Краулер для источника '{source.name}' запущен", "source_id": source_id}
