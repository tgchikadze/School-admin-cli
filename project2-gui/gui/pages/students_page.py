"""
Страница управления учениками (StudentsPage).

Функциональность модуля:
- Отображение списка учеников в виде таблицы с фильтрами и поиском.
- Добавление, редактирование, удаление учеников.
- Импорт и экспорт данных учеников в/из CSV.
- Работа с ценами обучения и выбором предметов ЕГЭ для 11 класса.
"""

from pathlib import Path
import csv
import platform
import os

import flet as ft

from core.data.student_db import StudentDatabase
from core.data.classes_db import ClassesDatabase
from core.data.exam_choices_db import ExamChoicesDatabase


class StudentsPage:
    """
    Страница управления учениками.

    Атрибуты:
        page (ft.Page): Объект страницы Flet, общий для всего приложения.
        db (StudentDatabase): Класс-обёртка над JSON-базой учеников.
        classes_db (ClassesDatabase): Доступ к данным о школьных классах.
        exam_db (ExamChoicesDatabase): Доступ к данным о выборах ЕГЭ.
        students_table (ft.DataTable | None): Таблица с учениками
            (создаётся в build()).
        search_field (ft.TextField | None): Поле поиска по ФИО.
        class_filter (ft.Dropdown | None): Фильтр по классу.
    """

    def __init__(self, page: ft.Page) -> None:
        """
        Инициализация страницы управления учениками.

        Параметры:
            page (ft.Page): Корневая страница приложения Flet, в которую
                добавляются все элементы интерфейса и диалоги.
        """
        self.page: ft.Page = page
        self.db: StudentDatabase = StudentDatabase()
        self.classes_db: ClassesDatabase = ClassesDatabase()
        self.exam_db: ExamChoicesDatabase = ExamChoicesDatabase()

        self.students_table: ft.DataTable | None = None
        self.search_field: ft.TextField | None = None
        self.class_filter: ft.Dropdown | None = None

    def build(self) -> ft.Column:
        """
        Построить интерфейс страницы.

        Возвращает:
            ft.Column: Корневой колонкой для страницы управления учениками,
            содержащую заголовок, панель управления и таблицу с данными.
        """
        # ===========
        # Поле поиска
        # ===========
        self.search_field = ft.TextField(
            label="Поиск по ФИО",
            width=300,
            dense=True,
            on_change=self._on_search,
        )

        # =================
        # Фильтр по классам
        # =================
        classes = self.classes_db.get_all_classes()
        class_filter_options: list[ft.dropdown.Option] = [
            ft.dropdown.Option(key="", text="Все классы"),
        ]
        class_filter_options.extend(
            [
                ft.dropdown.Option(key=c["id"], text=c["name"])
                for c in classes
            ],
        )

        self.class_filter = ft.Dropdown(
            label="Фильтр по классу",
            options=class_filter_options,
            width=200,
            value="",
            dense=True,
            on_change=self._on_class_filter_change,
        )

        # ==================
        # Кнопки управления
        # ==================
        add_btn = ft.ElevatedButton(
            "➕ Добавить ученика",
            on_click=self._show_add_dialog,
            style=ft.ButtonStyle(
                bgcolor=ft.colors.GREEN_700,
                color=ft.colors.WHITE,
            ),
        )

        import_btn = ft.IconButton(
            icon=ft.icons.UPLOAD_FILE,
            icon_color=ft.colors.GREY_700,
            icon_size=28,
            tooltip="Импорт из CSV",
            on_click=self._import_csv,
        )

        export_btn = ft.IconButton(
            icon=ft.icons.DOWNLOAD,
            icon_color=ft.colors.GREY_700,
            icon_size=28,
            tooltip="Экспорт в CSV",
            on_click=self._export_csv,
        )

        clear_btn = ft.IconButton(
            icon=ft.icons.DELETE_SWEEP,
            icon_color=ft.colors.GREY_700,
            icon_size=28,
            tooltip="Очистить базу",
            on_click=self._clear_database,
        )

        # ==================
        # Таблица учеников
        # ==================
        self.students_table = ft.DataTable(
            columns=[
                ft.DataColumn(ft.Text("ID", weight=ft.FontWeight.BOLD)),
                ft.DataColumn(ft.Text("ФИО", weight=ft.FontWeight.BOLD)),
                ft.DataColumn(ft.Text("Договор", weight=ft.FontWeight.BOLD)),
                ft.DataColumn(ft.Text("Класс", weight=ft.FontWeight.BOLD)),
                ft.DataColumn(ft.Text("Действия", weight=ft.FontWeight.BOLD)),
            ],
            rows=[],
            border=ft.border.all(1, ft.colors.GREY_300),
            border_radius=8,
            heading_row_color=ft.colors.GREY_100,
        )

        # Загрузить данные в таблицу
        self._load_students()

        # ========
        # Макет UI
        # ========
        return ft.Column(
            controls=[
                # Заголовок
                ft.Text(
                    "👥 Управление учениками",
                    size=20,
                    weight=ft.FontWeight.BOLD,
                ),
                ft.Divider(height=3),
                # Панель управления (поиск, фильтр, кнопки)
                ft.Row(
                    [
                        self.search_field,
                        self.class_filter,
                        add_btn,
                        import_btn,
                        export_btn,
                        clear_btn,
                    ],
                    spacing=10,
                    wrap=True,
                ),
                ft.Divider(height=3),
                # Таблица в контейнере с прокруткой
                ft.Container(
                    content=ft.Column(
                        [self.students_table],
                        scroll=ft.ScrollMode.AUTO,
                    ),
                    expand=True,
                ),
            ],
            spacing=6,
            expand=True,
        )

    # ========================
    # Загрузка и фильтрация БД
    # ========================

    def _load_students(
        self,
        search_query: str = "",
        class_filter: str = "",
    ) -> None:
        """
        Загрузить список учеников в таблицу с учётом фильтров.

        Параметры:
            search_query (str): Строка поиска по ФИО. Если пустая,
                поиск не применяется и загружаются все ученики.
            class_filter (str): Идентификатор класса для фильтрации.
                Пустая строка означает отсутствие фильтра по классу.

        Побочные эффекты:
            - Очищает self.students_table.rows.
            - Добавляет в таблицу строки по текущему набору учеников.
            - Обновляет страницу через page.update().
        """
        if self.students_table is None:
            return

        # Получить список учеников
        if search_query:
            students = self.db.search(search_query)
        else:
            students = self.db.get_all()

        # Применить фильтр по классу (если выбран)
        if class_filter:
            students = [
                s for s in students if s.get("class_id") == class_filter
            ]

        # Очистить таблицу
        self.students_table.rows.clear()

        # Заполнить таблицу
        for student in students:
            class_info = self.classes_db.get_class_by_id(
                student.get("class_id", ""),
            )
            class_name = (
                class_info["name"]
                if class_info
                else student.get("class_id", "N/A")
            )

            actions = ft.Row(
                [
                    ft.IconButton(
                        icon=ft.icons.INFO,
                        icon_color=ft.colors.BLUE_700,
                        icon_size=20,
                        tooltip="Просмотр",
                        on_click=lambda e, s=student: self._show_info(s),
                    ),
                    ft.IconButton(
                        icon=ft.icons.EDIT,
                        icon_color=ft.colors.ORANGE_700,
                        icon_size=20,
                        tooltip="Редактировать",
                        on_click=lambda e, s=student: self._show_edit_dialog(
                            s,
                        ),
                    ),
                    ft.IconButton(
                        icon=ft.icons.DELETE,
                        icon_color=ft.colors.RED_700,
                        icon_size=20,
                        tooltip="Удалить",
                        on_click=lambda e, s=student: self._delete_student(s),
                    ),
                ],
                spacing=5,
            )

            row = ft.DataRow(
                cells=[
                    ft.DataCell(ft.Text(student["id"], size=12)),
                    ft.DataCell(ft.Text(student["fio"], size=12)),
                    ft.DataCell(ft.Text(student["contract_number"], size=12)),
                    ft.DataCell(ft.Text(class_name, size=12)),
                    ft.DataCell(actions),
                ],
            )
            self.students_table.rows.append(row)

        self.page.update()

    def _on_search(self, e: ft.ControlEvent) -> None:
        """
        Обработчик изменения поля поиска по ФИО.

        Параметры:
            e (ft.ControlEvent): Событие изменения значения текстового поля.

        Логика:
            - Берёт текущие значения search_field и class_filter.
            - Вызывает _load_students с указанными фильтрами.
        """
        search_query = self.search_field.value if self.search_field else ""
        class_filter = self.class_filter.value if self.class_filter else ""
        self._load_students(
            search_query=search_query,
            class_filter=class_filter,
        )

    def _on_class_filter_change(self, e: ft.ControlEvent) -> None:
        """
        Обработчик изменения фильтра по классу.

        Параметры:
            e (ft.ControlEvent): Событие изменения значения Dropdown.

        Логика:
            - Берёт выбранный класс из self.class_filter.
            - Учитывает текущую строку поиска.
            - Перезагружает таблицу с новыми фильтрами.
        """
        class_filter = self.class_filter.value if self.class_filter else ""
        search_query = self.search_field.value if self.search_field else ""
        self._load_students(
            search_query=search_query,
            class_filter=class_filter,
        )

    # ============================
    # Добавление нового ученика
    # ============================

    def _show_add_dialog(self, e: ft.ControlEvent) -> None:
        """
        Показать диалоговое окно добавления нового ученика.

        Параметры:
            e (ft.ControlEvent): Событие нажатия на кнопку добавления.

        Логика:
            - Загружает список классов и формирует Dropdown.
            - Показывает поля для заполнения данных ученика.
            - Для 11 класса показывает дополнительные чекбоксы предметов ЕГЭ.
            - При сохранении вызывает _save_add_student.
        """
        classes = self.classes_db.get_all_classes()
        class_options = [
            ft.dropdown.Option(key=c["id"], text=c["name"]) for c in classes
        ]

        fio_field = ft.TextField(label="ФИО", width=400)
        contract_field = ft.TextField(label="Номер договора", width=200)

        # Контейнер для выбора предметов ЕГЭ (только для 11 класса)
        exam_selection_container = ft.Column(visible=False)
        exam_selection_container.data = []  # type: ignore[attr-defined]

        price_info_text = ft.Text("", size=12, color=ft.colors.GREY_700)
        compensation_field = ft.TextField(label="Компенсация", width=200)

        class_dropdown = ft.Dropdown(
            label="Класс",
            options=class_options,
            width=200,
        )

        def on_class_change(event: ft.ControlEvent) -> None:
            """
            Обработчик смены класса в форме добавления.

            Параметры:
                event (ft.ControlEvent): Событие изменения Dropdown класса.

            Логика:
                - Обновляет текст с информацией о цене.
                - Для 11 класса показывает список предметов ЕГЭ.
            """
            self._update_price_info(event, class_dropdown, price_info_text)

            class_id = class_dropdown.value
            if class_id:
                class_info = self.classes_db.get_class_by_id(class_id)
                pricing = class_info.get("pricing", {}) if class_info else {}
                is_per_subject = pricing.get("type") == "per_subject"

                if class_info and is_per_subject:
                    exam_selection_container.visible = True
                    exam_selection_container.controls.clear()

                    exam_subjects = class_info.get("exam_subjects", [])
                    exam_checkboxes: list[ft.Checkbox] = []

                    exam_selection_container.controls.append(
                        ft.Text(
                            "Выберите предметы ЕГЭ:",
                            size=13,
                            weight=ft.FontWeight.BOLD,
                        ),
                    )
                    for exam in exam_subjects:
                        cb = ft.Checkbox(label=exam, value=False)
                        exam_checkboxes.append(cb)
                        exam_selection_container.controls.append(cb)

                    exam_selection_container.data = exam_checkboxes
                else:
                    exam_selection_container.visible = False
            else:
                exam_selection_container.visible = False

            self.page.update()

        class_dropdown.on_change = on_class_change

        def save_student(event: ft.ControlEvent) -> None:
            """
            Обработчик сохранения нового ученика из диалога.

            Параметры:
                event (ft.ControlEvent): Событие нажатия на кнопку "Сохранить".

            Логика:
                - Собирает данные из полей формы.
                - Собирает выбранные предметы ЕГЭ (если применимо).
                - Передаёт всё в _save_add_student.
            """
            selected_exams: list[str] | None = None

            if exam_selection_container.visible:
                exam_checkboxes = exam_selection_container.data or []
                selected_exams = [
                    cb.label  # type: ignore[attr-defined]
                    for cb in exam_checkboxes
                    if cb.value
                ]

            self._save_add_student(
                dialog=add_dialog,
                fio=fio_field.value,
                contract=contract_field.value,
                class_id=class_dropdown.value,
                compensation=compensation_field.value,
                selected_exams=selected_exams,
            )

        add_dialog = ft.AlertDialog(
            title=ft.Text("➕ Добавить ученика"),
            content=ft.Container(
                content=ft.Column(
                    [
                        fio_field,
                        contract_field,
                        class_dropdown,
                        price_info_text,
                        exam_selection_container,
                        compensation_field,
                    ],
                    spacing=10,
                    scroll=ft.ScrollMode.AUTO,
                ),
                width=450,
                height=500,
            ),
            actions=[
                ft.TextButton(
                    "Отмена",
                    on_click=lambda ev: self._close_dialog(add_dialog),
                ),
                ft.ElevatedButton(
                    "Сохранить",
                    on_click=save_student,
                    bgcolor=ft.colors.GREEN_700,
                    color=ft.colors.WHITE,
                ),
            ],
        )

        self.page.dialog = add_dialog
        add_dialog.open = True
        self.page.update()

    def _update_price_info(
        self,
        e: ft.ControlEvent,
        class_dropdown: ft.Dropdown,
        price_info_text: ft.Text,
    ) -> None:
        """
        Обновить текст с информацией о цене обучения для выбранного класса.

        Параметры:
            e (ft.ControlEvent): Событие изменения Dropdown класса.
            class_dropdown (ft.Dropdown): Выпадающий список с классами.
            price_info_text (ft.Text): Текстовый элемент для вывода цены.
        """
        class_id = class_dropdown.value
        if class_id:
            price_info = self.classes_db.get_price_info(class_id)
            price_info_text.value = price_info
        else:
            price_info_text.value = ""
        self.page.update()

    def _save_add_student(
        self,
        dialog: ft.AlertDialog,
        fio: str,
        contract: str,
        class_id: str,
        compensation: str,
        selected_exams: list[str] | None = None,
    ) -> None:
        """
        Сохранить нового ученика в базу и обновить таблицу.

        Параметры:
            dialog (ft.AlertDialog): Диалог добавления ученика, который
                нужно закрыть при успешном добавлении.
            fio (str): ФИО ученика, вводится пользователем.
            contract (str): Номер договора.
            class_id (str): Идентификатор класса.
            compensation (str): Размер компенсации (строка, может быть пустой).
            selected_exams (list[str] | None): Список выбранных предметов ЕГЭ
                для 11 класса. Может быть None, если класс не ЕГЭшный.

        Логика:
            - Проверяет обязательные поля.
            - Для классов с помесячной оплатой за предметы (ЕГЭ):
              требует хотя бы один выбранный предмет и считает стоимость.
            - Для остальных классов берёт фиксированную стоимость.
            - Добавляет запись в БД, при успехе сохраняет выбор ЕГЭ и
              обновляет таблицу.
        """
        # Проверка обязательных полей
        if not fio or not contract or not class_id:
            self.page.show_snack_bar(
                ft.SnackBar(
                    content=ft.Text("⚠️ Заполните все обязательные поля"),
                    bgcolor=ft.colors.ORANGE,
                ),
            )
            return

        # Для 11 класса проверить выбор ЕГЭ
        class_info = self.classes_db.get_class_by_id(class_id)
        pricing = class_info.get("pricing", {}) if class_info else {}
        is_per_subject = pricing.get("type") == "per_subject"

        if is_per_subject:
            if not selected_exams or len(selected_exams) == 0:
                self.page.show_snack_bar(
                    ft.SnackBar(
                        content=ft.Text(
                            "⚠️ Выберите хотя бы один предмет ЕГЭ",
                        ),
                        bgcolor=ft.colors.ORANGE,
                    ),
                )
                return
            monthly_payment = self.exam_db.calculate_exam_cost(
                selected_exams,
                3000,
            )
        else:
            monthly_payment = self.classes_db.calculate_price(class_id, [])

        # Добавить ученика в базу
        result = self.db.add(
            fio=fio,
            contract_number=contract,
            class_id=class_id,
            monthly_payment=monthly_payment,
            compensation=compensation,
        )

        if result:
            # Сохранить выбор ЕГЭ, если он есть
            if selected_exams:
                self.exam_db.save_student_exams(result["id"], selected_exams)

            dialog.open = False
            self._load_students()
            self.page.show_snack_bar(
                ft.SnackBar(
                    content=ft.Text(f"✅ Ученик {fio} добавлен"),
                    bgcolor=ft.colors.GREEN,
                ),
            )
        else:
            self.page.show_snack_bar(
                ft.SnackBar(
                    content=ft.Text("⚠️ Такой ученик уже существует"),
                    bgcolor=ft.colors.ORANGE,
                ),
            )

        self.page.update()

    # ============================
    # Редактирование существующих
    # ============================

    def _show_edit_dialog(self, student: dict) -> None:
        """
        Показать диалог редактирования данных существующего ученика.

        Параметры:
            student (dict): Словарь с данными ученика, полученный из БД.
                Ожидаемые ключи: 'id', 'fio', 'contract_number',
                'class_id', 'compensation', 'monthly_payment'.
        """
        # Список классов для фильтра в диалоге (если нужен)
        classes = self.classes_db.get_all_classes()
        class_filter_options = [
            ft.dropdown.Option(key="", text="Все классы"),
        ]
        class_filter_options.extend(
            [
                ft.dropdown.Option(key=c["id"], text=c["name"])
                for c in classes
            ],
        )

        class_filter = ft.Dropdown(
            label="Фильтр по классу",
            options=class_filter_options,
            width=200,
            value="",
            dense=True,
            on_change=lambda e: self._load_students(
                class_filter=e.control.value,
            ),
        )

        fio_field = ft.TextField(
            label="ФИО",
            width=400,
            value=student.get("fio", ""),
        )
        contract_field = ft.TextField(
            label="Номер договора",
            width=200,
            value=student.get("contract_number", ""),
        )

        # Снова получаем список классов для выпадающего списка
        class_options = [
            ft.dropdown.Option(key=c["id"], text=c["name"]) for c in classes
        ]

        price_info = self.classes_db.get_price_info(
            student.get("class_id", ""),
        )
        price_info_text = ft.Text(
            price_info,
            size=12,
            color=ft.colors.GREY_700,
        )

        class_dropdown = ft.Dropdown(
            label="Класс",
            options=class_options,
            width=200,
            value=student.get("class_id", ""),
            on_change=lambda e: self._update_price_info(
                e,
                class_dropdown,
                price_info_text,
            ),
        )

        compensation_field = ft.TextField(
            label="Компенсация",
            width=200,
            value=student.get("compensation", ""),
        )

        def save_changes(e: ft.ControlEvent) -> None:
            """
            Обработчик нажатия кнопки сохранения изменений.

            Параметры:
                e (ft.ControlEvent): Событие клика по кнопке "Сохранить".
            """
            self._save_edit_student(
                dialog=edit_dialog,
                student_id=student["id"],
                fio=fio_field.value,
                contract=contract_field.value,
                class_id=class_dropdown.value,
                compensation=compensation_field.value,
            )

        edit_dialog = ft.AlertDialog(
            title=ft.Text("✏️ Редактировать ученика"),
            content=ft.Container(
                content=ft.Column(
                    [
                        fio_field,
                        contract_field,
                        class_dropdown,
                        price_info_text,
                        compensation_field,
                    ],
                    spacing=10,
                    scroll=ft.ScrollMode.AUTO,
                ),
                width=450,
                height=400,
            ),
            actions=[
                ft.TextButton(
                    "Отмена",
                    on_click=lambda e: self._close_dialog(edit_dialog),
                ),
                ft.ElevatedButton(
                    "Сохранить",
                    on_click=save_changes,
                    bgcolor=ft.colors.GREEN_700,
                    color=ft.colors.WHITE,
                ),
            ],
        )

        self.page.dialog = edit_dialog
        edit_dialog.open = True
        self.page.update()

    def _save_edit_student(
        self,
        dialog: ft.AlertDialog,
        student_id: str,
        fio: str,
        contract: str,
        class_id: str,
        compensation: str,
    ) -> None:
        """
        Сохранить изменения данных ученика.

        Параметры:
            dialog (ft.AlertDialog): Диалог редактирования, который нужно
                закрыть при успешном сохранении.
            student_id (str): Идентификатор ученика в БД.
            fio (str): Новое ФИО.
            contract (str): Новый номер договора.
            class_id (str): Новый идентификатор класса.
            compensation (str): Новая компенсация.
        """
        if not fio or not contract or not class_id:
            self.page.show_snack_bar(
                ft.SnackBar(
                    content=ft.Text("⚠️ Заполните все обязательные поля"),
                    bgcolor=ft.colors.ORANGE,
                ),
            )
            return

        monthly_payment = self.classes_db.calculate_price(class_id, [])

        success = self.db.update(
            student_id=student_id,
            fio=fio,
            contract_number=contract,
            class_id=class_id,
            monthly_payment=monthly_payment,
            compensation=compensation,
        )

        if success:
            dialog.open = False
            self._load_students()
            self.page.show_snack_bar(
                ft.SnackBar(
                    content=ft.Text("✅ Данные обновлены"),
                    bgcolor=ft.colors.GREEN,
                ),
            )

        self.page.update()

    # ============================
    # Удаление и просмотр ученика
    # ============================

    def _delete_student(self, student: dict) -> None:
        """
        Показать диалог подтверждения удаления ученика.

        Параметры:
            student (dict): Словарь с данными ученика, подлежащего удалению.
        """
        def confirm_delete(e: ft.ControlEvent) -> None:
            """
            Подтверждение удаления ученика.

            Параметры:
                e (ft.ControlEvent): Событие нажатия на кнопку удаления.
            """
            self.db.delete(student["id"])
            delete_dialog.open = False
            self._load_students()
            self.page.show_snack_bar(
                ft.SnackBar(
                    content=ft.Text("✅ Ученик удалён"),
                    bgcolor=ft.colors.GREEN,
                ),
            )
            self.page.update()

        delete_dialog = ft.AlertDialog(
            title=ft.Row(
                [
                    ft.Icon(ft.icons.WARNING, color=ft.colors.RED_700),
                    ft.Text("Удалить ученика?"),
                ],
            ),
            content=ft.Text(
                "Вы уверены, что хотите удалить:\n"
                f"{student['fio']} ({student['contract_number']})?",
            ),
            actions=[
                ft.TextButton(
                    "Отмена",
                    on_click=lambda e: self._close_dialog(delete_dialog),
                ),
                ft.ElevatedButton(
                    "Удалить",
                    on_click=confirm_delete,
                    bgcolor=ft.colors.RED_700,
                    color=ft.colors.WHITE,
                ),
            ],
        )

        self.page.dialog = delete_dialog
        delete_dialog.open = True
        self.page.update()

    def _show_info(self, student: dict) -> None:
        """
        Показать диалог с подробной информацией об ученике.

        Параметры:
            student (dict): Словарь с данными ученика.
        """
        class_info = self.classes_db.get_class_by_id(
            student.get("class_id", ""),
        )
        class_name = (
            class_info["name"]
            if class_info
            else student.get("class_id", "N/A")
        )

        subjects: list[str] = []
        if class_info:
            subjects = self.classes_db.get_subjects_by_class(
                student.get("class_id", ""),
            )
        subjects_text = ", ".join(subjects) if subjects else "Не указаны"

        info_dialog = ft.AlertDialog(
            title=ft.Text(f"ℹ️ {student['fio']}"),
            content=ft.Container(
                content=ft.Column(
                    [
                        ft.Text(f"ID: {student['id']}", size=13),
                        ft.Text(
                            f"Договор: {student['contract_number']}",
                            size=13,
                        ),
                        ft.Text(f"Класс: {class_name}", size=13),
                        ft.Text(
                            (
                                f"Оплата: "
                                f"{student.get('monthly_payment', 0):,} ₽"
                            ).replace(",", " "),
                            size=13,
                        ),
                        ft.Text(
                            (
                                "Компенсация: "
                                f"{student.get('compensation', 'Нет')}"
                            ),
                            size=13,
                        ),
                        ft.Divider(height=10),
                        ft.Text(
                            "Предметы класса:",
                            size=13,
                            weight=ft.FontWeight.BOLD,
                        ),
                        ft.Text(
                            subjects_text,
                            size=12,
                            color=ft.colors.GREY_700,
                        ),
                    ],
                    spacing=8,
                ),
                width=400,
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

    # =====================
    # Импорт / экспорт CSV
    # =====================

    def _import_csv(self, e: ft.ControlEvent) -> None:
        """
        Инициировать импорт учеников из CSV-файла.

        Параметры:
            e (ft.ControlEvent): Событие нажатия на кнопку импорта.
        """
        def pick_files_result(event: ft.FilePickerResultEvent) -> None:
            """
            Обработчик результата выбора файлов.

            Параметры:
                event (ft.FilePickerResultEvent): Результат работы FilePicker,
                    содержит список выбранных файлов.
            """
            if event.files and len(event.files) > 0:
                self._process_csv_import(event.files[0].path)

        file_picker = ft.FilePicker(on_result=pick_files_result)
        self.page.overlay.append(file_picker)
        self.page.update()

        file_picker.pick_files(
            dialog_title="Выберите CSV файл для импорта",
            allowed_extensions=["csv"],
            allow_multiple=False,
        )

    def _process_csv_import(self, file_path: str) -> None:
        """
        Обработать импорт учеников из CSV-файла.

        Параметры:
            file_path (str): Путь к выбранному CSV-файлу.

        Логика:
            - Читает CSV и пытается добавить каждого ученика в БД.
            - Подсчитывает количество успешных добавлений и ошибок.
            - Обновляет таблицу и показывает SnackBar или диалог с ошибками.
        """
        try:
            success_count = 0
            error_count = 0
            errors: list[str] = []

            with open(file_path, "r", encoding="utf-8") as f:
                reader = csv.DictReader(f)

                for row in reader:
                    try:
                        fio = row.get("fio", "").strip()
                        contract = row.get("contract_number", "").strip()
                        class_id = row.get("class_id", "").strip()
                        compensation = row.get("compensation", "").strip()

                        if not fio or not contract or not class_id:
                            error_count += 1
                            errors.append(
                                f"{fio or 'N/A'}: "
                                "Пропущены обязательные поля",
                            )
                            continue

                        monthly_payment = self.classes_db.calculate_price(
                            class_id,
                            [],
                        )

                        result = self.db.add(
                            fio=fio,
                            contract_number=contract,
                            class_id=class_id,
                            monthly_payment=monthly_payment,
                            compensation=compensation,
                        )

                        if result:
                            success_count += 1
                        else:
                            error_count += 1
                            errors.append(f"{fio}: Дубликат")
                    except Exception as ex:  # noqa: BLE001
                        error_count += 1
                        errors.append(f"{row.get('fio', 'N/A')}: {str(ex)}")

            self._load_students()

            if error_count == 0:
                self.page.show_snack_bar(
                    ft.SnackBar(
                        content=ft.Text(
                            f"✅ Импортировано: {success_count} учеников",
                        ),
                        bgcolor=ft.colors.GREEN,
                    ),
                )
            else:
                error_text = "\n".join(errors[:5])
                if len(errors) > 5:
                    error_text += f"\n... и еще {len(errors) - 5}"

                error_dialog = ft.AlertDialog(
                    title=ft.Text("⚠️ Импорт завершён с ошибками"),
                    content=ft.Container(
                        content=ft.Column(
                            [
                                ft.Text(
                                    f"✅ Импортировано: {success_count}",
                                    size=13,
                                    color=ft.colors.GREEN,
                                ),
                                ft.Text(
                                    f"❌ Ошибок: {error_count}",
                                    size=13,
                                    color=ft.colors.RED,
                                ),
                                ft.Divider(height=10),
                                ft.Text(
                                    "Ошибки:",
                                    size=12,
                                    weight=ft.FontWeight.BOLD,
                                ),
                                ft.Text(
                                    error_text,
                                    size=11,
                                    color=ft.colors.RED,
                                ),
                            ],
                            spacing=8,
                            scroll=ft.ScrollMode.AUTO,
                        ),
                        width=500,
                        height=300,
                    ),
                    actions=[
                        ft.TextButton(
                            "Закрыть",
                            on_click=lambda e: self._close_dialog(
                                error_dialog,
                            ),
                        ),
                    ],
                )

                self.page.dialog = error_dialog
                error_dialog.open = True
        except Exception as ex:  # noqa: BLE001
            self.page.show_snack_bar(
                ft.SnackBar(
                    content=ft.Text(f"❌ Ошибка чтения файла: {str(ex)}"),
                    bgcolor=ft.colors.RED,
                ),
            )

        self.page.update()

    def _export_csv(self, e: ft.ControlEvent) -> None:
        """
        Экспортировать текущий список учеников в CSV-файл.

        Параметры:
            e (ft.ControlEvent): Событие нажатия на кнопку экспорта.
        """
        students = self.db.get_all()
        if not students:
            self.page.show_snack_bar(
                ft.SnackBar(
                    content=ft.Text("⚠️ Нет данных для экспорта"),
                    bgcolor=ft.colors.ORANGE,
                ),
            )
            return

        def save_file_result(event: ft.FilePickerResultEvent) -> None:
            """
            Обработчик выбора пути сохранения CSV-файла.

            Параметры:
                event (ft.FilePickerResultEvent): Результат диалога
                    сохранения файла, содержит путь e.path.
            """
            if not event.path:
                return

            try:
                with open(
                    event.path,
                    "w",
                    encoding="utf-8",
                    newline="",
                ) as f:
                    fieldnames = [
                        "id",
                        "fio",
                        "contract_number",
                        "class_id",
                        "monthly_payment",
                        "compensation",
                    ]
                    writer = csv.DictWriter(f, fieldnames=fieldnames)
                    writer.writeheader()

                    for student in students:
                        writer.writerow(
                            {
                                "id": student["id"],
                                "fio": student["fio"],
                                "contract_number": student["contract_number"],
                                "class_id": student.get("class_id", ""),
                                "monthly_payment": student.get(
                                    "monthly_payment",
                                    0,
                                ),
                                "compensation": student.get(
                                    "compensation",
                                    "",
                                ),
                            },
                        )

                self.page.show_snack_bar(
                    ft.SnackBar(
                        content=ft.Text(
                            f"✅ Экспортировано: {len(students)} учеников",
                        ),
                        bgcolor=ft.colors.GREEN,
                    ),
                )

                # Попытаться открыть папку с файлом
                file_dir = Path(event.path).parent
                try:
                    if platform.system() == "Darwin":
                        os.system(f'open "{file_dir}"')
                    elif platform.system() == "Windows":
                        os.startfile(str(file_dir))  # type: ignore[attr-defined]
                    else:
                        os.system(f'xdg-open "{file_dir}"')
                except Exception:  # noqa: BLE001
                    pass
            except Exception as ex:  # noqa: BLE001
                self.page.show_snack_bar(
                    ft.SnackBar(
                        content=ft.Text(f"❌ Ошибка: {str(ex)}"),
                        bgcolor=ft.colors.RED,
                    ),
                )

        from datetime import datetime

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        default_filename = f"students_export_{timestamp}.csv"

        file_picker = ft.FilePicker(on_result=save_file_result)
        self.page.overlay.append(file_picker)
        self.page.update()

        file_picker.save_file(
            dialog_title="Сохранить экспорт",
            file_name=default_filename,
            allowed_extensions=["csv"],
        )

    # ==========================
    # Очистка базы и служебные
    # ==========================

    def _clear_database(self, e: ft.ControlEvent) -> None:
        """
        Показать диалог подтверждения очистки базы данных учеников.

        Параметры:
            e (ft.ControlEvent): Событие нажатия на кнопку очистки.
        """
        def confirm_clear(event: ft.ControlEvent) -> None:
            """
            Подтвердить очистку базы данных.

            Параметры:
                event (ft.ControlEvent): Событие нажатия на кнопку "Очистить".
            """
            self.db.clear_all()
            clear_dialog.open = False
            self._load_students()
            self.page.show_snack_bar(
                ft.SnackBar(
                    content=ft.Text("✅ База данных очищена"),
                    bgcolor=ft.colors.GREEN,
                ),
            )
            self.page.update()

        clear_dialog = ft.AlertDialog(
            title=ft.Row(
                [
                    ft.Icon(ft.icons.WARNING, color=ft.colors.RED_700),
                    ft.Text("Очистить базу данных?"),
                ],
            ),
            content=ft.Text(
                "⚠️ ВСЕ ДАННЫЕ БУДУТ УДАЛЕНЫ БЕЗВОЗВРАТНО!\n\n"
                "Рекомендуется сначала сделать экспорт в CSV.",
                size=13,
            ),
            actions=[
                ft.TextButton(
                    "Отмена",
                    on_click=lambda e: self._close_dialog(clear_dialog),
                ),
                ft.ElevatedButton(
                    "Очистить",
                    on_click=confirm_clear,
                    bgcolor=ft.colors.RED_700,
                    color=ft.colors.WHITE,
                ),
            ],
        )

        self.page.dialog = clear_dialog
        clear_dialog.open = True
        self.page.update()

    def _close_dialog(self, dialog: ft.AlertDialog) -> None:
        """
        Закрыть диалоговое окно и обновить страницу.

        Параметры:
            dialog (ft.AlertDialog): Объект диалога, у которого
                нужно сбросить флаг open.
        """
        dialog.open = False
        self.page.update()
