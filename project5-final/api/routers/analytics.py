"""
routers/analytics.py - Аналитический дашборд (доступ: admin + viewer/director).
"""

import os

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import func
from sqlalchemy.orm import Session

from ..dependencies import get_db, require_role
from ..models import (
    User, Student, SchoolClass, ExamChoice, Receipt,
    University, Program, Olympiad,
)

router = APIRouter(tags=["analytics"])

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
templates = Jinja2Templates(directory=os.path.join(BASE_DIR, "web", "templates"))

# Доступ: admin + viewer (директор)
require_analytics = require_role("admin", "viewer")


@router.get("/analytics", response_class=HTMLResponse)
def analytics_page(request: Request, user: User = Depends(require_analytics)):
    return templates.TemplateResponse("analytics.html", {
        "request": request, "role": user.role, "username": user.username,
    })


@router.get("/api/analytics/summary")
def analytics_summary(
    db: Session = Depends(get_db),
    user: User = Depends(require_analytics),
):
    """Сводная аналитика для дашборда."""

    # ─── Общие счётчики ──────────────────────────────────────
    total_students = db.query(Student).count()
    total_classes = db.query(SchoolClass).count()
    total_receipts = db.query(Receipt).count()
    total_universities = db.query(University).count()
    total_programs = db.query(Program).count()
    total_olympiads = db.query(Olympiad).count()

    # ─── Ученики по классам ──────────────────────────────────
    students_by_class = (
        db.query(SchoolClass.name, func.count(Student.id))
        .outerjoin(Student, Student.class_id == SchoolClass.id)
        .group_by(SchoolClass.name)
        .order_by(SchoolClass.name)
        .all()
    )

    # ─── Финансы ─────────────────────────────────────────────
    total_monthly_revenue = (
        db.query(func.sum(Student.monthly_payment)).scalar() or 0
    )
    total_compensation = (
        db.query(func.sum(Student.compensation)).scalar() or 0
    )
    total_receipts_amount = (
        db.query(func.sum(Receipt.amount)).scalar() or 0
    )

    # Доход по классам
    revenue_by_class = (
        db.query(SchoolClass.name, func.sum(Student.monthly_payment))
        .outerjoin(Student, Student.class_id == SchoolClass.id)
        .group_by(SchoolClass.name)
        .order_by(SchoolClass.name)
        .all()
    )

    # ─── ЕГЭ: популярность предметов (11 класс) ─────────────
    popular_exams = (
        db.query(ExamChoice.subject_name, func.count(ExamChoice.id))
        .group_by(ExamChoice.subject_name)
        .order_by(func.count(ExamChoice.id).desc())
        .all()
    )

    # ─── Вузы: топ по кол-ву программ ────────────────────────
    top_universities = (
        db.query(University.name, func.count(Program.id))
        .outerjoin(Program, Program.university_id == University.id)
        .group_by(University.name)
        .order_by(func.count(Program.id).desc())
        .limit(10)
        .all()
    )

    # ─── Олимпиады: проверенные vs непроверенные ─────────────
    reviewed_count = db.query(Olympiad).filter(Olympiad.reviewed == True).count()
    unreviewed_count = db.query(Olympiad).filter(Olympiad.reviewed == False).count()

    return {
        "counters": {
            "students": total_students,
            "classes": total_classes,
            "receipts": total_receipts,
            "universities": total_universities,
            "programs": total_programs,
            "olympiads": total_olympiads,
        },
        "students_by_class": [
            {"class_name": name, "count": count}
            for name, count in students_by_class
        ],
        "finance": {
            "monthly_revenue": round(total_monthly_revenue, 2),
            "total_compensation": round(total_compensation, 2),
            "receipts_total": round(total_receipts_amount, 2),
        },
        "revenue_by_class": [
            {"class_name": name, "revenue": round(rev or 0, 2)}
            for name, rev in revenue_by_class
        ],
        "popular_exams": [
            {"subject": name, "count": count}
            for name, count in popular_exams
        ],
        "top_universities": [
            {"name": name, "programs_count": count}
            for name, count in top_universities
        ],
        "olympiads_review": {
            "reviewed": reviewed_count,
            "unreviewed": unreviewed_count,
        },
    }
