"""
main.py — FastAPI приложение Биотех225 Admin.

Точка входа: uvicorn main:app --reload
Swagger UI: http://localhost:8000/docs
ReDoc:      http://localhost:8000/redoc
"""

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, RedirectResponse

from api.database import init_db
from api.routers import students as students_router
# Подключаем по мере готовности:
# from routers import exams as exams_router
# from routers import receipts as receipts_router
# from routers import classes as classes_router
# from routers import universities as universities_router
# from routers import auth as auth_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup: инициализация БД из JSON-файлов."""
    print("🚀 Initializing database...")
    init_db()
    print("✅ App ready!")
    yield


app = FastAPI(
    title="Биотех225 Admin API",
    description="""
API для управления школой Биотех225.

## Разделы

- **Ученики** — CRUD, поиск, фильтрация по классу
- **Выбор ЕГЭ** — предметы ЕГЭ для 11-классников
- **Классы** — справочник классов и расчёт стоимости
- **Квитанции** — генерация PDF (одиночная и пакетная)
- **Вузы** — программы подготовки и олимпиады
- **Авторизация** — JWT, роли admin / manager / viewer
""",
    version="5.0.0",
    lifespan=lifespan,
    docs_url="/docs",       # Swagger UI
    redoc_url="/redoc",     # ReDoc
)

# ─────────────── Роутеры ───────────────

app.include_router(students_router.router)
# app.include_router(exams_router.router)
# app.include_router(receipts_router.router)
# app.include_router(classes_router.router)
# app.include_router(universities_router.router)
# app.include_router(auth_router.router)


# ─────────────── Статика и HTML ───────────────

STATIC_DIR = Path("static")
STATIC_DIR.mkdir(exist_ok=True)

app.mount("/static", StaticFiles(directory="static"), name="static")


@app.get("/", response_class=HTMLResponse)
async def root():
    """Главная страница — отдаёт SPA-интерфейс."""
    html_path = Path("static/index.html")
    if html_path.exists():
        return HTMLResponse(html_path.read_text(encoding="utf-8"))
    return HTMLResponse("<h3>Положите biotech225_admin.html в static/index.html</h3>")


@app.get("/api")
async def api_info():
    """Мета-информация об API."""
    return {
        "app": "Биотех225 Admin",
        "version": "5.0.0",
        "docs": "/docs",
        "redoc": "/redoc",
        "endpoints": {
            "students": "/api/students",
            "exams": "/api/exams (coming soon)",
            "classes": "/api/classes (coming soon)",
            "receipts": "/api/receipts (coming soon)",
            "universities": "/api/universities (coming soon)",
            "auth": "/api/auth (coming soon)",
        },
    }
