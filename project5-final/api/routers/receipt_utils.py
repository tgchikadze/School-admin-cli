"""
routers/receipt_utils.py — Генерация PDF через координатную систему (P1/P2).

Обёртка над логикой generator.py для работы с моделями SQLAlchemy.
"""
import json
from pathlib import Path
from datetime import datetime
from pypdf import PdfReader, PdfWriter
from reportlab.lib.pagesizes import A4
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas
import io
import platform


# =======================
# Настройка шрифта
# =======================
try:
    if platform.system() == "Windows":
        pdfmetrics.registerFont(TTFont("TimesNewRoman", "C:/Windows/Fonts/times.ttf"))
        _FONT_NAME = "TimesNewRoman"
    else:
        _FONT_NAME = "Times-Roman"
except Exception:
    _FONT_NAME = "Times-Roman"


def load_template_config(json_path: Path) -> dict:
    """Загрузка конфигурации координат из JSON."""
    if not json_path.exists():
        raise FileNotFoundError(
            f"Файл координат не найден: {json_path}\n"
            f"Поместите receipt_coordinates.json в папку templates/"
        )
    with open(json_path, "r", encoding="utf-8") as f:
        return json.load(f)


def generate_receipt_pdf(
    student,
    school_class,
    exam_choices: list,
    output_path: str,
    templates_dir: Path,
):
    """
    Генерирует PDF-квитанцию через координатную систему.

    Args:
        student: Объект Student (SQLAlchemy)
        school_class: Объект SchoolClass (SQLAlchemy)
        exam_choices: Список ExamChoice (SQLAlchemy)
        output_path: Путь для сохранения PDF
        templates_dir: Папка с templates/ (receipt_template.pdf + receipt_coordinates.json)
    """
    # Загрузка конфигурации
    coordinates_path = templates_dir / "receipt_coordinates.json"
    config = load_template_config(coordinates_path)

    template_filename = config.get("source_template", "receipt_template.pdf")
    template_path = templates_dir / template_filename

    if not template_path.exists():
        raise FileNotFoundError(
            f"Шаблон не найден: {template_path}\n"
            f"Поместите {template_filename} в папку templates/"
        )

    # Подготовка данных
    student_name = student.full_name
    contract_number = student.contract_number
    month_year = datetime.now().strftime("%m.%Y")

    # Формирование списка предметов
    if school_class.pricing_type == "fixed":
        # 7-10 классы: список предметов класса
        courses = school_class.subjects if school_class.subjects else []
    else:
        # 11 класс: список выбранных ЕГЭ
        courses = [ec.subject_name for ec in exam_choices]

    if not courses:
        courses = ["Обучение"]

    # Расчёт суммы к оплате
    amount = student.monthly_payment - student.compensation
    compensation_str = f"{student.compensation:,.2f}".replace(",", " ") if student.compensation != 0 else ""
    amount_str = f"{amount:,.2f}".replace(",", " ")

    # Подготовка данных для наложения
    font_size = config.get("font_size", 10)
    line_height = config.get("line_height", 11)
    blocks = config.get("blocks", [])

    role_map = {
        "ФИО": student_name,
        "Вид платежа": courses,  # Список строк
        "№ договора": contract_number,
        "Месяц/год": month_year,
        "компенсация": compensation_str,
        "К оплате": amount_str,
    }

    # Создание overlay с текстом
    packet = io.BytesIO()
    can = canvas.Canvas(packet, pagesize=A4)
    can.setFont(_FONT_NAME, font_size)

    for block in blocks:
        for role, coord in block.items():
            value = role_map.get(role)
            if not value:
                continue

            x, y = coord["x"], coord["y"]

            if isinstance(value, list):
                # Многострочное поле (предметы)
                for i, line in enumerate(value):
                    if line:
                        can.drawString(x, y - i * line_height, str(line))
            else:
                # Однострочное поле
                can.drawString(x, y, str(value))

    can.save()

    # Наложение на шаблон
    packet.seek(0)
    overlay_pdf = PdfReader(packet)
    template_pdf = PdfReader(template_path)
    writer = PdfWriter()

    page = template_pdf.pages[0]
    page.merge_page(overlay_pdf.pages[0])
    writer.add_page(page)

    # Сохранение
    output_file_path = Path(output_path)
    output_file_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_file_path, "wb") as f:
        writer.write(f)

    return str(output_file_path.resolve())
