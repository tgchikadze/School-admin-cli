"""
Юнит-тесты для модуля массовой генерации квитанций (BatchReceiptsPage).

Тестируются:
    - Методы работы с данными учеников (_load_students, _reset_preview).
    - Логика управления чекбоксами (_on_select_all, _on_checkbox_change).
    - Формирование данных для генерации.

ВНИМАНИЕ: Методы GUI (build, диалоги) не тестируются напрямую, т.к.
требуют инициализации Flet Page. Тесты покрывают бизнес-логику.
"""

import sys
import unittest
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

sys.path.insert(0, str(Path(__file__).parent.parent))

from gui.pages.batch_receipts_page import BatchReceiptsPage


class MockPage:
    """Минимальный мок ft.Page для инициализации BatchReceiptsPage."""

    def __init__(self):
        self.overlay = []
        self.dialog = None

    def show_snack_bar(self, snackbar):
        pass

    def update(self):
        pass


class MockCheckbox:
    """Мок ft.Checkbox с атрибутом value."""

    def __init__(self, value=False):
        self.value = value


class MockTextField:
    """Мок ft.TextField с атрибутом value."""

    def __init__(self, value=""):
        self.value = value


class TestBatchReceiptsPageDataHandling(unittest.TestCase):
    """Тесты работы с данными учеников."""

    def setUp(self):
        self.mock_page = MockPage()
        self.page_instance = BatchReceiptsPage(self.mock_page)

        self.page_instance.month_field = MockTextField("Январь")
        self.page_instance.year_field = MockTextField("2025")
        self.page_instance.class_filter = MockTextField("")
        self.page_instance.select_all_checkbox = MockCheckbox(False)
        self.page_instance.students_container = Mock()
        self.page_instance.students_container.controls = []
        self.page_instance.generate_button = Mock(disabled=True)

    @patch("gui.pages.batch_receipts_page.StudentDatabase")
    @patch("gui.pages.batch_receipts_page.ClassesDatabase")
    @patch("gui.pages.batch_receipts_page.ExamChoicesDatabase")
    def test_load_students_populates_data(self, mock_exam_db, mock_classes_db, mock_student_db):
        """_load_students заполняет students_data при наличии учеников."""
        mock_student_db_instance = mock_student_db.return_value
        mock_student_db_instance.get_all.return_value = [
            {
                "id": "1",
                "fio": "Иванов Иван",
                "class_id": "class1",
                "contract_number": "001",
                "monthly_payment": 5000,
                "compensation": "",
            }
        ]

        mock_classes_db_instance = mock_classes_db.return_value
        mock_classes_db_instance.get_class_by_id.return_value = {
            "id": "class1",
            "name": "10А",
            "price_calculation": "fixed",
        }
        mock_classes_db_instance.get_subjects_by_class.return_value = ["Математика", "Физика"]
        mock_classes_db_instance.calculate_price.return_value = 5000

        self.page_instance.db = mock_student_db_instance
        self.page_instance.classes_db = mock_classes_db_instance
        self.page_instance.exam_db = mock_exam_db.return_value

        self.page_instance._load_students(Mock())

        self.assertEqual(len(self.page_instance.students_data), 1)
        self.assertFalse(self.page_instance.generate_button.disabled)

    def test_reset_preview_clears_data(self):
        """_reset_preview очищает все данные и блокирует кнопку генерации."""
        self.page_instance.students_data = [{"test": "data"}]
        self.page_instance.students_checkboxes = [MockCheckbox(True)]
        self.page_instance.students_container.controls = ["element"]

        self.page_instance._reset_preview(Mock())

        self.assertEqual(len(self.page_instance.students_data), 0)
        self.assertEqual(len(self.page_instance.students_checkboxes), 0)
        self.assertEqual(len(self.page_instance.students_container.controls), 0)
        self.assertTrue(self.page_instance.generate_button.disabled)
        self.assertFalse(self.page_instance.select_all_checkbox.value)


class TestBatchReceiptsPageCheckboxLogic(unittest.TestCase):
    """Тесты логики управления чекбоксами."""

    def setUp(self):
        self.mock_page = MockPage()
        self.page_instance = BatchReceiptsPage(self.mock_page)
        self.page_instance.select_all_checkbox = MockCheckbox(False)

    def test_on_select_all_sets_all_checkboxes(self):
        """_on_select_all устанавливает значение всем чекбоксам."""
        cb1, cb2, cb3 = MockCheckbox(False), MockCheckbox(False), MockCheckbox(False)
        self.page_instance.students_checkboxes = [cb1, cb2, cb3]
        self.page_instance.select_all_checkbox.value = True

        self.page_instance._on_select_all(Mock())

        self.assertTrue(cb1.value)
        self.assertTrue(cb2.value)
        self.assertTrue(cb3.value)

    def test_on_checkbox_change_updates_select_all(self):
        """_on_checkbox_change обновляет select_all_checkbox при изменении."""
        cb1, cb2, cb3 = MockCheckbox(True), MockCheckbox(True), MockCheckbox(True)
        self.page_instance.students_checkboxes = [cb1, cb2, cb3]

        self.page_instance._on_checkbox_change(Mock())
        self.assertTrue(self.page_instance.select_all_checkbox.value)

        cb2.value = False
        self.page_instance._on_checkbox_change(Mock())
        self.assertFalse(self.page_instance.select_all_checkbox.value)


class TestBatchReceiptsPageGenerateBatch(unittest.TestCase):
    """Тесты валидации перед запуском генерации."""

    def setUp(self):
        self.mock_page = MockPage()
        self.page_instance = BatchReceiptsPage(self.mock_page)
        self.page_instance.month_field = MockTextField("Январь")
        self.page_instance.year_field = MockTextField("2025")

    def test_generate_batch_requires_month_year(self):
        """_generate_batch требует заполненные месяц и год."""
        self.page_instance.month_field.value = ""
        self.page_instance.year_field.value = ""

        with patch.object(self.mock_page, "show_snack_bar") as mock_snackbar:
            self.page_instance._generate_batch(Mock())
            mock_snackbar.assert_called_once()

    def test_generate_batch_requires_selected_students(self):
        """_generate_batch требует хотя бы одного выбранного ученика."""
        self.page_instance.students_data = [
            {"checkbox": MockCheckbox(False), "fio": MockTextField("Тест")}
        ]

        with patch.object(self.mock_page, "show_snack_bar") as mock_snackbar:
            self.page_instance._generate_batch(Mock())
            mock_snackbar.assert_called_once()


if __name__ == "__main__":
    unittest.main()
