"""
routers/receipts.py — Генерация PDF-квитанций через координатную систему (из P1/P2).
"""
import os
from datetime import datetime
from pathlib import Path
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import FileResponse, HTMLResponse
from sqlalchemy.orm import Session
from ..database import SessionLocal
from ..dependencies import get_current_user, require_manager
from ..models import User, Student, Receipt, SchoolClass, ExamChoice
from ..schemas import ReceiptOut, ReceiptCreate, ReceiptBatch
from .receipt_utils import generate_receipt_pdf

router = APIRouter(tags=["receipts"])

# Директория для PDF
BASE_DIR = Path(__file__).parent.parent.parent
RECEIPTS_DIR = BASE_DIR / "data" / "receipts"
RECEIPTS_DIR.mkdir(parents=True, exist_ok=True)

TEMPLATES_DIR = BASE_DIR / "data" / "templates"
TEMPLATES_DIR.mkdir(parents=True, exist_ok=True)


@router.get("/receipts", response_class=HTMLResponse)
async def receipts_page(current_user: User = Depends(require_manager)):
    """HTML-страница генерации квитанций."""
    html_path = BASE_DIR / "web" / "templates" / "receipts.html"
    with open(html_path, "r", encoding="utf-8") as f:
        return f.read()


@router.get("/api/receipts", response_model=list[ReceiptOut])
async def list_receipts(
    student_id: int | None = None,
    db: Session = Depends(SessionLocal),
    current_user: User = Depends(require_manager),
):
    """Список квитанций (фильтр по ученику опционально)."""
    query = db.query(Receipt)
    if student_id:
        query = query.filter(Receipt.student_id == student_id)
    receipts = query.order_by(Receipt.created_at.desc()).all()
    return receipts


@router.post("/api/receipts/generate", response_model=ReceiptOut)
async def generate_receipt(
    data: ReceiptCreate,
    db: Session = Depends(SessionLocal),
    current_user: User = Depends(require_manager),
):
    """
    Генерация одной квитанции через координатную систему.

    Использует:
    - data/templates/receipt_template.pdf (бланк)
    - data/templates/receipt_coordinates.json (координаты полей)
    """
    student = db.query(Student).filter(Student.id == data.student_id).first()
    if not student:
        raise HTTPException(status_code=404, detail="Ученик не найден")

    school_class = db.query(SchoolClass).filter(SchoolClass.id == student.class_id).first()
    exam_choices = db.query(ExamChoice).filter(ExamChoice.student_id == student.id).all()

    # Генерация PDF через координатную систему
    receipt_filename = f"receipt_{student.id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
    receipt_path = RECEIPTS_DIR / receipt_filename

    try:
        generate_receipt_pdf(
            student=student,
            school_class=school_class,
            exam_choices=exam_choices,
            output_path=str(receipt_path),
            templates_dir=TEMPLATES_DIR,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка генерации PDF: {str(e)}")

    # Сохранение записи в БД
    receipt = Receipt(
        student_id=student.id,
        created_by=current_user.id,
        amount=student.monthly_payment - student.compensation,
        pdf_path=str(receipt_path),
    )
    db.add(receipt)
    db.commit()
    db.refresh(receipt)

    return receipt


@router.get("/api/receipts/{receipt_id}/pdf")
async def download_receipt(
    receipt_id: int,
    db: Session = Depends(SessionLocal),
    current_user: User = Depends(require_manager),
):
    """Скачивание PDF-квитанции."""
    receipt = db.query(Receipt).filter(Receipt.id == receipt_id).first()
    if not receipt:
        raise HTTPException(status_code=404, detail="Квитанция не найдена")

    pdf_path = Path(receipt.pdf_path)
    if not pdf_path.exists():
        raise HTTPException(status_code=404, detail="PDF-файл не найден")

    return FileResponse(
        path=pdf_path,
        media_type="application/pdf",
        filename=f"receipt_{receipt.id}.pdf",
    )


@router.post("/api/receipts/batch")
async def generate_batch(
    data: ReceiptBatch,
    db: Session = Depends(SessionLocal),
    current_user: User = Depends(require_manager),
):
    """Пакетная генерация квитанций (объединённый PDF)."""
    from pypdf import PdfWriter

    if not data.student_ids:
        raise HTTPException(status_code=400, detail="Не выбраны ученики")

    students = db.query(Student).filter(Student.id.in_(data.student_ids)).all()
    if not students:
        raise HTTPException(status_code=404, detail="Ученики не найдены")

    writer = PdfWriter()

    for student in students:
        school_class = db.query(SchoolClass).filter(SchoolClass.id == student.class_id).first()
        exam_choices = db.query(ExamChoice).filter(ExamChoice.student_id == student.id).all()

        temp_filename = f"temp_{student.id}.pdf"
        temp_path = RECEIPTS_DIR / temp_filename

        try:
            generate_receipt_pdf(
                student=student,
                school_class=school_class,
                exam_choices=exam_choices,
                output_path=str(temp_path),
                templates_dir=TEMPLATES_DIR,
            )

            from pypdf import PdfReader
            reader = PdfReader(temp_path)
            for page in reader.pages:
                writer.add_page(page)

            temp_path.unlink()  # Удаляем временный файл

        except Exception as e:
            if temp_path.exists():
                temp_path.unlink()
            raise HTTPException(status_code=500, detail=f"Ошибка при генерации для {student.full_name}: {str(e)}")

    batch_filename = f"batch_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
    batch_path = RECEIPTS_DIR / batch_filename

    with open(batch_path, "wb") as f:
        writer.write(f)

    return FileResponse(
        path=batch_path,
        media_type="application/pdf",
        filename=batch_filename,
    )


@router.delete("/api/receipts/{receipt_id}")
async def delete_receipt(
    receipt_id: int,
    db: Session = Depends(SessionLocal),
    current_user: User = Depends(require_manager),
):
    """Удаление квитанции и PDF-файла."""
    receipt = db.query(Receipt).filter(Receipt.id == receipt_id).first()
    if not receipt:
        raise HTTPException(status_code=404, detail="Квитанция не найдена")

    pdf_path = Path(receipt.pdf_path)
    if pdf_path.exists():
        pdf_path.unlink()

    db.delete(receipt)
    db.commit()

    return {"message": f"Квитанция {receipt_id} удалена"}
