"""
Юнит-тесты для ClassesDatabase.

Тестируемые операции:
    - Получение всех классов и поиск по ID.
    - Получение списка предметов класса.
    - Расчёт стоимости: фиксированная и по количеству предметов ЕГЭ.
    - Форматирование строки с информацией о ценообразовании.

Тестовые файлы создаются в tests/test_results/ и удаляются после каждого теста.
"""

import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from core.data.classes_db import ClassesDatabase

TEST_RESULTS_DIR = Path(__file__).parent / "test_results"

TEST_DATA = {
    "classes": [
        {
            "id": "8БТ",
            "name": "8 класс (Биотехнологии)",
            "base_price": 8000,
            "subjects": ["Биология", "Химия", "Физика"],
        },
        {
            "id": "11УНИ",
            "name": "11 класс (Подготовка к ЕГЭ)",
            "base_price": 5000,
            "price_calculation": "per_subject",
            "price_per_subject": 2500,
            "subjects": ["Математика (профиль)", "Русский язык", "Физика", "Химия"],
            "exam_subjects": ["Математика (профиль)", "Физика", "Химия"],
        },
    ]
}


class TestClassesDatabase(unittest.TestCase):
    """Тесты базы данных классов."""

    def setUp(self):
        """Создать тестовый JSON-файл с данными классов перед каждым тестом."""
        TEST_RESULTS_DIR.mkdir(exist_ok=True)
        self.test_db_file = TEST_RESULTS_DIR / "test_classes.json"
        with open(self.test_db_file, "w", encoding="utf-8") as f:
            json.dump(TEST_DATA, f, ensure_ascii=False, indent=2)
        self.db = ClassesDatabase()
        self.db.file_path = self.test_db_file

    def tearDown(self):
        """Удалить тестовый файл после каждого теста."""
        self.test_db_file.unlink(missing_ok=True)

    def test_get_all_classes(self):
        """Возвращает все классы в правильном порядке."""
        classes = self.db.get_all_classes()
        self.assertEqual(len(classes), 2)
        self.assertEqual(classes[0]["id"], "8БТ")
        self.assertEqual(classes[1]["id"], "11УНИ")

    def test_get_class_by_id(self):
        """Поиск по существующему ID возвращает корректные данные."""
        cls = self.db.get_class_by_id("8БТ")
        self.assertIsNotNone(cls)
        self.assertEqual(cls["name"], "8 класс (Биотехнологии)")
        self.assertEqual(cls["base_price"], 8000)

    def test_get_class_by_id_not_found(self):
        """Поиск по несуществующему ID возвращает None."""
        self.assertIsNone(self.db.get_class_by_id("НЕСУЩЕСТВУЕТ"))

    def test_get_subjects_by_class(self):
        """Возвращает полный список предметов класса."""
        subjects = self.db.get_subjects_by_class("8БТ")
        self.assertEqual(len(subjects), 3)
        self.assertIn("Биология", subjects)
        self.assertIn("Химия", subjects)
        self.assertIn("Физика", subjects)

    def test_calculate_price_fixed(self):
        """Фиксированная цена не зависит от набора предметов."""
        self.assertEqual(self.db.calculate_price("8БТ", ["Биология", "Химия"]), 8000)

    def test_calculate_price_per_subject(self):
        """Цена = база + количество предметов ЕГЭ × стоимость предмета."""
        subjects = ["Математика (профиль)", "Физика", "Русский язык"]
        self.assertEqual(self.db.calculate_price("11УНИ", subjects), 10000)

    def test_calculate_price_no_exam_subjects(self):
        """Без предметов ЕГЭ возвращается только базовая цена."""
        self.assertEqual(self.db.calculate_price("11УНИ", ["Русский язык"]), 5000)

    def test_calculate_price_all_exam_subjects(self):
        """Все три предмета ЕГЭ: база + 3 × 2500."""
        subjects = ["Математика (профиль)", "Физика", "Химия"]
        self.assertEqual(self.db.calculate_price("11УНИ", subjects), 12500)

    def test_get_price_info_fixed(self):
        """Строка ценообразования содержит слово «Фиксированная» и сумму."""
        info = self.db.get_price_info("8БТ")
        self.assertIn("Фиксированная", info)
        self.assertIn("8,000", info)

    def test_get_price_info_per_subject(self):
        """Строка ценообразования содержит базу и цену за предмет."""
        info = self.db.get_price_info("11УНИ")
        self.assertIn("Базовая", info)
        self.assertIn("5,000", info)
        self.assertIn("2,500", info)


if __name__ == "__main__":
    unittest.main()
