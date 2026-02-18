"""
Страница массовой генерации квитанций
"""
import flet as ft
from core.data.student_db import StudentDatabase
from core.data.classes_db import ClassesDatabase
from core.receipt.generator import generate_receipt
from pathlib import Path
from datetime import datetime
import platform
import os

class BatchReceiptsPage:
    """Страница массовой генерации квитанций"""

    def __init__(self, page: ft.Page):
        self.page = page
        self.db = StudentDatabase()
        self.classes_db = ClassesDatabase()

        # Элементы интерфейса
        self.month_field = None
        self.year_field = None
        self.class_filter = None  # *** НОВЫЙ ФИЛЬТР ***
        self.students_checkboxes = []
        self.students_data = []
        self.select_all_checkbox = None
        self.students_container = None
        self.generate_button = None

    def build(self) -> ft.Column:
        """Построить интерфейс страницы"""
        # Текущий месяц и год
        months_ru = [
            "Январь", "Февраль", "Март", "Апрель", "Май", "Июнь",
            "Июль", "Август", "Сентябрь", "Октябрь", "Ноябрь", "Декабрь"
        ]
        current_month = months_ru[datetime.now().month - 1]
        current_year = str(datetime.now().year)

        # Поля месяца и года
        self.month_field = ft.TextField(
            label="Месяц",
            value=current_month,
            width=200,
            dense=True,
            text_size=12,
        )

        self.year_field = ft.TextField(
            label="Год",
            value=current_year,
            width=150,
            dense=True,
            text_size=12,
        )

        # *** НОВЫЙ ФИЛЬТР ПО КЛАССАМ ***
        classes = self.classes_db.get_all_classes()
        class_options = [ft.dropdown.Option(key="", text="Все классы")]  # Опция "все"
        class_options.extend([
            ft.dropdown.Option(key=c['id'], text=c['name'])
            for c in classes
        ])

        self.class_filter = ft.Dropdown(
            label="Фильтр по классу",
            options=class_options,
            width=250,
            dense=True,
            value="",  # По умолчанию "Все классы"
        )

        # Чекбокс "Выбрать всех"
        self.select_all_checkbox = ft.Checkbox(
            label="Выбрать всех",
            value=False,
            on_change=self._on_select_all,
        )

        # Кнопка предпросмотра
        preview_button = ft.ElevatedButton(
            "🔍 Предпросмотр",
            on_click=self._load_students,
            style=ft.ButtonStyle(
                bgcolor=ft.colors.BLUE_700,
                color=ft.colors.WHITE,
            ),
        )

        # Кнопка генерации
        self.generate_button = ft.ElevatedButton(
            "📥 Сгенерировать квитанции",
            on_click=self._generate_batch,
            style=ft.ButtonStyle(
                bgcolor=ft.colors.GREEN_700,
                color=ft.colors.WHITE,
            ),
            disabled=True,
        )

        # Контейнер для списка учеников
        self.students_container = ft.Column(
            spacing=5,
            scroll=ft.ScrollMode.AUTO,
        )

        # Layout
        return ft.Column(
            controls=[
                # Заголовок
                ft.Text(
                    "📊 Массовая генерация квитанций",
                    size=20,
                    weight=ft.FontWeight.BOLD,
                ),
                ft.Divider(height=3),

                # Панель настроек
                ft.Container(
                    content=ft.Column([
                        ft.Text("Настройки генерации:", size=13, weight=ft.FontWeight.BOLD),
                        ft.Row([
                            self.month_field,
                            self.year_field,
                            self.class_filter,  # *** ДОБАВЛЕН ФИЛЬТР ***
                        ], spacing=10, wrap=True),
                        ft.Row([
                            preview_button,
                        ], spacing=10),
                        ft.Text(
                            "💡 Выберите период и класс (или 'Все классы'), затем нажмите 'Предпросмотр'",
                            size=11,
                            italic=True,
                            color=ft.colors.GREY_700,
                        ),
                    ], spacing=10),
                    padding=10,
                    bgcolor=ft.colors.BLUE_50,
                    border_radius=8,
                ),
                ft.Divider(height=3),

                # Панель управления выбором
                ft.Row([
                    self.select_all_checkbox,
                    ft.Container(expand=True),
                    self.generate_button,
                ], spacing=10),

                # Список учеников
                ft.Container(
                    content=self.students_container,
                    expand=True,
                    border=ft.border.all(1, ft.colors.GREY_300),
                    border_radius=8,
                    padding=10,
                ),
            ],
            spacing=6,
            expand=True,
        )

    def _load_students(self, e):
        """Загрузить список учеников для предпросмотра"""
        # Получить всех учеников
        all_students = self.db.get_all()

        if not all_students:
            self.page.show_snack_bar(
                ft.SnackBar(
                    content=ft.Text("⚠️ В базе нет учеников"),
                    bgcolor=ft.colors.ORANGE,
                )
            )
            return

        # *** ПРИМЕНИТЬ ФИЛЬТР ПО КЛАССУ ***
        selected_class = self.class_filter.value
        if selected_class:  # Если выбран конкретный класс
            students = [s for s in all_students if s.get('class_id', '') == selected_class]
            class_info = self.classes_db.get_class_by_id(selected_class)
            class_name = class_info['name'] if class_info else selected_class
            filter_msg = f" для класса '{class_name}'"
        else:  # Все классы
            students = all_students
            filter_msg = ""

        if not students:
            self.page.show_snack_bar(
                ft.SnackBar(
                    content=ft.Text(f"⚠️ Учеников{filter_msg} не найдено"),
                    bgcolor=ft.colors.ORANGE,
                )
            )
            return

        # Очистить контейнер
        self.students_container.controls.clear()
        self.students_checkboxes.clear()
        self.students_data.clear()

        # Создать карточки учеников
        for idx, student in enumerate(students):
            # Получить класс
            class_info = self.classes_db.get_class_by_id(student.get('class_id', ''))
            class_name = class_info['name'] if class_info else student.get('class_id', 'Не указан')

            # Получить предметы из класса
            class_id = student.get('class_id', '')
            if class_id:
                class_info_check = self.classes_db.get_class_by_id(class_id)
                if class_info_check:
                    subjects = self.classes_db.get_subjects_by_class(class_id)
                else:
                    subjects = []
            else:
                subjects = []

            # Убедиться что subjects это список строк
            subjects = [str(s) for s in subjects if s]
            subjects_text = ", ".join(subjects)
            if len(subjects_text) > 60:
                subjects_text = subjects_text[:57] + "..."

            # Чекбокс для выбора
            checkbox = ft.Checkbox(
                value=False,
                on_change=self._on_checkbox_change,
            )

            # Редактируемые поля
            student_fio = ft.TextField(
                value=student.get('fio', ''),
                label="ФИО",
                dense=True,
                text_size=12,
                width=250,
            )

            student_contract = ft.TextField(
                value=student.get('contract_number', ''),
                label="Договор",
                dense=True,
                text_size=12,
                width=120,
            )

            # ВАЖНО: Рассчитать стоимость из класса
            if class_id and subjects:
                calculated_payment = self.classes_db.calculate_price(class_id, subjects)
            else:
                calculated_payment = student.get('monthly_payment', 0)

            student_amount = ft.TextField(
                value=str(calculated_payment),
                label="Сумма",
                dense=True,
                text_size=12,
                width=100,
                keyboard_type=ft.KeyboardType.NUMBER,
            )

            student_compensation = ft.TextField(
                value=student.get('compensation', 0),
                label="Компенсация",
                dense=True,
                text_size=12,
                width=150,
            )

            # Кнопка редактирования предметов
            subjects_button = ft.IconButton(
                icon=ft.icons.EDIT_NOTE,
                icon_color=ft.colors.BLUE_700,
                icon_size=20,
                tooltip="Редактировать предметы",
                on_click=lambda e, s=student, idx=len(self.students_data): self._edit_subjects(idx),
            )

            # Сохранить данные
            student_data = {
                'original': student,
                'checkbox': checkbox,
                'fio': student_fio,
                'contract': student_contract,
                'amount': student_amount,
                'compensation': student_compensation,
                'subjects': subjects.copy(),
                'subjects_button': subjects_button,
            }

            self.students_data.append(student_data)
            self.students_checkboxes.append(checkbox)

            # Карточка ученика
            card = ft.Container(
                content=ft.Column([
                    ft.Row([
                        checkbox,
                        ft.Column([
                            ft.Row([
                                student_fio,
                                student_contract,
                                student_amount,
                                student_compensation,
                                subjects_button,
                            ], spacing=10, wrap=True),
                            ft.Text(f"Класс: {class_name}", size=11, color=ft.colors.GREY_700),
                            ft.Text(f"Предметы: {subjects_text}", size=11, color=ft.colors.GREY_600),
                        ], spacing=3),
                    ]),
                ], spacing=5),
                padding=10,
                border=ft.border.all(1, ft.colors.GREY_300),
                border_radius=8,
                bgcolor=ft.colors.WHITE,
            )

            self.students_container.controls.append(card)

        # Включить кнопку генерации
        self.generate_button.disabled = False
        self.page.show_snack_bar(
            ft.SnackBar(
                content=ft.Text(f"✅ Загружено {len(students)} учеников{filter_msg}"),
                bgcolor=ft.colors.GREEN,
            )
        )
        self.page.update()

    def _edit_subjects(self, student_idx):
        """Редактировать предметы ученика"""
        student_data = self.students_data[student_idx]
        current_subjects = student_data['subjects']

        # Поле для ввода предметов
        subjects_field = ft.TextField(
            label="Предметы (по одному на строку)",
            value="\n".join(current_subjects),
            multiline=True,
            min_lines=5,
            max_lines=10,
            width=400,
        )

        def save_subjects(e):
            # Разбить на строки и убрать пустые
            new_subjects = [s.strip() for s in subjects_field.value.split('\n') if s.strip()]
            student_data['subjects'] = new_subjects
            edit_dialog.open = False
            self.page.show_snack_bar(
                ft.SnackBar(
                    content=ft.Text(f"✅ Предметы обновлены ({len(new_subjects)} шт.)"),
                    bgcolor=ft.colors.GREEN,
                )
            )
            self.page.update()

        edit_dialog = ft.AlertDialog(
            title=ft.Text(f"Редактирование предметов: {student_data['fio'].value}"),
            content=ft.Container(
                content=ft.Column([
                    ft.Text("Введите предметы (по одному на строку):", size=12),
                    subjects_field,
                ], spacing=10),
                width=450,
            ),
            actions=[
                ft.TextButton("Отмена", on_click=lambda e: self._close_dialog(edit_dialog)),
                ft.ElevatedButton("Сохранить", on_click=save_subjects,
                    bgcolor=ft.colors.GREEN_700, color=ft.colors.WHITE),
            ],
        )

        self.page.dialog = edit_dialog
        edit_dialog.open = True
        self.page.update()

    def _on_select_all(self, e):
        """Обработчик "Выбрать всех" """
        select_all = self.select_all_checkbox.value
        for checkbox in self.students_checkboxes:
            checkbox.value = select_all
        self.page.update()

    def _on_checkbox_change(self, e):
        """Обработчик изменения чекбокса"""
        # Проверить, все ли выбраны
        all_selected = all(cb.value for cb in self.students_checkboxes)
        self.select_all_checkbox.value = all_selected
        self.page.update()

    def _generate_batch(self, e):
        """Сгенерировать квитанции для выбранных учеников"""
        # Проверить валидность периода
        if not self.month_field.value or not self.year_field.value:
            self.page.show_snack_bar(
                ft.SnackBar(
                    content=ft.Text("⚠️ Укажите месяц и год"),
                    bgcolor=ft.colors.ORANGE,
                )
            )
            return

        # Собрать выбранных учеников
        selected_students = []
        for student_data in self.students_data:
            if student_data['checkbox'].value:
                selected_students.append(student_data)

        if not selected_students:
            self.page.show_snack_bar(
                ft.SnackBar(
                    content=ft.Text("⚠️ Выберите хотя бы одного ученика"),
                    bgcolor=ft.colors.ORANGE,
                )
            )
            return

        # Показать диалог подтверждения
        self._show_confirmation_dialog(selected_students)

    def _show_confirmation_dialog(self, selected_students):
        """Показать диалог подтверждения генерации"""
        confirm_text = f"Будет создано {len(selected_students)} квитанций за {self.month_field.value} {self.year_field.value}"

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        month_normalized = self.month_field.value.replace(' ', '_')
        default_filename = f"receipts_batch_{month_normalized}_{self.year_field.value}_{timestamp}.pdf"

        def confirm_generate(e):
            confirm_dialog.open = False
            self.page.update()

            # Запустить выбор места сохранения
            def save_file_result(file_e: ft.FilePickerResultEvent):
                if file_e.path:
                    self._perform_generation(selected_students, file_e.path)

            file_picker = ft.FilePicker(on_result=save_file_result)
            self.page.overlay.append(file_picker)
            self.page.update()

            file_picker.save_file(
                dialog_title="Сохранить пакет квитанций",
                file_name=default_filename,
                allowed_extensions=["pdf"],
            )

        confirm_dialog = ft.AlertDialog(
            title=ft.Row([
                ft.Icon(ft.icons.INFO, color=ft.colors.BLUE_700),
                ft.Text("Подтверждение генерации"),
            ]),
            content=ft.Container(
                content=ft.Column([
                    ft.Text(confirm_text, size=13),
                    ft.Divider(height=5),
                    ft.Text(
                        "Квитанции будут объединены в один PDF файл",
                        size=11,
                        color=ft.colors.GREY_700,
                    ),
                ], spacing=10),
                width=400,
            ),
            actions=[
                ft.TextButton("Отмена", on_click=lambda e: self._close_dialog(confirm_dialog)),
                ft.ElevatedButton(
                    "Выбрать место сохранения",
                    on_click=confirm_generate,
                    bgcolor=ft.colors.GREEN_700,
                    color=ft.colors.WHITE,
                ),
            ],
        )

        self.page.dialog = confirm_dialog
        confirm_dialog.open = True
        self.page.update()

    def _perform_generation(self, selected_students, output_path):
        """Выполнить генерацию квитанций в один PDF файл"""
        try:
            from PyPDF2 import PdfMerger
        except ImportError:
            self.page.show_snack_bar(
                ft.SnackBar(
                    content=ft.Text("❌ Ошибка: PyPDF2 не установлен. Выполните: pip install PyPDF2"),
                    bgcolor=ft.colors.RED,
                    duration=10000,
                )
            )
            return

        month_year = f"{self.month_field.value}/{self.year_field.value}"

        # Создать временную папку рядом с выходным файлом
        temp_dir = Path(output_path).parent / "temp_receipts"
        temp_dir.mkdir(exist_ok=True)

        success_count = 0
        error_count = 0
        errors = []
        temp_files = []
        final_filename = None
        final_path = None

        # Прогресс-бар
        progress_text = ft.Text("Генерация квитанций...", size=12)
        progress_bar = ft.ProgressBar(width=400, value=0)

        progress_dialog = ft.AlertDialog(
            title=ft.Text("⏳ Генерация квитанций"),
            content=ft.Container(
                content=ft.Column([
                    progress_text,
                    progress_bar,
                ], spacing=10),
                width=450,
            ),
        )

        self.page.dialog = progress_dialog
        progress_dialog.open = True
        self.page.update()

        # Генерация отдельных квитанций
        total = len(selected_students)
        for i, student_data in enumerate(selected_students):
            try:
                fio = str(student_data['fio'].value)
                contract = str(student_data['contract'].value)
                amount = float(student_data['amount'].value)
                compensation = str(student_data['compensation'].value)
                courses = [str(c) for c in student_data['subjects'] if c]

                # Проверка что список не пустой
                if not courses:
                    error_count += 1
                    errors.append(f"{fio}: Нет предметов")
                    continue

                # Обновить прогресс
                progress_text.value = f"Создание квитанции {i + 1}/{total}: {fio}"
                progress = (i + 1) / total * 0.8
                progress_bar.value = progress
                self.page.update()

                # Создать временный файл
                fio_normalized = fio.replace(' ', '_').replace('/', '_')
                temp_path = temp_dir / f"temp_{fio_normalized}_{i}.pdf"
                temp_files.append(temp_path)

                # Генерация
                generate_receipt(
                    student_name=fio,
                    courses=courses,
                    contract_number=contract,
                    month_year=month_year,
                    amount=amount,
                    compensation=compensation,
                    output_path=str(temp_path)
                )

                success_count += 1

            except Exception as ex:
                error_count += 1
                errors.append(f"{student_data['fio'].value}: {str(ex)}")

        # Объединение PDF файлов
        if success_count > 0:
            try:
                progress_text.value = "Объединение в один файл..."
                progress_bar.value = 0.85
                self.page.update()

                merger = PdfMerger()

                for temp_file in temp_files:
                    if temp_file.exists():
                        merger.append(str(temp_file))

                final_path = Path(output_path)
                final_filename = final_path.name

                merger.write(str(final_path))
                merger.close()

                progress_bar.value = 0.95
                progress_text.value = "Удаление временных файлов..."
                self.page.update()

                # Удалить временные файлы
                for temp_file in temp_files:
                    try:
                        if temp_file.exists():
                            temp_file.unlink()
                    except Exception as del_ex:
                        print(f"⚠️ Не удалось удалить временный файл {temp_file}: {del_ex}")

                try:
                    if temp_dir.exists():
                        temp_dir.rmdir()
                except Exception as dir_ex:
                    print(f"⚠️ Не удалось удалить временную папку: {dir_ex}")

                progress_bar.value = 1.0
                progress_text.value = "Готово! ✅"
                self.page.update()

            except Exception as merge_ex:
                error_count += 1
                errors.append(f"Ошибка объединения PDF: {str(merge_ex)}")
                import traceback
                traceback.print_exc()

        # Закрыть прогресс
        import time
        time.sleep(0.5)
        progress_dialog.open = False

        # Показать результаты
        if error_count == 0 and success_count > 0 and final_filename:
            self.page.show_snack_bar(
                ft.SnackBar(
                    content=ft.Text(f"✅ Успешно создан файл с {success_count} квитанциями!"),
                    bgcolor=ft.colors.GREEN,
                    duration=5000,
                )
            )

            info_dialog = ft.AlertDialog(
                title=ft.Row([
                    ft.Icon(ft.icons.CHECK_CIRCLE, color=ft.colors.GREEN),
                    ft.Text("Успешно создано!"),
                ]),
                content=ft.Container(
                    content=ft.Column([
                        ft.Text(f"📄 Файл: {final_filename}", size=12, weight=ft.FontWeight.BOLD),
                        ft.Text(f"📊 Квитанций: {success_count}", size=12),
                        ft.Divider(height=10),
                        ft.Text(
                            "✅ Все квитанции объединены в один PDF файл для удобной печати",
                            size=11,
                            color=ft.colors.GREEN_700,
                        ),
                    ], spacing=8),
                    width=450,
                ),
                actions=[
                    ft.TextButton("Закрыть", on_click=lambda e: self._close_dialog(info_dialog)),
                ],
            )

            self.page.dialog = info_dialog
            info_dialog.open = True

        elif success_count > 0 and final_filename:
            error_text = "\n".join(errors[:10])
            if len(errors) > 10:
                error_text += f"\n... и еще {len(errors) - 10} ошибок"

            error_dialog = ft.AlertDialog(
                title=ft.Text("⚠️ Генерация завершена с ошибками"),
                content=ft.Container(
                    content=ft.Column([
                        ft.Text(f"Создано: {success_count}", size=13, color=ft.colors.GREEN),
                        ft.Text(f"Ошибок: {error_count}", size=13, color=ft.colors.RED),
                        ft.Divider(height=5),
                        ft.Text(f"📄 Файл: {final_filename}", size=12),
                        ft.Divider(height=5),
                        ft.Text("Ошибки:", size=12, weight=ft.FontWeight.BOLD),
                        ft.Text(error_text, size=11, color=ft.colors.RED),
                    ], spacing=5, scroll=ft.ScrollMode.AUTO),
                    width=500,
                    height=350,
                ),
                actions=[
                    ft.TextButton("Закрыть", on_click=lambda e: self._close_dialog(error_dialog)),
                ],
            )

            self.page.dialog = error_dialog
            error_dialog.open = True

        else:
            error_text = "\n".join(errors[:10])
            if len(errors) > 10:
                error_text += f"\n... и еще {len(errors) - 10} ошибок"

            error_dialog = ft.AlertDialog(
                title=ft.Text("❌ Ошибка генерации"),
                content=ft.Container(
                    content=ft.Column([
                        ft.Text("Не удалось создать ни одной квитанции", size=13, color=ft.colors.RED),
                        ft.Divider(height=5),
                        ft.Text("Ошибки:", size=12, weight=ft.FontWeight.BOLD),
                        ft.Text(error_text, size=11, color=ft.colors.RED),
                    ], spacing=5, scroll=ft.ScrollMode.AUTO),
                    width=500,
                    height=300,
                ),
                actions=[
                    ft.TextButton("Закрыть", on_click=lambda e: self._close_dialog(error_dialog)),
                ],
            )

            self.page.dialog = error_dialog
            error_dialog.open = True

        self.page.update()

    def _close_dialog(self, dialog):
        """Закрыть диалог"""
        dialog.open = False
        self.page.update()
