"""
Генератор PDF-бланков на основе шаблона и JSON-конфигурации координат.

Функциональность:
    - Универсальная генерация: структура бланка полностью определяется JSON.
    - Жёстких имён полей в коде нет — всё читается из конфигурации.
    - Поддержка многоблочных бланков (например, ПД-5: Извещение + Квитанция).
    - Поддержка многострочных полей (список значений → строки с line_height).
    - Шрифт Times New Roman (Windows) / Times-Roman (macOS, Linux).

Формат входного JSON (создаётся find_coordinates.py):
    {
        "source_template": "receipt_template.pdf",
        "font_size": 10,
        "line_height": 11,
        "roles": ["ФИО", "Вид платежа", "№ договора", ...],
        "blocks": [
            {"ФИО": {"page": 1, "x": 230, "y": 610}, ...},
            {"ФИО": {"page": 1, "x": 230, "y": 255}, ...}
        ]
    }

Формат field_values (передаётся в generate_pdf):
    {
        "ФИО": "Иванов Иван Иванович",
        "Вид платежа": ["Математика", "Физика"],  # список → многострочно
        "К оплате": "5 000.00",
        ...
    }

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
        pdfmetrics.registerFont(
            TTFont("TimesNewRoman", "C:/Windows/Fonts/times.ttf")
        )
        _FONT_NAME = "TimesNewRoman"
    else:
        _FONT_NAME = "Times-Roman"
except Exception:  # noqa: BLE001
    _FONT_NAME = "Times-Roman"


# =======================
# Загрузка конфигурации
# =======================

def load_template_config(json_path: str | Path) -> dict:
    """
    Загрузить конфигурацию бланка из JSON-файла.

    Параметры:
        json_path (str | Path): Путь к JSON-файлу.

    Возвращает:
        dict с ключами: source_template, font_size, line_height, roles, blocks.

    Исключения:
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
    Наложить текстовые данные на PDF-шаблон согласно конфигурации.

    Универсальная функция — не зависит от структуры конкретного бланка.
    Итерирует по блокам из config["blocks"], для каждой роли берёт
    значение из field_values и рисует его по координатам из блока.
    Значения-списки разворачиваются в многострочный текст.

    Параметры:
        field_values (dict): {роль: значение или список значений}.
        template_path (str | Path): Путь к PDF-шаблону.
        output_path (str | Path): Путь для сохранения результата.
        config (dict): Конфигурация из load_template_config().

    Возвращает:
        str: Абсолютный путь к созданному файлу.

    Исключения:
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

    # Создание overlay
    packet = io.BytesIO()
    can = canvas.Canvas(packet, pagesize=A4)
    can.setFont(_FONT_NAME, font_size)

    for block in blocks:
        for role, coord in block.items():
            value = field_values.get(role)
            if not value:
                continue

            x = coord["x"]
            y = coord["y"]

            # Список → многострочный текст с учётом line_height
            if isinstance(value, list):
                for i, line in enumerate(value):
                    if line:
                        can.drawString(x, y - i * line_height, str(line))
            else:
                can.drawString(x, y, str(value))

    can.save()

    # Наложение overlay на шаблон
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
    Сгенерировать квитанцию ПД-5.

    Обёртка над generate_pdf — формирует field_values из аргументов
    и вызывает универсальный генератор. Имена ролей должны совпадать
    с теми, что введены при создании JSON через find_coordinates.py.

    Параметры:
        student_name (str): ФИО ученика.
        courses (list[str]): Список предметов (многострочно).
        contract_number (str): Номер договора.
        month_year (str): Месяц и год платежа.
        amount (float): Сумма к оплате.
        compensation (str): Сумма компенсации (пустая — не печатается).
        output_path (str): Путь для сохранения PDF.
        coordinates_path (str | Path | None): Путь к JSON конфигурации.
            По умолчанию templates/receipt_coordinates.json.

    Возвращает:
        str: Абсолютный путь к созданному PDF.
    """
    # Нормализация
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

    # Загрузка конфигурации
    if coordinates_path is None:
        coordinates_path = (
            Path(__file__).parent / "templates" / "receipt_coordinates.json"
        )
    config = load_template_config(coordinates_path)
    template_path = Path(__file__).parent / "templates" / config["source_template"]

    # Формирование данных — имена ролей берутся из JSON, не из кода
    roles = config.get("roles", [])
    field_values = {}
    role_map = {
        # Стандартные роли квитанции → значения
        # Ищем по вхождению подстроки для гибкости
        "ФИО": student_name,
        "Вид платежа": courses,
        "№ договора": contract_number,
        "Месяц/год": month_year,
        "компенсация": compensation,
        "К оплате": amount_str,
    }
    for role in roles:
        # Точное совпадение
        if role in role_map:
            field_values[role] = role_map[role]

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
    """
    return generate_receipt(
        student_name=data.get("student_name") or data["Ф.И.О"],
        courses=data.get("courses") or data["Вид платежа"],
        contract_number=data.get("contract_number") or data["№ договора"],
        month_year=data.get("month_year") or data["Месяц/год"],
        amount=data.get("amount") or data["К оплате"],
        compensation=data.get("compensation", "") or data.get("компенсация", ""),
        output_path=output_path,
    )



if __name__ == "__main__":
    print("✅ generator загружен")
    print("📋 Используйте: python -m cli.commands generate-receipt-cmd")
