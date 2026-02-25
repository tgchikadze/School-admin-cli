"""
routers/admin.py - Техадмин: управление пользователями, пересборка БД, статистика.
Доступ: admin only (require_admin).
"""

import os
import json

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from ..dependencies import get_db, require_admin
from ..auth import hash_password
from ..models import (
    Base, User, Student, SchoolClass, ExamChoice, Receipt,
    University, Program, Olympiad,
)
from ..schemas import UserCreate, UserOut, UserUpdate

router = APIRouter(tags=["admin"])

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
templates = Jinja2Templates(directory=os.path.join(BASE_DIR, "web", "templates"))
DATA_DIR = os.path.join(BASE_DIR, "data")


# ═══════════════════════════════════════════════════════════════
#  HTML-страница
# ═══════════════════════════════════════════════════════════════

@router.get("/admin", response_class=HTMLResponse)
def admin_page(request: Request, user: User = Depends(require_admin)):
    return templates.TemplateResponse("admin.html", {
        "request": request, "role": user.role, "username": user.username,
    })


# ═══════════════════════════════════════════════════════════════
#  Статистика БД
# ═══════════════════════════════════════════════════════════════

@router.get("/api/admin/stats")
def db_stats(db: Session = Depends(get_db), user: User = Depends(require_admin)):
    """Количество записей по каждой таблице."""
    return {
        "users": db.query(User).count(),
        "school_classes": db.query(SchoolClass).count(),
        "students": db.query(Student).count(),
        "exam_choices": db.query(ExamChoice).count(),
        "receipts": db.query(Receipt).count(),
        "universities": db.query(University).count(),
        "programs": db.query(Program).count(),
        "olympiads": db.query(Olympiad).count(),
    }


# ═══════════════════════════════════════════════════════════════
#  Управление пользователями
# ═══════════════════════════════════════════════════════════════

@router.get("/api/admin/users", response_model=list[UserOut])
def list_users(db: Session = Depends(get_db), user: User = Depends(require_admin)):
    return db.query(User).order_by(User.id).all()


@router.post("/api/admin/users", response_model=UserOut, status_code=201)
def create_user(
    data: UserCreate,
    db: Session = Depends(get_db),
    user: User = Depends(require_admin),
):
    existing = db.query(User).filter(User.username == data.username).first()
    if existing:
        raise HTTPException(status_code=409, detail="Username already exists")

    new_user = User(
        username=data.username,
        hashed_password=hash_password(data.password),
        role=data.role if data.role in ("admin", "manager", "viewer") else "manager",
        full_name=data.full_name or data.username,
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user


@router.put("/api/admin/users/{user_id}", response_model=UserOut)
def update_user(
    user_id: int,
    data: UserUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(require_admin),
):
    target = db.query(User).get(user_id)
    if not target:
        raise HTTPException(status_code=404, detail="User not found")

    if data.full_name is not None:
        target.full_name = data.full_name
    if data.role is not None and data.role in ("admin", "manager", "viewer"):
        target.role = data.role
    if data.is_active is not None:
        target.is_active = data.is_active

    db.commit()
    db.refresh(target)
    return target


@router.delete("/api/admin/users/{user_id}")
def delete_user(
    user_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(require_admin),
):
    if user_id == user.id:
        raise HTTPException(status_code=400, detail="Cannot delete yourself")

    target = db.query(User).get(user_id)
    if not target:
        raise HTTPException(status_code=404, detail="User not found")

    db.delete(target)
    db.commit()
    return {"detail": "User deleted"}


# ═══════════════════════════════════════════════════════════════
#  Пересборка БД вузов из partners.json (P3 → P4)
# ═══════════════════════════════════════════════════════════════

@router.post("/api/admin/rebuild")
def rebuild_universities(
    db: Session = Depends(get_db),
    user: User = Depends(require_admin),
):
    """Пересобрать таблицы universities/programs/olympiads из partners.json."""
    json_path = os.path.join(DATA_DIR, "partners.json")
    if not os.path.exists(json_path):
        raise HTTPException(status_code=404,
                            detail="partners.json not found in data/")

    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    # Очистить старые данные
    db.query(Olympiad).delete()
    db.query(Program).delete()
    db.query(University).delete()
    db.flush()

    added = {"universities": 0, "programs": 0, "olympiads": 0}

    for entry in data:
        uni_name = entry.get("university_name", "").strip()
        if not uni_name:
            continue

        uni = University(
            name=uni_name,
            city=entry.get("city", "Санкт-Петербург"),
        )
        db.add(uni)
        db.flush()
        added["universities"] += 1

        for prog in entry.get("programs", []):
            p = Program(
                university_id=uni.id,
                okso_code=prog.get("okso_code"),
                program_name=prog.get("program_name", ""),
                program_level=prog.get("program_level"),
                min_score=prog.get("min_score"),
                budget_places=prog.get("budget_places"),
                cost=prog.get("cost"),
                ege_subjects=prog.get("ege_subjects"),
            )
            db.add(p)
            added["programs"] += 1

        for oly in entry.get("olympiads", []):
            o = Olympiad(
                university_id=uni.id,
                olympiad_name=oly.get("olympiad_name", ""),
                olympiad_level=oly.get("olympiad_level"),
                subject=oly.get("subject"),
                benefit_type=oly.get("benefit_type"),
                benefit_detail=oly.get("benefit_detail"),
                source_url=oly.get("source_url"),
                reviewed=False,
            )
            db.add(o)
            added["olympiads"] += 1

    db.commit()
    return {"detail": "Rebuild complete", "added": added}


# ═══════════════════════════════════════════════════════════════
#  Очистка данных
# ═══════════════════════════════════════════════════════════════

@router.post("/api/admin/clear/{table}")
def clear_table(
    table: str,
    db: Session = Depends(get_db),
    user: User = Depends(require_admin),
):
    """Очистить указанную таблицу."""
    table_map = {
        "universities": University,
        "programs": Program,
        "olympiads": Olympiad,
        "students": Student,
        "school_classes": SchoolClass,
        "exam_choices": ExamChoice,
        "receipts": Receipt,
    }
    model = table_map.get(table)
    if not model:
        raise HTTPException(status_code=400,
                            detail=f"Unknown table: {table}. "
                                   f"Options: {list(table_map.keys())}")

    # Соблюдаем порядок зависимостей
    if table == "students":
        db.query(Receipt).delete()
        db.query(ExamChoice).delete()
    if table == "school_classes":
        db.query(Receipt).delete()
        db.query(ExamChoice).delete()
        db.query(Student).delete()
    if table == "universities":
        db.query(Olympiad).delete()
        db.query(Program).delete()

    count = db.query(model).delete()
    db.commit()
    return {"detail": f"Cleared {count} rows from {table}"}
