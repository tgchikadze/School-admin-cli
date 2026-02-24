#!/usr/bin/env python3
"""
Create project4-api structure inside the monorepo.

Usage:
    python create_project4.py
    python create_project4.py --root E:\\path\\to\\school-admin-system
"""

import argparse
import os
from pathlib import Path

DIRS = [
    "api",
    "api/routers",
    "web/static/css",
    "web/static/js",
    "web/templates",
    "data",
    "tests",
    "screenshots",
]

FILES = {}

FILES["api/__init__.py"] = ""

FILES["api/main.py"] = """
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
"""

FILES["api/database.py"] = """
import json
from pathlib import Path
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

DATABASE_URL = "sqlite:///data/school.db"

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def import_partners_json():
    from api.models import University, Program, Olympiad

    db = SessionLocal()
    if db.query(University).count() > 0:
        db.close()
        return

    json_path = Path("data/partners.json")
    if not json_path.exists():
        print(f"WARNING: {json_path} not found, DB stays empty")
        db.close()
        return

    with open(json_path, "r", encoding="utf-8") as fp:
        data = json.load(fp)

    for uni_id, uni_data in data.items():
        progs = uni_data.get("programs", [])
        olyms = uni_data.get("olympiads", [])
        if not progs and not olyms:
            continue

        first = progs[0] if progs else {}
        uni = University(
            id=uni_id,
            name=first.get("university_name", uni_id),
            city=first.get("city", ""),
        )
        db.add(uni)

        for p in progs:
            db.add(Program(
                university_id=uni_id,
                okso_code=p.get("okso_code", ""),
                program_name=p.get("program_name", ""),
                program_level=p.get("program_level", ""),
                min_score=p.get("min_score", ""),
                avg_score=p.get("avg_score", ""),
                budget_places=p.get("budget_places", ""),
                cost=p.get("cost", ""),
                ege_subjects=p.get("ege_subjects", ""),
                achievements=p.get("achievements", "")[:500],
                source=p.get("source", ""),
                page_url=p.get("page_url", ""),
            ))

        for o in olyms:
            db.add(Olympiad(
                university_id=uni_id,
                olympiad_name=o.get("olympiad_name", ""),
                olympiad_level=o.get("olympiad_level", ""),
                subject=o.get("subject", ""),
                benefit_type=o.get("benefit_type", o.get("benefit_types", "")),
                benefit_detail=o.get("benefit_detail", "")[:1000],
                source_url=o.get("olympiad_url", ""),
            ))

    db.commit()
    total_u = db.query(University).count()
    total_p = db.query(Program).count()
    total_o = db.query(Olympiad).count()
    print(f"Imported: {total_u} universities, {total_p} programs, {total_o} olympiads")
    db.close()
"""

FILES["api/models.py"] = """
from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.orm import relationship
from api.database import Base


class University(Base):
    __tablename__ = "universities"
    id = Column(String, primary_key=True)
    name = Column(String, nullable=False)
    city = Column(String, default="")
    programs = relationship("Program", back_populates="university")
    olympiads = relationship("Olympiad", back_populates="university")


class Program(Base):
    __tablename__ = "programs"
    id = Column(Integer, primary_key=True, autoincrement=True)
    university_id = Column(String, ForeignKey("universities.id"))
    okso_code = Column(String, default="")
    program_name = Column(String, default="")
    program_level = Column(String, default="")
    min_score = Column(String, default="")
    avg_score = Column(String, default="")
    budget_places = Column(String, default="")
    cost = Column(String, default="")
    ege_subjects = Column(String, default="")
    achievements = Column(String, default="")
    source = Column(String, default="")
    page_url = Column(String, default="")
    university = relationship("University", back_populates="programs")


class Olympiad(Base):
    __tablename__ = "olympiads"
    id = Column(Integer, primary_key=True, autoincrement=True)
    university_id = Column(String, ForeignKey("universities.id"))
    olympiad_name = Column(String, default="")
    olympiad_level = Column(String, default="")
    subject = Column(String, default="")
    benefit_type = Column(String, default="")
    benefit_detail = Column(String, default="")
    source_url = Column(String, default="")
    university = relationship("University", back_populates="olympiads")
"""

FILES["api/schemas.py"] = """
from typing import List, Optional
from pydantic import BaseModel, Field


class ProgramOut(BaseModel):
    id: int
    university_id: str
    okso_code: str
    program_name: str
    program_level: str
    min_score: str
    budget_places: str
    cost: str
    ege_subjects: str
    class Config:
        from_attributes = True


class OlympiadOut(BaseModel):
    id: int
    university_id: str
    olympiad_name: str
    olympiad_level: str
    subject: str
    benefit_type: str
    benefit_detail: str
    class Config:
        from_attributes = True


class UniversityOut(BaseModel):
    id: str
    name: str
    city: str
    class Config:
        from_attributes = True


class UniversityDetailOut(UniversityOut):
    programs: List[ProgramOut] = []
    olympiads: List[OlympiadOut] = []
"""

FILES["api/dependencies.py"] = """
from fastapi import Query


def pagination_params(
    page: int = Query(1, ge=1, description="Page number"),
    size: int = Query(20, ge=1, le=100, description="Items per page"),
):
    return {"page": page, "size": size}
"""

FILES["api/routers/__init__.py"] = ""

FILES["api/routers/universities.py"] = """
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from api.database import get_db
from api.models import University
from api.schemas import UniversityOut, UniversityDetailOut

router = APIRouter()


@router.get("/universities")
def list_universities(
    city: Optional[str] = Query(None, description="Filter by city"),
    search: Optional[str] = Query(None, description="Search by name"),
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    q = db.query(University)
    if city:
        q = q.filter(University.city.ilike(f"%{city}%"))
    if search:
        q = q.filter(University.name.ilike(f"%{search}%"))
    total = q.count()
    items = q.offset((page - 1) * size).limit(size).all()
    return {
        "items": [UniversityOut.model_validate(u).model_dump() for u in items],
        "total": total, "page": page, "size": size,
        "pages": (total + size - 1) // size,
    }


@router.get("/universities/{uni_id}")
def get_university(uni_id: str, db: Session = Depends(get_db)):
    uni = db.query(University).filter(University.id == uni_id).first()
    if not uni:
        raise HTTPException(status_code=404, detail=f"University '{uni_id}' not found")
    return UniversityDetailOut.model_validate(uni).model_dump()
"""

FILES["api/routers/programs.py"] = """
from typing import Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from api.database import get_db
from api.models import Program
from api.schemas import ProgramOut

router = APIRouter()


@router.get("/programs")
def list_programs(
    university_id: Optional[str] = Query(None),
    city: Optional[str] = Query(None),
    okso_code: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    sort_by: Optional[str] = Query(None, enum=["program_name", "okso_code", "min_score"]),
    order: Optional[str] = Query("asc", enum=["asc", "desc"]),
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    q = db.query(Program)
    if university_id:
        q = q.filter(Program.university_id == university_id)
    if okso_code:
        q = q.filter(Program.okso_code.ilike(f"%{okso_code}%"))
    if search:
        q = q.filter(Program.program_name.ilike(f"%{search}%"))
    if city:
        from api.models import University
        q = q.join(University).filter(University.city.ilike(f"%{city}%"))
    if sort_by:
        col = getattr(Program, sort_by, None)
        if col:
            q = q.order_by(col.desc() if order == "desc" else col.asc())
    total = q.count()
    items = q.offset((page - 1) * size).limit(size).all()
    return {
        "items": [ProgramOut.model_validate(p).model_dump() for p in items],
        "total": total, "page": page, "size": size,
        "pages": (total + size - 1) // size,
    }
"""

FILES["api/routers/olympiads.py"] = """
from typing import Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from api.database import get_db
from api.models import Olympiad
from api.schemas import OlympiadOut

router = APIRouter()


@router.get("/olympiads")
def list_olympiads(
    university_id: Optional[str] = Query(None),
    subject: Optional[str] = Query(None),
    level: Optional[str] = Query(None),
    benefit_type: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    q = db.query(Olympiad)
    if university_id:
        q = q.filter(Olympiad.university_id == university_id)
    if subject:
        q = q.filter(Olympiad.subject.ilike(f"%{subject}%"))
    if level:
        q = q.filter(Olympiad.olympiad_level == level)
    if benefit_type:
        q = q.filter(Olympiad.benefit_type.ilike(f"%{benefit_type}%"))
    if search:
        q = q.filter(Olympiad.olympiad_name.ilike(f"%{search}%"))
    total = q.count()
    items = q.offset((page - 1) * size).limit(size).all()
    return {
        "items": [OlympiadOut.model_validate(o).model_dump() for o in items],
        "total": total, "page": page, "size": size,
        "pages": (total + size - 1) // size,
    }
"""

FILES["web/static/css/style.css"] = """
body { background-color: #f8f9fa; }
.card-uni { transition: transform 0.2s; }
.card-uni:hover { transform: translateY(-4px); box-shadow: 0 4px 12px rgba(0,0,0,.15); }
.filter-panel { background: #fff; border-radius: 8px; padding: 1.5rem; margin-bottom: 1.5rem; box-shadow: 0 1px 3px rgba(0,0,0,.1); }
.badge-bvi { background-color: #198754; }
.badge-100 { background-color: #0d6efd; }
.badge-extra { background-color: #6c757d; }
.pagination .page-link { cursor: pointer; }
"""

FILES["web/static/js/app.js"] = """
const API = "";

async function fetchJSON(url) {
    const resp = await fetch(url);
    if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
    return resp.json();
}

async function loadUniversities(page = 1) {
    const city = document.getElementById("filterCity")?.value || "";
    const search = document.getElementById("filterSearch")?.value || "";
    let url = `${API}/api/universities?page=${page}&size=20`;
    if (city) url += `&city=${encodeURIComponent(city)}`;
    if (search) url += `&search=${encodeURIComponent(search)}`;
    const data = await fetchJSON(url);
    renderUniversities(data);
}

function renderUniversities(data) {
    const c = document.getElementById("uniList");
    if (!c) return;
    c.innerHTML = data.items.map(u => `
        <div class="col-md-4 mb-3"><div class="card card-uni h-100"><div class="card-body">
            <h5 class="card-title">${u.name}</h5>
            <p class="card-text text-muted">${u.city}</p>
        </div></div></div>`).join("");
    renderPagination(data, "uniPagination", loadUniversities);
}

async function loadPrograms(page = 1) {
    const uni = document.getElementById("filterUni")?.value || "";
    const okso = document.getElementById("filterOkso")?.value || "";
    const search = document.getElementById("filterSearch")?.value || "";
    let url = `${API}/api/programs?page=${page}&size=20`;
    if (uni) url += `&university_id=${encodeURIComponent(uni)}`;
    if (okso) url += `&okso_code=${encodeURIComponent(okso)}`;
    if (search) url += `&search=${encodeURIComponent(search)}`;
    const data = await fetchJSON(url);
    renderPrograms(data);
}

function renderPrograms(data) {
    const tb = document.getElementById("programsBody");
    if (!tb) return;
    tb.innerHTML = data.items.map(p => `<tr>
        <td>${p.university_id}</td><td>${p.okso_code}</td><td>${p.program_name}</td>
        <td>${p.program_level}</td><td>${p.min_score || "-"}</td>
        <td>${p.budget_places || "-"}</td><td>${p.cost || "-"}</td>
        <td>${p.ege_subjects || "-"}</td></tr>`).join("");
    renderPagination(data, "programsPagination", loadPrograms);
}

async function loadOlympiads(page = 1) {
    const uni = document.getElementById("filterUni")?.value || "";
    const subject = document.getElementById("filterSubject")?.value || "";
    const benefit = document.getElementById("filterBenefit")?.value || "";
    let url = `${API}/api/olympiads?page=${page}&size=20`;
    if (uni) url += `&university_id=${encodeURIComponent(uni)}`;
    if (subject) url += `&subject=${encodeURIComponent(subject)}`;
    if (benefit) url += `&benefit_type=${encodeURIComponent(benefit)}`;
    const data = await fetchJSON(url);
    renderOlympiads(data);
}

function renderOlympiads(data) {
    const tb = document.getElementById("olympiadsBody");
    if (!tb) return;
    tb.innerHTML = data.items.map(o => `<tr>
        <td>${o.university_id}</td><td>${o.olympiad_name}</td>
        <td>${o.olympiad_level || "-"}</td><td>${o.subject}</td>
        <td><span class="badge ${o.benefit_type.includes("БВИ") ? "badge-bvi" : o.benefit_type.includes("100") ? "badge-100" : "badge-extra"}">${o.benefit_type || "-"}</span></td>
        <td>${o.benefit_detail ? o.benefit_detail.slice(0,120)+"..." : "-"}</td></tr>`).join("");
    renderPagination(data, "olympiadsPagination", loadOlympiads);
}

function renderPagination(data, containerId, loadFn) {
    const c = document.getElementById(containerId);
    if (!c || data.pages <= 1) { if (c) c.innerHTML = ""; return; }
    let html = "";
    for (let i = 1; i <= data.pages; i++) {
        html += `<li class="page-item ${i === data.page ? "active" : ""}">
            <a class="page-link" onclick="${loadFn.name}(${i})">${i}</a></li>`;
    }
    c.innerHTML = html;
}

async function loadStats() {
    const d = await fetchJSON(`${API}/api/stats`);
    const el = document.getElementById("statsBar");
    if (el) el.innerHTML = `<span class="badge bg-primary me-2">${d.universities} vuzov</span>
        <span class="badge bg-success me-2">${d.programs} programs</span>
        <span class="badge bg-info">${d.olympiads} olympiads</span>`;
}
"""

FILES["web/templates/index.html"] = """
<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>Universities</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css" rel="stylesheet">
    <link href="/static/css/style.css" rel="stylesheet">
</head>
<body>
<nav class="navbar navbar-expand-lg navbar-dark bg-dark mb-4">
    <div class="container">
        <a class="navbar-brand" href="/">School Partners</a>
        <div class="navbar-nav">
            <a class="nav-link active" href="/">Universities</a>
            <a class="nav-link " href="/programs.html">Programs</a>
            <a class="nav-link " href="/olympiads.html">Olympiads</a>
            <a class="nav-link" href="/docs" target="_blank">API Docs</a>
        </div>
        <div id="statsBar" class="ms-auto"></div>
    </div>
</nav>
<div class="container">
    <div class="filter-panel"><div class="row g-2">
        <div class="col-md-4"><input id="filterCity" class="form-control" placeholder="City" oninput="loadUniversities()"></div>
        <div class="col-md-4"><input id="filterSearch" class="form-control" placeholder="Search" oninput="loadUniversities()"></div>
    </div></div>
    <div id="uniList" class="row"></div>
    <nav><ul id="uniPagination" class="pagination justify-content-center"></ul></nav>
</div>
<script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/js/bootstrap.bundle.min.js"></script>
<script src="/static/js/app.js"></script>
<script>loadUniversities(); loadStats();</script>
</body></html>
"""

FILES["web/templates/programs.html"] = """
<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>Programs</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css" rel="stylesheet">
    <link href="/static/css/style.css" rel="stylesheet">
</head>
<body>
<nav class="navbar navbar-expand-lg navbar-dark bg-dark mb-4">
    <div class="container">
        <a class="navbar-brand" href="/">School Partners</a>
        <div class="navbar-nav">
            <a class="nav-link " href="/">Universities</a>
            <a class="nav-link active" href="/programs.html">Programs</a>
            <a class="nav-link " href="/olympiads.html">Olympiads</a>
            <a class="nav-link" href="/docs" target="_blank">API Docs</a>
        </div>
        <div id="statsBar" class="ms-auto"></div>
    </div>
</nav>
<div class="container">
    <div class="filter-panel"><div class="row g-2">
        <div class="col-md-3"><input id="filterUni" class="form-control" placeholder="University ID" oninput="loadPrograms()"></div>
        <div class="col-md-3"><input id="filterOkso" class="form-control" placeholder="OKSO code" oninput="loadPrograms()"></div>
        <div class="col-md-3"><input id="filterSearch" class="form-control" placeholder="Program name" oninput="loadPrograms()"></div>
    </div></div>
    <div class="table-responsive"><table class="table table-striped table-hover">
        <thead class="table-dark"><tr><th>Uni</th><th>OKSO</th><th>Program</th><th>Level</th><th>Min score</th><th>Budget</th><th>Cost</th><th>EGE</th></tr></thead>
        <tbody id="programsBody"></tbody>
    </table></div>
    <nav><ul id="programsPagination" class="pagination justify-content-center"></ul></nav>
</div>
<script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/js/bootstrap.bundle.min.js"></script>
<script src="/static/js/app.js"></script>
<script>loadPrograms(); loadStats();</script>
</body></html>
"""

FILES["web/templates/olympiads.html"] = """
<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>Olympiads</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css" rel="stylesheet">
    <link href="/static/css/style.css" rel="stylesheet">
</head>
<body>
<nav class="navbar navbar-expand-lg navbar-dark bg-dark mb-4">
    <div class="container">
        <a class="navbar-brand" href="/">School Partners</a>
        <div class="navbar-nav">
            <a class="nav-link " href="/">Universities</a>
            <a class="nav-link " href="/programs.html">Programs</a>
            <a class="nav-link active" href="/olympiads.html">Olympiads</a>
            <a class="nav-link" href="/docs" target="_blank">API Docs</a>
        </div>
        <div id="statsBar" class="ms-auto"></div>
    </div>
</nav>
<div class="container">
    <div class="filter-panel"><div class="row g-2">
        <div class="col-md-3"><input id="filterUni" class="form-control" placeholder="University ID" oninput="loadOlympiads()"></div>
        <div class="col-md-3"><input id="filterSubject" class="form-control" placeholder="Subject" oninput="loadOlympiads()"></div>
        <div class="col-md-3"><select id="filterBenefit" class="form-select" onchange="loadOlympiads()">
            <option value="">All benefits</option><option value="BVI">BVI</option><option value="100">100 points</option>
        </select></div>
    </div></div>
    <div class="table-responsive"><table class="table table-striped table-hover">
        <thead class="table-dark"><tr><th>Uni</th><th>Olympiad</th><th>Level</th><th>Subject</th><th>Benefit</th><th>Details</th></tr></thead>
        <tbody id="olympiadsBody"></tbody>
    </table></div>
    <nav><ul id="olympiadsPagination" class="pagination justify-content-center"></ul></nav>
</div>
<script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/js/bootstrap.bundle.min.js"></script>
<script src="/static/js/app.js"></script>
<script>loadOlympiads(); loadStats();</script>
</body></html>
"""

FILES["tests/__init__.py"] = ""

FILES["tests/conftest.py"] = """
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from api.database import Base, get_db
from api.models import University, Program, Olympiad
from api.main import app

TEST_DB = "sqlite:///./test.db"
engine = create_engine(TEST_DB, connect_args={"check_same_thread": False})
TestSession = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def override_get_db():
    db = TestSession()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture(scope="session", autouse=True)
def setup_db():
    Base.metadata.create_all(bind=engine)
    db = TestSession()
    db.add(University(id="test_uni", name="Test University", city="Testville"))
    db.add(Program(university_id="test_uni", okso_code="09.03.01",
                   program_name="CS", program_level="bachelor", min_score="250",
                   ege_subjects="math, cs"))
    db.add(Olympiad(university_id="test_uni", olympiad_name="VSOSH",
                    olympiad_level="1", subject="cs", benefit_type="BVI",
                    benefit_detail="Enrollment without exams"))
    db.commit()
    db.close()
    app.dependency_overrides[get_db] = override_get_db
    yield
    Base.metadata.drop_all(bind=engine)
    import os
    if os.path.exists("test.db"):
        os.remove("test.db")


@pytest.fixture
def client():
    return TestClient(app)
"""

FILES["tests/test_api.py"] = """
class TestUniversities:
    def test_list(self, client):
        r = client.get("/api/universities")
        assert r.status_code == 200
        assert r.json()["total"] >= 1

    def test_filter_city(self, client):
        r = client.get("/api/universities?city=Testville")
        assert all("Testville" in u["city"] for u in r.json()["items"])

    def test_detail(self, client):
        r = client.get("/api/universities/test_uni")
        assert r.status_code == 200
        assert r.json()["id"] == "test_uni"
        assert len(r.json()["programs"]) >= 1

    def test_404(self, client):
        assert client.get("/api/universities/nope").status_code == 404


class TestPrograms:
    def test_list(self, client):
        assert client.get("/api/programs").json()["total"] >= 1

    def test_filter_okso(self, client):
        items = client.get("/api/programs?okso_code=09.03.01").json()["items"]
        assert all("09.03.01" in p["okso_code"] for p in items)

    def test_pagination(self, client):
        d = client.get("/api/programs?page=1&size=1").json()
        assert len(d["items"]) <= 1


class TestOlympiads:
    def test_list(self, client):
        assert client.get("/api/olympiads").status_code == 200

    def test_filter_benefit(self, client):
        items = client.get("/api/olympiads?benefit_type=BVI").json()["items"]
        assert all("BVI" in o["benefit_type"] for o in items)


class TestStats:
    def test_stats(self, client):
        d = client.get("/api/stats").json()
        assert "universities" in d and "programs" in d and "olympiads" in d
"""

FILES["run.py"] = """
import uvicorn

if __name__ == "__main__":
    uvicorn.run("api.main:app", host="127.0.0.1", port=8000, reload=True)
"""

FILES["requirements.txt"] = """fastapi>=0.110.0
uvicorn>=0.27.0
sqlalchemy>=2.0.0
pydantic>=2.5.0
jinja2>=3.1.0
python-multipart>=0.0.6
httpx>=0.27.0
pytest>=8.0.0
"""

FILES[".gitignore"] = """__pycache__/
*.pyc
*.db
.pytest_cache/
data/school.db
screenshots/
.env
venv/
"""

FILES["README.md"] = "# Project 4: API + Web Interface\n\n> Fill after implementation\n"


def create_structure(root):
    base = root / "project4-api"
    for d in DIRS:
        (base / d).mkdir(parents=True, exist_ok=True)
        print(f"  DIR  {d}")
    for relpath, content in FILES.items():
        fpath = base / relpath
        fpath.parent.mkdir(parents=True, exist_ok=True)
        with open(fpath, "w", encoding="utf-8") as fp:
            fp.write(content)
        print(f"  FILE {relpath}")
    (base / "screenshots" / ".gitkeep").touch()
    print(f"\nDone! {len(DIRS)} dirs, {len(FILES)} files created in {base}")
    print(f"\nNext steps:")
    print(f"  1. Copy partners.json -> project4-api/data/partners.json")
    print(f"  2. cd project4-api")
    print(f"  3. pip install -r requirements.txt")
    print(f"  4. python run.py")
    print(f"  5. Open http://127.0.0.1:8000       (Web UI)")
    print(f"  6. Open http://127.0.0.1:8000/docs   (Swagger)")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Create project4-api structure")
    parser.add_argument("--root", default=".", help="Monorepo root (default: cwd)")
    args = parser.parse_args()
    create_structure(Path(args.root))
