"""
Страница генерации квитанций
"""
import flet as ft
from pathlib import Path
from datetime import datetime
import os
import time

from core.receipt.generator import generate_receipt
from core.data.student_db import StudentDatabase


class ReceiptsPage:
    """Страница для генерации квитанций"""

    def __init__(self, page: ft.Page):
        self.page = page
        self.db = StudentDatabase()

        # Элементы формы
        self.student_dropdown = None
        self.fio_field = None
        self.contract_field = None
        self.payment_field = None
        self.compensation_field = None
        self.month_field = None
        self.year_field = None
        self.courses_container = None
        self.courses_fields = []

        # Хранить последний выбранный ID для отладки
        self.last_selected_id = None

    def build(self) -> ft.Column:
        """Построить интерфейс страницы"""

        # Загрузка учеников
        students = self.db.get_all()
        print(f"\n{'=' * 60}")
        print(f"📊 Загружено учеников: {len(students)}")
        print(f"{'=' * 60}\n")

        # Создание опций для dropdown
        student_options = []
        for student in students:
            option = ft.dropdown.Option(
                key=student['id'],
                text=f"{student['fio']} (договор {student['contract_number']})"
            )
            student_options.append(option)

        # Dropdown
        self.student_dropdown = ft.Dropdown(
            label="Выбрать ученика из базы",
            hint_text="Выберите ученика для автозаполнения",
            options=student_options,
            on_change=self._on_student_selected,
            width=500,
            filled=True,
            border_color=ft.colors.BLUE_400,
            dense=True,
            text_size=13,
        )

        # Поля формы (КОМПАКТНЫЕ)
        self.fio_field = ft.TextField(
            label="ФИО ученика *",
            hint_text="Иванов Иван Петрович",
            width=500,
            dense=True,
            text_size=13,
        )

        self.contract_field = ft.TextField(
            label="Номер договора *",
            hint_text="8БТ-10",
            width=250,
            dense=True,
            text_size=13,
        )

        self.payment_field = ft.TextField(
            label="Сумма к оплате (руб.) *",
            hint_text="5000",
            keyboard_type=ft.KeyboardType.NUMBER,
            width=250,
            dense=True,
            text_size=13,
        )

        self.compensation_field = ft.TextField(
            label="Компенсация",
            hint_text="500",
            width=250,
            dense=True,
            text_size=13,
        )

        # Автоматически подставить текущий месяц и год
        months_ru = [
            "Январь", "Февраль", "Март", "Апрель", "Май", "Июнь",
            "Июль", "Август", "Сентябрь", "Октябрь", "Ноябрь", "Декабрь"
        ]
        current_month = months_ru[datetime.now().month - 1]

        self.month_field = ft.TextField(
            label="Месяц *",
            hint_text="Январь",
            value=current_month,
            width=180,
            dense=True,
            text_size=13,
        )

        self.year_field = ft.TextField(
            label="Год *",
            hint_text="2026",
            value=str(datetime.now().year),
            width=120,
            dense=True,
            text_size=13,
        )

        # Начальное поле для предмета
        course_field = ft.TextField(
            label="Предмет 1",
            hint_text="Математика",
            width=400,
            dense=True,
            text_size=13,
        )
        self.courses_fields = [course_field]

        # Контейнер для предметов
        self.courses_container = ft.Column(
            controls=self.courses_fields,
            spacing=8,
        )

        # Кнопки управления предметами (компактные иконки)
        add_course_btn = ft.IconButton(
            icon=ft.icons.ADD_CIRCLE_OUTLINE,
            tooltip="Добавить предмет",
            on_click=self._add_course_field,
            icon_color=ft.colors.BLUE_400,
            icon_size=24,
        )

        remove_course_btn = ft.IconButton(
            icon=ft.icons.REMOVE_CIRCLE_OUTLINE,
            tooltip="Удалить последний предмет",
            on_click=self._remove_course_field,
            icon_color=ft.colors.RED_300,
            icon_size=24,
        )

        # Кнопка генерации (компактная)
        generate_btn = ft.ElevatedButton(
            "🎯 Сгенерировать квитанцию",
            on_click=self._generate_receipt,
            icon=ft.icons.PICTURE_AS_PDF,
            style=ft.ButtonStyle(
                bgcolor=ft.colors.GREEN_700,
                color=ft.colors.WHITE,
                padding=12,
            ),
            width=280,
        )

        # Layout страницы (КОМПАКТНЫЙ)
        return ft.Column(
            controls=[
                # Заголовок
                ft.Text(
                    "🧾 Генерация квитанций",
                    size=24,
                    weight=ft.FontWeight.BOLD,
                ),

                ft.Divider(height=5),

                # Выбор ученика
                ft.Container(
                    content=ft.Column([
                        ft.Text("Быстрое заполнение:", size=14, weight=ft.FontWeight.BOLD),
                        self.student_dropdown,
                        ft.Text(
                            "💡 Выберите ученика из списка - форма заполнится автоматически",
                            size=11,
                            color=ft.colors.GREY_700,
                            italic=True,
                        ),
                    ], spacing=5),
                    padding=8,
                    bgcolor=ft.colors.BLUE_50,
                    border_radius=8,
                ),

                ft.Divider(height=5),

                # Форма
                ft.Text("Данные ученика:", size=14, weight=ft.FontWeight.BOLD),
                self.fio_field,

                ft.Row([
                    self.contract_field,
                    self.payment_field,
                ], spacing=10),

                self.compensation_field,

                ft.Divider(height=5),

                ft.Text("Период:", size=14, weight=ft.FontWeight.BOLD),
                ft.Row([
                    self.month_field,
                    self.year_field,
                ], spacing=10),

                ft.Divider(height=5),

                ft.Row([
                    ft.Text("Предметы:", size=14, weight=ft.FontWeight.BOLD),
                    add_course_btn,
                    remove_course_btn,
                ], spacing=5),

                self.courses_container,

                ft.Divider(height=5),

                # Кнопка генерации (выровнена по левому краю)
                generate_btn,
            ],
            scroll=ft.ScrollMode.AUTO,
            spacing=8,
        )

    def _on_student_selected(self, e):
        """Обработчик выбора ученика из dropdown"""
        student_id = e.control.value

        print(f"\n{'=' * 60}")
        print(f"🎯 СОБЫТИЕ: Ученик выбран")
        print(f"{'=' * 60}")
        print(f"ID ученика: {student_id}")
        print(f"Предыдущий ID: {self.last_selected_id}")

        if not student_id:
            print("⚠️ ID пустой, пропускаем")
            return

        # Сохранить ID
        self.last_selected_id = student_id

        # Найти ученика в базе
        student = self.db.get_by_id(student_id)

        if not student:
            print(f"❌ Ученик с ID {student_id} не найден!")
            self.page.show_snack_bar(
                ft.SnackBar(content=ft.Text("Ученик не найден"), bgcolor=ft.colors.RED)
            )
            return

        print(f"✅ Найден ученик: {student.get('fio')}")

        # Очистить форму СНАЧАЛА
        print(f"🧹 Очистка формы...")
        self.fio_field.value = ""
        self.contract_field.value = ""
        self.payment_field.value = ""
        self.compensation_field.value = ""

        # Очистить контейнер предметов ПОЛНОСТЬЮ
        self.courses_fields = []
        self.courses_container.controls = []

        # Обновить UI сразу после очистки
        self.fio_field.update()
        self.contract_field.update()
        self.payment_field.update()
        self.compensation_field.update()
        self.courses_container.update()
        self.page.update()

        # Небольшая пауза для отрисовки
        time.sleep(0.05)

        print(f"✓ Форма очищена")

        # Заполнить поля ЗАНОВО
        print(f"📝 Заполнение формы новыми данными...")
        self.fio_field.value = student.get('fio', '')
        self.contract_field.value = student.get('contract_number', '')
        self.payment_field.value = str(student.get('monthly_payment', ''))
        self.compensation_field.value = student.get('compensation', '')

        # Заполнить предметы
        courses = student.get('courses', [])
        print(f"📚 Добавление {len(courses)} предметов...")

        # Создать НОВЫЕ поля для каждого предмета
        if courses:
            for i, course in enumerate(courses, 1):
                course_field = ft.TextField(
                    label=f"Предмет {i}",
                    value=course,
                    width=400,
                    dense=True,
                    text_size=13,
                )
                self.courses_fields.append(course_field)
                self.courses_container.controls.append(course_field)
                print(f"   + Предмет {i}: {course}")
        else:
            # Если нет предметов - добавить одно пустое поле
            course_field = ft.TextField(
                label="Предмет 1",
                hint_text="Математика",
                width=400,
                dense=True,
                text_size=13,
            )
            self.courses_fields.append(course_field)
            self.courses_container.controls.append(course_field)
            print(f"   + Добавлено пустое поле")

        print(f"✅ Форма заполнена: {len(self.courses_fields)} полей предметов")

        # Принудительное обновление ВСЕХ элементов
        print(f"🔄 Принудительное обновление UI...")
        self.fio_field.update()
        self.contract_field.update()
        self.payment_field.update()
        self.compensation_field.update()
        self.courses_container.update()
        self.page.update()

        # Еще одна пауза для гарантии отрисовки
        time.sleep(0.05)

        print(f"✓ UI обновлен")

        # Сбросить dropdown для следующего выбора
        print(f"🔄 Сброс dropdown...")

        try:
            # Сохранить опции
            old_options = list(self.student_dropdown.options)

            # Очистить dropdown
            self.student_dropdown.value = None
            self.student_dropdown.options = []
            self.student_dropdown.update()

            # Пауза
            time.sleep(0.05)

            # Вернуть опции
            self.student_dropdown.options = old_options
            self.student_dropdown.value = None
            self.student_dropdown.update()

            print(f"✓ Dropdown сброшен")
        except Exception as ex:
            print(f"⚠️ Ошибка сброса dropdown: {ex}")

        print(f"{'=' * 60}\n")

        # Финальное обновление страницы
        self.page.update()

        # Уведомление
        self.page.show_snack_bar(
            ft.SnackBar(
                content=ft.Text(f"✅ Данные ученика '{student['fio']}' загружены"),
                bgcolor=ft.colors.GREEN,
            )
        )

    def _add_course_field(self, e):
        """Добавить поле для предмета"""
        course_field = ft.TextField(
            label=f"Предмет {len(self.courses_fields) + 1}",
            hint_text="Физика",
            width=400,
            dense=True,
            text_size=13,
        )
        self.courses_fields.append(course_field)
        self.courses_container.controls.append(course_field)
        self.page.update()

    def _remove_course_field(self, e):
        """Удалить последнее поле предмета"""
        if len(self.courses_fields) > 1:
            self.courses_fields.pop()
            self.courses_container.controls.pop()
            self.page.update()
        else:
            self.page.show_snack_bar(
                ft.SnackBar(content=ft.Text("Должен остаться хотя бы один предмет"))
            )

    def _generate_receipt(self, e):
        """Сгенерировать квитанцию"""

        # Валидация
        if not self.fio_field.value:
            self.page.show_snack_bar(
                ft.SnackBar(content=ft.Text("Введите ФИО ученика"), bgcolor=ft.colors.RED)
            )
            return

        if not self.contract_field.value:
            self.page.show_snack_bar(
                ft.SnackBar(content=ft.Text("Введите номер договора"), bgcolor=ft.colors.RED)
            )
            return

        if not self.payment_field.value:
            self.page.show_snack_bar(
                ft.SnackBar(content=ft.Text("Введите сумму оплаты"), bgcolor=ft.colors.RED)
            )
            return

        if not self.month_field.value:
            self.page.show_snack_bar(
                ft.SnackBar(content=ft.Text("Введите месяц"), bgcolor=ft.colors.RED)
            )
            return

        if not self.year_field.value:
            self.page.show_snack_bar(
                ft.SnackBar(content=ft.Text("Введите год"), bgcolor=ft.colors.RED)
            )
            return

        # Собрать предметы
        courses = [f.value for f in self.courses_fields if f.value]

        if not courses:
            self.page.show_snack_bar(
                ft.SnackBar(content=ft.Text("Добавьте хотя бы один предмет"), bgcolor=ft.colors.RED)
            )
            return

        # Показать прогресс
        progress_dialog = ft.AlertDialog(
            title=ft.Text("Генерация квитанции..."),
            content=ft.ProgressRing(),
        )
        self.page.dialog = progress_dialog
        progress_dialog.open = True
        self.page.update()

        try:
            # Подготовить данные для генератора
            month_year = f"{self.month_field.value}/{self.year_field.value}"
            amount = float(self.payment_field.value)

            # Создать папку receipts если нет
            receipts_dir = Path("receipts")
            receipts_dir.mkdir(exist_ok=True)

            # Имя файла
            fio_normalized = self.fio_field.value.replace(' ', '_')
            output_path = receipts_dir / f"receipt_{fio_normalized}.pdf"

            print(f"\n🎯 Генерация квитанции:")
            print(f"   ФИО: {self.fio_field.value}")
            print(f"   Договор: {self.contract_field.value}")
            print(f"   Сумма: {amount}")
            print(f"   Период: {month_year}")
            print(f"   Предметы: {courses}")
            print(f"   Путь: {output_path}\n")

            # Вызвать функцию генератора
            output_path = generate_receipt(
                student_name=self.fio_field.value,
                courses=courses,
                contract_number=self.contract_field.value,
                month_year=month_year,
                amount=amount,
                compensation=self.compensation_field.value or '',
                output_path=str(output_path)
            )

            # Закрыть прогресс
            progress_dialog.open = False
            self.page.update()

            print(f"✅ Квитанция успешно создана: {output_path}\n")

            # Успешное сообщение
            self.page.show_snack_bar(
                ft.SnackBar(
                    content=ft.Text(f"✅ Квитанция создана: {Path(output_path).name}"),
                    bgcolor=ft.colors.GREEN,
                )
            )

            # Открыть PDF
            import platform

            try:
                if platform.system() == 'Darwin':  # macOS
                    os.system(f'open "{output_path}"')
                elif platform.system() == 'Windows':
                    os.startfile(output_path)
                else:  # Linux
                    os.system(f'xdg-open "{output_path}"')
                print(f"✅ PDF открыт в системном просмотрщике\n")
            except Exception as open_ex:
                print(f"⚠️ Не удалось автоматически открыть PDF: {open_ex}")

        except Exception as ex:
            # Закрыть прогресс
            progress_dialog.open = False
            self.page.update()

            # Ошибка
            print(f"❌ Ошибка генерации: {ex}")
            import traceback
            traceback.print_exc()

            self.page.show_snack_bar(
                ft.SnackBar(
                    content=ft.Text(f"❌ Ошибка: {str(ex)}"),
                    bgcolor=ft.colors.RED,
                )
            )
