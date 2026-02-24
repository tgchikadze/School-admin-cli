
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
