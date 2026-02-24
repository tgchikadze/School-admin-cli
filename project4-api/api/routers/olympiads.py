
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
