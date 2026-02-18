"""
Страница управления учениками
"""
import flet as ft
from core.data.student_db import StudentDatabase
from core.data.classes_db import ClassesDatabase
from core.data.exam_choices_db import ExamChoicesDatabase

from pathlib import Path
import csv
import platform
import os


class StudentsPage:
    """Страница управления учениками"""

    def __init__(self, page: ft.Page):
        self.page = page
        self.db = StudentDatabase()
        self.classes_db = ClassesDatabase()
        self.exam_db = ExamChoicesDatabase()
        self.students_table = None
        self.search_field = None
        self.class_filter = None  # ДОБАВИТЬ ЭТУ СТРОКУ

    def build(self) -> ft.Column:
        """Построить интерфейс страницы"""

        # Поле поиска
        self.search_field = ft.TextField(
            label="Поиск по ФИО",
            width=300,
            dense=True,
            on_change=self._on_search,
        )

        # Фильтр по классам
        classes = self.classes_db.get_all_classes()
        class_filter_options = [ft.dropdown.Option(key="", text="Все классы")]
        class_filter_options.extend([
            ft.dropdown.Option(key=c['id'], text=c['name'])
            for c in classes
        ])

        self.class_filter = ft.Dropdown(
            label="Фильтр по классу",
            options=class_filter_options,
            width=200,
            value="",
            dense=True,
            on_change=self._on_class_filter_change,
        )

        # Кнопки управления
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

        # Таблица учеников
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

        # Загрузить данные
        self._load_students()

        # Layout
        return ft.Column(
            controls=[
                # Заголовок
                ft.Text(
                    "👥 Управление учениками",
                    size=20,
                    weight=ft.FontWeight.BOLD,
                ),

                ft.Divider(height=3),

                # Панель управления
                ft.Row([
                    self.search_field,
                    self.class_filter,  # ДОБАВИТЬ
                    add_btn,
                    import_btn,
                    export_btn,
                    clear_btn,
                ], spacing=10, wrap=True),

                ft.Divider(height=3),

                # Таблица
                ft.Container(
                    content=ft.Column([
                        self.students_table,
                    ], scroll=ft.ScrollMode.AUTO),
                    expand=True,
                ),
            ],
            spacing=6,
            expand=True,
        )

    def _load_students(self, search_query: str = "", class_filter: str = ""):

        """Загрузить список учеников"""

        # Получить учеников
        if search_query:
            students = self.db.search(search_query)
        else:
            students = self.db.get_all()

        # Применить фильтр по классу
        if class_filter:
            students = [s for s in students if s.get('class_id') == class_filter]

        # Очистить таблицу
        self.students_table.rows.clear()

        # Заполнить таблицу
        for student in students:
            # Получить название класса
            class_info = self.classes_db.get_class_by_id(student.get('class_id', ''))
            class_name = class_info['name'] if class_info else student.get('class_id', 'N/A')


            # Кнопки действий
            actions = ft.Row([
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
                    on_click=lambda e, s=student: self._show_edit_dialog(s),
                ),
                ft.IconButton(
                    icon=ft.icons.DELETE,
                    icon_color=ft.colors.RED_700,
                    icon_size=20,
                    tooltip="Удалить",
                    on_click=lambda e, s=student: self._delete_student(s),
                ),
            ], spacing=5)

            # Добавить строку
            row = ft.DataRow(
                cells=[
                    ft.DataCell(ft.Text(student['id'], size=12)),
                    ft.DataCell(ft.Text(student['fio'], size=12)),
                    ft.DataCell(ft.Text(student['contract_number'], size=12)),
                    ft.DataCell(ft.Text(class_name, size=12)),
                    ft.DataCell(actions),
                ],
            )

            self.students_table.rows.append(row)

        self.page.update()

    def _on_search(self, e):
        """Обработчик поиска"""
        search_query = self.search_field.value if self.search_field.value else ""
        class_filter = self.class_filter.value if self.class_filter else ""
        self._load_students(search_query=search_query, class_filter=class_filter)

    def _show_add_dialog(self, e):
        """Показать диалог добавления ученика"""

        # Получить список классов
        classes = self.classes_db.get_all_classes()
        class_options = [
            ft.dropdown.Option(key=c['id'], text=c['name'])
            for c in classes
        ]

        # Поля формы
        fio_field = ft.TextField(label="ФИО", width=400)
        contract_field = ft.TextField(label="Номер договора", width=200)
        # Контейнер для выбора ЕГЭ (для 11 класса)
        exam_selection_container = ft.Column(visible=False)

        def on_class_change(e):
            # Обновить информацию о цене
            self._update_price_info(e, class_dropdown, price_info_text)

            # Показать выбор ЕГЭ для 11 класса
            class_id = class_dropdown.value
            if class_id:
                class_info = self.classes_db.get_class_by_id(class_id)
                if class_info and class_info.get('pricing', {}).get('type') == 'per_subject':
                    # Это 11 класс с ЕГЭ
                    exam_selection_container.visible = True
                    exam_selection_container.controls.clear()

                    exam_subjects = class_info.get('exam_subjects', [])
                    exam_checkboxes = []

                    exam_selection_container.controls.append(
                        ft.Text("Выберите предметы ЕГЭ:", size=13, weight=ft.FontWeight.BOLD)
                    )

                    for exam in exam_subjects:
                        cb = ft.Checkbox(label=exam, value=False)
                        exam_checkboxes.append(cb)
                        exam_selection_container.controls.append(cb)

                    # Сохранить ссылки на чекбоксы
                    exam_selection_container.data = exam_checkboxes
                else:
                    exam_selection_container.visible = False
            else:
                exam_selection_container.visible = False

            self.page.update()

        class_dropdown = ft.Dropdown(
            label="Класс",
            options=class_options,
            width=200,
            on_change=on_class_change,
        )

        compensation_field = ft.TextField(label="Компенсация", width=200)

        price_info_text = ft.Text("", size=12, color=ft.colors.GREY_700)

        def save_student(e):
            self._save_add_student(
                add_dialog,
                fio_field.value,
                contract_field.value,
                class_dropdown.value,
                compensation_field.value,
            )

        add_dialog = ft.AlertDialog(
            title=ft.Text("➕ Добавить ученика"),
            content=ft.Container(
                content=ft.Column([
                    fio_field,
                    contract_field,
                    class_dropdown,
                    price_info_text,
                    exam_selection_container,  # ДОБАВИТЬ
                    compensation_field,
                ], spacing=10, scroll=ft.ScrollMode.AUTO),
                width=450,
                height=500,  # Увеличить высоту
            ),
            actions=[
                ft.TextButton("Отмена", on_click=lambda e: self._close_dialog(add_dialog)),
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

    def _update_price_info(self, e, class_dropdown, price_info_text):
        """Обновить информацию о цене"""
        class_id = class_dropdown.value
        if class_id:
            price_info = self.classes_db.get_price_info(class_id)
            price_info_text.value = price_info
        else:
            price_info_text.value = ""
        self.page.update()

    def _save_add_student(self, dialog, fio, contract, class_id, compensation, selected_exams=None):
        """Сохранить нового ученика"""

        # Валидация
        if not fio or not contract or not class_id:
            self.page.show_snack_bar(
                ft.SnackBar(
                    content=ft.Text("⚠️ Заполните все обязательные поля"),
                    bgcolor=ft.colors.ORANGE,
                )
            )
            return

        # Для 11 класса проверить выбор ЕГЭ
        class_info = self.classes_db.get_class_by_id(class_id)
        if class_info and class_info.get('pricing', {}).get('type') == 'per_subject':
            if not selected_exams or len(selected_exams) == 0:
                self.page.show_snack_bar(
                    ft.SnackBar(
                        content=ft.Text("⚠️ Выберите хотя бы один предмет ЕГЭ"),
                        bgcolor=ft.colors.ORANGE,
                    )
                )
                return

            # Рассчитать стоимость по ЕГЭ
            monthly_payment = self.exam_db.calculate_exam_cost(selected_exams, 3000)
        else:
            # Для остальных классов - фиксированная стоимость
            monthly_payment = self.classes_db.calculate_price(class_id, [])

        # Добавить в базу
        result = self.db.add(
            fio=fio,
            contract_number=contract,
            class_id=class_id,
            monthly_payment=monthly_payment,
            compensation=compensation
        )

        if result:
            # Сохранить выбор ЕГЭ если есть
            if selected_exams:
                self.exam_db.save_student_exams(result['id'], selected_exams)

            dialog.open = False
            self._load_students()
            self.page.show_snack_bar(
                ft.SnackBar(
                    content=ft.Text(f"✅ Ученик {fio} добавлен"),
                    bgcolor=ft.colors.GREEN,
                )
            )
        else:
            self.page.show_snack_bar(
                ft.SnackBar(
                    content=ft.Text("⚠️ Такой ученик уже существует"),
                    bgcolor=ft.colors.ORANGE,
                )
            )

        self.page.update()


    def _show_edit_dialog(self, student):
        """Показать диалог редактирования"""

        # Получить список классов для фильтра
        classes = self.classes_db.get_all_classes()
        class_filter_options = [ft.dropdown.Option(key="", text="Все классы")]  # Опция "все"
        class_filter_options.extend([
            ft.dropdown.Option(key=c['id'], text=c['name'])
            for c in classes
        ])

        # Выпадающий список фильтра по классам
        class_filter = ft.Dropdown(
            label="Фильтр по классу",
            options=class_filter_options,
            width=200,
            value="",
            dense=True,
            on_change=lambda e: self._load_students(class_filter=e.control.value),
        )

        # Поля формы (заполненные)
        fio_field = ft.TextField(label="ФИО", width=400, value=student.get('fio', ''))
        contract_field = ft.TextField(label="Номер договора", width=200, value=student.get('contract_number', ''))
        # Получить список классов
        classes = self.classes_db.get_all_classes()
        class_options = [
            ft.dropdown.Option(key=c['id'], text=c['name'])
            for c in classes
        ]

        class_dropdown = ft.Dropdown(
            label="Класс",
            options=class_options,
            width=200,
            value=student.get('class_id', ''),
            on_change=lambda e: self._update_price_info(e, class_dropdown, price_info_text),
        )
        compensation_field = ft.TextField(label="Компенсация", width=200, value=student.get('compensation', ''))

        price_info = self.classes_db.get_price_info(student.get('class_id', ''))
        price_info_text = ft.Text(price_info, size=12, color=ft.colors.GREY_700)

        def save_changes(e):
            self._save_edit_student(
                edit_dialog,
                student['id'],
                fio_field.value,
                contract_field.value,
                class_dropdown.value,
                compensation_field.value,
            )

        edit_dialog = ft.AlertDialog(
            title=ft.Text("✏️ Редактировать ученика"),
            content=ft.Container(
                content=ft.Column([
                    fio_field,
                    contract_field,
                    class_dropdown,
                    price_info_text,
                    compensation_field,
                ], spacing=10, scroll=ft.ScrollMode.AUTO),
                width=450,
                height=400,
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

    def _save_edit_student(self, dialog, student_id, fio, contract, class_id, compensation):
        """Сохранить изменения ученика"""

        # Валидация
        if not fio or not contract or not class_id:
            self.page.show_snack_bar(
                ft.SnackBar(
                    content=ft.Text("⚠️ Заполните все обязательные поля"),
                    bgcolor=ft.colors.ORANGE,
                )
            )
            return

        # Рассчитать стоимость
        monthly_payment = self.classes_db.calculate_price(class_id, [])

        # Обновить в базе
        success = self.db.update(
            student_id=student_id,
            fio=fio,
            contract_number=contract,
            class_id=class_id,
            monthly_payment=monthly_payment,
            compensation=compensation
        )

        if success:
            dialog.open = False
            self._load_students()
            self.page.show_snack_bar(
                ft.SnackBar(
                    content=ft.Text(f"✅ Данные обновлены"),
                    bgcolor=ft.colors.GREEN,
                )
            )

        self.page.update()

    def _delete_student(self, student):
        """Удалить ученика"""

        def confirm_delete(e):
            self.db.delete(student['id'])
            delete_dialog.open = False
            self._load_students()
            self.page.show_snack_bar(
                ft.SnackBar(
                    content=ft.Text(f"✅ Ученик удалён"),
                    bgcolor=ft.colors.GREEN,
                )
            )
            self.page.update()

        delete_dialog = ft.AlertDialog(
            title=ft.Row([
                ft.Icon(ft.icons.WARNING, color=ft.colors.RED_700),
                ft.Text("Удалить ученика?"),
            ]),
            content=ft.Text(f"Вы уверены, что хотите удалить:\n{student['fio']} ({student['contract_number']})?"),
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

    def _show_info(self, student):
        """Показать информацию об ученике"""

        # Получить класс и предметы
        class_info = self.classes_db.get_class_by_id(student.get('class_id', ''))
        class_name = class_info['name'] if class_info else student.get('class_id', 'N/A')

        subjects = []
        if class_info:
            subjects = self.classes_db.get_subjects_by_class(student.get('class_id', ''))

        subjects_text = ", ".join(subjects) if subjects else "Не указаны"

        info_dialog = ft.AlertDialog(
            title=ft.Text(f"ℹ️ {student['fio']}"),
            content=ft.Container(
                content=ft.Column([
                    ft.Text(f"ID: {student['id']}", size=13),
                    ft.Text(f"Договор: {student['contract_number']}", size=13),
                    ft.Text(f"Класс: {class_name}", size=13),
                    ft.Text(f"Оплата: {student.get('monthly_payment', 0):,} ₽".replace(',', ' '), size=13),
                    ft.Text(f"Компенсация: {student.get('compensation', 'Нет')}", size=13),
                    ft.Divider(height=10),
                    ft.Text("Предметы класса:", size=13, weight=ft.FontWeight.BOLD),
                    ft.Text(subjects_text, size=12, color=ft.colors.GREY_700),
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

    def _import_csv(self, e):
        """Импорт из CSV"""

        def pick_files_result(e: ft.FilePickerResultEvent):
            if e.files and len(e.files) > 0:
                self._process_csv_import(e.files[0].path)

        file_picker = ft.FilePicker(on_result=pick_files_result)
        self.page.overlay.append(file_picker)
        self.page.update()

        file_picker.pick_files(
            dialog_title="Выберите CSV файл для импорта",
            allowed_extensions=["csv"],
            allow_multiple=False,
        )

    def _process_csv_import(self, file_path):
        """Обработать импорт CSV"""

        try:
            success_count = 0
            error_count = 0
            errors = []

            with open(file_path, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)

                for row in reader:
                    try:
                        fio = row.get('fio', '').strip()
                        contract = row.get('contract_number', '').strip()
                        class_id = row.get('class_id', '').strip()
                        compensation = row.get('compensation', '').strip()

                        if not fio or not contract or not class_id:
                            error_count += 1
                            errors.append(f"{fio or 'N/A'}: Пропущены обязательные поля")
                            continue

                        # Рассчитать стоимость
                        monthly_payment = self.classes_db.calculate_price(class_id, [])

                        # Добавить
                        result = self.db.add(
                            fio=fio,
                            contract_number=contract,
                            class_id=class_id,
                            monthly_payment=monthly_payment,
                            compensation=compensation
                        )

                        if result:
                            success_count += 1
                        else:
                            error_count += 1
                            errors.append(f"{fio}: Дубликат")

                    except Exception as ex:
                        error_count += 1
                        errors.append(f"{row.get('fio', 'N/A')}: {str(ex)}")

            # Обновить таблицу
            self._load_students()

            # Показать результат
            if error_count == 0:
                self.page.show_snack_bar(
                    ft.SnackBar(
                        content=ft.Text(f"✅ Импортировано: {success_count} учеников"),
                        bgcolor=ft.colors.GREEN,
                    )
                )
            else:
                error_text = "\n".join(errors[:5])
                if len(errors) > 5:
                    error_text += f"\n... и еще {len(errors) - 5}"

                # Диалог с ошибками
                error_dialog = ft.AlertDialog(
                    title=ft.Text("⚠️ Импорт завершён с ошибками"),
                    content=ft.Container(
                        content=ft.Column([
                            ft.Text(f"✅ Импортировано: {success_count}", size=13, color=ft.colors.GREEN),
                            ft.Text(f"❌ Ошибок: {error_count}", size=13, color=ft.colors.RED),
                            ft.Divider(height=10),
                            ft.Text("Ошибки:", size=12, weight=ft.FontWeight.BOLD),
                            ft.Text(error_text, size=11, color=ft.colors.RED),
                        ], spacing=8, scroll=ft.ScrollMode.AUTO),
                        width=500,
                        height=300,
                    ),
                    actions=[
                        ft.TextButton("Закрыть", on_click=lambda e: self._close_dialog(error_dialog)),
                    ],
                )

                self.page.dialog = error_dialog
                error_dialog.open = True

        except Exception as ex:
            self.page.show_snack_bar(
                ft.SnackBar(
                    content=ft.Text(f"❌ Ошибка чтения файла: {str(ex)}"),
                    bgcolor=ft.colors.RED,
                )
            )

        self.page.update()

    def _export_csv(self, e):
        """Экспорт в CSV"""

        students = self.db.get_all()

        if not students:
            self.page.show_snack_bar(
                ft.SnackBar(
                    content=ft.Text("⚠️ Нет данных для экспорта"),
                    bgcolor=ft.colors.ORANGE,
                )
            )
            return

        def save_file_result(e: ft.FilePickerResultEvent):
            if e.path:
                try:
                    # Записать CSV
                    with open(e.path, 'w', encoding='utf-8', newline='') as f:
                        fieldnames = ['id', 'fio', 'contract_number', 'class_id', 'monthly_payment', 'compensation']
                        writer = csv.DictWriter(f, fieldnames=fieldnames)

                        writer.writeheader()
                        for student in students:
                            writer.writerow({
                                'id': student['id'],
                                'fio': student['fio'],
                                'contract_number': student['contract_number'],
                                'class_id': student.get('class_id', ''),
                                'monthly_payment': student.get('monthly_payment', 0),
                                'compensation': student.get('compensation', ''),
                            })

                    # Показать уведомление
                    self.page.show_snack_bar(
                        ft.SnackBar(
                            content=ft.Text(f"✅ Экспортировано: {len(students)} учеников"),
                            bgcolor=ft.colors.GREEN,
                        )
                    )

                    # Открыть папку с файлом
                    import os
                    file_dir = Path(e.path).parent
                    try:
                        if platform.system() == 'Darwin':
                            os.system(f'open "{file_dir}"')
                        elif platform.system() == 'Windows':
                            os.startfile(str(file_dir))
                        else:
                            os.system(f'xdg-open "{file_dir}"')
                    except:
                        pass

                except Exception as ex:
                    self.page.show_snack_bar(
                        ft.SnackBar(
                            content=ft.Text(f"❌ Ошибка: {str(ex)}"),
                            bgcolor=ft.colors.RED,
                        )
                    )

        # Создать file picker для сохранения
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

    def _clear_database(self, e):
        """Очистить базу данных"""

        def confirm_clear(e):
            self.db.clear_all()
            clear_dialog.open = False
            self._load_students()
            self.page.show_snack_bar(
                ft.SnackBar(
                    content=ft.Text("✅ База данных очищена"),
                    bgcolor=ft.colors.GREEN,
                )
            )
            self.page.update()

        clear_dialog = ft.AlertDialog(
            title=ft.Row([
                ft.Icon(ft.icons.WARNING, color=ft.colors.RED_700),
                ft.Text("Очистить базу данных?"),
            ]),
            content=ft.Text(
                "⚠️ ВСЕ ДАННЫЕ БУДУТ УДАЛЕНЫ БЕЗВОЗВРАТНО!\n\n"
                "Рекомендуется сначала сделать экспорт в CSV.",
                size=13,
            ),
            actions=[
                ft.TextButton("Отмена", on_click=lambda e: self._close_dialog(clear_dialog)),
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

    def _close_dialog(self, dialog):
        """Закрыть диалог"""
        dialog.open = False
        self.page.update()

    def _on_class_filter_change(self, e):
        """Обработчик изменения фильтра по классу"""
        class_filter = self.class_filter.value
        search_query = self.search_field.value if self.search_field.value else ""
        self._load_students(search_query=search_query, class_filter=class_filter)

