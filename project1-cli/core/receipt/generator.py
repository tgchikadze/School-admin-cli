"""
Генератор PDF-бланков на основе шаблона и JSON-конфигурации координат.

Функциональность:
- Универсальная генерация: структура бланка определяется JSON.
- Поддержка многоблочных бланков (ПД-5: Извещение + Квитанция).
- Поддержка многострочных полей (список → строки с line_height).
- Шрифт Times New Roman (Windows) / Times-Roman (macOS, Linux).

Зависимости: reportlab, pypdf.
"""

import io
import json
import platform
from pathlib import Path

from pypdf import PdfReader, PdfWriter
from reportlab.lib.pagesizes import A4
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas


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


# =======================
# Загрузка конфигурации
# =======================
def load_template_config(json_path: str | Path) -> dict:
    """
    Загружает конфигурацию бланка из JSON-файла.

    Args:
        json_path: Путь к JSON-файлу конфигурации.

    Returns:
        dict с ключами: source_template, font_size, line_height, roles, blocks.

    Raises:
        FileNotFoundError: Если файл не найден.
    """
    path = Path(json_path)
    if not path.exists():
        raise FileNotFoundError(
            f"Файл конфигурации не найден: {path}\n"
            f"Запустите find_coordinates.py для его создания."
        )
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


# =======================
# Генерация PDF
# =======================
def generate_pdf(
    field_values: dict,
    template_path: str | Path,
    output_path: str | Path,
    config: dict,
) -> str:
    """
    Накладывает текстовые данные на PDF-шаблон согласно конфигурации.

    Args:
        field_values: Словарь {роль: значение или список значений}.
        template_path: Путь к PDF-шаблону.
        output_path: Путь для сохранения результата.
        config: Конфигурация из load_template_config().

    Returns:
        Абсолютный путь к созданному файлу.

    Raises:
        FileNotFoundError: Если шаблон не найден.
    """
    template_path = Path(template_path)
    if not template_path.exists():
        raise FileNotFoundError(
            f"Шаблон не найден: {template_path}\n"
            f"Поместите шаблон в папку: {template_path.parent}"
        )

    font_size = config.get("font_size", 10)
    line_height = config.get("line_height", 11)
    blocks = config.get("blocks", [])

    packet = io.BytesIO()
    can = canvas.Canvas(packet, pagesize=A4)
    can.setFont(_FONT_NAME, font_size)

    for block in blocks:
        for role, coord in block.items():
            value = field_values.get(role)
            if not value:
                continue
            x, y = coord["x"], coord["y"]
            if isinstance(value, list):
                for i, line in enumerate(value):
                    if line:
                        can.drawString(x, y - i * line_height, str(line))
            else:
                can.drawString(x, y, str(value))

    can.save()

    packet.seek(0)
    overlay_pdf = PdfReader(packet)
    template_pdf = PdfReader(template_path)
    writer = PdfWriter()
    page = template_pdf.pages[0]
    page.merge_page(overlay_pdf.pages[0])
    writer.add_page(page)

    output_file_path = Path(output_path)
    output_file_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_file_path, "wb") as f:
        writer.write(f)

    return str(output_file_path.resolve())


# =======================
# Генерация квитанции
# =======================
def generate_receipt(
    student_name: str,
    courses: list[str],
    contract_number: str,
    month_year: str,
    amount: float,
    compensation: str,
    output_path: str,
    coordinates_path: str | Path | None = None,
) -> str:
    """
    Генерирует квитанцию ПД-5.

    Args:
        student_name: ФИО ученика.
        courses: Список предметов.
        contract_number: Номер договора.
        month_year: Месяц и год платежа.
        amount: Сумма к оплате.
        compensation: Сумма компенсации (пустая — не печатается).
        output_path: Путь для сохранения PDF.
        coordinates_path: Путь к JSON конфигурации (по умолчанию templates/receipt_coordinates.json).

    Returns:
        Абсолютный путь к созданному PDF.
    """
    student_name = str(student_name)
    contract_number = str(contract_number)
    month_year = str(month_year)
    compensation = str(compensation) if compensation else ""
    amount = float(amount)

    if not isinstance(courses, list):
        courses = [str(courses)]
    else:
        courses = [str(c) for c in courses if str(c).strip()]

    if not courses:
        raise ValueError("Список предметов не может быть пустым")

    amount_str = f"{amount:,.2f}".replace(",", " ")

    if coordinates_path is None:
        coordinates_path = Path(__file__).parent / "templates" / "receipt_coordinates.json"

    config = load_template_config(coordinates_path)
    template_path = Path(__file__).parent / "templates" / config["source_template"]

    roles = config.get("roles", [])
    role_map = {
        "ФИО": student_name,
        "Вид платежа": courses,
        "№ договора": contract_number,
        "Месяц/год": month_year,
        "компенсация": compensation,
        "К оплате": amount_str,
    }

    field_values = {role: role_map[role] for role in roles if role in role_map}

    return generate_pdf(field_values, template_path, output_path, config)


def generate_receipt_from_dict(
    data: dict,
    output_path: str = "receipt_output.pdf",
) -> str:
    """
    Генерирует квитанцию из словаря.

    Поддерживает два формата ключей:
    - Русские: 'Ф.И.О', 'Вид платежа', '№ договора', 'Месяц/год', 'К оплате', 'компенсация'
    - Английские: 'student_name', 'courses', 'contract_number', 'month_year', 'amount', 'compensation'

    Args:
        data: Словарь с данными ученика.
        output_path: Путь для сохранения PDF.

    Returns:
        Абсолютный путь к созданному PDF.
    """
    return generate_receipt(
        student_name=data.get("student_name") or data.get("Ф.И.О", ""),
        courses=data.get("courses") or data.get("Вид платежа", []),
        contract_number=data.get("contract_number") or data.get("№ договора", ""),
        month_year=data.get("month_year") or data.get("Месяц/год", ""),
        amount=data.get("amount") or data.get("К оплате", 0),
        compensation=data.get("compensation", "") or data.get("компенсация", ""),
        output_path=output_path,
    )


if __name__ == "__main__":
    print("✅ generator загружен")
    print("📋 Используйте: python -m cli.commands generate-receipt-cmd")
