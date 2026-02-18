"""
Страница управления выбором ЕГЭ для учеников 11 класса (ExamSelectionPage).

Функциональность модуля:
- Отображение таблицы всех сохранённых выборов ЕГЭ (ученик, класс,
  количество предметов, стоимость).
- Добавление нового выбора ЕГЭ для ученика через диалог с чекбоксами.
- Редактирование существующего выбора ЕГЭ.
- Просмотр подробной информации о выборе.
- Удаление записи с подтверждением.
- Данные сохраняются через ExamChoicesDatabase и читаются всеми
  страницами приложения (receipts_page, search_page, batch_receipts_page).
"""

import flet as ft

from core.data.student_db import StudentDatabase
from core.data.classes_db import ClassesDatabase
from core.data.exam_choices_db import ExamChoicesDatabase


class ExamSelectionPage:
    """
    Страница управления выбором предметов ЕГЭ для учеников 11 класса.

    Атрибуты:
        page (ft.Page): Корневая страница Flet-приложения.
        db (StudentDatabase): База данных учеников.
        classes_db (ClassesDatabase): База данных классов.
        exam_db (ExamChoicesDatabase): База данных выборов ЕГЭ — единственное
            хранилище предметов ЕГЭ, которое читают все остальные страницы.

    Атрибуты интерфейса (инициализируются None до вызова build()):
        records_table (ft.DataTable | None): Таблица с записями выбора ЕГЭ.
    """

    def __init__(self, page: ft.Page) -> None:
        """
        Инициализация страницы выбора ЕГЭ.

        Параметры:
            page (ft.Page): Корневая страница Flet, в которую добавляются
                все элементы интерфейса и диалоги.
        """
        self.page: ft.Page = page
        self.db: StudentDatabase = StudentDatabase()
        self.classes_db: ClassesDatabase = ClassesDatabase()
        self.exam_db: ExamChoicesDatabase = ExamChoicesDatabase()

        # Элементы интерфейса (создаются в build())
        self.records_table: ft.DataTable | None = None

    # ====================
    # Построение интерфейса
    # ====================

    def build(self) -> ft.Column:
        """
        Построить и вернуть интерфейс страницы.

        Возвращает:
            ft.Column: Корневая колонка страницы с кнопкой добавления
                и таблицей записей выбора ЕГЭ.
        """
        add_btn = ft.ElevatedButton(
            "➕ Добавить выбор ЕГЭ",
            on_click=self._show_add_dialog,
            style=ft.ButtonStyle(
                bgcolor=ft.colors.GREEN_700,
                color=ft.colors.WHITE,
            ),
        )

        # Таблица записей
        self.records_table = ft.DataTable(
            columns=[
                ft.DataColumn(ft.Text("ID", weight=ft.FontWeight.BOLD)),
                ft.DataColumn(
                    ft.Text("ФИО ученика", weight=ft.FontWeight.BOLD),
                ),
                ft.DataColumn(ft.Text("Класс", weight=ft.FontWeight.BOLD)),
                ft.DataColumn(
                    ft.Text("Предметов ЕГЭ", weight=ft.FontWeight.BOLD),
                ),
                ft.DataColumn(
                    ft.Text("Стоимость", weight=ft.FontWeight.BOLD),
                ),
                ft.DataColumn(
                    ft.Text("Действия", weight=ft.FontWeight.BOLD),
                ),
            ],
            rows=[],
            border=ft.border.all(1, ft.colors.GREY_300),
            border_radius=8,
            heading_row_color=ft.colors.GREY_100,
        )

        # Загрузить данные сразу при построении страницы
        self._load_records()

        return ft.Column(
            controls=[
                ft.Text(
                    "🎓 Управление выбором ЕГЭ",
                    size=20,
                    weight=ft.FontWeight.BOLD,
                ),
                ft.Divider(height=3),
                ft.Row([add_btn], spacing=10),
                ft.Divider(height=3),
                ft.Container(
                    content=ft.Column(
                        [self.records_table],
                        scroll=ft.ScrollMode.AUTO,
                    ),
                    expand=True,
                ),
            ],
            spacing=6,
            expand=True,
        )

    # ============================
    # Загрузка таблицы
    # ============================

    def _load_records(self) -> None:
        """
        Загрузить все записи выбора ЕГЭ и отобразить в таблице.

        Читает данные напрямую через exam_db._load() для получения
        полного списка записей. Очищает таблицу перед перезаполнением.

        Логика строк:
            - При пустой базе — одна строка-заглушка с прочерками.
            - Для каждой записи: ID ученика, ФИО, класс, количество
              предметов, рассчитанная стоимость, кнопки действий.
        """
        data = self.exam_db._load()
        exam_choices = data.get("exam_choices", [])

        self.records_table.rows.clear()

        if not exam_choices:
            self.records_table.rows.append(
                ft.DataRow(
                    cells=[
                        ft.DataCell(ft.Text("—", size=12)),
                        ft.DataCell(
                            ft.Text(
                                "Нет записей",
                                size=12,
                                color=ft.colors.GREY_600,
                                italic=True,
                            ),
                        ),
                        ft.DataCell(ft.Text("—", size=12)),
                        ft.DataCell(ft.Text("—", size=12)),
                        ft.DataCell(ft.Text("—", size=12)),
                        ft.DataCell(ft.Text("—", size=12)),
                    ],
                ),
            )
        else:
            for choice in exam_choices:
                student_id = choice.get("student_id", "")
                selected_exams = choice.get("selected_exams", [])

                # Получить данные ученика
                student = self.db.get_by_id(student_id)
                if student:
                    fio = student.get("fio", "N/A")
                    class_id = student.get("class_id", "")
                    class_info = self.classes_db.get_class_by_id(class_id)
                    class_name = (
                        class_info["name"] if class_info else class_id
                    )
                else:
                    fio = f"Ученик не найден (ID: {student_id})"
                    class_name = "N/A"

                # Рассчитать стоимость (3000₽ за предмет)
                cost = self.exam_db.calculate_exam_cost(selected_exams, 3000)
                cost_text = f"{int(cost):,}₽".replace(",", " ")

                # Кнопки действий
                actions = ft.Row(
                    [
                        ft.IconButton(
                            icon=ft.icons.INFO,
                            icon_color=ft.colors.BLUE_700,
                            icon_size=20,
                            tooltip="Просмотр",
                            on_click=lambda ev, c=choice: self._show_info(c),
                        ),
                        ft.IconButton(
                            icon=ft.icons.EDIT,
                            icon_color=ft.colors.ORANGE_700,
                            icon_size=20,
                            tooltip="Редактировать",
                            on_click=lambda ev, c=choice: (
                                self._show_edit_dialog(c)
                            ),
                        ),
                        ft.IconButton(
                            icon=ft.icons.DELETE,
                            icon_color=ft.colors.RED_700,
                            icon_size=20,
                            tooltip="Удалить",
                            on_click=lambda ev, sid=student_id: (
                                self._delete_record(sid)
                            ),
                        ),
                    ],
                    spacing=5,
                )

                self.records_table.rows.append(
                    ft.DataRow(
                        cells=[
                            ft.DataCell(ft.Text(student_id, size=12)),
                            ft.DataCell(ft.Text(fio, size=12)),
                            ft.DataCell(ft.Text(class_name, size=12)),
                            ft.DataCell(
                                ft.Text(str(len(selected_exams)), size=12),
                            ),
                            ft.DataCell(ft.Text(cost_text, size=12)),
                            ft.DataCell(actions),
                        ],
                    ),
                )

        self.page.update()

    # ============================
    # Добавление записи
    # ============================

    def _show_add_dialog(self, e: ft.ControlEvent) -> None:
        """
        Показать диалог добавления нового выбора ЕГЭ.

        Параметры:
            e (ft.ControlEvent): Событие нажатия кнопки «Добавить».

        Логика:
            - Фильтрует учеников, у которых класс имеет тип 'per_subject'.
            - Показывает Dropdown выбора ученика и чекбоксы предметов ЕГЭ
              из настроек класса.
            - При сохранении вызывает exam_db.save_student_exams() и
              обновляет таблицу.

        Ограничения:
            - Если нет учеников 11 класса — показывает SnackBar и выходит.
            - Если не найден класс с exam_subjects — показывает SnackBar.
            - Требует выбора ученика и хотя бы одного предмета.
        """
        # Найти учеников с классом типа per_subject (11 класс / ЕГЭ)
        all_students = self.db.get_all()
        students_11: list[dict] = []
        for student in all_students:
            class_id = student.get("class_id", "")
            class_info = self.classes_db.get_class_by_id(class_id)
            if class_info:
                pricing = class_info.get("pricing", {})
                if pricing.get("type") == "per_subject":
                    students_11.append(student)

        if not students_11:
            self.page.show_snack_bar(
                ft.SnackBar(
                    content=ft.Text("⚠️ В базе нет учеников 11 класса"),
                    bgcolor=ft.colors.ORANGE,
                ),
            )
            return

        # Dropdown учеников 11 класса
        student_options = [
            ft.dropdown.Option(
                key=s["id"],
                text=f"{s['fio']} (ID: {s['id']})",
            )
            for s in students_11
        ]
        student_dropdown = ft.Dropdown(
            label="Выберите ученика",
            options=student_options,
            width=400,
        )

        # Получить список предметов ЕГЭ из первого найденного класса 11
        class_11: dict | None = None
        for student in students_11:
            class_id = student.get("class_id", "")
            class_11 = self.classes_db.get_class_by_id(class_id)
            if class_11:
                break

        if not class_11:
            self.page.show_snack_bar(
                ft.SnackBar(
                    content=ft.Text("⚠️ Не найден класс 11"),
                    bgcolor=ft.colors.RED,
                ),
            )
            return

        exam_subjects = class_11.get("exam_subjects", [])

        # Чекбоксы для выбора предметов
        exam_checkboxes: list[ft.Checkbox] = []
        exam_container = ft.Column(spacing=5)
        for exam in exam_subjects:
            cb = ft.Checkbox(label=exam, value=False)
            exam_checkboxes.append(cb)
            exam_container.controls.append(cb)

        def save_choice(ev: ft.ControlEvent) -> None:
            """
            Сохранить новый выбор ЕГЭ в базу данных.

            Параметры:
                ev (ft.ControlEvent): Событие нажатия кнопки «Сохранить».

            Логика:
                - Проверяет, что ученик выбран.
                - Проверяет, что отмечен хотя бы один предмет.
                - Вызывает exam_db.save_student_exams() и обновляет таблицу.
            """
            student_id = student_dropdown.value
            if not student_id:
                self.page.show_snack_bar(
                    ft.SnackBar(
                        content=ft.Text("⚠️ Выберите ученика"),
                        bgcolor=ft.colors.ORANGE,
                    ),
                )
                return

            selected_exams = [
                cb.label for cb in exam_checkboxes if cb.value
            ]
            if not selected_exams:
                self.page.show_snack_bar(
                    ft.SnackBar(
                        content=ft.Text(
                            "⚠️ Выберите хотя бы один предмет ЕГЭ",
                        ),
                        bgcolor=ft.colors.ORANGE,
                    ),
                )
                return

            self.exam_db.save_student_exams(student_id, selected_exams)
            add_dialog.open = False
            self._load_records()
            self.page.show_snack_bar(
                ft.SnackBar(
                    content=ft.Text(
                        f"✅ Выбор ЕГЭ сохранён "
                        f"({len(selected_exams)} предметов)",
                    ),
                    bgcolor=ft.colors.GREEN,
                ),
            )
            self.page.update()

        add_dialog = ft.AlertDialog(
            title=ft.Text("➕ Добавить выбор ЕГЭ"),
            content=ft.Container(
                content=ft.Column(
                    [
                        student_dropdown,
                        ft.Divider(height=10),
                        ft.Text(
                            "Выберите предметы ЕГЭ:",
                            size=13,
                            weight=ft.FontWeight.BOLD,
                        ),
                        ft.Container(
                            content=ft.Column(
                                [exam_container],
                                scroll=ft.ScrollMode.AUTO,
                            ),
                            height=300,
                            border=ft.border.all(1, ft.colors.GREY_300),
                            border_radius=5,
                            padding=10,
                        ),
                    ],
                    spacing=10,
                ),
                width=450,
            ),
            actions=[
                ft.TextButton(
                    "Отмена",
                    on_click=lambda ev: self._close_dialog(add_dialog),
                ),
                ft.ElevatedButton(
                    "Сохранить",
                    on_click=save_choice,
                    bgcolor=ft.colors.GREEN_700,
                    color=ft.colors.WHITE,
                ),
            ],
        )

        self.page.dialog = add_dialog
        add_dialog.open = True
        self.page.update()

    # ============================
    # Редактирование записи
    # ============================

    def _show_edit_dialog(self, choice: dict) -> None:
        """
        Показать диалог редактирования существующего выбора ЕГЭ.

        Параметры:
            choice (dict): Запись выбора ЕГЭ из ExamChoicesDatabase.
                Содержит 'student_id' и 'selected_exams'.

        Логика:
            - Загружает список всех доступных предметов ЕГЭ из класса.
            - Предзаполняет чекбоксы текущим выбором ученика.
            - При сохранении перезаписывает запись через
              exam_db.save_student_exams() и обновляет таблицу.
        """
        student_id = choice.get("student_id", "")
        current_exams = choice.get("selected_exams", [])

        student = self.db.get_by_id(student_id)
        if not student:
            self.page.show_snack_bar(
                ft.SnackBar(
                    content=ft.Text("⚠️ Ученик не найден"),
                    bgcolor=ft.colors.RED,
                ),
            )
            return

        class_id = student.get("class_id", "")
        class_info = self.classes_db.get_class_by_id(class_id)
        if not class_info:
            self.page.show_snack_bar(
                ft.SnackBar(
                    content=ft.Text("⚠️ Класс не найден"),
                    bgcolor=ft.colors.RED,
                ),
            )
            return

        exam_subjects = class_info.get("exam_subjects", [])

        # Чекбоксы с предзаполнением текущего выбора
        exam_checkboxes: list[ft.Checkbox] = []
        exam_container = ft.Column(spacing=5)
        for exam in exam_subjects:
            cb = ft.Checkbox(label=exam, value=(exam in current_exams))
            exam_checkboxes.append(cb)
            exam_container.controls.append(cb)

        def save_changes(ev: ft.ControlEvent) -> None:
            """
            Сохранить изменённый список предметов ЕГЭ.

            Параметры:
                ev (ft.ControlEvent): Событие нажатия кнопки «Сохранить».

            Логика:
                - Проверяет, что выбран хотя бы один предмет.
                - Перезаписывает запись через exam_db.save_student_exams()
                  и обновляет таблицу.
            """
            selected_exams = [
                cb.label for cb in exam_checkboxes if cb.value
            ]
            if not selected_exams:
                self.page.show_snack_bar(
                    ft.SnackBar(
                        content=ft.Text(
                            "⚠️ Выберите хотя бы один предмет ЕГЭ",
                        ),
                        bgcolor=ft.colors.ORANGE,
                    ),
                )
                return

            self.exam_db.save_student_exams(student_id, selected_exams)
            edit_dialog.open = False
            self._load_records()
            self.page.show_snack_bar(
                ft.SnackBar(
                    content=ft.Text("✅ Выбор ЕГЭ обновлён"),
                    bgcolor=ft.colors.GREEN,
                ),
            )
            self.page.update()

        edit_dialog = ft.AlertDialog(
            title=ft.Text(f"✏️ Редактировать: {student.get('fio')}"),
            content=ft.Container(
                content=ft.Column(
                    [
                        ft.Text(
                            f"ID: {student_id}",
                            size=12,
                            color=ft.colors.GREY_700,
                        ),
                        ft.Divider(height=10),
                        ft.Text(
                            "Выберите предметы ЕГЭ:",
                            size=13,
                            weight=ft.FontWeight.BOLD,
                        ),
                        ft.Container(
                            content=ft.Column(
                                [exam_container],
                                scroll=ft.ScrollMode.AUTO,
                            ),
                            height=300,
                            border=ft.border.all(1, ft.colors.GREY_300),
                            border_radius=5,
                            padding=10,
                        ),
                    ],
                    spacing=10,
                ),
                width=450,
            ),
            actions=[
                ft.TextButton(
                    "Отмена",
                    on_click=lambda ev: self._close_dialog(edit_dialog),
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

    # ============================
    # Просмотр записи
    # ============================

    def _show_info(self, choice: dict) -> None:
        """
        Показать диалог с подробной информацией о выборе ЕГЭ.

        Параметры:
            choice (dict): Запись выбора ЕГЭ из ExamChoicesDatabase.
                Содержит 'student_id' и 'selected_exams'.

        Отображает:
            - ФИО ученика, его ID и класс.
            - Список выбранных предметов ЕГЭ с маркерами.
            - Итоговую стоимость с формулой (N × 3 000₽).
        """
        student_id = choice.get("student_id", "")
        selected_exams = choice.get("selected_exams", [])

        student = self.db.get_by_id(student_id)
        if student:
            fio = student.get("fio", "N/A")
            class_id = student.get("class_id", "")
            class_info = self.classes_db.get_class_by_id(class_id)
            class_name = class_info["name"] if class_info else class_id
        else:
            fio = "Ученик не найден"
            class_name = "N/A"

        exams_text = "\n".join([f"• {exam}" for exam in selected_exams])
        cost = self.exam_db.calculate_exam_cost(selected_exams, 3000)

        info_dialog = ft.AlertDialog(
            title=ft.Text("ℹ️ Информация о выборе ЕГЭ"),
            content=ft.Container(
                content=ft.Column(
                    [
                        ft.Text(f"ФИО: {fio}", size=13),
                        ft.Text(f"ID ученика: {student_id}", size=13),
                        ft.Text(f"Класс: {class_name}", size=13),
                        ft.Divider(height=10),
                        ft.Text(
                            f"Выбрано предметов: {len(selected_exams)}",
                            size=13,
                            weight=ft.FontWeight.BOLD,
                        ),
                        ft.Text(
                            exams_text,
                            size=12,
                            color=ft.colors.GREY_700,
                        ),
                        ft.Divider(height=10),
                        ft.Text(
                            (
                                f"Стоимость: {int(cost):,}₽ "
                                f"({len(selected_exams)} × 3 000₽)"
                            ).replace(",", " "),
                            size=13,
                            color=ft.colors.GREEN_700,
                            weight=ft.FontWeight.BOLD,
                        ),
                    ],
                    spacing=8,
                ),
                width=400,
            ),
            actions=[
                ft.TextButton(
                    "Закрыть",
                    on_click=lambda ev: self._close_dialog(info_dialog),
                ),
            ],
        )

        self.page.dialog = info_dialog
        info_dialog.open = True
        self.page.update()

    # ============================
    # Удаление записи
    # ============================

    def _delete_record(self, student_id: str) -> None:
        """
        Показать диалог подтверждения и удалить запись выбора ЕГЭ.

        Параметры:
            student_id (str): ID ученика, чья запись будет удалена.

        Логика:
            - Показывает диалог подтверждения перед удалением.
            - При подтверждении вызывает exam_db.delete_student_exams()
              и перезагружает таблицу.
        """
        def confirm_delete(ev: ft.ControlEvent) -> None:
            """
            Выполнить удаление после подтверждения пользователем.

            Параметры:
                ev (ft.ControlEvent): Событие нажатия кнопки «Удалить».
            """
            self.exam_db.delete_student_exams(student_id)
            delete_dialog.open = False
            self._load_records()
            self.page.show_snack_bar(
                ft.SnackBar(
                    content=ft.Text("✅ Запись удалена"),
                    bgcolor=ft.colors.GREEN,
                ),
            )
            self.page.update()

        delete_dialog = ft.AlertDialog(
            title=ft.Row(
                [
                    ft.Icon(ft.icons.WARNING, color=ft.colors.RED_700),
                    ft.Text("Удалить выбор ЕГЭ?"),
                ],
            ),
            content=ft.Text(
                f"Вы уверены, что хотите удалить выбор ЕГЭ "
                f"для ученика ID: {student_id}?",
            ),
            actions=[
                ft.TextButton(
                    "Отмена",
                    on_click=lambda ev: self._close_dialog(delete_dialog),
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
