"""
main.py - FastAPI app для админки "Биотех225".
Lifespan, middleware, подключение роутеров, статика и шаблоны.
"""

import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import RedirectResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from .database import init_db
from .auth import decode_access_token

# ─── Роутеры ──────────────────────────────────────────────────
from .routers import auth as auth_router
from .routers import admin as admin_router
from .routers import universities as universities_router
from .routers import programs as programs_router
from .routers import olympiads as olympiads_router
from .routers import students as students_router
from .routers import receipts as receipts_router
from .routers import analytics as analytics_router


# ─── Lifespan: создание таблиц при старте ────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


# ─── Приложение ───────────────────────────────────────────────
app = FastAPI(
    title="Биотех225 — Админка",
    description="Административная панель профильной школы",
    version="5.0.0",
    lifespan=lifespan,
)


# ─── Шаблоны Jinja2 ──────────────────────────────────────────
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TEMPLATES_DIR = os.path.join(BASE_DIR, "web", "templates")
templates = Jinja2Templates(directory=TEMPLATES_DIR)


# ─── Middleware: редирект на /login если нет токена ────────────
PUBLIC_PATHS = {"/login", "/api/login", "/api/register/json", "/docs", "/openapi.json", "/redoc"}


@app.middleware("http")
async def auth_middleware(request: Request, call_next):
    path = request.url.path

    # Пропускаем публичные пути и статику
    if path in PUBLIC_PATHS or path.startswith("/static"):
        return await call_next(request)

    # Проверяем токен
    token = request.cookies.get("access_token")
    if not token:
        return RedirectResponse(url="/login", status_code=302)

    payload = decode_access_token(token)
    if payload is None:
        response = RedirectResponse(url="/login", status_code=302)
        response.delete_cookie("access_token")
        return response

    return await call_next(request)


# ─── Подключение роутеров ─────────────────────────────────────
app.include_router(auth_router.router)
app.include_router(admin_router.router)
app.include_router(universities_router.router)
app.include_router(programs_router.router)
app.include_router(olympiads_router.router)
app.include_router(students_router.router)
app.include_router(receipts_router.router)
app.include_router(analytics_router.router)


# ─── Главная страница ─────────────────────────────────────────
@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    """Главная страница с навигацией по ролям."""
    token = request.cookies.get("access_token")
    payload = decode_access_token(token) if token else None
    role = payload.get("role", "viewer") if payload else "viewer"
    username = payload.get("sub", "") if payload else ""

    return templates.TemplateResponse("index.html", {
        "request": request,
        "role": role,
        "username": username,
    })
