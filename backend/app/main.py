from fastapi import FastAPI, Request, Form, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import select, or_, func
import os

from app.core.config import settings
from app.core.database import get_db, async_session_factory
from app.core.security import verify_password, get_password_hash, create_access_token, create_refresh_token, decode_token
from app.models.user import User, UserRole
from app.models.order import Order, OrderStatus, OrderStatusHistory
from app.models.bid import Bid, BidStatus
from app.models.crawler_source import CrawlerSource
from app.models.crawler_log import CrawlerLog
from app.models.verification import CustomerVerification, VerificationStatus
from app.models.external_order import ExternalOrder, ExternalOrderStatus
from app.services.crawler_service import crawl_source
from app.api.deps import get_current_user

app = FastAPI(title=settings.PROJECT_NAME, docs_url="/api/docs")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

templates = Jinja2Templates(directory=os.path.join(os.path.dirname(__file__), "..", "templates"))


@app.get("/external-orders", response_class=HTMLResponse)
async def external_orders_page(request: Request):
    user = await get_user_from_cookie(request)
    if not user or user.role != UserRole.ADMIN:
        return RedirectResponse("/login")
    
    async with async_session_factory() as db:
        result = await db.execute(
            select(ExternalOrder).order_by(ExternalOrder.discovered_at.desc()).limit(50)
        )
        orders = result.scalars().all()
    
    return templates.TemplateResponse("admin/external_orders.html", {
        "request": request, "user": user, "active_page": "external_orders", "orders": orders
    })

# API роутеры
from app.api.auth import router as auth_router
from app.api.users import router as users_router
from app.api.orders import router as orders_router
from app.api.bids import router as bids_router
from app.api.moderation import router as moderation_router
from app.api.crawler import router as crawler_router
from app.api.reports import router as reports_router

app.include_router(auth_router, prefix="/api")
app.include_router(users_router, prefix="/api")
app.include_router(orders_router, prefix="/api")
app.include_router(bids_router, prefix="/api")
app.include_router(moderation_router, prefix="/api")
app.include_router(crawler_router, prefix="/api")
app.include_router(reports_router, prefix="/api")

# Функция получения пользователя из куки (для веб-страниц)
async def get_user_from_cookie(request: Request):
    token = request.cookies.get("access_token")
    if not token:
        return None
    try:
        payload = decode_token(token)
        user_id = int(payload.get("sub"))
        async with async_session_factory() as db:
            result = await db.execute(select(User).where(User.id == user_id))
            user = result.scalar_one_or_none()
            if user:
                # Принудительно обновляем is_customer из БД
                await db.refresh(user, ["is_customer", "is_freelancer"])
            return user
    except:
        return None

# Веб-страницы
@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    user = await get_user_from_cookie(request)
    if user:
        return RedirectResponse("/dashboard")
    return RedirectResponse("/login")

@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request, error: str = None):
    return templates.TemplateResponse("registration/login.html", {"request": request, "user": None, "error": error})

@app.post("/login")
async def login_post(request: Request, email: str = Form(...), password: str = Form(...)):
    async with async_session_factory() as db:
        result = await db.execute(select(User).where(User.email == email))
        user = result.scalar_one_or_none()
        if not user or not verify_password(password, user.hashed_password):
            return templates.TemplateResponse("registration/login.html", {"request": request, "user": None, "error": "Неверный email или пароль"})
        if not user.is_active:
            return templates.TemplateResponse("registration/login.html", {"request": request, "user": None, "error": "Аккаунт заблокирован"})
        
        response = RedirectResponse("/dashboard", status_code=302)
        response.set_cookie("access_token", create_access_token(user.id, user.role.value), httponly=True)
        response.set_cookie("refresh_token", create_refresh_token(user.id, user.role.value), httponly=True)
        return response

@app.get("/register", response_class=HTMLResponse)
async def register_page(request: Request, error: str = None):
    return templates.TemplateResponse("registration/register.html", {"request": request, "user": None, "error": error})

@app.post("/register")
async def register_post(request: Request, email: str = Form(...), password: str = Form(...), password_confirm: str = Form(...)):
    if password != password_confirm:
        return templates.TemplateResponse("registration/register.html", {"request": request, "user": None, "error": "Пароли не совпадают"})
    
    async with async_session_factory() as db:
        existing = await db.execute(select(User).where(User.email == email))
        if existing.scalar_one_or_none():
            return templates.TemplateResponse("registration/register.html", {"request": request, "user": None, "error": "Email уже зарегистрирован"})
        
        user = User(email=email, hashed_password=get_password_hash(password))
        db.add(user)
        await db.commit()
        
        response = RedirectResponse("/dashboard", status_code=302)
        response.set_cookie("access_token", create_access_token(user.id, user.role.value), httponly=True)
        response.set_cookie("refresh_token", create_refresh_token(user.id, user.role.value), httponly=True)
        return response

@app.get("/logout")
async def logout():
    response = RedirectResponse("/login")
    response.delete_cookie("access_token")
    response.delete_cookie("refresh_token")
    return response

@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request):
    user = await get_user_from_cookie(request)
    if not user:
        return RedirectResponse("/login")
    
    async with async_session_factory() as db:
        published = await db.scalar(select(func.count(Order.id)).where(Order.status == OrderStatus.PUBLISHED))
        on_mod = await db.scalar(select(func.count(Order.id)).where(Order.status == OrderStatus.ON_MODERATION))
        in_prog = await db.scalar(select(func.count(Order.id)).where(Order.status == OrderStatus.IN_PROGRESS))
        completed = await db.scalar(select(func.count(Order.id)).where(Order.status == OrderStatus.COMPLETED))
        
        cats = await db.execute(select(Order.category, func.count(Order.id)).where(Order.status == OrderStatus.PUBLISHED).group_by(Order.category).order_by(func.count(Order.id).desc()).limit(8))
        popular = [{"category": row[0], "count": row[1]} for row in cats.all()]
    
    return templates.TemplateResponse("dashboard.html", {
        "request": request, "user": user, "active_page": "dashboard",
        "stats": {"published": published or 0, "on_moderation": on_mod or 0, "in_progress": in_prog or 0, "completed": completed or 0},
        "popular_categories": popular
    })

@app.get("/jobs", response_class=HTMLResponse)
async def jobs_list(request: Request, keywords: str = "", category: str = "", budget_from: str = ""):
    user = await get_user_from_cookie(request)
    if not user:
        return RedirectResponse("/login")
    
    async with async_session_factory() as db:
        if user.role == UserRole.CUSTOMER:
            query = select(Order).where(Order.customer_id == user.id).order_by(Order.created_at.desc())
            my_orders = True
            all_orders = (await db.execute(query)).scalars().all()
            external_orders = []
        else:
            # Внутренние заказы
            query = select(Order).where(Order.status == OrderStatus.PUBLISHED)
            my_orders = False
            if keywords:
                query = query.where(or_(Order.title.ilike(f"%{keywords}%"), Order.description.ilike(f"%{keywords}%")))
            if category:
                query = query.where(Order.category == category)
            if budget_from and budget_from.strip():
                try:
                    bf = float(budget_from)
                    query = query.where(Order.budget_max >= bf)
                except ValueError:
                    pass
            
            all_orders = (await db.execute(query)).scalars().all()
            
            # Внешние заказы от краулера
            ext_query = select(ExternalOrder).where(ExternalOrder.status == ExternalOrderStatus.ACTIVE)
            if keywords:
                ext_query = ext_query.where(or_(ExternalOrder.title.ilike(f"%{keywords}%"), ExternalOrder.description.ilike(f"%{keywords}%")))
            if category:
                ext_query = ext_query.where(ExternalOrder.category == category)
            if budget_from and budget_from.strip():
                try:
                    bf = float(budget_from)
                    ext_query = ext_query.where(ExternalOrder.budget_max >= bf)
                except ValueError:
                    pass
            
            external_orders = (await db.execute(ext_query)).scalars().all()
    
    return templates.TemplateResponse("jobs/list.html", {
        "request": request, "user": user, "active_page": "jobs",
        "orders": all_orders, "external_orders": external_orders, "my_orders": my_orders,
        "keywords": keywords or "", "category": category or "", "budget_from": budget_from or ""
    })

@app.get("/create-order", response_class=HTMLResponse)
async def create_order_page(request: Request):
    user = await get_user_from_cookie(request)
    if not user or (not user.is_customer and user.role not in [UserRole.MODERATOR, UserRole.ADMIN]):
        return RedirectResponse("/login")
    return templates.TemplateResponse("customer/create_order.html", {"request": request, "user": user, "active_page": "create_order"})

@app.post("/orders/create")
async def create_order_post(request: Request, title: str = Form(...), description: str = Form(...), category: str = Form(...), required_skills: str = Form(""), budget_min: float = Form(None), budget_max: float = Form(None), payment_format: str = Form("fixed")):
    user = await get_user_from_cookie(request)
    if not user:
        return RedirectResponse("/login")
    
    async with async_session_factory() as db:
        order = Order(title=title, description=description, category=category, required_skills=required_skills, budget_min=budget_min, budget_max=budget_max, payment_format=payment_format, customer_id=user.id, status=OrderStatus.DRAFT)
        db.add(order)
        await db.flush()
        db.add(OrderStatusHistory(order_id=order.id, new_status=OrderStatus.DRAFT, changed_by=user.id))
        await db.commit()
    
    return RedirectResponse("/jobs", status_code=302)

@app.post("/orders/{order_id}/submit")
async def submit_order(order_id: int, request: Request):
    user = await get_user_from_cookie(request)
    if not user:
        return RedirectResponse("/login")
    
    async with async_session_factory() as db:
        order = await db.get(Order, order_id)
        if order and order.customer_id == user.id and order.status == OrderStatus.DRAFT:
            order.status = OrderStatus.ON_MODERATION
            db.add(OrderStatusHistory(order_id=order.id, old_status=OrderStatus.DRAFT, new_status=OrderStatus.ON_MODERATION, changed_by=user.id))
            await db.commit()
    
    return RedirectResponse("/jobs", status_code=302)

@app.get("/jobs/{order_id}/bid", response_class=HTMLResponse)
async def bid_page(order_id: int, request: Request):
    user = await get_user_from_cookie(request)
    if not user:
        return RedirectResponse("/login")
    
    async with async_session_factory() as db:
        order = await db.get(Order, order_id)
        if not order:
            raise HTTPException(404)
    
    return templates.TemplateResponse("jobs/bid.html", {"request": request, "user": user, "order": order})

@app.post("/jobs/{order_id}/bid")
async def bid_post(order_id: int, request: Request, message: str = Form(...), proposed_price: float = Form(...)):
    user = await get_user_from_cookie(request)
    if not user:
        return RedirectResponse("/login")
    
    async with async_session_factory() as db:
        existing = await db.execute(select(Bid).where(Bid.order_id == order_id, Bid.freelancer_id == user.id, Bid.status.in_([BidStatus.SENT, BidStatus.VIEWED, BidStatus.ACCEPTED])))
        if existing.scalar_one_or_none():
            return RedirectResponse("/jobs")
        
        bid = Bid(order_id=order_id, freelancer_id=user.id, message=message, proposed_price=proposed_price)
        db.add(bid)
        await db.commit()
    
    return RedirectResponse("/jobs", status_code=302)

@app.get("/moderation", response_class=HTMLResponse)
async def moderation_page(request: Request):
    user = await get_user_from_cookie(request)
    if not user or user.role not in [UserRole.MODERATOR, UserRole.ADMIN]:
        return RedirectResponse("/login")
    
    async with async_session_factory() as db:
        result = await db.execute(select(Order).where(Order.status == OrderStatus.ON_MODERATION).order_by(Order.created_at.asc()))
        orders = result.scalars().all()
    
    return templates.TemplateResponse("moderator/moderation.html", {"request": request, "user": user, "active_page": "moderation", "orders": orders})

@app.post("/moderation/orders/{order_id}/approve")
async def moderation_approve(order_id: int, request: Request):
    user = await get_user_from_cookie(request)
    if not user or user.role not in [UserRole.MODERATOR, UserRole.ADMIN]:
        return RedirectResponse("/login")
    
    async with async_session_factory() as db:
        order = await db.get(Order, order_id)
        if order and order.status == OrderStatus.ON_MODERATION:
            order.status = OrderStatus.PUBLISHED
            db.add(OrderStatusHistory(order_id=order.id, old_status=OrderStatus.ON_MODERATION, new_status=OrderStatus.PUBLISHED, changed_by=user.id))
            await db.commit()
    
    return RedirectResponse("/moderation", status_code=302)

@app.post("/moderation/orders/{order_id}/reject")
async def moderation_reject(order_id: int, reason: str, request: Request):
    user = await get_user_from_cookie(request)
    if not user or user.role not in [UserRole.MODERATOR, UserRole.ADMIN]:
        return RedirectResponse("/login")
    
    async with async_session_factory() as db:
        order = await db.get(Order, order_id)
        if order and order.status == OrderStatus.ON_MODERATION:
            order.status = OrderStatus.REJECTED
            order.rejection_reason = reason
            db.add(OrderStatusHistory(order_id=order.id, old_status=OrderStatus.ON_MODERATION, new_status=OrderStatus.REJECTED, changed_by=user.id))
            await db.commit()
    
    return RedirectResponse("/moderation", status_code=302)

@app.get("/crawler", response_class=HTMLResponse)
async def crawler_page(request: Request):
    user = await get_user_from_cookie(request)
    if not user or user.role != UserRole.ADMIN:
        return RedirectResponse("/login")
    
    async with async_session_factory() as db:
        sources = (await db.execute(select(CrawlerSource).order_by(CrawlerSource.created_at.desc()))).scalars().all()
        logs = (await db.execute(select(CrawlerLog).order_by(CrawlerLog.created_at.desc()).limit(20))).scalars().all()
    
    return templates.TemplateResponse("admin/crawler.html", {"request": request, "user": user, "active_page": "crawler", "sources": sources, "logs": logs})

@app.post("/crawler/sources")
async def crawler_add_source(request: Request, name: str = Form(...), base_url: str = Form(...)):
    user = await get_user_from_cookie(request)
    if not user or user.role != UserRole.ADMIN:
        return RedirectResponse("/login")
    
    async with async_session_factory() as db:
        source = CrawlerSource(name=name, base_url=base_url)
        db.add(source)
        await db.commit()
    
    return RedirectResponse("/crawler", status_code=302)

@app.get("/crawler/run/{source_id}")
async def crawler_run(source_id: int, request: Request):
    user = await get_user_from_cookie(request)
    if not user or user.role != UserRole.ADMIN:
        return RedirectResponse("/login")
    
    await crawl_source(source_id)
    
    return RedirectResponse("/crawler", status_code=302)

@app.get("/reports", response_class=HTMLResponse)
async def reports_page(request: Request):
    user = await get_user_from_cookie(request)
    if not user or user.role not in [UserRole.MODERATOR, UserRole.ADMIN]:
        return RedirectResponse("/login")
    
    async with async_session_factory() as db:
        published = await db.scalar(select(func.count(Order.id)).where(Order.status == OrderStatus.PUBLISHED))
        on_mod = await db.scalar(select(func.count(Order.id)).where(Order.status == OrderStatus.ON_MODERATION))
        in_prog = await db.scalar(select(func.count(Order.id)).where(Order.status == OrderStatus.IN_PROGRESS))
        completed = await db.scalar(select(func.count(Order.id)).where(Order.status == OrderStatus.COMPLETED))
        cats = await db.execute(select(Order.category, func.count(Order.id)).where(Order.status == OrderStatus.PUBLISHED).group_by(Order.category).order_by(func.count(Order.id).desc()).limit(10))
        
    return templates.TemplateResponse("moderator/reports.html", {
        "request": request, "user": user, "active_page": "reports",
        "report": {
            "orders": {"published": published or 0, "on_moderation": on_mod or 0, "in_progress": in_prog or 0, "completed": completed or 0},
            "popular_categories": [{"category": row[0], "count": row[1]} for row in cats.all()]
        }
    })

@app.get("/external-orders/{order_id}/approve")
async def external_order_approve(order_id: int, request: Request):
    user = await get_user_from_cookie(request)
    if not user or user.role not in [UserRole.MODERATOR, UserRole.ADMIN]:
        return RedirectResponse("/login")
    
    async with async_session_factory() as db:
        order = await db.get(ExternalOrder, order_id)
        if order:
            order.status = ExternalOrderStatus.ACTIVE
            await db.commit()
    
    return RedirectResponse("/external-orders", status_code=302)

@app.get("/external-orders/{order_id}/archive")
async def external_order_archive(order_id: int, request: Request):
    user = await get_user_from_cookie(request)
    if not user or user.role not in [UserRole.MODERATOR, UserRole.ADMIN]:
        return RedirectResponse("/login")
    
    async with async_session_factory() as db:
        order = await db.get(ExternalOrder, order_id)
        if order:
            order.status = ExternalOrderStatus.ARCHIVED
            await db.commit()
    
    return RedirectResponse("/external-orders", status_code=302)

@app.get("/users", response_class=HTMLResponse)
async def users_list(request: Request):
    user = await get_user_from_cookie(request)
    if not user or user.role != UserRole.ADMIN:
        return RedirectResponse("/login")
    
    async with async_session_factory() as db:
        result = await db.execute(select(User).order_by(User.id))
        users = result.scalars().all()
    
    return templates.TemplateResponse("admin/users.html", {
        "request": request, "user": user, "active_page": "users", "users": users
    })

@app.get("/users/{user_id}/role/{role}")
async def change_user_role(user_id: int, role: str, request: Request):
    user = await get_user_from_cookie(request)
    if not user or user.role != UserRole.ADMIN:
        return RedirectResponse("/login")
    
    async with async_session_factory() as db:
        target = await db.get(User, user_id)
        if target:
            target.role = UserRole(role)
            await db.commit()
    
    return RedirectResponse("/users", status_code=302)

@app.get("/users/{user_id}/block")
async def toggle_user_block(user_id: int, request: Request):
    user = await get_user_from_cookie(request)
    if not user or user.role != UserRole.ADMIN:
        return RedirectResponse("/login")
    
    async with async_session_factory() as db:
        target = await db.get(User, user_id)
        if target:
            target.is_active = not target.is_active
            await db.commit()
    
    return RedirectResponse("/users", status_code=302)

@app.get("/become-customer", response_class=HTMLResponse)
async def become_customer_page(request: Request):
    user = await get_user_from_cookie(request)
    if not user:
        return RedirectResponse("/login")
    
    async with async_session_factory() as db:
        existing = await db.execute(
            select(CustomerVerification).where(
                CustomerVerification.user_id == user.id,
                CustomerVerification.status == VerificationStatus.PENDING
            )
        )
        already = existing.scalar_one_or_none()
    
    return templates.TemplateResponse("freelancer/become_customer.html", {
        "request": request, "user": user, "already_requested": already is not None
    })

@app.post("/become-customer")
async def become_customer_post(
    request: Request,
    company_name: str = Form(...),
    description: str = Form(...),
    reason: str = Form(...),
    contact_phone: str = Form(""),
    contact_telegram: str = Form("")
):
    user = await get_user_from_cookie(request)
    if not user:
        return RedirectResponse("/login")
    
    async with async_session_factory() as db:
        existing = await db.execute(
            select(CustomerVerification).where(
                CustomerVerification.user_id == user.id,
                CustomerVerification.status == VerificationStatus.PENDING
            )
        )
        if existing.scalar_one_or_none():
            return templates.TemplateResponse("freelancer/become_customer.html", {
                "request": request, "user": user, "already_requested": True,
                "error": "У вас уже есть активная заявка"
            })
        
        verification = CustomerVerification(
            user_id=user.id,
            company_name=company_name,
            description=description,
            reason=reason,
            contact_phone=contact_phone,
            contact_telegram=contact_telegram
        )
        db.add(verification)
        await db.commit()
    
    return templates.TemplateResponse("freelancer/become_customer.html", {
        "request": request, "user": user, "already_requested": True,
        "success": "Заявка отправлена! Администратор рассмотрит её."
    })

@app.get("/admin/verifications", response_class=HTMLResponse)
async def verifications_list(request: Request):
    user = await get_user_from_cookie(request)
    if not user or user.role != UserRole.ADMIN:
        return RedirectResponse("/login")
    
    async with async_session_factory() as db:
        result = await db.execute(
            select(CustomerVerification).where(
                CustomerVerification.status == VerificationStatus.PENDING
            ).order_by(CustomerVerification.created_at.asc())
        )
        verifications = result.scalars().all()
        
        # Заранее загружаем email пользователя для каждой заявки
        verifications_data = []
        for v in verifications:
            v_user = await db.get(User, v.user_id)
            verifications_data.append({
                "id": v.id,
                "company_name": v.company_name,
                "description": v.description,
                "reason": v.reason,
                "contact_phone": v.contact_phone,
                "contact_telegram": v.contact_telegram,
                "status": v.status,
                "created_at": v.created_at,
                "user_email": v_user.email if v_user else "Неизвестно"
            })
    
    return templates.TemplateResponse("admin/verifications.html", {
        "request": request, "user": user, "active_page": "verifications",
        "verifications": verifications_data
    })

@app.get("/admin/verifications/{v_id}/approve")
async def approve_verification(v_id: int, request: Request):
    admin_user = await get_user_from_cookie(request)
    if not admin_user or admin_user.role != UserRole.ADMIN:
        return RedirectResponse("/login")
    
    async with async_session_factory() as db:
        v = await db.get(CustomerVerification, v_id)
        if v:
            v.status = VerificationStatus.APPROVED
            target = await db.get(User, v.user_id)
            if target:
                target.is_customer = True
                # Создаём CustomerProfile только если ещё нет
                from app.models.profile import CustomerProfile
                existing_profile = await db.execute(
                    select(CustomerProfile).where(CustomerProfile.user_id == target.id)
                )
                if not existing_profile.scalar_one_or_none():
                    profile = CustomerProfile(
                        user_id=target.id,
                        company_name=v.company_name,
                        description=v.description,
                        contact_phone=v.contact_phone,
                        contact_telegram=v.contact_telegram
                    )
                    db.add(profile)
            
            # Обновляем токен пользователя (перезаписываем is_customer)
            new_token = create_access_token(target.id, target.role.value)
            await db.commit()
    
    response = RedirectResponse("/admin/verifications", status_code=302)
    response.set_cookie("access_token", new_token, httponly=True)
    return response

@app.get("/admin/verifications/{v_id}/reject")
async def reject_verification(v_id: int, comment: str = "", request: Request = None):
    user = await get_user_from_cookie(request)
    if not user or user.role != UserRole.ADMIN:
        return RedirectResponse("/login")
    
    async with async_session_factory() as db:
        v = await db.get(CustomerVerification, v_id)
        if v:
            v.status = VerificationStatus.REJECTED
            v.admin_comment = comment
            await db.commit()
    
    return RedirectResponse("/admin/verifications", status_code=302)
