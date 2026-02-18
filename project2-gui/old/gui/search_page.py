"""
Страница поиска учеников
"""
import flet as ft
from core.data.student_db import StudentDatabase
from core.data.classes_db import ClassesDatabase
from core.data.exam_choices_db import ExamChoicesDatabase
from core.receipt.generator import generate_receipt
from pathlib import Path
from datetime import datetime


class SearchPage:
    """Страница поиска учеников"""

    def __init__(self, page: ft.Page):
        self.page = page
        self.db = StudentDatabase()
        self.classes_db = ClassesDatabase()
        self.exam_db = ExamChoicesDatabase()
        self.search_field = None
        self.results_container = None

    def build(self) -> ft.Column:
        """Построить интерфейс страницы"""

        # Поля поиска
        self.search_field = ft.TextField(
            label="Поиск по ФИО",
            width=300,
            dense=True,
            on_submit=self._perform_search,
        )

        # Поле поиска по классу
        classes = self.classes_db.get_all_classes()
        class_options = [ft.dropdown.Option(key="", text="Все классы")]  # Опция "все"
        class_options.extend([
            ft.dropdown.Option(key=c['id'], text=c['name'])
            for c in classes
        ])

        self.class_filter = ft.Dropdown(
            label="Фильтр по классу",
            options=class_options,
            width=200,
            dense=True,
            value="",
        )

        # Поле поиска по договору
        self.contract_field = ft.TextField(
            label="Поиск по договору",
            width=200,
            dense=True,
            on_submit=self._perform_search,
        )

        # Кнопка поиска
        search_btn = ft.ElevatedButton(
            "🔍 Найти",
            on_click=self._perform_search,
            style=ft.ButtonStyle(
                bgcolor=ft.colors.BLUE_700,
                color=ft.colors.WHITE,
            ),
        )

        # Кнопка сброса
        reset_btn = ft.TextButton(
            "🔄 Сбросить",
            on_click=self._reset_search,
        )

        # Контейнер для результатов
        self.results_container = ft.Column(
            spacing=10,
            scroll=ft.ScrollMode.AUTO,
        )

        # Layout
        return ft.Column(
            controls=[
                ft.Text("🔍 Поиск по базе данных", size=20, weight=ft.FontWeight.BOLD),
                ft.Divider(height=3),

                # Панель поиска
                ft.Container(
                    content=ft.Column([
                        ft.Row([
                            self.search_field,
                            self.class_filter,
                            self.contract_field,
                        ], spacing=10, wrap=True),
                        ft.Row([
                            search_btn,
                            reset_btn,
                        ], spacing=10),
                    ], spacing=10),
                    padding=10,
                    bgcolor=ft.colors.BLUE_50,
                    border_radius=8,
                ),

                ft.Divider(height=3),
                ft.Container(
                    content=self.results_container,
                    expand=True,
                ),
            ],
            spacing=6,
            expand=True,
        )

    def _perform_search(self, e):
        """Выполнить поиск"""
        fio_query = self.search_field.value.strip() if self.search_field.value else ""
        class_filter = self.class_filter.value
        contract_query = self.contract_field.value.strip() if self.contract_field.value else ""

        # Проверка: хотя бы один фильтр заполнен
        if not fio_query and not class_filter and not contract_query:
            self.page.show_snack_bar(
                ft.SnackBar(
                    content=ft.Text("⚠️ Заполните хотя бы одно поле для поиска"),
                    bgcolor=ft.colors.ORANGE,
                )
            )
            return

        # Получить всех учеников
        all_students = self.db.get_all()

        # Фильтрация
        results = []

        for student in all_students:
            # Фильтр по ФИО
            if fio_query:
                if fio_query.lower() not in student.get('fio', '').lower():
                    continue

            # Фильтр по классу
            if class_filter:
                if student.get('class_id', '') != class_filter:
                    continue

            # Фильтр по договору
            if contract_query:
                if contract_query.lower() not in student.get('contract_number', '').lower():
                    continue

            # Если прошёл все фильтры - добавить
            results.append(student)

        # Очистить контейнер
        self.results_container.controls.clear()

        if not results:
            query_parts = []
            if fio_query:
                query_parts.append(f'ФИО: "{fio_query}"')
            if class_filter:
                class_info = self.classes_db.get_class_by_id(class_filter)
                class_name = class_info['name'] if class_info else class_filter
                query_parts.append(f'Класс: {class_name}')
            if contract_query:
                query_parts.append(f'Договор: "{contract_query}"')

            query_text = ", ".join(query_parts)

            self.results_container.controls.append(
                ft.Container(
                    content=ft.Column([
                        ft.Icon(ft.icons.SEARCH_OFF, size=64, color=ft.colors.GREY_400),
                        ft.Text("Ничего не найдено", size=16, color=ft.colors.GREY_600),
                        ft.Text(f"По запросу: {query_text}", size=12, color=ft.colors.GREY_500),
                    ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=10),
                    alignment=ft.alignment.center,
                    padding=50,
                )
            )
        else:
            # Заголовок результатов
            self.results_container.controls.append(
                ft.Text(
                    f"Найдено: {len(results)} ученик(ов)",
                    size=14,
                    weight=ft.FontWeight.BOLD,
                    color=ft.colors.GREEN_700,
                )
            )

            # Карточки результатов
            for student in results:
                card = self._create_student_card(student)
                self.results_container.controls.append(card)

        self.page.update()

    def _reset_search(self, e):
        """Сбросить поля поиска"""
        self.search_field.value = ""
        self.class_filter.value = ""
        self.contract_field.value = ""
        self.results_container.controls.clear()
        self.page.update()

    def _create_student_card(self, student):
        """Создать карточку ученика"""

        # Получить информацию о классе
        class_id = student.get('class_id', '')
        class_info = self.classes_db.get_class_by_id(class_id)
        class_name = class_info['name'] if class_info else class_id

        # Рассчитать стоимость из класса и предметов
        class_id = student.get('class_id', '')
        if class_id:
            class_info_check = self.classes_db.get_class_by_id(class_id)
            if class_info_check:
                pricing = class_info_check.get('pricing', {})
                is_exam_class = (pricing.get('type') == 'per_subject')

                if is_exam_class:
                    # Для 11 класса - загрузить ЕГЭ
                    subjects = self.exam_db.get_student_exams(student['id'])
                    if subjects:
                        monthly_payment = self.exam_db.calculate_exam_cost(subjects, 3000)
                    else:
                        monthly_payment = 0
                else:
                    # Обычный класс - все предметы
                    subjects = self.classes_db.get_subjects_by_class(class_id)
                    monthly_payment = self.classes_db.calculate_price(class_id, subjects)
            else:
                monthly_payment = 0
        else:
            monthly_payment = 0

        # Компенсация
        compensation = student.get('compensation', '')
        compensation_text = compensation if compensation else "Нет"

        # Кнопки действий
        info_btn = ft.ElevatedButton(
            "👁️ Просмотр",
            on_click=lambda e, s=student: self._show_student_info(s),
            style=ft.ButtonStyle(bgcolor=ft.colors.BLUE_700, color=ft.colors.WHITE),
        )

        receipt_btn = ft.ElevatedButton(
            "📄 Квитанция",
            on_click=lambda e, s=student: self._generate_receipt_for_student(s),
            style=ft.ButtonStyle(bgcolor=ft.colors.GREEN_700, color=ft.colors.WHITE),
        )

        # Карточка
        card = ft.Container(
            content=ft.Column([
                ft.Row([
                    ft.Icon(ft.icons.PERSON, size=40, color=ft.colors.BLUE_700),
                    ft.Column([
                        ft.Text(student.get('fio', 'N/A'), size=16, weight=ft.FontWeight.BOLD),
                        ft.Text(f"Класс: {class_name}", size=12, color=ft.colors.GREY_700),
                        ft.Text(f"Договор: {student.get('contract_number', 'N/A')}", size=12, color=ft.colors.GREY_700),
                        ft.Text(f"Оплата: {monthly_payment:,}₽".replace(',', ' '), size=12, color=ft.colors.GREEN_700),
                    ], spacing=3, expand=True),
                ]),
                ft.Divider(height=5),
                ft.Row([info_btn, receipt_btn], spacing=10),
            ], spacing=10),
            padding=15,
            border=ft.border.all(1, ft.colors.GREY_300),
            border_radius=10,
            bgcolor=ft.colors.WHITE,
        )

        return card

    def _show_student_info(self, student):
        """Показать подробную информацию об ученике"""

        # Получить класс
        class_id = student.get('class_id', '')
        class_info = self.classes_db.get_class_by_id(class_id)
        class_name = class_info['name'] if class_info else class_id

        # Получить предметы
        if class_info:
            pricing = class_info.get('pricing', {})
            is_exam_class = (pricing.get('type') == 'per_subject')

            if is_exam_class:
                # Для 11 класса - загрузить сохранённые ЕГЭ
                subjects = self.exam_db.get_student_exams(student['id'])
                if not subjects:
                    subjects = ["⚠️ Предметы ЕГЭ не выбраны"]
            else:
                # Обычный класс - все предметы
                subjects = self.classes_db.get_subjects_by_class(class_id)
        else:
            subjects = []

        subjects_text = "\n".join([f"• {s}" for s in subjects]) if subjects else "Не указаны"

        # Компенсация
        compensation = student.get('compensation', '')
        compensation_text = compensation if compensation else "Нет"

        # Оплата
        monthly_payment = student.get('monthly_payment', 0)

        # Диалог с информацией
        info_dialog = ft.AlertDialog(
            title=ft.Row([
                ft.Icon(ft.icons.INFO, color=ft.colors.BLUE_700),
                ft.Text(f"Информация об ученике"),
            ]),
            content=ft.Container(
                content=ft.Column([
                    ft.Text("📝 Основные данные:", size=13, weight=ft.FontWeight.BOLD),
                    ft.Divider(height=5),
                    ft.Text(f"ФИО: {student.get('fio', 'N/A')}", size=13),
                    ft.Text(f"ID: {student.get('id', 'N/A')}", size=13),
                    ft.Text(f"Договор: {student.get('contract_number', 'N/A')}", size=13),
                    ft.Text(f"Класс: {class_name}", size=13),

                    ft.Divider(height=10),
                    ft.Text("💰 Финансы:", size=13, weight=ft.FontWeight.BOLD),
                    ft.Divider(height=5),
                    ft.Text(f"Ежемесячная оплата: {monthly_payment:,}₽".replace(',', ' '), size=13),
                    ft.Text(f"Компенсация: {compensation_text}", size=13),

                    ft.Divider(height=10),
                    ft.Text("📚 Предметы:", size=13, weight=ft.FontWeight.BOLD),
                    ft.Divider(height=5),
                    ft.Text(subjects_text, size=12, color=ft.colors.GREY_700),
                ], spacing=5, scroll=ft.ScrollMode.AUTO),
                width=450,
                height=450,
            ),
            actions=[
                ft.TextButton("Закрыть", on_click=lambda e: self._close_dialog(info_dialog)),
            ],
        )

        self.page.dialog = info_dialog
        info_dialog.open = True
        self.page.update()

    def _generate_receipt_for_student(self, student):
        """Генерация квитанции для найденного ученика"""

        # Получить класс
        class_id = student.get('class_id', '')
        class_info = self.classes_db.get_class_by_id(class_id)

        if not class_info:
            self.page.show_snack_bar(
                ft.SnackBar(
                    content=ft.Text(f"⚠️ Класс {class_id} не найден"),
                    bgcolor=ft.colors.ORANGE,
                )
            )
            return

        # Получить предметы
        pricing = class_info.get('pricing', {})
        is_exam_class = (pricing.get('type') == 'per_subject')

        if is_exam_class:
            # Для 11 класса - загрузить сохранённые ЕГЭ
            courses = self.exam_db.get_student_exams(student['id'])
            if not courses:
                self.page.show_snack_bar(
                    ft.SnackBar(
                        content=ft.Text(f"⚠️ Для ученика 11 класса не выбраны предметы ЕГЭ"),
                        bgcolor=ft.colors.ORANGE,
                        duration=5000,
                    )
                )
                return
        else:
            # Обычный класс - все предметы
            courses = self.classes_db.get_subjects_by_class(class_id)

        if not courses:
            self.page.show_snack_bar(
                ft.SnackBar(
                    content=ft.Text(f"⚠️ Нет предметов для генерации квитанции"),
                    bgcolor=ft.colors.ORANGE,
                )
            )
            return

        # Данные для квитанции
        student_name = student.get('fio', '')
        contract_number = student.get('contract_number', '')
        # Рассчитать стоимость
        class_id_for_receipt = student.get('class_id', '')
        if class_id_for_receipt:
            class_info_receipt = self.classes_db.get_class_by_id(class_id_for_receipt)
            if class_info_receipt:
                pricing_receipt = class_info_receipt.get('pricing', {})
                is_exam_class_receipt = (pricing_receipt.get('type') == 'per_subject')

                if is_exam_class_receipt:
                    # Для 11 класса
                    subjects_receipt = self.exam_db.get_student_exams(student['id'])
                    if subjects_receipt:
                        monthly_payment = self.exam_db.calculate_exam_cost(subjects_receipt, 3000)
                    else:
                        monthly_payment = 0
                else:
                    # Обычный класс
                    subjects_receipt = self.classes_db.get_subjects_by_class(class_id_for_receipt)
                    monthly_payment = self.classes_db.calculate_price(class_id_for_receipt, subjects_receipt)
            else:
                monthly_payment = 0
        else:
            monthly_payment = 0
        compensation = student.get('compensation', '')

        # Текущий месяц и год
        months_ru = [
            "Январь", "Февраль", "Март", "Апрель", "Май", "Июнь",
            "Июль", "Август", "Сентябрь", "Октябрь", "Ноябрь", "Декабрь"
        ]
        current_month = months_ru[datetime.now().month - 1]
        current_year = str(datetime.now().year)
        month_year = f"{current_month}/{current_year}"

        # Имя файла
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
                        amount=monthly_payment,
                        compensation=compensation,
                        output_path=file_e.path
                    )

                    self.page.show_snack_bar(
                        ft.SnackBar(
                            content=ft.Text(f"✅ Квитанция создана: {Path(file_e.path).name}"),
                            bgcolor=ft.colors.GREEN,
                            duration=5000,
                        )
                    )
                except Exception as ex:
                    self.page.show_snack_bar(
                        ft.SnackBar(
                            content=ft.Text(f"❌ Ошибка: {str(ex)}"),
                            bgcolor=ft.colors.RED,
                            duration=10000,
                        )
                    )

        # Диалог выбора места сохранения
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
