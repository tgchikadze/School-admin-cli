"""
Сервисный скрипт для определения координат полей на PDF-бланках.

Флоу:
    1. Выбрать PDF через диалог → сетка наложена, файл сохранён.
    2. Открыть coordinate_grid_<имя>.pdf, найти координаты полей.
    3. Ввести роли полей через запятую: ФИО, Вид платежа, К оплате ...
    4. Ввести размер шрифта и межстрочный интервал.
    5. Указать, повторяются ли поля (Y/N) и сколько раз.
    6. Для каждой роли ввести: стр X Y (три числа через пробел).
    7. JSON сохранён — готово.

Формат JSON:
    {
        "source_template": "...",
        "font_size": 10,
        "line_height": 11,
        "roles": ["ФИО", "Вид платежа", ...],
        "blocks": [
            {"ФИО": {"page": 1, "x": 230, "y": 610}, ...},
            {"ФИО": {"page": 1, "x": 230, "y": 255}, ...}
        ]
    }

Зависимости: reportlab, pypdf, tkinter.
"""

import io
import json
import sys
from pathlib import Path
from tkinter import Tk, filedialog

from pypdf import PdfReader, PdfWriter
from reportlab.pdfgen import canvas

# =======================
# Настройки сетки
# =======================

GRID_STEP_MINOR = 10
GRID_STEP_MAJOR = 50
FONT_LABEL = "Helvetica"
FONT_SIZE_LABEL = 5
FONT_SIZE_TITLE = 7


# =======================
# Выбор файла
# =======================

def select_pdf_file() -> Path:
    root = Tk()
    root.withdraw()
    root.attributes("-topmost", True)
    file_path = filedialog.askopenfilename(
        title="Выберите PDF-шаблон",
        filetypes=[("PDF файлы", "*.pdf"), ("Все файлы", "*.*")],
    )
    root.destroy()
    if not file_path:
        print("❌ Файл не выбран. Выход.")
        sys.exit(0)
    return Path(file_path)


# =======================
# Генерация сетки
# =======================

def _make_grid_overlay(page_width: float, page_height: float, page_num: int) -> bytes:
    packet = io.BytesIO()
    c = canvas.Canvas(packet, pagesize=(page_width, page_height))
    c.setFont(FONT_LABEL, FONT_SIZE_LABEL)

    # Мелкие деления — 10pt
    c.setStrokeColorRGB(0.85, 0.85, 0.85)
    for x in range(0, int(page_width), GRID_STEP_MINOR):
        if x % GRID_STEP_MAJOR != 0:
            c.line(x, 0, x, page_height)
    for y in range(0, int(page_height), GRID_STEP_MINOR):
        if y % GRID_STEP_MAJOR != 0:
            c.line(0, y, page_width, y)

    # Крупные деления — 50pt с подписями
    c.setStrokeColorRGB(0.5, 0.5, 0.5)
    c.setFillColorRGB(0.1, 0.1, 0.7)
    for x in range(0, int(page_width), GRID_STEP_MAJOR):
        c.line(x, 0, x, page_height)
        c.drawString(x + 1, 12, str(x))
    for y in range(0, int(page_height), GRID_STEP_MAJOR):
        c.line(0, y, page_width, y)
        c.drawString(2, y + 2, str(y))

    # Заголовок
    c.setFillColorRGB(0.8, 0.0, 0.0)
    c.setFont(FONT_LABEL, FONT_SIZE_TITLE)
    c.drawString(
        page_width / 2 - 130, page_height - 15,
        f"Стр. {page_num} | (0,0)=нижний левый | "
        f"мелкая {GRID_STEP_MINOR}pt, крупная {GRID_STEP_MAJOR}pt",
    )
    c.save()
    packet.seek(0)
    return packet.read()


def apply_grid_to_pdf(template_path: Path) -> Path:
    template_pdf = PdfReader(template_path)
    writer = PdfWriter()
    total_pages = len(template_pdf.pages)
    print(f"\n📄 Накладываю сетку: {total_pages} стр.")
    for i, page in enumerate(template_pdf.pages):
        page_num = i + 1
        width = float(page.mediabox.width)
        height = float(page.mediabox.height)
        grid_bytes = _make_grid_overlay(width, height, page_num)
        overlay_reader = PdfReader(io.BytesIO(grid_bytes))
        page.merge_page(overlay_reader.pages[0])
        writer.add_page(page)
    output_path = template_path.parent / f"coordinate_grid_{template_path.name}"
    with open(output_path, "wb") as f:
        writer.write(f)
    print(f"✅ Сохранено: {output_path}")
    return output_path


# =======================
# Консольный интерфейс
# =======================

def _ask_int(prompt: str) -> int:
    while True:
        raw = input(prompt).strip()
        try:
            return int(raw)
        except ValueError:
            print(f"  ⚠️  Ожидается целое число. Повторите.")


def _ask_page_coords(role: str) -> tuple[int, int, int]:
    """Запросить страницу и координаты одной строкой: стр X Y"""
    while True:
        raw = input(f"  {role:20s} → стр X Y: ").strip()
        parts = raw.split()
        if len(parts) == 3:
            try:
                return int(parts[0]), int(parts[1]), int(parts[2])
            except ValueError:
                pass
        print("  ⚠️  Введите три числа через пробел: страница X Y. Повторите.")


def collect_roles() -> list[str]:
    """Запросить список ролей через запятую."""
    print("\n  Введите роли полей через запятую.")
    print("  Пример: ФИО, Вид платежа, № договора, Месяц/год, компенсация, К оплате")
    while True:
        raw = input("  Роли: ").strip()
        roles = [r.strip() for r in raw.split(",") if r.strip()]
        if roles:
            return roles
        print("  ⚠️  Список ролей не может быть пустым.")


def collect_blocks(roles: list[str]) -> list[dict]:
    """
    Собрать координаты для всех повторений (блоков).

    Если поля не повторяются — один блок.
    Если повторяются — пользователь указывает количество повторений
    и вводит координаты для каждого.

    Возвращает:
        list[dict]: Список блоков вида [{"роль": {"page": p, "x": x, "y": y}, ...}, ...]
    """
    repeats_raw = input("\n  Поля повторяются на бланке? (Y/N): ").strip().upper()
    if repeats_raw == "Y":
        n_blocks = _ask_int("  Количество повторений: ")
    else:
        n_blocks = 1

    blocks = []
    for i in range(n_blocks):
        if n_blocks > 1:
            print(f"\n  Повторение {i + 1}:")
        block = {}
        for role in roles:
            page, x, y = _ask_page_coords(role)
            block[role] = {"page": page, "x": x, "y": y}
        blocks.append(block)

    return blocks


def save_result(
    roles: list[str],
    blocks: list[dict],
    template_path: Path,
    font_size: int,
    line_height: int,
) -> Path:
    default_name = template_path.stem.replace("_template", "") + "_coordinates.json"
    print(f"\n  Имя файла по умолчанию: {default_name}")
    user_name = input("  Имя JSON-файла (Enter — по умолчанию): ").strip()
    output_name = user_name if user_name else default_name
    output_path = template_path.parent / output_name

    data = {
        "source_template": template_path.name,
        "font_size": font_size,
        "line_height": line_height,
        "roles": roles,
        "blocks": blocks,
    }

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print(f"\n✅ Конфигурация сохранена: {output_path}")
    return output_path


# =======================
# Точка входа
# =======================

def main() -> None:
    print("=" * 60)
    print("  FIND COORDINATES — помощник по координатам PDF-бланков")
    print("=" * 60)

    template_path = select_pdf_file()
    print(f"\n✅ Выбран: {template_path.name}")

    output_path = apply_grid_to_pdf(template_path)

    print(f"\n👁  Откройте и изучите координаты:")
    print(f"   {output_path}")
    input("\n  Нажмите Enter, когда готовы вводить...")

    roles = collect_roles()

    print("\n📐 Настройки шрифта:")
    font_size = _ask_int("  Размер шрифта в pt (обычно 10): ") or 10
    line_height = _ask_int("  Межстрочный интервал в pt (обычно 11): ") or 11

    blocks = collect_blocks(roles)

    save_result(roles, blocks, template_path, font_size, line_height)


if __name__ == "__main__":
    main()
