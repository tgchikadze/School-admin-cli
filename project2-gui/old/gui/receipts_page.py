"""
Страница генерации квитанций
"""
import flet as ft
from core.data.student_db import StudentDatabase
from core.data.classes_db import ClassesDatabase
from core.receipt.generator import generate_receipt
from core.data.exam_choices_db import ExamChoicesDatabase
from datetime import datetime

from pathlib import Path
import platform
import os


class ReceiptsPage:
    """Страница для генерации квитанций"""

    def __init__(self, page: ft.Page):
        self.page = page
        self.db = StudentDatabase()
        self.classes_db = ClassesDatabase()
        self.exam_db = ExamChoicesDatabase()  # НОВАЯ СТРОКА
        # ... остальное

        # Поля формы
        self.student_dropdown = None
        self.fio_field = None
        self.contract_field = None
        self.class_field = None
        self.month_field = None
        self.year_field = None
        self.amount_field = None
        self.compensation_field = None
        self.courses_container = None
        self.courses_list = []
        self.current_class_id = None
        self.available_subjects = []
        self.is_class_11 = False

    def build(self) -> ft.Column:
        """Построить интерфейс страницы"""

        if hasattr(self, '_layout') and self._layout is not None:
            return self._layout

        # Получить список учеников
        students = self.db.get_all()
        student_options = [
            ft.dropdown.Option(key=str(s['id']), text=s['fio'])
            for s in students
        ]

        # Выпадающий список учеников
        self.student_dropdown = ft.Dropdown(
            label="Выберите ученика",
            options=student_options,
            width=400,
            on_change=self._on_student_selected,
        )

        # Поля формы
        self.fio_field = ft.TextField(
            label="ФИО",
            width=400,
            dense=True,
        )

        self.contract_field = ft.TextField(
            label="Номер договора",
            width=200,
            dense=True,
        )

        self.class_field = ft.TextField(
            label="Класс",
            width=150,
            dense=True,
            read_only=True,
            bgcolor=ft.colors.GREY_100,
        )

        # Текущий месяц и год
        months_ru = [
            "Январь", "Февраль", "Март", "Апрель", "Май", "Июнь",
            "Июль", "Август", "Сентябрь", "Октябрь", "Ноябрь", "Декабрь"
        ]
        current_month = months_ru[datetime.now().month - 1]
        current_year = str(datetime.now().year)

        self.month_field = ft.TextField(
            label="Месяц",
            value=current_month,
            width=150,
            dense=True,
        )

        self.year_field = ft.TextField(
            label="Год",
            value=current_year,
            width=100,
            dense=True,
        )

        self.amount_field = ft.TextField(
            label="Сумма к оплате (₽)",
            width=200,
            dense=True,
            keyboard_type=ft.KeyboardType.NUMBER,
        )

        self.compensation_field = ft.TextField(
            label="Компенсация",
            width=200,
            dense=True,
        )

        # Контейнер для списка курсов
        self.courses_container = ft.Column(spacing=5)

        # Кнопка добавления курса
        add_course_btn = ft.IconButton(
            icon=ft.icons.ADD_CIRCLE,
            icon_color=ft.colors.GREEN_700,
            icon_size=30,
            tooltip="Добавить предмет",
            on_click=self._add_course,
        )

        # Кнопка генерации
        generate_btn = ft.ElevatedButton(
            "📥 Сгенерировать квитанцию",
            on_click=self._generate_receipt,
            style=ft.ButtonStyle(
                bgcolor=ft.colors.GREEN_700,
                color=ft.colors.WHITE,
            ),
        )

        # Layout
        self._layout =  ft.Column(
            controls=[
                ft.Text("📄 Создание квитанции", size=20, weight=ft.FontWeight.BOLD),
                ft.Divider(height=3),
                self.student_dropdown,
                ft.Divider(height=3),
                ft.Text("Основные данные:", size=14, weight=ft.FontWeight.BOLD),
                ft.Row([self.fio_field, self.contract_field], spacing=10),
                ft.Row([self.class_field, self.month_field, self.year_field], spacing=10),
                ft.Row([self.amount_field, self.compensation_field], spacing=10),
                ft.Divider(height=3),
                ft.Row([ft.Text("Предметы/Курсы:", size=14, weight=ft.FontWeight.BOLD), add_course_btn]),
                ft.Container(
                    content=ft.Column([self.courses_container], scroll=ft.ScrollMode.AUTO),
                    border=ft.border.all(1, ft.colors.GREY_300),
                    border_radius=8,
                    padding=10,
                    height=250,
                ),
                ft.Divider(height=3),
                generate_btn,
            ],
            spacing=6,
            scroll=ft.ScrollMode.AUTO,
        )
        return self._layout

    def _on_student_selected(self, e):
        """Обработчик выбора ученика"""
        student_id = self.student_dropdown.value

        if not student_id:
            return

        student = self.db.get_by_id(student_id)

        if student:
            # Заполнить основные поля
            self.fio_field.value = student.get('fio', '')
            self.contract_field.value = student.get('contract_number', '')
            self.compensation_field.value = student.get('compensation', '')

            # Класс
            self.current_class_id = student.get('class_id', '')
            class_info = self.classes_db.get_class_by_id(self.current_class_id)

            if class_info:
                self.class_field.value = class_info['name']

                # Проверить, это 11 класс с ЕГЭ?
                pricing = class_info.get('pricing', {})
                self.is_class_11 = (pricing.get('type') == 'per_subject')

                if self.is_class_11:
                    # Загрузить СОХРАНЁННЫЕ предметы ЕГЭ из базы
                    self.available_subjects = class_info.get('exam_subjects', [])
                    saved_exams = self.exam_db.get_student_exams(student_id)

                    if saved_exams:
                        self.courses_list = saved_exams
                    else:
                        # Если не сохранены - загрузить все
                        self.courses_list = self.available_subjects.copy()
                else:
                    # Обычный класс - все предметы
                    self.available_subjects = self.classes_db.get_subjects_by_class(self.current_class_id)
                    self.courses_list = self.available_subjects.copy()

                # Рассчитать стоимость
                if self.is_class_11:
                    monthly_payment = self.exam_db.calculate_exam_cost(self.courses_list, 3000)
                else:
                    monthly_payment = self.classes_db.calculate_price(self.current_class_id, self.courses_list)

                self.amount_field.value = str(int(monthly_payment))

                print(f"✅ Загружен ученик: {student.get('fio')}")
                print(f"   Класс: {class_info['name']} (11 класс: {self.is_class_11})")
                print(f"   Предметов: {len(self.courses_list)}")
                print(f"   Стоимость: {monthly_payment}₽")
            else:
                self.class_field.value = self.current_class_id
                self.available_subjects = []
                self.courses_list = []
                self.is_class_11 = False
                self.amount_field.value = str(student.get('monthly_payment', 0))

            self._update_courses_display()
            self.page.update()

    def _recalculate_price(self):
        """Пересчитать стоимость на основе выбранных предметов"""
        if not self.current_class_id:
            return

        if self.is_class_11:
            # Для 11 класса - по ЕГЭ
            monthly_payment = self.exam_db.calculate_exam_cost(self.courses_list, 3000)
        else:
            # Для остальных - стандартный расчёт
            monthly_payment = self.classes_db.calculate_price(self.current_class_id, self.courses_list)

        self.amount_field.value = str(int(monthly_payment))

        if self.is_class_11:
            print(f"   11 класс - предметов ЕГЭ: {len(self.courses_list)}, стоимость: {monthly_payment}₽")


    def _update_courses_display(self):
        """Обновить отображение списка курсов"""
        self.courses_container.controls.clear()

        if not self.courses_list:
            self.courses_container.controls.append(
                ft.Text("Нет предметов. Нажмите ➕", size=12, color=ft.colors.GREY_600, italic=True)
            )
        else:
            # Получить список предметов ЕГЭ
            exam_subjects = []
            if self.is_class_11 and self.current_class_id:
                class_info = self.classes_db.get_class_by_id(self.current_class_id)
                if class_info:
                    exam_subjects = class_info.get('exam_subjects', [])

            for course in self.courses_list:
                is_exam = course in exam_subjects
                icon = ft.icons.WORKSPACE_PREMIUM if is_exam else ft.icons.BOOK
                icon_color = ft.colors.ORANGE_700 if is_exam else ft.colors.BLUE_700
                exam_label = ft.Text(" 🎓", size=10, color=ft.colors.ORANGE_700) if is_exam else ft.Container()

                course_row = ft.Row([
                    ft.Icon(icon, size=16, color=icon_color),
                    ft.Text(course, size=13, expand=True),
                    exam_label,
                    ft.IconButton(
                        icon=ft.icons.DELETE,
                        icon_color=ft.colors.RED_700,
                        icon_size=18,
                        tooltip="Удалить",
                        on_click=lambda e, c=course: self._remove_course(c),
                    ),
                ], spacing=5)
                self.courses_container.controls.append(course_row)

            # Для 11 класса показать расчёт
            if self.is_class_11:
                total = len(self.courses_list) * 3000

                info_row = ft.Container(
                    content=ft.Text(
                        f"💰 ЕГЭ: {len(self.courses_list)} × 3 000₽ = {total:,}₽".replace(',', ' '),
                        size=12,
                        color=ft.colors.GREEN_700,
                        weight=ft.FontWeight.BOLD,
                    ),
                    padding=10,
                    bgcolor=ft.colors.GREEN_50,
                    border_radius=5,
                )
                self.courses_container.controls.append(info_row)

        self.page.update()

    def _remove_course(self, course):
        """Удалить предмет"""
        if course in self.courses_list:
            self.courses_list.remove(course)
            if self.is_class_11:
                self._recalculate_price()
            self._update_courses_display()

    def _add_course(self, e):
        """Добавить новый предмет"""

        if self.available_subjects:
            subject_dropdown = ft.Dropdown(
                label="Выберите предмет",
                options=[ft.dropdown.Option(text=s) for s in self.available_subjects],
                width=300,
            )
        else:
            subject_dropdown = None

        course_input = ft.TextField(label="Или введите название", width=300)

        def save_course(e):
            new_course = None
            if subject_dropdown and subject_dropdown.value:
                new_course = subject_dropdown.value
            elif course_input.value:
                new_course = course_input.value.strip()

            if new_course:
                if new_course not in self.courses_list:
                    self.courses_list.append(new_course)
                    if self.is_class_11:
                        self._recalculate_price()
                    self._update_courses_display()
                    add_dialog.open = False
                    self.page.update()
                else:
                    self.page.show_snack_bar(ft.SnackBar(content=ft.Text("⚠️ Уже добавлен"), bgcolor=ft.colors.ORANGE))
            else:
                self.page.show_snack_bar(ft.SnackBar(content=ft.Text("⚠️ Введите предмет"), bgcolor=ft.colors.ORANGE))

        dialog_controls = []
        if subject_dropdown:
            dialog_controls.append(subject_dropdown)
            dialog_controls.append(ft.Text("— или —", size=12, color=ft.colors.GREY_600))
        dialog_controls.append(course_input)

        add_dialog = ft.AlertDialog(
            title=ft.Text("Добавить предмет"),
            content=ft.Container(content=ft.Column(dialog_controls, spacing=10), width=350),
            actions=[
                ft.TextButton("Отмена", on_click=lambda e: self._close_dialog(add_dialog)),
                ft.ElevatedButton("Добавить", on_click=save_course, bgcolor=ft.colors.GREEN_700, color=ft.colors.WHITE),
            ],
        )

        self.page.dialog = add_dialog
        add_dialog.open = True
        self.page.update()

    def _generate_receipt(self, e):
        """Сгенерировать квитанцию"""

        if not self.fio_field.value:
            self.page.show_snack_bar(ft.SnackBar(content=ft.Text("⚠️ Заполните ФИО"), bgcolor=ft.colors.ORANGE))
            return

        if not self.contract_field.value:
            self.page.show_snack_bar(ft.SnackBar(content=ft.Text("⚠️ Заполните договор"), bgcolor=ft.colors.ORANGE))
            return

        if not self.courses_list:
            self.page.show_snack_bar(ft.SnackBar(content=ft.Text("⚠️ Добавьте предметы"), bgcolor=ft.colors.ORANGE))
            return

        if not self.amount_field.value:
            self.page.show_snack_bar(ft.SnackBar(content=ft.Text("⚠️ Укажите сумму"), bgcolor=ft.colors.ORANGE))
            return

        student_name = self.fio_field.value
        contract_number = self.contract_field.value
        month_year = f"{self.month_field.value}/{self.year_field.value}"
        amount = float(self.amount_field.value)
        compensation = self.compensation_field.value
        courses = self.courses_list

        fio_normalized = student_name.replace(' ', '_')
        default_filename = f"receipt_{fio_normalized}.pdf"

        def save_file_result(file_e: ft.FilePickerResultEvent):
            if file_e.path:
                try:
                    generate_receipt(
                        student_name=student_name,
                        courses=courses,
                        contract_number=contract_number,
                        month_year=month_year,
                        amount=amount,
                        compensation=compensation,
                        output_path=file_e.path
                    )

                    self.page.show_snack_bar(
                        ft.SnackBar(content=ft.Text(f"✅ Квитанция создана: {Path(file_e.path).name}"),
                                    bgcolor=ft.colors.GREEN, duration=5000)
                    )
                except Exception as ex:
                    self.page.show_snack_bar(
                        ft.SnackBar(content=ft.Text(f"❌ Ошибка: {str(ex)}"), bgcolor=ft.colors.RED, duration=10000)
                    )

        file_picker = ft.FilePicker(on_result=save_file_result)
        self.page.overlay.append(file_picker)
        self.page.update()

        file_picker.save_file(
            dialog_title="Сохранить квитанцию",
            file_name=default_filename,
            allowed_extensions=["pdf"],
        )

    def _close_dialog(self, dialog):
        """Закрыть диалог"""
        dialog.open = False
        self.page.update()
