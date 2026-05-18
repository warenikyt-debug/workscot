import hashlib
import asyncio
import httpx
from bs4 import BeautifulSoup
from datetime import datetime
from sqlalchemy import select
from app.core.database import async_session_factory
from app.models.crawler_source import CrawlerSource
from app.models.crawler_log import CrawlerLog
from app.models.external_order import ExternalOrder, ExternalOrderStatus

async def crawl_source(source_id: int):
    """Обходит сайт-источник и собирает заказы"""
    async with async_session_factory() as db:
        source = await db.get(CrawlerSource, source_id)
        if not source:
            return
        
        items_found = 0
        error_msg = None
        status = "success"
        
        try:
            async with httpx.AsyncClient(timeout=30, follow_redirects=True) as client:
                response = await client.get(source.base_url)
                
                if response.status_code == 200:
                    soup = BeautifulSoup(response.text, 'html.parser')
                    
                    # Ищем ссылки и заголовки на странице
                    links = soup.find_all('a', href=True)
                    for link in links[:20]:  # Ограничиваем 20 первыми ссылками
                        title = link.get_text(strip=True)
                        href = link.get('href', '')
                        
                        if title and len(title) > 10:  # Только осмысленные заголовки
                            # Создаём уникальный ID из URL
                            external_id = hashlib.md5(href.encode()).hexdigest()
                            
                            # Проверяем нет ли уже такого заказа
                            existing = await db.execute(
                                select(ExternalOrder).where(ExternalOrder.external_id == external_id)
                            )
                            if existing.scalar_one_or_none():
                                continue
                            
                            # Сохраняем новый внешний заказ
                            order = ExternalOrder(
                                external_id=external_id,
                                title=title[:500],
                                description=f"Найден на {source.name}",
                                source_url=href if href.startswith('http') else source.base_url + href,
                                source_name=source.name,
                                category="Не указана",
                                budget="Не указан",
                                budget_min=None,
                                budget_max=None,
                                status=ExternalOrderStatus.NEW,
                                discovered_at=datetime.utcnow(),
                                last_updated=datetime.utcnow(),
                            )
                            db.add(order)
                            items_found += 1
                    
                    await db.commit()
                else:
                    status = "error"
                    error_msg = f"HTTP {response.status_code}"
        except Exception as e:
            status = "error"
            error_msg = str(e)[:500]
        
        # Пишем лог
        log = CrawlerLog(
            source_id=source_id,
            status=status,
            items_found=items_found,
            error_message=error_msg,
        )
        db.add(log)
        await db.commit()
        
        return {"status": status, "items_found": items_found, "error": error_msg}
