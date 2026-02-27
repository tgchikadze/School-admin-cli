"""
receipt_utils.py — Генерация PDF-квитанций для веб-интерфейса.

Адаптирует generator.py (из Project 1-2) для работы в FastAPI:
  - расчёт стоимости (fixed / per_subject + компенсация)
  - одиночная генерация
  - пакетная генерация (склейка в многостраничный PDF)
"""

import os
import io
from datetime import datetime
from pathlib import Path

from pypdf import PdfReader, PdfWriter
from reportlab.lib.pagesizes import A4
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas

import json
import platform

# ── Шрифт (Times New Roman / Times-Roman) ──────────────────

try:
    if platform.system() == "Windows":
        pdfmetrics.registerFont(
            TTFont("TimesNewRoman", r"C:\Windows\Fonts\times.ttf")
        )
        FONTNAME = "TimesNewRoman"
    else:
        FONTNAME = "Times-Roman"
except Exception:
    FONTNAME = "Times-Roman"


# ── Пути к шаблону и координатам ───────────────────────────

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DATA_DIR = os.path.join(BASE_DIR, "data")
TEMPLATES_DIR = os.path.join(DATA_DIR, "templates")
RECEIPTS_DIR = os.path.join(DATA_DIR, "receipts")

TEMPLATE_PDF = os.path.join(TEMPLATES_DIR, "receipt_template.pdf")
COORDINATES_JSON = os.path.join(TEMPLATES_DIR, "receipt_coordinates.json")


def _ensure_dirs():
    """Создаёт папки data/templates и data/receipts если их нет."""
    os.makedirs(TEMPLATES_DIR, exist_ok=True)
    os.makedirs(RECEIPTS_DIR, exist_ok=True)


def load_config(json_path: str | None = None) -> dict:
    """Загружает JSON-конфигурацию координат полей."""
    path = json_path or COORDINATES_JSON
    if not os.path.exists(path):
        raise FileNotFoundError(f"Файл координат не найден: {path}")
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


# ── Расчёт стоимости ───────────────────────────────────────

def calc_receipt_amount(
    pricing_type: str,
    base_price: float,
    price_per_subject: float,
    exam_count: int,
    compensation: float,
) -> float:
    """
    Рассчитать итоговую сумму к оплате.

    Классы 7-10 (fixed):       base_price - compensation
    Класс 11   (per_subject):  exam_count * price_per_subject - compensation

    compensation > 0 → переплата (вычитаем из суммы)
    compensation < 0 → задолженность (прибавляем к сумме, т.к. -(-x) = +x)
    """
    if pricing_type == "per_subject":
        raw = exam_count * price_per_subject
    else:
        raw = base_price
    return raw - compensation


# ── Низкоуровневая генерация PDF ───────────────────────────

def _generate_overlay(field_values: dict, config: dict) -> bytes:
    """
    Создаёт PDF-overlay с текстовыми данными по координатам.
    Возвращает bytes готового одностраничного PDF.
    """
    font_size = config.get("font_size", 10)
    line_height = config.get("line_height", 11)
    blocks = config.get("blocks", [])

    packet = io.BytesIO()
    can = canvas.Canvas(packet, pagesize=A4)
    can.setFont(FONTNAME, font_size)

    for block in blocks:
        for role, coord in block.items():
            value = field_values.get(role)
            if not value:
                continue
            x = coord["x"]
            y = coord["y"]

            if isinstance(value, list):
                for i, line in enumerate(value):
                    if line:
                        can.drawString(x, y - i * line_height, str(line))
            else:
                can.drawString(x, y, str(value))

    can.save()
    packet.seek(0)
    return packet.read()


def generate_single_receipt(
    student_name: str,
    courses: list[str] | str,
    contract_number: str,
    month_year: str,
    amount: float,
    compensation: float,
    output_path: str,
    config: dict | None = None,
) -> str:
    """
    Генерирует одну PDF-квитанцию (overlay на шаблон).

    Возвращает абсолютный путь к файлу.
    """
    _ensure_dirs()

    if config is None:
        config = load_config()

    template_path = TEMPLATE_PDF
    if not os.path.exists(template_path):
        raise FileNotFoundError(f"Шаблон PDF не найден: {template_path}")

    # Подготовка «Вид платежа» — список предметов (каждый на своей строке)
    if isinstance(courses, list):
        courses_list = [str(c) for c in courses if str(c).strip()]
    else:
        courses_list = [str(courses)]

    # Формат суммы
    amount_str = f"{amount:,.2f}".replace(",", " ").replace(".", ",")

    # Компенсация — показываем только если != 0
    comp_str = ""
    if compensation and compensation != 0:
        comp_str = f"{compensation:,.2f}".replace(",", " ").replace(".", ",")

    # Маппинг ролей → значений (согласно receipt_coordinates.json)
    roles = config.get("roles", [])
    role_map = {
        "ФИО": student_name,
        "Вид платежа": courses_list,
        "№ договора": contract_number,
        "Месяц/год": month_year,
        "компенсация": comp_str,
        "К оплате": amount_str,
    }
    field_values = {}
    for role in roles:
        if role in role_map:
            field_values[role] = role_map[role]

    # Генерируем overlay
    overlay_bytes = _generate_overlay(field_values, config)

    # Мержим overlay с шаблоном
    overlay_reader = PdfReader(io.BytesIO(overlay_bytes))
    template_reader = PdfReader(template_path)

    writer = PdfWriter()
    page = template_reader.pages[0]
    page.merge_page(overlay_reader.pages[0])
    writer.add_page(page)

    # Сохраняем
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    with open(output, "wb") as f:
        writer.write(f)

    return str(output.resolve())


def generate_batch_receipts(
    receipts_data: list[dict],
    output_path: str,
    config: dict | None = None,
) -> str:
    """
    Пакетная генерация — склеивает несколько квитанций в один PDF.

    receipts_data — список словарей, каждый содержит:
        student_name, courses, contract_number, month_year, amount, compensation

    Возвращает абсолютный путь к файлу.
    """
    _ensure_dirs()

    if config is None:
        config = load_config()

    template_path = TEMPLATE_PDF
    if not os.path.exists(template_path):
        raise FileNotFoundError(f"Шаблон PDF не найден: {template_path}")

    writer = PdfWriter()

    for data in receipts_data:
        student_name = data["student_name"]
        courses = data.get("courses", "")
        contract_number = data.get("contract_number", "")
        month_year = data.get("month_year", "")
        amount = data.get("amount", 0.0)
        compensation = data.get("compensation", 0.0)

        if isinstance(courses, list):
            courses_list = [str(c) for c in courses if str(c).strip()]
        else:
            courses_list = [str(courses)]

        amount_str = f"{amount:,.2f}".replace(",", " ").replace(".", ",")
        comp_str = ""
        if compensation and compensation != 0:
            comp_str = f"{compensation:,.2f}".replace(",", " ").replace(".", ",")

        roles = config.get("roles", [])
        role_map = {
            "ФИО": student_name,
            "Вид платежа": courses_list,
            "№ договора": contract_number,
            "Месяц/год": month_year,
            "компенсация": comp_str,
            "К оплате": amount_str,
        }
        field_values = {r: role_map[r] for r in roles if r in role_map}

        overlay_bytes = _generate_overlay(field_values, config)
        overlay_reader = PdfReader(io.BytesIO(overlay_bytes))

        # Каждая квитанция — свежая копия шаблона
        template_reader = PdfReader(template_path)
        page = template_reader.pages[0]
        page.merge_page(overlay_reader.pages[0])
        writer.add_page(page)

    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    with open(output, "wb") as f:
        writer.write(f)

    return str(output.resolve())
