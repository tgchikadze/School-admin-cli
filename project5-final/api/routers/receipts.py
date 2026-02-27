"""
routers/receipts.py — API генерации и скачивания PDF-квитанций.

Эндпоинты:
  POST /api/receipts/generate   — одиночная квитанция
  POST /api/receipts/batch      — пакетная генерация (многостраничный PDF)
  GET  /api/receipts            — список квитанций
  GET  /api/receipts/{id}/pdf   — скачивание PDF
"""

import os
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from ..dependencies import get_db, require_manager
from ..models import Student, SchoolClass, ExamChoice, Receipt, User
from ..schemas import ReceiptCreate, ReceiptOut, ReceiptBatch
from .receipt_utils import (
    generate_single_receipt,
    generate_batch_receipts,
    calc_receipt_amount,
    load_config,
    RECEIPTS_DIR,
)

router = APIRouter(tags=["receipts"])


# ── Вспомогательные функции ────────────────────────────────

def _get_student_receipt_data(student: Student, db: Session) -> dict:
    """
    Собирает все данные ученика для генерации квитанции:
    ФИО, предметы, договор, месяц/год, сумма, компенсация.
    """
    sc = db.query(SchoolClass).get(student.class_id)
    if not sc:
        raise HTTPException(status_code=404, detail="Класс ученика не найден")

    # Предметы
    if sc.pricing_type == "per_subject":
        exams = (
            db.query(ExamChoice)
            .filter(ExamChoice.student_id == student.id)
            .all()
        )
        courses = [e.subject_name for e in exams]
        exam_count = len(courses)
    else:
        courses = sc.subjects or []
        exam_count = 0

    # Сумма к оплате
    amount = calc_receipt_amount(
        pricing_type=sc.pricing_type,
        base_price=sc.base_price,
        price_per_subject=sc.price_per_subject,
        exam_count=exam_count,
        compensation=student.compensation or 0.0,
    )

    now = datetime.now()
    month_year = f"{now.month:02d}/{now.year}"

    return {
        "student_name": student.full_name,
        "courses": courses,
        "contract_number": student.contract_number or "—",
        "month_year": month_year,
        "amount": amount,
        "compensation": student.compensation or 0.0,
    }


# ── POST /api/receipts/generate ────────────────────────────

@router.post("/api/receipts/generate", response_model=ReceiptOut, status_code=201)
def generate_receipt(
    data: ReceiptCreate,
    db: Session = Depends(get_db),
    user: User = Depends(require_manager),
):
    """Генерация одной PDF-квитанции для ученика."""
    student = db.query(Student).get(data.student_id)
    if not student:
        raise HTTPException(status_code=404, detail="Ученик не найден")

    receipt_data = _get_student_receipt_data(student, db)

    # Имя файла: receipt_{student_id}_{timestamp}.pdf
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"receipt_{student.id}_{ts}.pdf"
    output_path = os.path.join(RECEIPTS_DIR, filename)

    try:
        config = load_config()
        generate_single_receipt(
            student_name=receipt_data["student_name"],
            courses=receipt_data["courses"],
            contract_number=receipt_data["contract_number"],
            month_year=receipt_data["month_year"],
            amount=receipt_data["amount"],
            compensation=receipt_data["compensation"],
            output_path=output_path,
            config=config,
        )
    except FileNotFoundError as e:
        raise HTTPException(status_code=500, detail=str(e))

    # Сохраняем запись в БД
    receipt = Receipt(
        student_id=student.id,
        created_by=user.id,
        amount=receipt_data["amount"],
        pdf_path=filename,
    )
    db.add(receipt)
    db.commit()
    db.refresh(receipt)

    return receipt


# ── POST /api/receipts/batch ───────────────────────────────

@router.post("/api/receipts/batch")
def generate_batch(
    data: ReceiptBatch,
    db: Session = Depends(get_db),
    user: User = Depends(require_manager),
):
    """Пакетная генерация: склейка квитанций нескольких учеников в один PDF."""
    if not data.student_ids:
        raise HTTPException(status_code=400, detail="Список учеников пуст")

    all_data = []
    receipt_records = []

    for sid in data.student_ids:
        student = db.query(Student).get(sid)
        if not student:
            raise HTTPException(status_code=404, detail=f"Ученик id={sid} не найден")

        rd = _get_student_receipt_data(student, db)
        all_data.append(rd)

        receipt_records.append(Receipt(
            student_id=student.id,
            created_by=user.id,
            amount=rd["amount"],
        ))

    # Генерируем общий PDF
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"batch_{len(data.student_ids)}_{ts}.pdf"
    output_path = os.path.join(RECEIPTS_DIR, filename)

    try:
        config = load_config()
        generate_batch_receipts(all_data, output_path, config)
    except FileNotFoundError as e:
        raise HTTPException(status_code=500, detail=str(e))

    # Сохраняем все записи, batch PDF path — в каждой записи
    for rec in receipt_records:
        rec.pdf_path = filename
        db.add(rec)
    db.commit()

    # Возвращаем ID первой записи + путь для скачивания
    db.refresh(receipt_records[0])
    return {
        "id": receipt_records[0].id,
        "count": len(receipt_records),
        "pdf_path": f"/api/receipts/{receipt_records[0].id}/pdf",
        "filename": filename,
    }


# ── GET /api/receipts ──────────────────────────────────────

@router.get("/api/receipts", response_model=list[ReceiptOut])
def list_receipts(
    student_id: int | None = None,
    db: Session = Depends(get_db),
    user: User = Depends(require_manager),
):
    """Список квитанций (с опциональной фильтрацией по ученику)."""
    q = db.query(Receipt).order_by(Receipt.created_at.desc())
    if student_id:
        q = q.filter(Receipt.student_id == student_id)
    return q.all()


# ── GET /api/receipts/{id}/pdf ─────────────────────────────

@router.get("/api/receipts/{receipt_id}/pdf")
def download_receipt(
    receipt_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(require_manager),
):
    """Скачивание PDF-файла квитанции."""
    receipt = db.query(Receipt).get(receipt_id)
    if not receipt:
        raise HTTPException(status_code=404, detail="Квитанция не найдена")
    if not receipt.pdf_path:
        raise HTTPException(status_code=404, detail="PDF-файл не привязан")

    file_path = os.path.join(RECEIPTS_DIR, receipt.pdf_path)
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="PDF-файл не найден на диске")

    return FileResponse(
        file_path,
        media_type="application/pdf",
        filename=receipt.pdf_path,
    )
