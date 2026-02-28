"""
routers/olympiads.py - CRUD олимпиад + ревью. Доступ: все авторизованные.
"""

import csv
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from ..dependencies import get_db, require_any, require_manager
from ..models import Olympiad, University, User
from ..schemas import OlympiadCreate, OlympiadOut
from fastapi import Body

router = APIRouter(tags=["olympiads"])

@router.get("/api/olympiads")
def list_olympiads(
    university_id: int | None = None,
    subject: str | None = None,
    reviewed: bool | None = None,
    search: str | None = None,
    page: int = Query(default=1, ge=1),
    size: int = Query(default=100, le=500),
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

    total = q.count()
    items = q.order_by(Olympiad.olympiad_name).offset((page - 1) * size).limit(size).all()

    return {
        "total": total,
        "page": page,
        "size": size,
        "items": [OlympiadOut.model_validate(i) for i in items],
    }

@router.patch("/api/olympiads/{oly_id}")
def patch_olympiad(oly_id: int, body: dict = Body(...), db: Session = Depends(get_db), user: User = Depends(require_any)):
    oly = db.query(Olympiad).get(oly_id)
    if not oly:
        raise HTTPException(status_code=404, detail="Olympiad not found")
    allowed = {"subject", "olympiad_level", "benefit_type", "benefit_detail", "source_url", "reviewed"}
    for k, v in body.items():
        if k in allowed:
            setattr(oly, k, v)
    db.commit()
    db.refresh(oly)
    return OlympiadOut.model_validate(oly)


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

@router.post("/api/admin/import_olympiads_raw")
def import_olympiads_raw(db: Session = Depends(get_db), user: User = Depends(require_manager)):
    csv_path = Path(__file__).resolve().parent.parent.parent / "data" / "olympiads_raw.csv"
    if not csv_path.exists():
        raise HTTPException(status_code=404, detail=f"File not found: {csv_path}")

    created = 0
    skipped_dup = 0
    skipped_no_name = 0
    skipped_no_uni = 0

    with open(csv_path, encoding="utf-8") as f:
        reader = csv.DictReader(f)
        # Маппинг slug из CSV → название в БД
        SLUG_MAP = {
            "itmo": "ИТМО",
            "spbgu": "СПбГУ",
            "spbpu": "СПбПУ",
            "hse_msk": "ВШЭ (Москва)",
            "hse_spb": "ВШЭ (СПб)",
            "herzen": "Герцена",
            "au_ran": "АУ РАН",
            "pavlov": "Павлова",
            "mechnikov": "Мечникова",
            "spbgpmu": "СПбГПМУ",
            "rosbiotech": "РОСБИОТЕХ",
            "nsu": "НГУ",
            "spbguvm": "СПбГУВМ",
        }
        for row in reader:
            name = (row.get("olympiad_name") or "").strip()
            if not name:
                skipped_no_name += 1
                continue



            uni_slug = (row.get("university_id") or "").strip()
            if not uni_slug:
                skipped_no_uni += 1
                continue

            search_name = SLUG_MAP.get(uni_slug, uni_slug)
            uni = db.query(University).filter(
                University.name.ilike(f"%{search_name}%")
            ).first()
            if not uni:
                skipped_no_uni += 1
                continue
            uni_id = uni.id

            # Проверка дубля
            exists = db.query(Olympiad).filter(
                Olympiad.olympiad_name == name,
                Olympiad.university_id == uni_id
            ).first()
            if exists:
                skipped_dup += 1
                continue

            oly = Olympiad(
                olympiad_name=name,
                university_id=uni_id,
                olympiad_level=row.get("olympiad_level"),
                subject=row.get("subject"),
                benefit_type=row.get("benefit_type"),
                benefit_detail=row.get("benefit_detail"),
                source_url=row.get("source_url"),
                reviewed=False,
            )
            db.add(oly)
            created += 1

    db.commit()
    return {
        "created": created,
        "skipped_dup": skipped_dup,
        "skipped_no_name": skipped_no_name,
        "skipped_no_uni": skipped_no_uni,
    }
