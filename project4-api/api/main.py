"""FastAPI application entry point."""

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from api.database import engine, Base, import_partners_json

BASE_DIR = Path(__file__).resolve().parent.parent
TEMPLATES_DIR = BASE_DIR / "web" / "templates"
STATIC_DIR = BASE_DIR / "web" / "static"


@asynccontextmanager
async def lifespan(app):
    Base.metadata.create_all(bind=engine)
    import_partners_json()
    yield


app = FastAPI(
    title="School Partners API",
    description="API for university partners, programs and olympiads data",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

from api.routers import universities, programs, olympiads, admin

app.include_router(universities.router, prefix="/api", tags=["Universities"])
app.include_router(programs.router, prefix="/api", tags=["Programs"])
app.include_router(olympiads.router, prefix="/api", tags=["Olympiads"])
app.include_router(admin.router)

app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


@app.get("/", include_in_schema=False)
def serve_index():
    return FileResponse(str(TEMPLATES_DIR / "index.html"))


@app.get("/admin.html", include_in_schema=False)
def serve_admin():
    return FileResponse(str(TEMPLATES_DIR / "admin.html"))


@app.get("/programs.html", include_in_schema=False)
def serve_programs():
    return FileResponse(str(TEMPLATES_DIR / "programs.html"))


@app.get("/olympiads.html", include_in_schema=False)
def serve_olympiads():
    return FileResponse(str(TEMPLATES_DIR / "olympiads.html"))


@app.get("/review.html", include_in_schema=False)
def serve_review():
    return FileResponse(str(TEMPLATES_DIR / "review.html"))
