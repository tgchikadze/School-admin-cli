"""
Страница поиска учеников (SearchPage).

Функциональность модуля:
- Поиск учеников по трём независимым фильтрам: ФИО (подстрока),
  класс (Dropdown) и номер договора (подстрока).
- Отображение карточек найденных учеников с расчётом стоимости обучения.
- Просмотр подробной информации об ученике в диалоге.
- Быстрая генерация PDF-квитанции для найденного ученика прямо со страницы.
- Поддержка специального режима 11 класса (ЕГЭ, расчёт по предметам).
"""

from datetime import datetime
from pathlib import Path

import flet as ft

from core.data.student_db import StudentDatabase
from core.data.classes_db import ClassesDatabase
from core.data.exam_choices_db import ExamChoicesDatabase
from core.receipt.generator import generate_receipt


class SearchPage:
    """
    Страница поиска учеников по базе данных.

    Атрибуты:
        page (ft.Page): Корневая страница Flet-приложения.
        db (StudentDatabase): База данных учеников.
        classes_db (ClassesDatabase): База данных классов.
        exam_db (ExamChoicesDatabase): База данных выборов ЕГЭ.

    Атрибуты интерфейса (инициализируются None до вызова build()):
        search_field (ft.TextField | None): Поле поиска по ФИО.
        class_filter (ft.Dropdown | None): Фильтр по классу.
        contract_field (ft.TextField | None): Поле поиска по номеру договора.
        results_container (ft.Column | None): Контейнер для карточек.
    """

    def __init__(self, page: ft.Page) -> None:
        """
        Инициализация страницы поиска.

        Параметры:
            page (ft.Page): Корневая страница Flet, в которую добавляются
                все элементы интерфейса и диалоги.
        """
        self.page: ft.Page = page
        self.db: StudentDatabase = StudentDatabase()
        self.classes_db: ClassesDatabase = ClassesDatabase()
        self.exam_db: ExamChoicesDatabase = ExamChoicesDatabase()

        # Элементы интерфейса (создаются в build())
        self.search_field: ft.TextField | None = None
        self.class_filter: ft.Dropdown | None = None
        self.contract_field: ft.TextField | None = None
        self.results_container: ft.Column | None = None

    # ====================
    # Построение интерфейса
    # ====================

    def build(self) -> ft.Column:
        """
        Построить и вернуть интерфейс страницы поиска.

        Возвращает:
            ft.Column: Корневая колонка страницы с панелью поиска
                и контейнером результатов.
        """
        # ================================
        # Поля фильтрации
        # ================================
        self.search_field = ft.TextField(
            label="Поиск по ФИО",
            width=300,
            dense=True,
            on_submit=self._perform_search,
        )

        # Фильтр по классу с опцией «Все классы»
        classes = self.classes_db.get_all_classes()
        class_options: list[ft.dropdown.Option] = [
            ft.dropdown.Option(key="", text="Все классы"),
        ]
        class_options.extend(
            [
                ft.dropdown.Option(key=c["id"], text=c["name"])
                for c in classes
            ],
        )

        self.class_filter = ft.Dropdown(
            label="Фильтр по классу",
            options=class_options,
            width=200,
            dense=True,
            value="",
        )

        self.contract_field = ft.TextField(
            label="Поиск по договору",
            width=200,
            dense=True,
            on_submit=self._perform_search,
        )

        # ================================
        # Кнопки управления
        # ================================
        search_btn = ft.ElevatedButton(
            "🔍 Найти",
            on_click=self._perform_search,
            style=ft.ButtonStyle(
                bgcolor=ft.colors.BLUE_700,
                color=ft.colors.WHITE,
            ),
        )
        reset_btn = ft.TextButton(
            "🔄 Сбросить",
            on_click=self._reset_search,
        )

        # ================================
        # Контейнер результатов
        # ================================
        self.results_container = ft.Column(
            spacing=10,
            scroll=ft.ScrollMode.AUTO,
        )

        # ================================
        # Основной макет
        # ================================
        return ft.Column(
            controls=[
                ft.Text(
                    "🔍 Поиск по базе данных",
                    size=20,
                    weight=ft.FontWeight.BOLD,
                ),
                ft.Divider(height=3),
                # Панель фильтров
                ft.Container(
                    content=ft.Column(
                        [
                            ft.Row(
                                [
                                    self.search_field,
                                    self.class_filter,
                                    self.contract_field,
                                ],
                                spacing=10,
                                wrap=True,
                            ),
                            ft.Row([search_btn, reset_btn], spacing=10),
                        ],
                        spacing=10,
                    ),
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

    # ============================
    # Поиск и сброс
    # ============================

    def _perform_search(self, e: ft.ControlEvent) -> None:
        """
        Выполнить поиск по заполненным фильтрам и отобразить результаты.

        Параметры:
            e (ft.ControlEvent): Событие нажатия кнопки «Найти»
                или нажатия Enter в текстовом поле.

        Логика:
            - Требует заполнения хотя бы одного фильтра.
            - Применяет фильтры последовательно: ФИО (подстрока, без учёта
              регистра), класс (точное совпадение class_id), договор
              (подстрока, без учёта регистра).
            - При пустом результате — показывает заглушку с описанием запроса.
            - При наличии результатов — строит карточки через
              _create_student_card.

        Примечание:
            Фильтр по классу игнорируется при значении "" или "Все классы"
            (аналогично batch_receipts_page.py).
        """
        fio_query = (
            self.search_field.value.strip()
            if self.search_field.value
            else ""
        )
        class_filter = self.class_filter.value
        contract_query = (
            self.contract_field.value.strip()
            if self.contract_field.value
            else ""
        )

        # Требуется хотя бы один заполненный фильтр
        if not fio_query and not class_filter and not contract_query:
            self.page.show_snack_bar(
                ft.SnackBar(
                    content=ft.Text(
                        "⚠️ Заполните хотя бы одно поле для поиска",
                    ),
                    bgcolor=ft.colors.ORANGE,
                ),
            )
            return

        all_students = self.db.get_all()

        # Последовательная фильтрация
        results: list[dict] = []
        for student in all_students:
            # Фильтр по ФИО (подстрока, case-insensitive)
            if fio_query:
                if fio_query.lower() not in student.get("fio", "").lower():
                    continue

            # Фильтр по классу (точное совпадение; "" и "Все классы" — пропуск)
            if class_filter and class_filter != "Все классы":
                if student.get("class_id", "") != class_filter:
                    continue

            # Фильтр по договору (подстрока, case-insensitive)
            if contract_query:
                if contract_query.lower() not in student.get(
                    "contract_number", ""
                ).lower():
                    continue

            results.append(student)

        # Отобразить результаты
        self.results_container.controls.clear()

        if not results:
            # Собрать текст запроса для заглушки
            query_parts: list[str] = []
            if fio_query:
                query_parts.append(f'ФИО: "{fio_query}"')
            if class_filter and class_filter != "Все классы":
                class_info = self.classes_db.get_class_by_id(class_filter)
                class_name = (
                    class_info["name"] if class_info else class_filter
                )
                query_parts.append(f"Класс: {class_name}")
            if contract_query:
                query_parts.append(f'Договор: "{contract_query}"')

            query_text = ", ".join(query_parts)
            self.results_container.controls.append(
                ft.Container(
                    content=ft.Column(
                        [
                            ft.Icon(
                                ft.icons.SEARCH_OFF,
                                size=64,
                                color=ft.colors.GREY_400,
                            ),
                            ft.Text(
                                "Ничего не найдено",
                                size=16,
                                color=ft.colors.GREY_600,
                            ),
                            ft.Text(
                                f"По запросу: {query_text}",
                                size=12,
                                color=ft.colors.GREY_500,
                            ),
                        ],
                        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                        spacing=10,
                    ),
                    alignment=ft.alignment.center,
                    padding=50,
                ),
            )
        else:
            # Заголовок со счётчиком
            self.results_container.controls.append(
                ft.Text(
                    f"Найдено: {len(results)} ученик(ов)",
                    size=14,
                    weight=ft.FontWeight.BOLD,
                    color=ft.colors.GREEN_700,
                ),
            )
            # Карточки найденных учеников
            for student in results:
                card = self._create_student_card(student)
                self.results_container.controls.append(card)

        self.page.update()

    def _reset_search(self, e: ft.ControlEvent) -> None:
        """
        Сбросить все поля поиска и очистить результаты.

        Параметры:
            e (ft.ControlEvent): Событие нажатия кнопки «Сбросить».
        """
        self.search_field.value = ""
        self.class_filter.value = ""
        self.contract_field.value = ""
        self.results_container.controls.clear()
        self.page.update()

    # ============================
    # Карточка ученика
    # ============================

    def _create_student_card(self, student: dict) -> ft.Container:
        """
        Создать карточку ученика для отображения в результатах поиска.

        Параметры:
            student (dict): Словарь с данными ученика из StudentDatabase.

        Возвращает:
            ft.Container: Карточка с ФИО, классом, договором, суммой и
                кнопками «Просмотр» и «Квитанция».

        Логика расчёта стоимости:
            - Для 11 класса (per_subject): exam_db.calculate_exam_cost.
            - Для обычного класса: classes_db.calculate_price.
            - При отсутствии данных класса: 0.
        """
        class_id = student.get("class_id", "")

        # Название класса
        class_info = self.classes_db.get_class_by_id(class_id)
        class_name = class_info["name"] if class_info else class_id

        # Расчёт стоимости
        monthly_payment: float = 0
        if class_id:
            class_info_check = self.classes_db.get_class_by_id(class_id)
            if class_info_check:
                pricing = class_info_check.get("pricing", {})
                is_exam_class = pricing.get("type") == "per_subject"

                if is_exam_class:
                    subjects = self.exam_db.get_student_exams(student["id"])
                    if subjects:
                        monthly_payment = self.exam_db.calculate_exam_cost(
                            subjects,
                            3000,
                        )
                else:
                    subjects = self.classes_db.get_subjects_by_class(class_id)
                    monthly_payment = self.classes_db.calculate_price(
                        class_id,
                        subjects,
                    )

        # Кнопки действий
        info_btn = ft.ElevatedButton(
            "👁️ Просмотр",
            on_click=lambda ev, s=student: self._show_student_info(s),
            style=ft.ButtonStyle(
                bgcolor=ft.colors.BLUE_700,
                color=ft.colors.WHITE,
            ),
        )
        receipt_btn = ft.ElevatedButton(
            "📄 Квитанция",
            on_click=lambda ev, s=student: (
                self._generate_receipt_for_student(s)
            ),
            style=ft.ButtonStyle(
                bgcolor=ft.colors.GREEN_700,
                color=ft.colors.WHITE,
            ),
        )

        return ft.Container(
            content=ft.Column(
                [
                    ft.Row(
                        [
                            ft.Icon(
                                ft.icons.PERSON,
                                size=40,
                                color=ft.colors.BLUE_700,
                            ),
                            ft.Column(
                                [
                                    ft.Text(
                                        student.get("fio", "N/A"),
                                        size=16,
                                        weight=ft.FontWeight.BOLD,
                                    ),
                                    ft.Text(
                                        f"Класс: {class_name}",
                                        size=12,
                                        color=ft.colors.GREY_700,
                                    ),
                                    ft.Text(
                                        f"Договор: "
                                        f"{student.get('contract_number', 'N/A')}",
                                        size=12,
                                        color=ft.colors.GREY_700,
                                    ),
                                    ft.Text(
                                        (
                                            f"Оплата: {monthly_payment:,}₽"
                                        ).replace(",", " "),
                                        size=12,
                                        color=ft.colors.GREEN_700,
                                    ),
                                ],
                                spacing=3,
                                expand=True,
                            ),
                        ],
                    ),
                    ft.Divider(height=5),
                    ft.Row([info_btn, receipt_btn], spacing=10),
                ],
                spacing=10,
            ),
            padding=15,
            border=ft.border.all(1, ft.colors.GREY_300),
            border_radius=10,
            bgcolor=ft.colors.WHITE,
        )

    # ============================
    # Просмотр данных ученика
    # ============================

    def _show_student_info(self, student: dict) -> None:
        """
        Показать диалог с подробной информацией об ученике.

        Параметры:
            student (dict): Словарь с данными ученика из StudentDatabase.

        Отображает:
            - ФИО, ID, номер договора, класс.
            - Ежемесячную оплату и компенсацию.
            - Список предметов (с пометкой для 11 класса, если ЕГЭ не выбраны).
        """
        class_id = student.get("class_id", "")
        class_info = self.classes_db.get_class_by_id(class_id)
        class_name = class_info["name"] if class_info else class_id

        # Предметы в зависимости от типа класса
        subjects: list[str] = []
        if class_info:
            pricing = class_info.get("pricing", {})
            is_exam_class = pricing.get("type") == "per_subject"

            if is_exam_class:
                subjects = self.exam_db.get_student_exams(student["id"])
                if not subjects:
                    subjects = ["⚠️ Предметы ЕГЭ не выбраны"]
            else:
                subjects = self.classes_db.get_subjects_by_class(class_id)

        subjects_text = (
            "\n".join([f"• {s}" for s in subjects])
            if subjects
            else "Не указаны"
        )

        compensation = student.get("compensation", "")
        compensation_text = compensation if compensation else "Нет"
        monthly_payment = student.get("monthly_payment", 0)

        info_dialog = ft.AlertDialog(
            title=ft.Row(
                [
                    ft.Icon(ft.icons.INFO, color=ft.colors.BLUE_700),
                    ft.Text("Информация об ученике"),
                ],
            ),
            content=ft.Container(
                content=ft.Column(
                    [
                        ft.Text(
                            "📝 Основные данные:",
                            size=13,
                            weight=ft.FontWeight.BOLD,
                        ),
                        ft.Divider(height=5),
                        ft.Text(
                            f"ФИО: {student.get('fio', 'N/A')}",
                            size=13,
                        ),
                        ft.Text(
                            f"ID: {student.get('id', 'N/A')}",
                            size=13,
                        ),
                        ft.Text(
                            f"Договор: "
                            f"{student.get('contract_number', 'N/A')}",
                            size=13,
                        ),
                        ft.Text(f"Класс: {class_name}", size=13),
                        ft.Divider(height=10),
                        ft.Text(
                            "💰 Финансы:",
                            size=13,
                            weight=ft.FontWeight.BOLD,
                        ),
                        ft.Divider(height=5),
                        ft.Text(
                            (
                                f"Ежемесячная оплата: "
                                f"{monthly_payment:,}₽"
                            ).replace(",", " "),
                            size=13,
                        ),
                        ft.Text(
                            f"Компенсация: {compensation_text}",
                            size=13,
                        ),
                        ft.Divider(height=10),
                        ft.Text(
                            "📚 Предметы:",
                            size=13,
                            weight=ft.FontWeight.BOLD,
                        ),
                        ft.Divider(height=5),
                        ft.Text(
                            subjects_text,
                            size=12,
                            color=ft.colors.GREY_700,
                        ),
                    ],
                    spacing=5,
                    scroll=ft.ScrollMode.AUTO,
                ),
                width=450,
                height=450,
            ),
            actions=[
                ft.TextButton(
                    "Закрыть",
                    on_click=lambda e: self._close_dialog(info_dialog),
                ),
            ],
        )

        self.page.dialog = info_dialog
        info_dialog.open = True
        self.page.update()

    # ================================
    # Генерация квитанции из поиска
    # ================================

    def _generate_receipt_for_student(self, student: dict) -> None:
        """
        Сгенерировать PDF-квитанцию для ученика прямо из результатов поиска.

        Параметры:
            student (dict): Словарь с данными ученика из StudentDatabase.

        Логика:
            - Определяет тип класса (обычный / ЕГЭ) и загружает предметы.
            - Для 11 класса: проверяет, что предметы ЕГЭ сохранены.
            - Рассчитывает стоимость по типу класса.
            - Подставляет текущий месяц и год автоматически.
            - Открывает FilePicker для выбора пути сохранения.
            - В колбэке вызывает generate_receipt и показывает результат.
        """
        class_id = student.get("class_id", "")
        class_info = self.classes_db.get_class_by_id(class_id)

        if not class_info:
            self.page.show_snack_bar(
                ft.SnackBar(
                    content=ft.Text(f"⚠️ Класс {class_id} не найден"),
                    bgcolor=ft.colors.ORANGE,
                ),
            )
            return

        # Определить предметы по типу класса
        pricing = class_info.get("pricing", {})
        is_exam_class = pricing.get("type") == "per_subject"

        if is_exam_class:
            courses = self.exam_db.get_student_exams(student["id"])
            if not courses:
                self.page.show_snack_bar(
                    ft.SnackBar(
                        content=ft.Text(
                            "⚠️ Для ученика 11 класса "
                            "не выбраны предметы ЕГЭ",
                        ),
                        bgcolor=ft.colors.ORANGE,
                        duration=5000,
                    ),
                )
                return
        else:
            courses = self.classes_db.get_subjects_by_class(class_id)
            if not courses:
                self.page.show_snack_bar(
                    ft.SnackBar(
                        content=ft.Text(
                            "⚠️ Нет предметов для генерации квитанции",
                        ),
                        bgcolor=ft.colors.ORANGE,
                    ),
                )
                return

        # Данные ученика
        student_name: str = student.get("fio", "")
        contract_number: str = student.get("contract_number", "")
        compensation: str = student.get("compensation", "")

        # Расчёт стоимости
        monthly_payment: float = 0
        if class_id:
            class_info_receipt = self.classes_db.get_class_by_id(class_id)
            if class_info_receipt:
                pricing_receipt = class_info_receipt.get("pricing", {})
                is_exam = pricing_receipt.get("type") == "per_subject"

                if is_exam:
                    subjects_receipt = self.exam_db.get_student_exams(
                        student["id"],
                    )
                    if subjects_receipt:
                        monthly_payment = self.exam_db.calculate_exam_cost(
                            subjects_receipt,
                            3000,
                        )
                else:
                    subjects_receipt = self.classes_db.get_subjects_by_class(
                        class_id,
                    )
                    monthly_payment = self.classes_db.calculate_price(
                        class_id,
                        subjects_receipt,
                    )

        # Текущий месяц и год
        months_ru = [
            "Январь", "Февраль", "Март", "Апрель", "Май", "Июнь",
            "Июль", "Август", "Сентябрь", "Октябрь", "Ноябрь", "Декабрь",
        ]
        current_month = months_ru[datetime.now().month - 1]
        current_year = str(datetime.now().year)
        month_year = f"{current_month}/{current_year}"

        # Имя файла по умолчанию
        fio_normalized = student_name.replace(" ", "_")
        default_filename = f"receipt_{fio_normalized}.pdf"

        def save_file_result(file_e: ft.FilePickerResultEvent) -> None:
            """
            Колбэк FilePicker: сохранить квитанцию по выбранному пути.

            Параметры:
                file_e (ft.FilePickerResultEvent): Результат диалога
                    сохранения; содержит file_e.path с выбранным путём.
            """
            if not file_e.path:
                return

            try:
                generate_receipt(
                    student_name=student_name,
                    courses=courses,
                    contract_number=contract_number,
                    month_year=month_year,
                    amount=monthly_payment,
                    compensation=compensation,
                    output_path=file_e.path,
                )
                self.page.show_snack_bar(
                    ft.SnackBar(
                        content=ft.Text(
                            f"✅ Квитанция создана: "
                            f"{Path(file_e.path).name}",
                        ),
                        bgcolor=ft.colors.GREEN,
                        duration=5000,
                    ),
                )
            except Exception as ex:  # noqa: BLE001
                self.page.show_snack_bar(
                    ft.SnackBar(
                        content=ft.Text(f"❌ Ошибка: {str(ex)}"),
                        bgcolor=ft.colors.RED,
                        duration=10000,
                    ),
                )

        file_picker = ft.FilePicker(on_result=save_file_result)
        self.page.overlay.append(file_picker)
        self.page.update()

        file_picker.save_file(
            dialog_title="Сохранить квитанцию",
            file_name=default_filename,
            allowed_extensions=["pdf"],
        )

    # ==============
    # Служебные
    # ==============

    def _close_dialog(self, dialog: ft.AlertDialog) -> None:
        """
        Закрыть диалоговое окно и обновить страницу.

        Параметры:
            dialog (ft.AlertDialog): Диалог, у которого нужно
                сбросить флаг open в False.
        """
        dialog.open = False
        self.page.update()
