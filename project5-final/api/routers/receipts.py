"""
routers/receipts.py - Генерация квитанций на оплату.
Одиночная + массовая генерация PDF. Доступ: admin + manager.
"""

import os
import io
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from ..dependencies import get_db, require_manager
from ..models import Student, SchoolClass, ExamChoice, Receipt, User
from ..schemas import ReceiptCreate, ReceiptOut, ReceiptBatch

router = APIRouter(tags=["receipts"])

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
templates = Jinja2Templates(directory=os.path.join(BASE_DIR, "web", "templates"))
RECEIPTS_DIR = os.path.join(BASE_DIR, "data", "receipts")
os.makedirs(RECEIPTS_DIR, exist_ok=True)


# ═══════════════════════════════════════════════════════════════
#  PDF-генератор (встроенный, без шаблона — reportlab)
# ═══════════════════════════════════════════════════════════════

def _generate_receipt_pdf(student: Student, school_class: SchoolClass,
                          exam_choices: list, receipt_id: int) -> bytes:
    """
    Генерирует PDF-квитанцию для ученика.
    Возвращает байты PDF.
    """
    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.units import mm
        from reportlab.pdfgen import canvas
        from reportlab.pdfbase import pdfmetrics
        from reportlab.pdfbase.ttfonts import TTFont
    except ImportError:
        return _generate_receipt_pdf_fallback(student, school_class, exam_choices, receipt_id)

    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=A4)
    w, h = A4

    # Попытка зарегистрировать шрифт с кириллицей
    font_name = "Helvetica"
    for font_path in [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/TTF/DejaVuSans.ttf",
        os.path.join(BASE_DIR, "data", "fonts", "DejaVuSans.ttf"),
    ]:
        if os.path.exists(font_path):
            try:
                pdfmetrics.registerFont(TTFont("DejaVuSans", font_path))
                font_name = "DejaVuSans"
                break
            except Exception:
                pass

    # ─── Заголовок ────────────────────────────────────────────
    c.setFont(font_name, 18)
    c.drawCentredString(w / 2, h - 40 * mm, "КВИТАНЦИЯ НА ОПЛАТУ")

    c.setFont(font_name, 10)
    c.drawCentredString(w / 2, h - 48 * mm, f"Профильная школа «Биотех225»")

    c.setFont(font_name, 9)
    c.drawString(20 * mm, h - 58 * mm, f"Квитанция №{receipt_id}")
    c.drawRightString(w - 20 * mm, h - 58 * mm,
                      f"Дата: {datetime.now().strftime('%d.%m.%Y')}")

    # ─── Линия ────────────────────────────────────────────────
    c.setLineWidth(0.5)
    c.line(20 * mm, h - 62 * mm, w - 20 * mm, h - 62 * mm)

    # ─── Данные ученика ───────────────────────────────────────
    y = h - 72 * mm
    c.setFont(font_name, 11)

    fields = [
        ("Ученик:", student.full_name),
        ("Класс:", school_class.name),
        ("Договор:", student.contract_number or "—"),
    ]

    for label, value in fields:
        c.setFont(font_name, 10)
        c.drawString(20 * mm, y, label)
        c.setFont(font_name, 11)
        c.drawString(60 * mm, y, str(value))
        y -= 7 * mm

    # ─── Предметы / стоимость ─────────────────────────────────
    y -= 5 * mm
    c.setLineWidth(0.3)
    c.line(20 * mm, y, w - 20 * mm, y)
    y -= 7 * mm

    if school_class.pricing_type == "per_subject":
        # 11 класс — список ЕГЭ
        c.setFont(font_name, 10)
        c.drawString(20 * mm, y, "Предметы ЕГЭ:")
        y -= 7 * mm

        for i, ec in enumerate(exam_choices, 1):
            c.setFont(font_name, 10)
            c.drawString(25 * mm, y, f"{i}. {ec.subject_name}")
            c.drawRightString(w - 20 * mm, y,
                              f"{school_class.price_per_subject:.0f} руб.")
            y -= 6 * mm

        y -= 3 * mm
        c.line(20 * mm, y, w - 20 * mm, y)
        y -= 7 * mm

        c.setFont(font_name, 12)
        c.drawString(20 * mm, y,
                     f"Итого: {len(exam_choices)} × "
                     f"{school_class.price_per_subject:.0f} = "
                     f"{student.monthly_payment:.0f} руб./мес")
    else:
        # 7-10 класс — фиксированная стоимость
        c.setFont(font_name, 10)
        c.drawString(20 * mm, y, "Предметы:")
        y -= 7 * mm

        for i, subj in enumerate(school_class.subjects or [], 1):
            c.setFont(font_name, 10)
            c.drawString(25 * mm, y, f"{i}. {subj}")
            y -= 6 * mm

        y -= 3 * mm
        c.line(20 * mm, y, w - 20 * mm, y)
        y -= 7 * mm

        c.setFont(font_name, 12)
        c.drawString(20 * mm, y,
                     f"Стоимость: {student.monthly_payment:.0f} руб./мес")

    # ─── Компенсация ──────────────────────────────────────────
    if student.compensation != 0:
        y -= 10 * mm
        c.setFont(font_name, 10)
        if student.compensation > 0:
            c.drawString(20 * mm, y,
                         f"Переплата (школа должна ученику): "
                         f"+{student.compensation:.2f} руб.")
        else:
            c.drawString(20 * mm, y,
                         f"Задолженность (ученик должен школе): "
                         f"{student.compensation:.2f} руб.")

    # ─── К оплате ─────────────────────────────────────────────
    amount_due = student.monthly_payment - student.compensation
    y -= 12 * mm
    c.setFont(font_name, 14)
    c.drawCentredString(w / 2, y, f"К ОПЛАТЕ: {amount_due:.0f} руб.")

    # ─── Подпись ──────────────────────────────────────────────
    y -= 20 * mm
    c.setFont(font_name, 9)
    c.drawString(20 * mm, y, "Подпись ответственного: _______________")
    c.drawRightString(w - 20 * mm, y, "Дата: _______________")

    c.save()
    buf.seek(0)
    return buf.read()


def _generate_receipt_pdf_fallback(student, school_class, exam_choices,
                                   receipt_id):
    """Простейший текстовый PDF без reportlab (plain text → PDF via fpdf2)."""
    try:
        from fpdf import FPDF
        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("Helvetica", size=12)
        pdf.cell(0, 10, f"Receipt #{receipt_id}", ln=True)
        pdf.cell(0, 10, f"Student: {student.full_name}", ln=True)
        pdf.cell(0, 10, f"Class: {school_class.name}", ln=True)
        pdf.cell(0, 10, f"Payment: {student.monthly_payment}", ln=True)
        return pdf.output()
    except ImportError:
        # Совсем минимальный вариант — вернём текст
        return (
            f"Receipt #{receipt_id}\n"
            f"Student: {student.full_name}\n"
            f"Class: {school_class.name}\n"
            f"Payment: {student.monthly_payment}\n"
        ).encode("utf-8")


def _merge_pdfs(pdf_bytes_list: list[bytes]) -> bytes:
    """Объединить несколько PDF в один."""
    try:
        from pypdf import PdfReader, PdfWriter
    except ImportError:
        from PyPDF2 import PdfReader, PdfWriter

    writer = PdfWriter()
    for pdf_bytes in pdf_bytes_list:
        reader = PdfReader(io.BytesIO(pdf_bytes))
        for page in reader.pages:
            writer.add_page(page)

    output = io.BytesIO()
    writer.write(output)
    output.seek(0)
    return output.read()


# ═══════════════════════════════════════════════════════════════
#  HTML-страница
# ═══════════════════════════════════════════════════════════════

@router.get("/receipts", response_class=HTMLResponse)
def receipts_page(request: Request, user: User = Depends(require_manager)):
    return templates.TemplateResponse("receipts.html", {
        "request": request, "role": user.role, "username": user.username,
    })


# ═══════════════════════════════════════════════════════════════
#  API: список квитанций
# ═══════════════════════════════════════════════════════════════

@router.get("/api/receipts", response_model=list[ReceiptOut])
def list_receipts(
    student_id: int | None = None,
    db: Session = Depends(get_db),
    user: User = Depends(require_manager),
):
    """Список всех квитанций (с фильтром по ученику)."""
    q = db.query(Receipt).order_by(Receipt.created_at.desc())
    if student_id:
        q = q.filter(Receipt.student_id == student_id)
    return q.limit(200).all()


# ═══════════════════════════════════════════════════════════════
#  API: одиночная генерация
# ═══════════════════════════════════════════════════════════════

@router.post("/api/receipts/generate", response_model=ReceiptOut,
             status_code=201)
def generate_receipt(
    data: ReceiptCreate,
    db: Session = Depends(get_db),
    user: User = Depends(require_manager),
):
    """Сгенерировать квитанцию для одного ученика (сохранить PDF + запись)."""
    student = db.query(Student).get(data.student_id)
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")

    school_class = db.query(SchoolClass).get(student.class_id)
    exam_choices = student.exam_choices if school_class.pricing_type == "per_subject" else []

    # Сумма к оплате
    amount = student.monthly_payment - student.compensation

    # Создать запись
    receipt = Receipt(
        student_id=student.id,
        created_by=user.id,
        amount=amount,
    )
    db.add(receipt)
    db.flush()

    # Сгенерировать PDF
    pdf_bytes = _generate_receipt_pdf(student, school_class, exam_choices,
                                      receipt.id)

    # Сохранить файл
    filename = f"receipt_{receipt.id}_{student.id}_{datetime.now():%Y%m%d_%H%M%S}.pdf"
    filepath = os.path.join(RECEIPTS_DIR, filename)
    with open(filepath, "wb") as f:
        f.write(pdf_bytes)

    receipt.pdf_path = filepath
    db.commit()
    db.refresh(receipt)
    return receipt


# ═══════════════════════════════════════════════════════════════
#  API: скачать PDF квитанции
# ═══════════════════════════════════════════════════════════════

@router.get("/api/receipts/{receipt_id}/pdf")
def download_receipt(
    receipt_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(require_manager),
):
    """Скачать PDF-файл квитанции."""
    receipt = db.query(Receipt).get(receipt_id)
    if not receipt:
        raise HTTPException(status_code=404, detail="Receipt not found")

    if not receipt.pdf_path or not os.path.exists(receipt.pdf_path):
        raise HTTPException(status_code=404, detail="PDF file not found")

    with open(receipt.pdf_path, "rb") as f:
        content = f.read()

    student = db.query(Student).get(receipt.student_id)
    filename = f"receipt_{receipt.id}_{student.full_name if student else 'unknown'}.pdf"

    return StreamingResponse(
        io.BytesIO(content),
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


# ═══════════════════════════════════════════════════════════════
#  API: массовая генерация (пакет → один PDF)
# ═══════════════════════════════════════════════════════════════

@router.post("/api/receipts/batch")
def generate_batch(
    data: ReceiptBatch,
    db: Session = Depends(get_db),
    user: User = Depends(require_manager),
):
    """Сгенерировать квитанции для списка учеников → объединённый PDF."""
    if not data.student_ids:
        raise HTTPException(status_code=400, detail="No students provided")

    pdf_list = []
    receipt_ids = []

    for sid in data.student_ids:
        student = db.query(Student).get(sid)
        if not student:
            continue

        school_class = db.query(SchoolClass).get(student.class_id)
        exam_choices = (
            student.exam_choices
            if school_class.pricing_type == "per_subject"
            else []
        )
        amount = student.monthly_payment - student.compensation

        receipt = Receipt(
            student_id=student.id,
            created_by=user.id,
            amount=amount,
        )
        db.add(receipt)
        db.flush()

        pdf_bytes = _generate_receipt_pdf(
            student, school_class, exam_choices, receipt.id
        )

        filename = f"receipt_{receipt.id}_{student.id}.pdf"
        filepath = os.path.join(RECEIPTS_DIR, filename)
        with open(filepath, "wb") as f:
            f.write(pdf_bytes)

        receipt.pdf_path = filepath
        pdf_list.append(pdf_bytes)
        receipt_ids.append(receipt.id)

    db.commit()

    if not pdf_list:
        raise HTTPException(status_code=404, detail="No valid students found")

    # Объединить все PDF в один
    merged = _merge_pdfs(pdf_list)

    batch_filename = f"batch_{datetime.now():%Y%m%d_%H%M%S}.pdf"

    return StreamingResponse(
        io.BytesIO(merged),
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="{batch_filename}"'
        },
    )


# ═══════════════════════════════════════════════════════════════
#  API: удалить квитанцию
# ═══════════════════════════════════════════════════════════════

@router.delete("/api/receipts/{receipt_id}")
def delete_receipt(
    receipt_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(require_manager),
):
    """Удалить запись о квитанции (+ файл)."""
    receipt = db.query(Receipt).get(receipt_id)
    if not receipt:
        raise HTTPException(status_code=404, detail="Receipt not found")

    if receipt.pdf_path and os.path.exists(receipt.pdf_path):
        os.remove(receipt.pdf_path)

    db.delete(receipt)
    db.commit()
    return {"detail": "Receipt deleted"}
