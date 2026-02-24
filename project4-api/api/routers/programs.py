
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
