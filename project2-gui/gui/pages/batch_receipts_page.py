"""
Страница массовой генерации квитанций (BatchReceiptsPage).

Функциональность:
    - Отображение списка учеников с редактируемыми данными и чекбоксами выбора.
    - Фильтрация учеников по классу.
    - Массовая генерация PDF-квитанций для выбранных учеников с объединением
      всех квитанций в один PDF-файл (с помощью PyPDF2).
    - Возможность редактировать список предметов каждого ученика перед генерацией.
    - Прогресс-диалог с отображением хода генерации.
"""

import time
from datetime import datetime
from pathlib import Path

import flet as ft

from core.data.classes_db import ClassesDatabase
from core.data.exam_choices_db import ExamChoicesDatabase
from core.data.student_db import StudentDatabase
from core.receipt.generator import generate_receipt


class BatchReceiptsPage:
    """
    Страница массовой генерации квитанций.

    Атрибуты:
        page (ft.Page): Корневая страница Flet-приложения.
        db (StudentDatabase): База данных учеников.
        classes_db (ClassesDatabase): База данных классов.
        exam_db (ExamChoicesDatabase): База данных выборов экзаменов.

    Атрибуты интерфейса (инициализируются None до вызова build()):
        month_field (ft.TextField | None): Поле ввода месяца.
        year_field (ft.TextField | None): Поле ввода года.
        class_filter (ft.Dropdown | None): Фильтр по классу.
        select_all_checkbox (ft.Checkbox | None): Чекбокс «Выбрать всех».
        students_container (ft.Column | None): Колонка с карточками учеников.
        generate_button (ft.ElevatedButton | None): Кнопка запуска генерации.
        reset_button (ft.TextButton | None): Кнопка сброса предпросмотра.

    Атрибуты состояния:
        students_checkboxes (list[ft.Checkbox]): Чекбоксы всех учеников.
        students_data (list[dict]): Данные по каждому ученику в предпросмотре.
            Каждый dict содержит: 'original', 'checkbox', 'fio', 'contract',
            'amount', 'compensation', 'subjects', 'subjects_button'.
    """

    def __init__(self, page: ft.Page) -> None:
        """
        Инициализация страницы массовой генерации квитанций.

        Параметры:
            page (ft.Page): Корневая страница Flet, в которую добавляются
                все элементы интерфейса и диалоги.
        """
        self.page: ft.Page = page
        self.db: StudentDatabase = StudentDatabase()
        self.classes_db: ClassesDatabase = ClassesDatabase()
        self.exam_db = ExamChoicesDatabase()

        self.month_field: ft.TextField | None = None
        self.year_field: ft.TextField | None = None
        self.class_filter: ft.Dropdown | None = None
        self.select_all_checkbox: ft.Checkbox | None = None
        self.students_container: ft.Column | None = None
        self.generate_button: ft.ElevatedButton | None = None
        self.reset_button: ft.TextButton | None = None

        self.students_checkboxes: list[ft.Checkbox] = []
        self.students_data: list[dict] = []

    # ====================
    # Построение интерфейса
    # ====================

    def build(self) -> ft.Column:
        """
        Построить и вернуть интерфейс страницы.

        Возвращает:
            ft.Column: Корневая колонка страницы с панелью настроек,
                чекбоксом «Выбрать всех», кнопками и контейнером учеников.
        """
        months_ru = [
            "Январь", "Февраль", "Март", "Апрель", "Май", "Июнь",
            "Июль", "Август", "Сентябрь", "Октябрь", "Ноябрь", "Декабрь",
        ]
        current_month = months_ru[datetime.now().month - 1]
        current_year = str(datetime.now().year)

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

        classes = self.classes_db.get_all_classes()
        class_options: list[ft.dropdown.Option] = [
            ft.dropdown.Option(key="", text="Все классы"),
        ]
        class_options.extend(
            ft.dropdown.Option(key=c["id"], text=c["name"])
            for c in classes
        )
        self.class_filter = ft.Dropdown(
            label="Фильтр по классу",
            options=class_options,
            width=250,
            dense=True,
            value="",
        )

        self.select_all_checkbox = ft.Checkbox(
            label="Выбрать всех",
            value=False,
            on_change=self._on_select_all,
        )
        preview_button = ft.ElevatedButton(
            "🔍 Предпросмотр",
            on_click=self._load_students,
            style=ft.ButtonStyle(
                bgcolor=ft.colors.BLUE_700,
                color=ft.colors.WHITE,
            ),
        )
        self.generate_button = ft.ElevatedButton(
            "📥 Сгенерировать квитанции",
            on_click=self._generate_batch,
            style=ft.ButtonStyle(
                bgcolor=ft.colors.GREEN_700,
                color=ft.colors.WHITE,
            ),
            disabled=True,
        )
        self.reset_button = ft.TextButton(
            "🔄 Сбросить",
            on_click=self._reset_preview,
        )
        self.students_container = ft.Column(
            spacing=5,
            scroll=ft.ScrollMode.AUTO,
        )

        return ft.Column(
            controls=[
                ft.Text(
                    "📊 Массовая генерация квитанций",
                    size=20,
                    weight=ft.FontWeight.BOLD,
                ),
                ft.Divider(height=3),
                ft.Container(
                    content=ft.Column(
                        [
                            ft.Text(
                                "Настройки генерации:",
                                size=13,
                                weight=ft.FontWeight.BOLD,
                            ),
                            ft.Row(
                                [
                                    self.month_field,
                                    self.year_field,
                                    self.class_filter,
                                ],
                                spacing=10,
                                wrap=True,
                            ),
                            ft.Row([preview_button], spacing=10),
                            ft.Text(
                                "💡 Выберите период и класс "
                                "(или 'Все классы'), "
                                "затем нажмите 'Предпросмотр'",
                                size=11,
                                italic=True,
                                color=ft.colors.GREY_700,
                            ),
                        ],
                        spacing=10,
                    ),
                    padding=10,
                    bgcolor=ft.colors.BLUE_50,
                    border_radius=8,
                ),
                ft.Divider(height=3),
                ft.Row(
                    [
                        self.select_all_checkbox,
                        ft.Container(expand=True),
                        self.reset_button,
                        self.generate_button,
                    ],
                    spacing=10,
                ),
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

    # ============================
    # Загрузка предпросмотра
    # ============================

    def _load_students(self, e: ft.ControlEvent) -> None:
        """
        Загрузить список учеников в предпросмотр с учётом фильтра по классу.

        Параметры:
            e (ft.ControlEvent): Событие нажатия кнопки «Предпросмотр».

        Логика:
            - Получает всех учеников из БД.
            - Применяет фильтр по классу, если он выбран.
            - Очищает предыдущий список и строит карточки учеников.
            - Для каждого ученика определяет предметы и рассчитывает стоимость
              через classes_db.calculate_price (поддерживает оба типа классов).
            - Разблокирует кнопку генерации после успешной загрузки.
        """
        all_students = self.db.get_all()
        if not all_students:
            self.page.show_snack_bar(
                ft.SnackBar(
                    content=ft.Text("⚠️ В базе нет учеников"),
                    bgcolor=ft.colors.ORANGE,
                )
            )
            return

        selected_class = self.class_filter.value
        if selected_class and selected_class != "Все классы":
            students = [
                s for s in all_students
                if s.get("class_id", "") == selected_class
            ]
            class_info = self.classes_db.get_class_by_id(selected_class)
            class_name = class_info["name"] if class_info else selected_class
            filter_msg = f" для класса '{class_name}'"
        else:
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

        self.students_container.controls.clear()
        self.students_checkboxes.clear()
        self.students_data.clear()

        for student in students:
            class_id = student.get("class_id", "")

            class_info = self.classes_db.get_class_by_id(class_id)
            class_name = (
                class_info["name"] if class_info
                else student.get("class_id", "Не указан")
            )

            if class_id and class_info:
                is_exam_class = class_info.get("pricing", {}).get("type") == "per_subject"

                if is_exam_class:
                    subjects = self.exam_db.get_student_exams(student["id"])
                    if not subjects:
                        subjects = class_info.get("exam_subjects", [])
                else:
                    subjects = self.classes_db.get_subjects_by_class(class_id)
            else:
                subjects = []

            subjects = [str(s) for s in subjects if s]

            subjects_text = ", ".join(subjects)
            if len(subjects_text) > 60:
                subjects_text = subjects_text[:57] + "..."

            if class_id and subjects:
                calculated_payment = self.classes_db.calculate_price(class_id, subjects)
            else:
                calculated_payment = student.get("monthly_payment", 0)

            checkbox = ft.Checkbox(
                value=False,
                on_change=self._on_checkbox_change,
            )
            student_fio = ft.TextField(
                value=student.get("fio", ""),
                label="ФИО",
                dense=True,
                text_size=12,
                width=250,
            )
            student_contract = ft.TextField(
                value=student.get("contract_number", ""),
                label="Договор",
                dense=True,
                text_size=12,
                width=120,
            )
            student_amount = ft.TextField(
                value=str(calculated_payment),
                label="Сумма",
                dense=True,
                text_size=12,
                width=100,
                keyboard_type=ft.KeyboardType.NUMBER,
            )
            student_compensation = ft.TextField(
                value=str(student.get("compensation", "")),
                label="Компенсация",
                dense=True,
                text_size=12,
                width=150,
            )

            current_idx = len(self.students_data)
            subjects_button = ft.IconButton(
                icon=ft.icons.EDIT_NOTE,
                icon_color=ft.colors.BLUE_700,
                icon_size=20,
                tooltip="Редактировать предметы",
                on_click=lambda ev, i=current_idx: self._edit_subjects(i),
            )

            student_data: dict = {
                "original": student,
                "checkbox": checkbox,
                "fio": student_fio,
                "contract": student_contract,
                "amount": student_amount,
                "compensation": student_compensation,
                "subjects": subjects.copy(),
                "subjects_button": subjects_button,
            }
            self.students_data.append(student_data)
            self.students_checkboxes.append(checkbox)

            card = ft.Container(
                content=ft.Column(
                    [
                        ft.Row(
                            [
                                checkbox,
                                ft.Column(
                                    [
                                        ft.Row(
                                            [
                                                student_fio,
                                                student_contract,
                                                student_amount,
                                                student_compensation,
                                                subjects_button,
                                            ],
                                            spacing=10,
                                            wrap=True,
                                        ),
                                        ft.Text(
                                            f"Класс: {class_name}",
                                            size=11,
                                            color=ft.colors.GREY_700,
                                        ),
                                        ft.Text(
                                            f"Предметы: {subjects_text}",
                                            size=11,
                                            color=ft.colors.GREY_600,
                                        ),
                                    ],
                                    spacing=3,
                                ),
                            ],
                        ),
                    ],
                    spacing=5,
                ),
                padding=10,
                border=ft.border.all(1, ft.colors.GREY_300),
                border_radius=8,
                bgcolor=ft.colors.WHITE,
            )
            self.students_container.controls.append(card)

        self.generate_button.disabled = False
        self.page.show_snack_bar(
            ft.SnackBar(
                content=ft.Text(f"✅ Загружено {len(students)} учеников{filter_msg}"),
                bgcolor=ft.colors.GREEN,
            )
        )
        self.page.update()

    # ============================
    # Сброс предпросмотра
    # ============================

    def _reset_preview(self, e: ft.ControlEvent) -> None:
        """
        Сбросить предпросмотр: очистить список учеников и вернуть
        интерфейс в исходное состояние.

        Параметры:
            e (ft.ControlEvent): Событие нажатия кнопки «Сбросить».
        """
        self.students_container.controls.clear()
        self.students_checkboxes.clear()
        self.students_data.clear()
        self.select_all_checkbox.value = False
        self.generate_button.disabled = True
        self.page.update()

    # ==============================
    # Редактирование предметов
    # ==============================

    def _edit_subjects(self, student_idx: int) -> None:
        """
        Показать диалог редактирования предметов конкретного ученика.

        Параметры:
            student_idx (int): Индекс ученика в self.students_data.

        Логика:
            - Показывает текстовое поле с предметами (по одному на строку).
            - При сохранении обновляет список subjects в student_data.
        """
        student_data = self.students_data[student_idx]
        current_subjects = student_data["subjects"]

        subjects_field = ft.TextField(
            label="Предметы (по одному на строку)",
            value="\n".join(current_subjects),
            multiline=True,
            min_lines=5,
            max_lines=10,
            width=400,
        )

        def save_subjects(e: ft.ControlEvent) -> None:
            """
            Сохранить отредактированный список предметов.

            Параметры:
                e (ft.ControlEvent): Событие нажатия кнопки «Сохранить».
            """
            new_subjects = [
                s.strip()
                for s in subjects_field.value.split("\n")
                if s.strip()
            ]
            student_data["subjects"] = new_subjects
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
                content=ft.Column(
                    [
                        ft.Text("Введите предметы (по одному на строку):", size=12),
                        subjects_field,
                    ],
                    spacing=10,
                ),
                width=450,
            ),
            actions=[
                ft.TextButton(
                    "Отмена",
                    on_click=lambda e: self._close_dialog(edit_dialog),
                ),
                ft.ElevatedButton(
                    "Сохранить",
                    on_click=save_subjects,
                    bgcolor=ft.colors.GREEN_700,
                    color=ft.colors.WHITE,
                ),
            ],
        )
        self.page.dialog = edit_dialog
        edit_dialog.open = True
        self.page.update()

    # ============================
    # Управление чекбоксами
    # ============================

    def _on_select_all(self, e: ft.ControlEvent) -> None:
        """
        Обработчик чекбокса «Выбрать всех».

        Параметры:
            e (ft.ControlEvent): Событие изменения главного чекбокса.

        Логика:
            Устанавливает значение всем чекбоксам учеников в соответствии
            с select_all_checkbox.value.
        """
        select_all = self.select_all_checkbox.value
        for checkbox in self.students_checkboxes:
            checkbox.value = select_all
        self.page.update()

    def _on_checkbox_change(self, e: ft.ControlEvent) -> None:
        """
        Обработчик изменения отдельного чекбокса ученика.

        Параметры:
            e (ft.ControlEvent): Событие изменения чекбокса.

        Логика:
            Если все чекбоксы выбраны — ставит select_all_checkbox в True,
            иначе сбрасывает его.
        """
        self.select_all_checkbox.value = all(
            cb.value for cb in self.students_checkboxes
        )
        self.page.update()

    # ============================
    # Запуск генерации
    # ============================

    def _generate_batch(self, e: ft.ControlEvent) -> None:
        """
        Проверить выбор и запустить диалог подтверждения генерации.

        Параметры:
            e (ft.ControlEvent): Событие нажатия кнопки «Сгенерировать».

        Логика:
            - Проверяет, что заполнены месяц и год.
            - Проверяет, что выбран хотя бы один ученик.
            - Вызывает _show_confirmation_dialog для подтверждения.
        """
        if not self.month_field.value or not self.year_field.value:
            self.page.show_snack_bar(
                ft.SnackBar(
                    content=ft.Text("⚠️ Укажите месяц и год"),
                    bgcolor=ft.colors.ORANGE,
                )
            )
            return

        selected_students = [
            sd for sd in self.students_data if sd["checkbox"].value
        ]
        if not selected_students:
            self.page.show_snack_bar(
                ft.SnackBar(
                    content=ft.Text("⚠️ Выберите хотя бы одного ученика"),
                    bgcolor=ft.colors.ORANGE,
                )
            )
            return

        self._show_confirmation_dialog(selected_students)

    def _show_confirmation_dialog(
        self,
        selected_students: list[dict],
    ) -> None:
        """
        Показать диалог подтверждения перед началом генерации.

        Параметры:
            selected_students (list[dict]): Список данных выбранных учеников
                (элементы из self.students_data с checkbox.value=True).

        Логика:
            - Показывает количество квитанций и период.
            - При подтверждении открывает FilePicker для выбора пути.
            - Передаёт путь и список учеников в _perform_generation.
        """
        confirm_text = (
            f"Будет создано {len(selected_students)} квитанций "
            f"за {self.month_field.value} {self.year_field.value}"
        )
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        month_normalized = self.month_field.value.replace(" ", "_")
        default_filename = (
            f"receipts_batch_{month_normalized}_"
            f"{self.year_field.value}_{timestamp}.pdf"
        )

        def confirm_generate(e: ft.ControlEvent) -> None:
            """
            Обработчик подтверждения: закрыть диалог и открыть FilePicker.

            Параметры:
                e (ft.ControlEvent): Событие нажатия кнопки подтверждения.
            """
            confirm_dialog.open = False
            self.page.update()

        def save_file_result(file_e: ft.FilePickerResultEvent) -> None:
            """
            Колбэк FilePicker: запустить генерацию по выбранному пути.

            Параметры:
                file_e (ft.FilePickerResultEvent): Результат сохранения;
                    содержит file_e.path с выбранным путём.
            """
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
            title=ft.Row(
                [
                    ft.Icon(ft.icons.INFO, color=ft.colors.BLUE_700),
                    ft.Text("Подтверждение генерации"),
                ],
            ),
            content=ft.Container(
                content=ft.Column(
                    [
                        ft.Text(confirm_text, size=13),
                        ft.Divider(height=5),
                        ft.Text(
                            "Квитанции будут объединены в один PDF файл",
                            size=11,
                            color=ft.colors.GREY_700,
                        ),
                    ],
                    spacing=10,
                ),
                width=400,
            ),
            actions=[
                ft.TextButton(
                    "Отмена",
                    on_click=lambda e: self._close_dialog(confirm_dialog),
                ),
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

    # ============================
    # Выполнение генерации PDF
    # ============================

    def _perform_generation(
        self,
        selected_students: list[dict],
        output_path: str,
    ) -> None:
        """
        Выполнить генерацию квитанций и объединить их в один PDF.

        Параметры:
            selected_students (list[dict]): Список данных выбранных учеников.
            output_path (str): Путь к итоговому PDF-файлу.

        Логика:
            - Показывает прогресс-диалог в реальном времени.
            - Для каждого ученика создаёт временный PDF в temp_receipts/.
            - Объединяет все временные файлы через PyPDF2.PdfMerger.
            - Удаляет временные файлы и папку.
            - Показывает итоговый диалог (успех, частичная ошибка, полная ошибка).
        """
        try:
            from PyPDF2 import PdfMerger
        except ImportError:
            self.page.show_snack_bar(
                ft.SnackBar(
                    content=ft.Text(
                        "❌ Ошибка: PyPDF2 не установлен. "
                        "Выполните: pip install PyPDF2"
                    ),
                    bgcolor=ft.colors.RED,
                    duration=10000,
                )
            )
            return

        month_year = f"{self.month_field.value}/{self.year_field.value}"
        temp_dir = Path(output_path).parent / "temp_receipts"
        temp_dir.mkdir(exist_ok=True)

        success_count = 0
        error_count = 0
        errors: list[str] = []
        temp_files: list[Path] = []
        final_filename: str | None = None

        progress_text = ft.Text("Генерация квитанций...", size=12)
        progress_bar = ft.ProgressBar(width=400, value=0)
        progress_dialog = ft.AlertDialog(
            title=ft.Text("⏳ Генерация квитанций"),
            content=ft.Container(
                content=ft.Column(
                    [progress_text, progress_bar],
                    spacing=10,
                ),
                width=450,
            ),
        )
        self.page.dialog = progress_dialog
        progress_dialog.open = True
        self.page.update()

        total = len(selected_students)
        for i, student_data in enumerate(selected_students):
            print(student_data.keys())
            try:

                fio = str(student_data["fio"].value)
                contract = str(student_data["contract"].value)
                amount = float(student_data["amount"].value)

                compensation = str(student_data["compensation"].value)
                courses = [str(c) for c in student_data["subjects"] if c]

                if not courses:
                    error_count += 1
                    errors.append(f"{fio}: Нет предметов")
                    continue
                '''
                elif class_ == '11': #@
                    print(self.exam_db["id"])
                    #courses =
                '''



                progress_text.value = f"Создание квитанции {i + 1}/{total}: {fio}"
                progress_bar.value = (i + 1) / total * 0.8
                self.page.update()

                fio_normalized = fio.replace(" ", "_").replace("/", "_")
                temp_path = temp_dir / f"temp_{fio_normalized}_{i}.pdf"
                temp_files.append(temp_path)

                generate_receipt(
                    student_name=fio,
                    courses=courses,
                    contract_number=contract,
                    month_year=month_year,
                    amount=amount,
                    compensation=compensation,
                    output_path=str(temp_path),
                )
                success_count += 1

            except Exception as ex:  # noqa: BLE001
                error_count += 1
                errors.append(f"{student_data['fio'].value}: {str(ex)}")

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

                for temp_file in temp_files:
                    try:
                        if temp_file.exists():
                            temp_file.unlink()
                    except Exception:  # noqa: BLE001
                        pass
                try:
                    if temp_dir.exists():
                        temp_dir.rmdir()
                except Exception:  # noqa: BLE001
                    pass

                progress_bar.value = 1.0
                progress_text.value = "Готово! ✅"
                self.page.update()

            except Exception as merge_ex:  # noqa: BLE001
                error_count += 1
                errors.append(f"Ошибка объединения PDF: {str(merge_ex)}")

        time.sleep(0.5)
        progress_dialog.open = False

        self._show_result_dialog(
            success_count=success_count,
            error_count=error_count,
            errors=errors,
            final_filename=final_filename,
        )
        self.page.update()

    def _show_result_dialog(
        self,
        success_count: int,
        error_count: int,
        errors: list[str],
        final_filename: str | None,
    ) -> None:
        """
        Показать итоговый диалог после завершения генерации.

        Параметры:
            success_count (int): Количество успешно созданных квитанций.
            error_count (int): Количество ошибок при генерации.
            errors (list[str]): Список строк с описанием ошибок.
            final_filename (str | None): Имя итогового PDF-файла или None,
                если файл не был создан.
        """
        error_text = "\n".join(errors[:10])
        if len(errors) > 10:
            error_text += f"\n... и еще {len(errors) - 10} ошибок"

        if error_count == 0 and success_count > 0 and final_filename:
            result_dialog = ft.AlertDialog(
                title=ft.Row(
                    [
                        ft.Icon(ft.icons.CHECK_CIRCLE, color=ft.colors.GREEN),
                        ft.Text("Успешно создано!"),
                    ],
                ),
                content=ft.Container(
                    content=ft.Column(
                        [
                            ft.Text(
                                f"📄 Файл: {final_filename}",
                                size=12,
                                weight=ft.FontWeight.BOLD,
                            ),
                            ft.Text(f"📊 Квитанций: {success_count}", size=12),
                            ft.Divider(height=10),
                            ft.Text(
                                "✅ Все квитанции объединены в один "
                                "PDF файл для удобной печати",
                                size=11,
                                color=ft.colors.GREEN_700,
                            ),
                        ],
                        spacing=8,
                    ),
                    width=450,
                ),
                actions=[
                    ft.TextButton(
                        "Закрыть",
                        on_click=lambda e: self._close_dialog(result_dialog),
                    ),
                ],
            )

        elif success_count > 0 and final_filename:
            result_dialog = ft.AlertDialog(
                title=ft.Text("⚠️ Генерация завершена с ошибками"),
                content=ft.Container(
                    content=ft.Column(
                        [
                            ft.Text(f"Создано: {success_count}", size=13, color=ft.colors.GREEN),
                            ft.Text(f"Ошибок: {error_count}", size=13, color=ft.colors.RED),
                            ft.Divider(height=5),
                            ft.Text(f"📄 Файл: {final_filename}", size=12),
                            ft.Divider(height=5),
                            ft.Text("Ошибки:", size=12, weight=ft.FontWeight.BOLD),
                            ft.Text(error_text, size=11, color=ft.colors.RED),
                        ],
                        spacing=5,
                        scroll=ft.ScrollMode.AUTO,
                    ),
                    width=500,
                    height=350,
                ),
                actions=[
                    ft.TextButton(
                        "Закрыть",
                        on_click=lambda e: self._close_dialog(result_dialog),
                    ),
                ],
            )

        else:
            result_dialog = ft.AlertDialog(
                title=ft.Text("❌ Ошибка генерации"),
                content=ft.Container(
                    content=ft.Column(
                        [
                            ft.Text(
                                "Не удалось создать ни одной квитанции",
                                size=13,
                                color=ft.colors.RED,
                            ),
                            ft.Divider(height=5),
                            ft.Text("Ошибки:", size=12, weight=ft.FontWeight.BOLD),
                            ft.Text(error_text, size=11, color=ft.colors.RED),
                        ],
                        spacing=5,
                        scroll=ft.ScrollMode.AUTO,
                    ),
                    width=500,
                    height=300,
                ),
                actions=[
                    ft.TextButton(
                        "Закрыть",
                        on_click=lambda e: self._close_dialog(result_dialog),
                    ),
                ],
            )

        self.page.dialog = result_dialog
        result_dialog.open = True
        self.page.update()

    # ==============
    # Служебные
    # ==============

    def _close_dialog(self, dialog: ft.AlertDialog) -> None:
        """
        Закрыть диалоговое окно и обновить страницу.

        Параметры:
            dialog (ft.AlertDialog): Диалог для закрытия.
        """
        dialog.open = False
        self.page.update()
