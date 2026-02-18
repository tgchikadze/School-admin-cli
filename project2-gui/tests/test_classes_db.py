"""
Юнит-тесты для ClassesDatabase
"""

import unittest
import json
import tempfile
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))
from core.data.classes_db import ClassesDatabase


class TestClassesDatabase(unittest.TestCase):
    """Тесты для базы данных классов"""

    def setUp(self):
        self.temp_file = tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json')
        self.temp_file.close()
        self.db = ClassesDatabase()
        self.db.file_path = Path(self.temp_file.name)

        test_data = {
            "classes": [
                {
                    "id": "8",
                    "name": "8 класс (Биотехнологии)",
                    "base_price": 8000,
                    "subjects": ["Биология", "Химия", "Физика"],
                    "pricing": {
                        "type": "fixed",
                        "base_price": 8000
                    }
                },
                {
                    "id": "11",
                    "name": "11 класс (Подготовка к ЕГЭ)",
                    "base_price": 5000,
                    "subjects": ["Математика (профиль)", "Русский язык", "Физика", "Химия"],
                    "exam_subjects": ["Математика (профиль)", "Физика", "Химия"],
                    "pricing": {
                        "type": "per_subject",
                        "base_subjects_price": 5000,
                        "price_per_subject": 2500
                    }
                }
            ]
        }

        with open(self.temp_file.name, 'w', encoding='utf-8') as f:
            json.dump(test_data, f, ensure_ascii=False, indent=2)

    def tearDown(self):
        Path(self.temp_file.name).unlink(missing_ok=True)

    def test_get_all_classes(self):
        """Возвращает все классы в правильном порядке."""
        classes = self.db.get_all_classes()
        self.assertEqual(len(classes), 2)
        self.assertEqual(classes[0]['id'], '8')
        self.assertEqual(classes[1]['id'], '11')

    def test_get_class_by_id(self):
        """Поиск по существующему ID возвращает корректные данные."""
        cls = self.db.get_class_by_id('8')
        self.assertIsNotNone(cls)
        self.assertEqual(cls['name'], '8 класс (Биотехнологии)')
        self.assertEqual(cls['base_price'], 8000)

    def test_get_class_by_id_not_found(self):
        """Поиск по несуществующему ID возвращает None."""
        cls = self.db.get_class_by_id('НЕСУЩЕСТВУЕТ')
        self.assertIsNone(cls)

    def test_get_subjects_by_class(self):
        """Возвращает полный список предметов класса."""
        subjects = self.db.get_subjects_by_class('8')
        self.assertEqual(len(subjects), 3)
        self.assertIn('Биология', subjects)
        self.assertIn('Химия', subjects)
        self.assertIn('Физика', subjects)

    def test_calculate_price_fixed(self):
        """Фиксированная цена не зависит от набора предметов."""
        price = self.db.calculate_price('8', ['Биология', 'Химия'])
        self.assertEqual(price, 8000)

    def test_calculate_price_per_subject(self):
        """Цена = база + количество предметов ЕГЭ × стоимость предмета."""
        price = self.db.calculate_price('11', ['Математика (профиль)', 'Физика', 'Русский язык'])
        self.assertEqual(price, 10000)

    def test_calculate_price_no_exam_subjects(self):
        """Без предметов ЕГЭ возвращается только базовая цена."""
        price = self.db.calculate_price('11', ['Русский язык'])
        self.assertEqual(price, 5000)

    def test_calculate_price_all_exam_subjects(self):
        """Все три предмета ЕГЭ: база + 3 × 2500."""
        price = self.db.calculate_price('11', ['Математика (профиль)', 'Физика', 'Химия'])
        self.assertEqual(price, 12500)

    def test_get_price_info_fixed(self):
        """Строка ценообразования содержит слово «Фиксированная» и сумму."""
        info = self.db.get_price_info('8')
        self.assertIn('Фиксированная', info)
        self.assertIn('8', info)

    def test_get_price_info_per_subject(self):
        """Строка ценообразования содержит базу и цену за предмет."""
        info = self.db.get_price_info('11')
        self.assertIn('Базовая', info)
        self.assertIn('5', info)
        self.assertIn('2', info)  #


if __name__ == '__main__':
    unittest.main()
