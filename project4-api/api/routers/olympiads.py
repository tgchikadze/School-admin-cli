from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from api.database import get_db
from api.models import Olympiad
from api.schemas import OlympiadOut, OlympiadUpdate, OlympiadCreate

router = APIRouter()


@router.get("/olympiads")
def list_olympiads(
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    reviewed: bool | None = None,
    db: Session = Depends(get_db),
):
    q = db.query(Olympiad)
    if reviewed is not None:
        q = q.filter(Olympiad.reviewed == reviewed)
    total = q.count()
    items = q.offset((page - 1) * size).limit(size).all()
    return {
        "total": total,
        "page": page,
        "size": size,
        "items": [OlympiadOut.model_validate(o).model_dump() for o in items],
    }


@router.patch("/olympiads/{oid}")
def update_olympiad(oid: int, body: OlympiadUpdate, db: Session = Depends(get_db)):
    o = db.query(Olympiad).get(oid)
    if not o:
        raise HTTPException(404, "Olympiad not found")
    for field, val in body.model_dump(exclude_unset=True).items():
        setattr(o, field, val)
    db.commit()
    db.refresh(o)
    return OlympiadOut.model_validate(o).model_dump()


@router.delete("/olympiads/{oid}")
def delete_olympiad(oid: int, db: Session = Depends(get_db)):
    o = db.query(Olympiad).get(oid)
    if not o:
        raise HTTPException(404, "Olympiad not found")
    db.delete(o)
    db.commit()
    return {"status": "deleted", "id": oid}

@router.post("/olympiads")
def create_olympiad(body: OlympiadCreate, db: Session = Depends(get_db)):
    o = Olympiad(
        university_id=body.university_id,
        olympiad_name=body.olympiad_name,
        olympiad_level=body.olympiad_level,
        subject=body.subject,
        benefit_type=body.benefit_type,
        benefit_detail=body.benefit_detail,
        source_url=body.source_url,
        notes=body.notes,
        reviewed=False,
    )
    db.add(o)
    db.commit()
    db.refresh(o)
    return OlympiadOut.model_validate(o).model_dump()
