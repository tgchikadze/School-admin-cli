"""Генератор квитанций ПД-5"""
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.pagesizes import A4
from pypdf import PdfReader, PdfWriter
import os
import io


def generate_receipt(student_name, courses, contract_number, month_year,
                     amount, compensation='', output_path='receipt_output.pdf'):
    """
    Генерирует квитанцию ПД-5 на основе шаблона

    Args:
        student_name (str): ФИО ученика
        courses (list): Список предметов
        contract_number (str): Номер договора
        month_year (str): Месяц/год
        amount (float): Сумма к оплате
        compensation (str): Компенсация (опционально)
        output_path (str): Путь для сохранения PDF

    Returns:
        str: Путь к созданному файлу
    """
    # ===== ПУТЬ К ШАБЛОНУ =====
    current_dir = os.path.dirname(os.path.abspath(__file__))
    template_path = os.path.join(current_dir, 'templates', 'receipt_template.pdf')

    if not os.path.exists(template_path):
        raise FileNotFoundError(
            f"Шаблон не найден: {template_path}\n"
            f"Поместите receipt_template.pdf в папку: {os.path.dirname(template_path)}"
        )

    # ===== НАСТРОЙКА ШРИФТА =====
    try:
        import platform
        system = platform.system()

        if system == 'Windows':
            try:
                pdfmetrics.registerFont(TTFont('TimesNewRoman', 'C:/Windows/Fonts/times.ttf'))
                font_name = 'TimesNewRoman'
            except:
                font_name = 'Times-Roman'
        else:
            font_name = 'Times-Roman'

    except Exception as e:
        font_name = 'Times-Roman'

    # ===== СОЗДАНИЕ OVERLAY =====
    packet = io.BytesIO()
    can = canvas.Canvas(packet, pagesize=A4)
    can.setFont(font_name, 10)  # 10pt размер шрифта

    # ===== КООРДИНАТЫ =====
    coordinates_1 = {
        'Ф.И.О': (230, 610),
        'Вид платежа': (190, 550),
        '№ договора': (380, 560),
        'Месяц/год': (190, 468),
        'компенсация': (275, 468),
        'К оплате': (360, 468)
    }

    coordinates_0 = {
        'Ф.И.О': (230, 255),
        'Вид платежа': (190, 195),
        '№ договора': (380, 205),
        'Месяц/год': (190, 116),
        'компенсация': (275, 116),
        'К оплате': (360, 116)
    }

    line_height = 11  # 11pt межстрочный интервал


    # ИЗВЕЩЕНИЕ (верх)
    can.drawString(coordinates_1['Ф.И.О'][0], coordinates_1['Ф.И.О'][1], student_name)

    x_courses, y_courses_start = coordinates_1['Вид платежа']
    for i, course in enumerate(courses):
        can.drawString(x_courses, y_courses_start - (i * line_height), course)

    can.drawString(coordinates_1['№ договора'][0], coordinates_1['№ договора'][1], contract_number)
    can.drawString(coordinates_1['Месяц/год'][0], coordinates_1['Месяц/год'][1], month_year)

    if compensation:
        can.drawString(coordinates_1['компенсация'][0], coordinates_1['компенсация'][1], compensation)

    amount_str = f"{amount:,.2f}".replace(',', ' ')
    can.drawString(coordinates_1['К оплате'][0], coordinates_1['К оплате'][1], amount_str)

    # КВИТАНЦИЯ (низ)
    can.drawString(coordinates_0['Ф.И.О'][0], coordinates_0['Ф.И.О'][1], student_name)

    x_courses_bottom, y_courses_start_bottom = coordinates_0['Вид платежа']
    for i, course in enumerate(courses):
        can.drawString(x_courses_bottom, y_courses_start_bottom - (i * line_height), course)

    can.drawString(coordinates_0['№ договора'][0], coordinates_0['№ договора'][1], contract_number)
    can.drawString(coordinates_0['Месяц/год'][0], coordinates_0['Месяц/год'][1], month_year)

    if compensation:
        can.drawString(coordinates_0['компенсация'][0], coordinates_0['компенсация'][1], compensation)

    can.drawString(coordinates_0['К оплате'][0], coordinates_0['К оплате'][1], amount_str)

    can.save()

    # ===== ОБЪЕДИНЕНИЕ С ШАБЛОНОМ =====
    packet.seek(0)
    overlay_pdf = PdfReader(packet)
    template_pdf = PdfReader(template_path)

    output = PdfWriter()
    page = template_pdf.pages[0]
    page.merge_page(overlay_pdf.pages[0])
    output.add_page(page)

    # Создать директорию если нужно
    output_dir = os.path.dirname(output_path)
    if output_dir and not os.path.exists(output_dir):
        os.makedirs(output_dir, exist_ok=True)

    with open(output_path, 'wb') as output_file:
        output.write(output_file)

    return os.path.abspath(output_path)


def generate_receipt_from_dict(data, output_path='receipt_output.pdf'):
    """
    Генерирует квитанцию из словаря с данными

    Args:
        data (dict): Словарь с ключами:
            - 'Ф.И.О': str
            - 'Вид платежа': list[str]
            - '№ договора': str
            - 'Месяц/год': str
            - 'К оплате': float
            - 'компенсация': str (опционально)
        output_path (str): Путь для сохранения

    Returns:
        str: Путь к созданному файлу
    """
    return generate_receipt(
        student_name=data['Ф.И.О'],
        courses=data['Вид платежа'],
        contract_number=data['№ договора'],
        month_year=data['Месяц/год'],
        amount=data['К оплате'],
        compensation=data.get('компенсация', ''),
        output_path=output_path
    )


if __name__ == "__main__":
    print("✅ receipt generator загружен")
    print("📋 Используйте: python -m cli.commands generate-receipt-cmd")
