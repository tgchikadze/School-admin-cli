"""
Юнит-тесты для StudentDatabase.

Тестируемые операции:
    - Добавление ученика и автоинкремент ID.
    - Получение всех записей, по ID.
    - Обновление и удаление записей.
    - Поиск по подстроке.
    - Проверка дубликатов по ФИО и номеру договора.
    - Полная очистка базы.

Тестовые файлы создаются в tests/test_results/ и удаляются после каждого теста.
"""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from core.data.student_db import StudentDatabase

TEST_RESULTS_DIR = Path(__file__).parent / "test_results"


class TestStudentDatabase(unittest.TestCase):
    """Тесты базы данных учеников."""

    def setUp(self):
        """Создать чистую тестовую БД перед каждым тестом."""
        TEST_RESULTS_DIR.mkdir(exist_ok=True)
        self.test_db_file = TEST_RESULTS_DIR / "test_students.json"
        self.db = StudentDatabase(str(self.test_db_file))
        self.db.clear_all()

    def tearDown(self):
        """Удалить тестовый файл после каждого теста."""
        self.test_db_file.unlink(missing_ok=True)

    def test_add_student(self):
        """Добавление ученика возвращает корректные данные."""
        result = self.db.add(
            fio="Иванов Иван Иванович",
            contract_number="2024-001",
            class_id="8bt",
            monthly_payment=8000,
        )
        self.assertIsNotNone(result)
        self.assertEqual(result["fio"], "Иванов Иван Иванович")
        self.assertEqual(result["contract_number"], "2024-001")
        self.assertEqual(result["class_id"], "8bt")
        self.assertEqual(result["monthly_payment"], 8000)
        self.assertEqual(result["id"], "001")

    def test_get_all_empty(self):
        """Пустая база возвращает пустой список."""
        self.assertEqual(len(self.db.get_all()), 0)

    def test_get_by_id(self):
        """Поиск по ID возвращает нужного ученика; несуществующий ID — None."""
        self.db.add(
            fio="Петров Петр Петрович",
            contract_number="2024-002",
            class_id="9mi",
            monthly_payment=8000,
        )
        student = self.db.get_by_id("001")
        self.assertIsNotNone(student)
        self.assertEqual(student["fio"], "Петров Петр Петрович")
        self.assertIsNone(self.db.get_by_id("999"))

    def test_update_student(self):
        """Обновление изменяет только переданные поля."""
        self.db.add(
            fio="Сидоров Сидор Сидорович",
            contract_number="2024-003",
            class_id="10bt",
            monthly_payment=9000,
        )
        success = self.db.update(
            student_id="001",
            fio="Сидоров Сидор Сидорович (обновлено)",
            monthly_payment=9500,
        )
        self.assertTrue(success)
        student = self.db.get_by_id("001")
        self.assertEqual(student["fio"], "Сидоров Сидор Сидорович (обновлено)")
        self.assertEqual(student["monthly_payment"], 9500)

    def test_delete_student(self):
        """Удаление ученика — база становится пустой."""
        self.db.add(
            fio="Удалов Удалий Удаляемович",
            contract_number="2024-004",
            class_id="11mi",
            monthly_payment=10000,
        )
        self.assertTrue(self.db.delete("001"))
        self.assertEqual(len(self.db.get_all()), 0)

    def test_search_students(self):
        """Поиск по подстроке возвращает все совпадения."""
        self.db.add(fio="Иванов Иван Иванович",   contract_number="2024-001", class_id="8bt",  monthly_payment=8000)
        self.db.add(fio="Петров Петр Петрович",   contract_number="2024-002", class_id="9mi",  monthly_payment=8000)
        self.db.add(fio="Иванова Мария Ивановна", contract_number="2024-003", class_id="10bt", monthly_payment=9000)

        self.assertEqual(len(self.db.search("Иван")), 2)
        results = self.db.search("Петров")
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["fio"], "Петров Петр Петрович")

    def test_check_duplicate_contract(self):
        """Дубликат обнаруживается по совпадению номера договора."""
        self.db.add(fio="Тестов Тест Тестович", contract_number="2024-UNIQUE", class_id="8bt", monthly_payment=8000)
        self.assertTrue(self.db.check_duplicate("Другой Ученик", "2024-UNIQUE"))

    def test_check_duplicate_fio(self):
        """Дубликат обнаруживается по совпадению ФИО."""
        self.db.add(fio="Уникальный Человек Очень", contract_number="2024-100", class_id="8bt", monthly_payment=8000)
        self.assertTrue(self.db.check_duplicate("Уникальный Человек Очень", "2024-200"))

    def test_no_duplicate(self):
        """Новый ученик с уникальными ФИО и договором — не дубликат."""
        self.db.add(fio="Существующий Ученик", contract_number="2024-300", class_id="8bt", monthly_payment=8000)
        self.assertFalse(self.db.check_duplicate("Совершенно Новый Человек", "2024-400"))

    def test_clear_all(self):
        """После clear_all база пуста."""
        for i in range(5):
            self.db.add(
                fio=f"Ученик {i}",
                contract_number=f"2024-{i}",
                class_id="8bt",
                monthly_payment=8000,
            )
        self.assertEqual(len(self.db.get_all()), 5)
        self.db.clear_all()
        self.assertEqual(len(self.db.get_all()), 0)

    def test_auto_increment_id(self):
        """ID присваиваются последовательно начиная с 001."""
        for i in range(1, 4):
            self.db.add(fio=f"Ученик {i}", contract_number=f"C-{i}", class_id="8bt", monthly_payment=8000)
        students = self.db.get_all()
        self.assertEqual(students[0]["id"], "001")
        self.assertEqual(students[1]["id"], "002")
        self.assertEqual(students[2]["id"], "003")


if __name__ == "__main__":
    unittest.main()
