"""
routers/universities.py - CRUD вузов. Доступ: все авторизованные.
"""

import os

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from ..dependencies import get_db, require_any
from ..models import University, User
from ..schemas import UniversityCreate, UniversityOut

router = APIRouter(tags=["universities"])

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
templates = Jinja2Templates(directory=os.path.join(BASE_DIR, "web", "templates"))


@router.get("/api/universities", response_model=list[UniversityOut])
def list_universities(
    search: str | None = None,
    db: Session = Depends(get_db),
    user: User = Depends(require_any),
):
    q = db.query(University)
    if search:
        q = q.filter(University.name.ilike(f"%{search}%"))
    return q.order_by(University.name).all()


@router.get("/api/universities/{uni_id}", response_model=UniversityOut)
def get_university(uni_id: int, db: Session = Depends(get_db),
                   user: User = Depends(require_any)):
    uni = db.query(University).get(uni_id)
    if not uni:
        raise HTTPException(status_code=404, detail="University not found")
    return uni


@router.post("/api/universities", response_model=UniversityOut, status_code=201)
def create_university(data: UniversityCreate, db: Session = Depends(get_db),
                      user: User = Depends(require_any)):
    existing = db.query(University).filter(University.name == data.name).first()
    if existing:
        raise HTTPException(status_code=409, detail="University already exists")
    uni = University(name=data.name, city=data.city)
    db.add(uni)
    db.commit()
    db.refresh(uni)
    return uni


@router.put("/api/universities/{uni_id}", response_model=UniversityOut)
def update_university(uni_id: int, data: UniversityCreate,
                      db: Session = Depends(get_db), user: User = Depends(require_any)):
    uni = db.query(University).get(uni_id)
    if not uni:
        raise HTTPException(status_code=404, detail="University not found")
    uni.name = data.name
    uni.city = data.city
    db.commit()
    db.refresh(uni)
    return uni


@router.delete("/api/universities/{uni_id}")
def delete_university(uni_id: int, db: Session = Depends(get_db),
                      user: User = Depends(require_any)):
    uni = db.query(University).get(uni_id)
    if not uni:
        raise HTTPException(status_code=404, detail="University not found")
    db.delete(uni)
    db.commit()
    return {"detail": "University deleted"}
