
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from api.database import engine, Base, import_partners_json
from api.routers import universities, programs, olympiads

app = FastAPI(
    title="School Partners API",
    description="API for university partners, programs and olympiads data",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(universities.router, prefix="/api", tags=["Universities"])
app.include_router(programs.router, prefix="/api", tags=["Programs"])
app.include_router(olympiads.router, prefix="/api", tags=["Olympiads"])

app.mount("/static", StaticFiles(directory="web/static"), name="static")


@app.on_event("startup")
def on_startup():
    Base.metadata.create_all(bind=engine)
    import_partners_json()


@app.get("/api/stats", tags=["Stats"])
def get_stats():
    from api.database import SessionLocal
    from api.models import University, Program, Olympiad
    db = SessionLocal()
    try:
        return {
            "universities": db.query(University).count(),
            "programs": db.query(Program).count(),
            "olympiads": db.query(Olympiad).count(),
        }
    finally:
        db.close()


@app.get("/", include_in_schema=False)
def serve_index():
    return FileResponse("web/templates/index.html")


@app.get("/{page}.html", include_in_schema=False)
def serve_page(page: str):
    path = Path(f"web/templates/{page}.html")
    if path.exists():
        return FileResponse(path)
    return FileResponse("web/templates/index.html")
