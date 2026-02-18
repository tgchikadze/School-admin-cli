"""
Страница генерации одиночной квитанции (ReceiptsPage).

Функциональность модуля:
- Выбор ученика из базы данных через выпадающий список.
- Автозаполнение полей формы: ФИО, договор, класс, стоимость, компенсация.
- Управление списком предметов/курсов (добавление, удаление).
- Поддержка специального режима 11 класса (ЕГЭ): расчёт стоимости
  по количеству выбранных предметов.
- Генерация PDF-квитанции с сохранением в выбранный путь через FilePicker.
"""

from datetime import datetime
from pathlib import Path
import platform
import os

import flet as ft

from core.data.student_db import StudentDatabase
from core.data.classes_db import ClassesDatabase
from core.data.exam_choices_db import ExamChoicesDatabase
from core.receipt.generator import generate_receipt


class ReceiptsPage:
    """
    Страница создания одиночной квитанции.

    Атрибуты:
        page (ft.Page): Корневая страница Flet-приложения.
        db (StudentDatabase): База данных учеников.
        classes_db (ClassesDatabase): База данных классов.
        exam_db (ExamChoicesDatabase): База данных выборов ЕГЭ.

    Атрибуты формы (инициализируются None до вызова build()):
        student_dropdown (ft.Dropdown | None): Выпадающий список учеников.
        fio_field (ft.TextField | None): Поле ФИО ученика.
        contract_field (ft.TextField | None): Поле номера договора.
        class_field (ft.TextField | None): Поле названия класса (read-only).
        month_field (ft.TextField | None): Поле месяца квитанции.
        year_field (ft.TextField | None): Поле года квитанции.
        amount_field (ft.TextField | None): Поле суммы к оплате.
        compensation_field (ft.TextField | None): Поле компенсации.
        courses_container (ft.Column | None): Колонка со списком предметов.

    Атрибуты состояния:
        courses_list (list[str]): Список текущих предметов/курсов.
        current_class_id (str | None): ID класса выбранного ученика.
        available_subjects (list[str]): Все доступные предметы класса.
        is_class_11 (bool): Флаг режима 11 класса (ЕГЭ, оплата за предмет).
        _layout (ft.Column | None): Кэш построенного layout.
    """

    def __init__(self, page: ft.Page) -> None:
        """
        Инициализация страницы квитанций.

        Параметры:
            page (ft.Page): Корневая страница Flet, в которую добавляются
                все элементы интерфейса и диалоги.
        """
        self.page: ft.Page = page
        self.db: StudentDatabase = StudentDatabase()
        self.classes_db: ClassesDatabase = ClassesDatabase()
        self.exam_db: ExamChoicesDatabase = ExamChoicesDatabase()

        # Поля формы (создаются в build())
        self.student_dropdown: ft.Dropdown | None = None
        self.fio_field: ft.TextField | None = None
        self.contract_field: ft.TextField | None = None
        self.class_field: ft.TextField | None = None
        self.month_field: ft.TextField | None = None
        self.year_field: ft.TextField | None = None
        self.amount_field: ft.TextField | None = None
        self.compensation_field: ft.TextField | None = None
        self.courses_container: ft.Column | None = None

        # Состояние страницы
        self.courses_list: list[str] = []
        self.current_class_id: str | None = None
        self.available_subjects: list[str] = []
        self.is_class_11: bool = False
        self._layout: ft.Column | None = None

    # ====================
    # Построение интерфейса
    # ====================

    def build(self) -> ft.Column:
        """
        Построить и вернуть интерфейс страницы.

        Кэширует результат в self._layout: повторный вызов build()
        вернёт уже созданный layout без пересборки.

        Возвращает:
            ft.Column: Корневая колонка страницы с формой квитанции.
        """
        # Вернуть кэшированный layout при повторном вызове
        if hasattr(self, "_layout") and self._layout is not None:
            return self._layout

        # ===================
        # Список учеников
        # ===================
        students = self.db.get_all()
        student_options = [
            ft.dropdown.Option(key=str(s["id"]), text=s["fio"])
            for s in students
        ]

        self.student_dropdown = ft.Dropdown(
            label="Выберите ученика",
            options=student_options,
            width=400,
            on_change=self._on_student_selected,
        )

        # ===================
        # Поля формы
        # ===================
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
        # Класс — только для чтения, заполняется автоматически
        self.class_field = ft.TextField(
            label="Класс",
            width=150,
            dense=True,
            read_only=True,
            bgcolor=ft.colors.GREY_100,
        )

        # ==========================
        # Месяц и год (текущие)
        # ==========================
        months_ru = [
            "Январь", "Февраль", "Март", "Апрель", "Май", "Июнь",
            "Июль", "Август", "Сентябрь", "Октябрь", "Ноябрь", "Декабрь",
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

        # ==========================
        # Контейнер списка предметов
        # ==========================
        self.courses_container = ft.Column(spacing=5)

        add_course_btn = ft.IconButton(
            icon=ft.icons.ADD_CIRCLE,
            icon_color=ft.colors.GREEN_700,
            icon_size=30,
            tooltip="Добавить предмет",
            on_click=self._add_course,
        )

        # ==================
        # Кнопка генерации
        # ==================
        generate_btn = ft.ElevatedButton(
            "📥 Сгенерировать квитанцию",
            on_click=self._generate_receipt,
            style=ft.ButtonStyle(
                bgcolor=ft.colors.GREEN_700,
                color=ft.colors.WHITE,
            ),
        )

        # ================
        # Основной макет
        # ================
        self._layout = ft.Column(
            controls=[
                ft.Text(
                    "📄 Создание квитанции",
                    size=20,
                    weight=ft.FontWeight.BOLD,
                ),
                ft.Divider(height=3),
                self.student_dropdown,
                ft.Divider(height=3),
                ft.Text(
                    "Основные данные:",
                    size=14,
                    weight=ft.FontWeight.BOLD,
                ),
                ft.Row([self.fio_field, self.contract_field], spacing=10),
                ft.Row(
                    [self.class_field, self.month_field, self.year_field],
                    spacing=10,
                ),
                ft.Row(
                    [self.amount_field, self.compensation_field],
                    spacing=10,
                ),
                ft.Divider(height=3),
                ft.Row(
                    [
                        ft.Text(
                            "Предметы/Курсы:",
                            size=14,
                            weight=ft.FontWeight.BOLD,
                        ),
                        add_course_btn,
                    ],
                ),
                ft.Container(
                    content=ft.Column(
                        [self.courses_container],
                        scroll=ft.ScrollMode.AUTO,
                    ),
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

    # ==========================
    # Выбор ученика из списка
    # ==========================

    def _on_student_selected(self, e: ft.ControlEvent) -> None:
        """
        Обработчик выбора ученика из выпадающего списка.

        Параметры:
            e (ft.ControlEvent): Событие изменения Dropdown.

        Логика:
            - Загружает данные выбранного ученика из БД.
            - Заполняет поля формы (ФИО, договор, класс, компенсация).
            - Для 11 класса (per_subject) загружает сохранённые предметы ЕГЭ;
              для остальных — список предметов класса.
            - Рассчитывает стоимость и подставляет в amount_field.
            - Обновляет отображение списка предметов.
        """
        student_id = self.student_dropdown.value
        if not student_id:
            return

        student = self.db.get_by_id(student_id)
        if not student:
            return

        # Заполнить основные поля данными ученика
        self.fio_field.value = student.get("fio", "")
        self.contract_field.value = student.get("contract_number", "")
        self.compensation_field.value = student.get("compensation", "")

        # Определить класс и его тип ценообразования
        self.current_class_id = student.get("class_id", "")
        class_info = self.classes_db.get_class_by_id(self.current_class_id)

        if class_info:
            self.class_field.value = class_info["name"]
            pricing = class_info.get("pricing", {})
            self.is_class_11 = pricing.get("type") == "per_subject"

            if self.is_class_11:
                # 11 класс: загрузить предметы ЕГЭ (сохранённые или все)
                self.available_subjects = class_info.get("exam_subjects", [])
                saved_exams = self.exam_db.get_student_exams(student_id)
                self.courses_list = (
                    saved_exams
                    if saved_exams
                    else self.available_subjects.copy()
                )
            else:
                # Обычный класс: все предметы класса
                self.available_subjects = (
                    self.classes_db.get_subjects_by_class(
                        self.current_class_id,
                    )
                )
                self.courses_list = self.available_subjects.copy()

            # Рассчитать стоимость по типу класса
            if self.is_class_11:
                monthly_payment = self.exam_db.calculate_exam_cost(
                    self.courses_list,
                    3000,
                )
            else:
                monthly_payment = self.classes_db.calculate_price(
                    self.current_class_id,
                    self.courses_list,
                )

            self.amount_field.value = str(int(monthly_payment))
        else:
            # Класс не найден — сбросить значения
            self.class_field.value = self.current_class_id
            self.available_subjects = []
            self.courses_list = []
            self.is_class_11 = False
            self.amount_field.value = str(student.get("monthly_payment", 0))

        self._update_courses_display()
        self.page.update()

    # ====================
    # Работа с предметами
    # ====================

    def _recalculate_price(self) -> None:
        """
        Пересчитать стоимость обучения по текущему списку предметов.

        Обновляет значение self.amount_field.value.
        Вызывается при добавлении или удалении предмета из courses_list.

        Логика:
            - Если current_class_id не задан — выходит без действий.
            - Для 11 класса считает стоимость через exam_db.calculate_exam_cost.
            - Для остальных классов — через classes_db.calculate_price.
        """
        if not self.current_class_id:
            return

        if self.is_class_11:
            monthly_payment = self.exam_db.calculate_exam_cost(
                self.courses_list,
                3000,
            )
        else:
            monthly_payment = self.classes_db.calculate_price(
                self.current_class_id,
                self.courses_list,
            )

        self.amount_field.value = str(int(monthly_payment))

    def _update_courses_display(self) -> None:
        """
        Обновить отображение списка предметов в courses_container.

        Логика:
            - Очищает courses_container.
            - Если список пуст — показывает подсказку.
            - Для каждого предмета создаёт строку с иконкой (ЕГЭ или обычный),
              названием и кнопкой удаления.
            - Для 11 класса добавляет строку с итоговым расчётом.
            - Обновляет страницу через page.update().
        """
        self.courses_container.controls.clear()

        if not self.courses_list:
            self.courses_container.controls.append(
                ft.Text(
                    "Нет предметов. Нажмите ➕",
                    size=12,
                    color=ft.colors.GREY_600,
                    italic=True,
                ),
            )
        else:
            # Получить список предметов ЕГЭ для отличия иконок
            exam_subjects: list[str] = []
            if self.is_class_11 and self.current_class_id:
                class_info = self.classes_db.get_class_by_id(
                    self.current_class_id,
                )
                if class_info:
                    exam_subjects = class_info.get("exam_subjects", [])

            for course in self.courses_list:
                is_exam = course in exam_subjects

                icon = (
                    ft.icons.WORKSPACE_PREMIUM
                    if is_exam
                    else ft.icons.BOOK
                )
                icon_color = (
                    ft.colors.ORANGE_700
                    if is_exam
                    else ft.colors.BLUE_700
                )
                exam_label = (
                    ft.Text(" 🎓", size=10, color=ft.colors.ORANGE_700)
                    if is_exam
                    else ft.Container()
                )

                course_row = ft.Row(
                    [
                        ft.Icon(icon, size=16, color=icon_color),
                        ft.Text(course, size=13, expand=True),
                        exam_label,
                        ft.IconButton(
                            icon=ft.icons.DELETE,
                            icon_color=ft.colors.RED_700,
                            icon_size=18,
                            tooltip="Удалить",
                            on_click=lambda ev, c=course: self._remove_course(
                                c,
                            ),
                        ),
                    ],
                    spacing=5,
                )
                self.courses_container.controls.append(course_row)

            # Итоговая строка расчёта для 11 класса
            if self.is_class_11:
                total = len(self.courses_list) * 3000
                info_row = ft.Container(
                    content=ft.Text(
                        (
                            f"💰 ЕГЭ: {len(self.courses_list)} × 3 000₽ "
                            f"= {total:,}₽"
                        ).replace(",", " "),
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

    def _remove_course(self, course: str) -> None:
        """
        Удалить предмет из списка и обновить форму.

        Параметры:
            course (str): Название предмета для удаления из courses_list.
        """
        if course in self.courses_list:
            self.courses_list.remove(course)
            if self.is_class_11:
                self._recalculate_price()
            self._update_courses_display()

    def _add_course(self, e: ft.ControlEvent) -> None:
        """
        Показать диалог добавления предмета в список.

        Параметры:
            e (ft.ControlEvent): Событие нажатия на кнопку «➕».

        Логика:
            - Если available_subjects не пуст — предлагает выбрать из списка.
            - Всегда отображает поле для ручного ввода названия.
            - При добавлении уже существующего предмета — показывает SnackBar.
            - После добавления пересчитывает цену (для 11 класса) и обновляет
              отображение предметов.
        """
        # Dropdown выбора из доступных предметов (только если они есть)
        subject_dropdown: ft.Dropdown | None = None
        if self.available_subjects:
            subject_dropdown = ft.Dropdown(
                label="Выберите предмет",
                options=[
                    ft.dropdown.Option(text=s) for s in self.available_subjects
                ],
                width=300,
            )

        course_input = ft.TextField(label="Или введите название", width=300)

        def save_course(event: ft.ControlEvent) -> None:
            """
            Обработчик сохранения нового предмета.

            Параметры:
                event (ft.ControlEvent): Событие нажатия кнопки «Добавить».

            Логика:
                - Берёт значение из Dropdown (приоритет) или текстового поля.
                - Добавляет в courses_list, если предмет уникален.
            """
            new_course: str | None = None

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
                    self.page.show_snack_bar(
                        ft.SnackBar(
                            content=ft.Text("⚠️ Уже добавлен"),
                            bgcolor=ft.colors.ORANGE,
                        ),
                    )
            else:
                self.page.show_snack_bar(
                    ft.SnackBar(
                        content=ft.Text("⚠️ Введите предмет"),
                        bgcolor=ft.colors.ORANGE,
                    ),
                )

        # Собрать элементы диалога
        dialog_controls: list[ft.Control] = []
        if subject_dropdown:
            dialog_controls.append(subject_dropdown)
            dialog_controls.append(
                ft.Text("— или —", size=12, color=ft.colors.GREY_600),
            )
        dialog_controls.append(course_input)

        add_dialog = ft.AlertDialog(
            title=ft.Text("Добавить предмет"),
            content=ft.Container(
                content=ft.Column(dialog_controls, spacing=10),
                width=350,
            ),
            actions=[
                ft.TextButton(
                    "Отмена",
                    on_click=lambda ev: self._close_dialog(add_dialog),
                ),
                ft.ElevatedButton(
                    "Добавить",
                    on_click=save_course,
                    bgcolor=ft.colors.GREEN_700,
                    color=ft.colors.WHITE,
                ),
            ],
        )

        self.page.dialog = add_dialog
        add_dialog.open = True
        self.page.update()

    # ====================
    # Генерация квитанции
    # ====================

    def _generate_receipt(self, e: ft.ControlEvent) -> None:
        """
        Сгенерировать PDF-квитанцию для текущего ученика.

        Параметры:
            e (ft.ControlEvent): Событие нажатия кнопки генерации.

        Логика:
            - Проверяет заполненность обязательных полей (ФИО, договор,
              предметы, сумма); при ошибке показывает SnackBar и выходит.
            - Открывает диалог сохранения файла через FilePicker.
            - В колбэке save_file_result вызывает generate_receipt и
              показывает результат (успех или ошибку) через SnackBar.
        """
        # Валидация обязательных полей
        if not self.fio_field.value:
            self.page.show_snack_bar(
                ft.SnackBar(
                    content=ft.Text("⚠️ Заполните ФИО"),
                    bgcolor=ft.colors.ORANGE,
                ),
            )
            return
        if not self.contract_field.value:
            self.page.show_snack_bar(
                ft.SnackBar(
                    content=ft.Text("⚠️ Заполните договор"),
                    bgcolor=ft.colors.ORANGE,
                ),
            )
            return
        if not self.courses_list:
            self.page.show_snack_bar(
                ft.SnackBar(
                    content=ft.Text("⚠️ Добавьте предметы"),
                    bgcolor=ft.colors.ORANGE,
                ),
            )
            return
        if not self.amount_field.value:
            self.page.show_snack_bar(
                ft.SnackBar(
                    content=ft.Text("⚠️ Укажите сумму"),
                    bgcolor=ft.colors.ORANGE,
                ),
            )
            return

        # Собрать данные для генерации
        student_name: str = self.fio_field.value
        contract_number: str = self.contract_field.value
        month_year: str = (
            f"{self.month_field.value}/{self.year_field.value}"
        )
        amount: float = float(self.amount_field.value)
        compensation: str = self.compensation_field.value
        courses: list[str] = self.courses_list

        # Имя файла по умолчанию
        fio_normalized = student_name.replace(" ", "_")
        default_filename = f"receipt_{fio_normalized}.pdf"

        def save_file_result(file_e: ft.FilePickerResultEvent) -> None:
            """
            Колбэк FilePicker: сохранить квитанцию по выбранному пути.

            Параметры:
                file_e (ft.FilePickerResultEvent): Результат диалога
                    сохранения файла; содержит file_e.path с выбранным путём.
            """
            if not file_e.path:
                return

            try:
                generate_receipt(
                    student_name=student_name,
                    courses=courses,
                    contract_number=contract_number,
                    month_year=month_year,
                    amount=amount,
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

    # =============
    # Служебные
    # =============

    def _close_dialog(self, dialog: ft.AlertDialog) -> None:
        """
        Закрыть диалоговое окно и обновить страницу.

        Параметры:
            dialog (ft.AlertDialog): Диалог, у которого нужно
                сбросить флаг open в False.
        """
        dialog.open = False
        self.page.update()
