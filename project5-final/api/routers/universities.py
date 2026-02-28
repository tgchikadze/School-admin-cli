"""
routers/universities.py — CRUD вузов + программ + олимпиад + импорт partners.json.

Все данные из Project 3 (scraping) и Project 4 (API).
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func

from ..dependencies import get_db, require_manager, get_current_user
from ..models import University, Program, Olympiad, User
from ..schemas import (
    UniversityCreate, UniversityOut,
    ProgramCreate, ProgramOut,
    OlympiadCreate, OlympiadOut,
)

router = APIRouter(tags=["universities"])


# ═══════════════════════════════════════════════════════════════
#  ИМПОРТ из partners.json
# ═══════════════════════════════════════════════════════════════

@router.post("/api/universities/import")
def import_partners(
    db: Session = Depends(get_db),
    user: User = Depends(require_manager),
):
    """Импорт вузов/программ/олимпиад из data/partners.json."""
    from ..database import import_partners_json
    try:
        stats = import_partners_json(db)
        return {"detail": "Импорт завершён", **stats}
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ═══════════════════════════════════════════════════════════════
#  СТАТИСТИКА (для дашборда)
# ═══════════════════════════════════════════════════════════════

@router.get("/api/universities/stats")
def university_stats(db: Session = Depends(get_db),
                     user: User = Depends(get_current_user)):
    return {
        "universities": db.query(func.count(University.id)).scalar(),
        "programs": db.query(func.count(Program.id)).scalar(),
        "olympiads": db.query(func.count(Olympiad.id)).scalar(),
        "olympiads_reviewed": db.query(func.count(Olympiad.id)).filter(
            Olympiad.reviewed == True
        ).scalar(),
    }

# ═══════════════════════════════════════════════════════════════
#  UNIVERSITIES
# ═══════════════════════════════════════════════════════════════

@router.get("/api/universities", response_model=list[UniversityOut])
def list_universities(
    search: str | None = None,
    city: str | None = None,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Список вузов с фильтрацией."""
    q = db.query(University)
    if search:
        q = q.filter(University.name.ilike(f"%{search}%"))
    if city:
        q = q.filter(University.city.ilike(f"%{city}%"))
    return q.order_by(University.name).all()


@router.get("/api/universities/{uni_id}", response_model=UniversityOut)
def get_university(uni_id: int, db: Session = Depends(get_db),
                   user: User = Depends(get_current_user)):
    uni = db.query(University).get(uni_id)
    if not uni:
        raise HTTPException(status_code=404, detail="Вуз не найден")
    return uni


@router.post("/api/universities", response_model=UniversityOut, status_code=201)
def create_university(data: UniversityCreate, db: Session = Depends(get_db),
                      user: User = Depends(require_manager)):
    existing = db.query(University).filter(University.name == data.name).first()
    if existing:
        raise HTTPException(status_code=409, detail="Вуз уже существует")
    uni = University(name=data.name, city=data.city)
    db.add(uni)
    db.commit()
    db.refresh(uni)
    return uni


@router.delete("/api/universities/{uni_id}")
def delete_university(uni_id: int, db: Session = Depends(get_db),
                      user: User = Depends(require_manager)):
    uni = db.query(University).get(uni_id)
    if not uni:
        raise HTTPException(status_code=404, detail="Вуз не найден")
    db.delete(uni)
    db.commit()
    return {"detail": "Вуз удалён"}


# ═══════════════════════════════════════════════════════════════
#  PROGRAMS (по вузу или общий список)
# ═══════════════════════════════════════════════════════════════

@router.get("/api/programs", response_model=list[ProgramOut])
def list_programs(
    university_id: int | None = None,
    search: str | None = None,
    level: str | None = None,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Список программ с фильтрацией по вузу, названию, уровню."""
    q = db.query(Program)
    if university_id:
        q = q.filter(Program.university_id == university_id)
    if search:
        q = q.filter(Program.program_name.ilike(f"%{search}%"))
    if level:
        q = q.filter(Program.program_level.ilike(f"%{level}%"))
    return q.order_by(Program.program_name).limit(200).all()


@router.get("/api/programs/{prog_id}", response_model=ProgramOut)
def get_program(prog_id: int, db: Session = Depends(get_db),
                user: User = Depends(get_current_user)):
    prog = db.query(Program).get(prog_id)
    if not prog:
        raise HTTPException(status_code=404, detail="Программа не найдена")
    return prog


@router.post("/api/programs", response_model=ProgramOut, status_code=201)
def create_program(data: ProgramCreate, db: Session = Depends(get_db),
                   user: User = Depends(require_manager)):
    if not db.query(University).get(data.university_id):
        raise HTTPException(status_code=404, detail="Вуз не найден")
    prog = Program(**data.model_dump())
    db.add(prog)
    db.commit()
    db.refresh(prog)
    return prog


@router.delete("/api/programs/{prog_id}")
def delete_program(prog_id: int, db: Session = Depends(get_db),
                   user: User = Depends(require_manager)):
    prog = db.query(Program).get(prog_id)
    if not prog:
        raise HTTPException(status_code=404, detail="Программа не найдена")
    db.delete(prog)
    db.commit()
    return {"detail": "Программа удалена"}


# ═══════════════════════════════════════════════════════════════
#  OLYMPIADS
# ═══════════════════════════════════════════════════════════════
'''
@router.get("/api/olympiads", response_model=list[OlympiadOut])
def list_olympiads(
    university_id: int | None = None,
    search: str | None = None,
    subject: str | None = None,
    reviewed: bool | None = None,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Список олимпиад с фильтрацией."""
    q = db.query(Olympiad)
    if university_id:
        q = q.filter(Olympiad.university_id == university_id)
    if search:
        q = q.filter(Olympiad.olympiad_name.ilike(f"%{search}%"))
    if subject:
        q = q.filter(Olympiad.subject.ilike(f"%{subject}%"))
    if reviewed is not None:
        q = q.filter(Olympiad.reviewed == reviewed)
    return q.order_by(Olympiad.olympiad_name).limit(200).all()
'''

@router.get("/api/olympiads/{oly_id}", response_model=OlympiadOut)
def get_olympiad(oly_id: int, db: Session = Depends(get_db),
                 user: User = Depends(get_current_user)):
    oly = db.query(Olympiad).get(oly_id)
    if not oly:
        raise HTTPException(status_code=404, detail="Олимпиада не найдена")
    return oly


@router.post("/api/olympiads", response_model=OlympiadOut, status_code=201)
def create_olympiad(data: OlympiadCreate, db: Session = Depends(get_db),
                    user: User = Depends(require_manager)):
    if not db.query(University).get(data.university_id):
        raise HTTPException(status_code=404, detail="Вуз не найден")
    oly = Olympiad(**data.model_dump())
    db.add(oly)
    db.commit()
    db.refresh(oly)
    return oly


@router.put("/api/olympiads/{oly_id}/review")
def toggle_review(oly_id: int, db: Session = Depends(get_db),
                  user: User = Depends(require_manager)):
    """Переключить статус рецензирования олимпиады."""
    oly = db.query(Olympiad).get(oly_id)
    if not oly:
        raise HTTPException(status_code=404, detail="Олимпиада не найдена")
    oly.reviewed = not oly.reviewed
    db.commit()
    db.refresh(oly)
    return {"id": oly.id, "reviewed": oly.reviewed}


@router.delete("/api/olympiads/{oly_id}")
def delete_olympiad(oly_id: int, db: Session = Depends(get_db),
                    user: User = Depends(require_manager)):
    oly = db.query(Olympiad).get(oly_id)
    if not oly:
        raise HTTPException(status_code=404, detail="Олимпиада не найдена")
    db.delete(oly)
    db.commit()
    return {"detail": "Олимпиада удалена"}


