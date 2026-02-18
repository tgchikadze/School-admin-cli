"""
Страница выбора ЕГЭ для 11 класса
"""
import flet as ft
from core.data.student_db import StudentDatabase
from core.data.classes_db import ClassesDatabase
from core.data.exam_choices_db import ExamChoicesDatabase


class ExamSelectionPage:
    """Страница управления выбором ЕГЭ"""

    def __init__(self, page: ft.Page):
        self.page = page
        self.db = StudentDatabase()
        self.classes_db = ClassesDatabase()
        self.exam_db = ExamChoicesDatabase()
        self.records_table = None

    def build(self) -> ft.Column:
        """Построить интерфейс страницы"""

        # Кнопка добавления записи
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
                ft.DataColumn(ft.Text("ФИО ученика", weight=ft.FontWeight.BOLD)),
                ft.DataColumn(ft.Text("Класс", weight=ft.FontWeight.BOLD)),
                ft.DataColumn(ft.Text("Предметов ЕГЭ", weight=ft.FontWeight.BOLD)),
                ft.DataColumn(ft.Text("Стоимость", weight=ft.FontWeight.BOLD)),
                ft.DataColumn(ft.Text("Действия", weight=ft.FontWeight.BOLD)),
            ],
            rows=[],
            border=ft.border.all(1, ft.colors.GREY_300),
            border_radius=8,
            heading_row_color=ft.colors.GREY_100,
        )

        # Загрузить данные
        self._load_records()

        # Layout
        return ft.Column(
            controls=[
                ft.Text(
                    "🎓 Управление выбором ЕГЭ",
                    size=20,
                    weight=ft.FontWeight.BOLD,
                ),

                ft.Divider(height=3),

                # Панель управления
                ft.Row([add_btn], spacing=10),

                ft.Divider(height=3),

                # Таблица
                ft.Container(
                    content=ft.Column([
                        self.records_table,
                    ], scroll=ft.ScrollMode.AUTO),
                    expand=True,
                ),
            ],
            spacing=6,
            expand=True,
        )

    def _load_records(self):
        """Загрузить все записи выбора ЕГЭ"""

        # Получить все записи
        data = self.exam_db._load()
        exam_choices = data.get('exam_choices', [])

        # Очистить таблицу
        self.records_table.rows.clear()

        if not exam_choices:
            # Пустая таблица
            self.records_table.rows.append(
                ft.DataRow(
                    cells=[
                        ft.DataCell(ft.Text("—", size=12)),
                        ft.DataCell(ft.Text("Нет записей", size=12, color=ft.colors.GREY_600, italic=True)),
                        ft.DataCell(ft.Text("—", size=12)),
                        ft.DataCell(ft.Text("—", size=12)),
                        ft.DataCell(ft.Text("—", size=12)),
                        ft.DataCell(ft.Text("—", size=12)),
                    ],
                )
            )
        else:
            # Заполнить таблицу
            for choice in exam_choices:
                student_id = choice.get('student_id', '')
                selected_exams = choice.get('selected_exams', [])

                # Получить данные ученика
                student = self.db.get_by_id(student_id)

                if student:
                    fio = student.get('fio', 'N/A')
                    class_id = student.get('class_id', '')
                    class_info = self.classes_db.get_class_by_id(class_id)
                    class_name = class_info['name'] if class_info else class_id
                else:
                    fio = f"Ученик не найден (ID: {student_id})"
                    class_name = "N/A"

                # Рассчитать стоимость
                cost = self.exam_db.calculate_exam_cost(selected_exams, 3000)
                cost_text = f"{int(cost):,}₽".replace(',', ' ')

                # Кнопки действий
                actions = ft.Row([
                    ft.IconButton(
                        icon=ft.icons.INFO,
                        icon_color=ft.colors.BLUE_700,
                        icon_size=20,
                        tooltip="Просмотр",
                        on_click=lambda e, c=choice: self._show_info(c),
                    ),
                    ft.IconButton(
                        icon=ft.icons.EDIT,
                        icon_color=ft.colors.ORANGE_700,
                        icon_size=20,
                        tooltip="Редактировать",
                        on_click=lambda e, c=choice: self._show_edit_dialog(c),
                    ),
                    ft.IconButton(
                        icon=ft.icons.DELETE,
                        icon_color=ft.colors.RED_700,
                        icon_size=20,
                        tooltip="Удалить",
                        on_click=lambda e, sid=student_id: self._delete_record(sid),
                    ),
                ], spacing=5)

                # Добавить строку
                row = ft.DataRow(
                    cells=[
                        ft.DataCell(ft.Text(student_id, size=12)),
                        ft.DataCell(ft.Text(fio, size=12)),
                        ft.DataCell(ft.Text(class_name, size=12)),
                        ft.DataCell(ft.Text(str(len(selected_exams)), size=12)),
                        ft.DataCell(ft.Text(cost_text, size=12)),
                        ft.DataCell(actions),
                    ],
                )

                self.records_table.rows.append(row)

        self.page.update()

    def _show_add_dialog(self, e):
        """Показать диалог добавления выбора ЕГЭ"""

        # Получить учеников 11 класса
        all_students = self.db.get_all()
        students_11 = []

        for student in all_students:
            class_id = student.get('class_id', '')
            class_info = self.classes_db.get_class_by_id(class_id)
            if class_info:
                pricing = class_info.get('pricing', {})
                if pricing.get('type') == 'per_subject':
                    students_11.append(student)

        if not students_11:
            self.page.show_snack_bar(
                ft.SnackBar(
                    content=ft.Text("⚠️ В базе нет учеников 11 класса"),
                    bgcolor=ft.colors.ORANGE,
                )
            )
            return

        # Выпадающий список учеников
        student_options = [
            ft.dropdown.Option(key=s['id'], text=f"{s['fio']} (ID: {s['id']})")
            for s in students_11
        ]

        student_dropdown = ft.Dropdown(
            label="Выберите ученика",
            options=student_options,
            width=400,
        )

        # Получить все предметы ЕГЭ
        class_11 = None
        for student in students_11:
            class_id = student.get('class_id', '')
            class_11 = self.classes_db.get_class_by_id(class_id)
            if class_11:
                break

        if not class_11:
            self.page.show_snack_bar(
                ft.SnackBar(
                    content=ft.Text("⚠️ Не найден класс 11"),
                    bgcolor=ft.colors.RED,
                )
            )
            return

        exam_subjects = class_11.get('exam_subjects', [])

        # Чекбоксы для выбора ЕГЭ
        exam_checkboxes = []
        exam_container = ft.Column(spacing=5)

        for exam in exam_subjects:
            cb = ft.Checkbox(label=exam, value=False)
            exam_checkboxes.append(cb)
            exam_container.controls.append(cb)

        def save_choice(e):
            student_id = student_dropdown.value
            if not student_id:
                self.page.show_snack_bar(
                    ft.SnackBar(
                        content=ft.Text("⚠️ Выберите ученика"),
                        bgcolor=ft.colors.ORANGE,
                    )
                )
                return

            selected_exams = [cb.label for cb in exam_checkboxes if cb.value]

            if not selected_exams:
                self.page.show_snack_bar(
                    ft.SnackBar(
                        content=ft.Text("⚠️ Выберите хотя бы один предмет ЕГЭ"),
                        bgcolor=ft.colors.ORANGE,
                    )
                )
                return

            # Сохранить
            self.exam_db.save_student_exams(student_id, selected_exams)

            add_dialog.open = False
            self._load_records()
            self.page.show_snack_bar(
                ft.SnackBar(
                    content=ft.Text(f"✅ Выбор ЕГЭ сохранён ({len(selected_exams)} предметов)"),
                    bgcolor=ft.colors.GREEN,
                )
            )
            self.page.update()

        add_dialog = ft.AlertDialog(
            title=ft.Text("➕ Добавить выбор ЕГЭ"),
            content=ft.Container(
                content=ft.Column([
                    student_dropdown,
                    ft.Divider(height=10),
                    ft.Text("Выберите предметы ЕГЭ:", size=13, weight=ft.FontWeight.BOLD),
                    ft.Container(
                        content=ft.Column([exam_container], scroll=ft.ScrollMode.AUTO),
                        height=300,
                        border=ft.border.all(1, ft.colors.GREY_300),
                        border_radius=5,
                        padding=10,
                    ),
                ], spacing=10),
                width=450,
            ),
            actions=[
                ft.TextButton("Отмена", on_click=lambda e: self._close_dialog(add_dialog)),
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

    def _show_edit_dialog(self, choice):
        """Показать диалог редактирования"""

        student_id = choice.get('student_id', '')
        current_exams = choice.get('selected_exams', [])

        # Получить ученика
        student = self.db.get_by_id(student_id)
        if not student:
            self.page.show_snack_bar(
                ft.SnackBar(
                    content=ft.Text("⚠️ Ученик не найден"),
                    bgcolor=ft.colors.RED,
                )
            )
            return

        # Получить все предметы ЕГЭ
        class_id = student.get('class_id', '')
        class_info = self.classes_db.get_class_by_id(class_id)

        if not class_info:
            self.page.show_snack_bar(
                ft.SnackBar(
                    content=ft.Text("⚠️ Класс не найден"),
                    bgcolor=ft.colors.RED,
                )
            )
            return

        exam_subjects = class_info.get('exam_subjects', [])

        # Чекбоксы
        exam_checkboxes = []
        exam_container = ft.Column(spacing=5)

        for exam in exam_subjects:
            cb = ft.Checkbox(label=exam, value=(exam in current_exams))
            exam_checkboxes.append(cb)
            exam_container.controls.append(cb)

        def save_changes(e):
            selected_exams = [cb.label for cb in exam_checkboxes if cb.value]

            if not selected_exams:
                self.page.show_snack_bar(
                    ft.SnackBar(
                        content=ft.Text("⚠️ Выберите хотя бы один предмет ЕГЭ"),
                        bgcolor=ft.colors.ORANGE,
                    )
                )
                return

            # Сохранить
            self.exam_db.save_student_exams(student_id, selected_exams)

            edit_dialog.open = False
            self._load_records()
            self.page.show_snack_bar(
                ft.SnackBar(
                    content=ft.Text(f"✅ Выбор ЕГЭ обновлён"),
                    bgcolor=ft.colors.GREEN,
                )
            )
            self.page.update()

        edit_dialog = ft.AlertDialog(
            title=ft.Text(f"✏️ Редактировать: {student.get('fio')}"),
            content=ft.Container(
                content=ft.Column([
                    ft.Text(f"ID: {student_id}", size=12, color=ft.colors.GREY_700),
                    ft.Divider(height=10),
                    ft.Text("Выберите предметы ЕГЭ:", size=13, weight=ft.FontWeight.BOLD),
                    ft.Container(
                        content=ft.Column([exam_container], scroll=ft.ScrollMode.AUTO),
                        height=300,
                        border=ft.border.all(1, ft.colors.GREY_300),
                        border_radius=5,
                        padding=10,
                    ),
                ], spacing=10),
                width=450,
            ),
            actions=[
                ft.TextButton("Отмена", on_click=lambda e: self._close_dialog(edit_dialog)),
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

    def _show_info(self, choice):
        """Показать подробную информацию"""

        student_id = choice.get('student_id', '')
        selected_exams = choice.get('selected_exams', [])

        # Получить ученика
        student = self.db.get_by_id(student_id)

        if student:
            fio = student.get('fio', 'N/A')
            class_id = student.get('class_id', '')
            class_info = self.classes_db.get_class_by_id(class_id)
            class_name = class_info['name'] if class_info else class_id
        else:
            fio = f"Ученик не найден"
            class_name = "N/A"

        # Список экзаменов
        exams_text = "\n".join([f"• {exam}" for exam in selected_exams])

        # Стоимость
        cost = self.exam_db.calculate_exam_cost(selected_exams, 3000)

        info_dialog = ft.AlertDialog(
            title=ft.Text(f"ℹ️ Информация о выборе ЕГЭ"),
            content=ft.Container(
                content=ft.Column([
                    ft.Text(f"ФИО: {fio}", size=13),
                    ft.Text(f"ID ученика: {student_id}", size=13),
                    ft.Text(f"Класс: {class_name}", size=13),
                    ft.Divider(height=10),
                    ft.Text(f"Выбрано предметов: {len(selected_exams)}", size=13, weight=ft.FontWeight.BOLD),
                    ft.Text(exams_text, size=12, color=ft.colors.GREY_700),
                    ft.Divider(height=10),
                    ft.Text(f"Стоимость: {int(cost):,}₽ ({len(selected_exams)} × 3 000₽)".replace(',', ' '),
                            size=13,
                            color=ft.colors.GREEN_700,
                            weight=ft.FontWeight.BOLD),
                ], spacing=8),
                width=400,
            ),
            actions=[
                ft.TextButton("Закрыть", on_click=lambda e: self._close_dialog(info_dialog)),
            ],
        )

        self.page.dialog = info_dialog
        info_dialog.open = True
        self.page.update()

    def _delete_record(self, student_id):
        """Удалить запись"""

        def confirm_delete(e):
            self.exam_db.delete_student_exams(student_id)
            delete_dialog.open = False
            self._load_records()
            self.page.show_snack_bar(
                ft.SnackBar(
                    content=ft.Text(f"✅ Запись удалена"),
                    bgcolor=ft.colors.GREEN,
                )
            )
            self.page.update()

        delete_dialog = ft.AlertDialog(
            title=ft.Row([
                ft.Icon(ft.icons.WARNING, color=ft.colors.RED_700),
                ft.Text("Удалить выбор ЕГЭ?"),
            ]),
            content=ft.Text(f"Вы уверены, что хотите удалить выбор ЕГЭ для ученика ID: {student_id}?"),
            actions=[
                ft.TextButton("Отмена", on_click=lambda e: self._close_dialog(delete_dialog)),
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

    def _close_dialog(self, dialog):
        """Закрыть диалог"""
        dialog.open = False
        self.page.update()
