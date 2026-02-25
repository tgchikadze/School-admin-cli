"""
routers/olympiads.py - CRUD олимпиад + ревью. Доступ: все авторизованные.
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from ..dependencies import get_db, require_any, require_manager
from ..models import Olympiad, University, User
from ..schemas import OlympiadCreate, OlympiadOut

router = APIRouter(tags=["olympiads"])


@router.get("/api/olympiads", response_model=list[OlympiadOut])
def list_olympiads(
    university_id: int | None = None,
    subject: str | None = None,
    reviewed: bool | None = None,
    search: str | None = None,
    skip: int = 0,
    limit: int = Query(default=100, le=500),
    db: Session = Depends(get_db),
    user: User = Depends(require_any),
):
    q = db.query(Olympiad)
    if university_id:
        q = q.filter(Olympiad.university_id == university_id)
    if subject:
        q = q.filter(Olympiad.subject.ilike(f"%{subject}%"))
    if reviewed is not None:
        q = q.filter(Olympiad.reviewed == reviewed)
    if search:
        q = q.filter(Olympiad.olympiad_name.ilike(f"%{search}%"))
    return q.order_by(Olympiad.olympiad_name).offset(skip).limit(limit).all()


@router.get("/api/olympiads/{oly_id}", response_model=OlympiadOut)
def get_olympiad(oly_id: int, db: Session = Depends(get_db),
                 user: User = Depends(require_any)):
    oly = db.query(Olympiad).get(oly_id)
    if not oly:
        raise HTTPException(status_code=404, detail="Olympiad not found")
    return oly


@router.post("/api/olympiads", response_model=OlympiadOut, status_code=201)
def create_olympiad(data: OlympiadCreate, db: Session = Depends(get_db),
                    user: User = Depends(require_any)):
    if not db.query(University).get(data.university_id):
        raise HTTPException(status_code=404, detail="University not found")
    oly = Olympiad(**data.model_dump())
    db.add(oly)
    db.commit()
    db.refresh(oly)
    return oly


@router.put("/api/olympiads/{oly_id}", response_model=OlympiadOut)
def update_olympiad(oly_id: int, data: OlympiadCreate,
                    db: Session = Depends(get_db), user: User = Depends(require_any)):
    oly = db.query(Olympiad).get(oly_id)
    if not oly:
        raise HTTPException(status_code=404, detail="Olympiad not found")
    for key, value in data.model_dump().items():
        setattr(oly, key, value)
    db.commit()
    db.refresh(oly)
    return oly


@router.patch("/api/olympiads/{oly_id}/review")
def toggle_review(oly_id: int, db: Session = Depends(get_db),
                  user: User = Depends(require_manager)):
    """Переключить флаг reviewed (✅ / ❌)."""
    oly = db.query(Olympiad).get(oly_id)
    if not oly:
        raise HTTPException(status_code=404, detail="Olympiad not found")
    oly.reviewed = not oly.reviewed
    db.commit()
    db.refresh(oly)
    return {"id": oly.id, "reviewed": oly.reviewed}


@router.delete("/api/olympiads/{oly_id}")
def delete_olympiad(oly_id: int, db: Session = Depends(get_db),
                    user: User = Depends(require_any)):
    oly = db.query(Olympiad).get(oly_id)
    if not oly:
        raise HTTPException(status_code=404, detail="Olympiad not found")
    db.delete(oly)
    db.commit()
    return {"detail": "Olympiad deleted"}
