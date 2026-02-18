"""
Юнит-тесты для модуля одиночной генерации квитанций (generator.py).

Тестируемые функции:
    - load_template_config: загрузка и валидация JSON-конфигурации.
    - generate_pdf: универсальная генерация PDF по конфигурации.
    - generate_receipt: генерация квитанции с нормализацией входных данных.
    - generate_receipt_from_dict: генерация из словаря.

Тестовые PDF сохраняются в tests/test_results/ и удаляются после каждого теста.
"""

import io
import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

from core.receipt.generator import (
    generate_pdf,
    generate_receipt,
    generate_receipt_from_dict,
    load_template_config,
)

TEST_RESULTS_DIR = Path(__file__).parent / "test_results"

MINIMAL_CONFIG = {
    "source_template": "test_template.pdf",
    "font_size": 10,
    "line_height": 11,
    "roles": ["ФИО", "Вид платежа", "№ договора", "Месяц/год", "компенсация", "К оплате"],
    "blocks": [
        {
            "ФИО": {"page": 1, "x": 230, "y": 610},
            "Вид платежа": {"page": 1, "x": 190, "y": 550},
            "№ договора": {"page": 1, "x": 380, "y": 560},
            "Месяц/год": {"page": 1, "x": 190, "y": 468},
            "компенсация": {"page": 1, "x": 275, "y": 468},
            "К оплате": {"page": 1, "x": 360, "y": 468},
        },
        {
            "ФИО": {"page": 1, "x": 230, "y": 255},
            "Вид платежа": {"page": 1, "x": 190, "y": 195},
            "№ договора": {"page": 1, "x": 380, "y": 205},
            "Месяц/год": {"page": 1, "x": 190, "y": 116},
            "компенсация": {"page": 1, "x": 275, "y": 116},
            "К оплате": {"page": 1, "x": 360, "y": 116},
        },
    ],
}


def _make_blank_pdf(path: Path) -> None:
    """Создать минимальный однострочный PDF-файл по указанному пути."""
    packet = io.BytesIO()
    c = canvas.Canvas(packet, pagesize=A4)
    c.drawString(10, 10, " ")
    c.save()
    path.write_bytes(packet.getvalue())


class TestLoadTemplateConfig(unittest.TestCase):
    """Тесты загрузки JSON-конфигурации."""

    def setUp(self):
        TEST_RESULTS_DIR.mkdir(exist_ok=True)
        self.config_path = TEST_RESULTS_DIR / "test_config.json"
        with open(self.config_path, "w", encoding="utf-8") as f:
            json.dump(MINIMAL_CONFIG, f, ensure_ascii=False)

    def tearDown(self):
        self.config_path.unlink(missing_ok=True)

    def test_load_returns_dict(self):
        """Загрузка корректного файла возвращает словарь."""
        config = load_template_config(self.config_path)
        self.assertIsInstance(config, dict)

    def test_load_contains_required_keys(self):
        """Загруженный конфиг содержит все обязательные ключи."""
        config = load_template_config(self.config_path)
        for key in ("source_template", "font_size", "line_height", "roles", "blocks"):
            self.assertIn(key, config)

    def test_load_missing_file_raises(self):
        """Несуществующий файл вызывает FileNotFoundError."""
        with self.assertRaises(FileNotFoundError):
            load_template_config(TEST_RESULTS_DIR / "nonexistent.json")


class TestGeneratePdf(unittest.TestCase):
    """Тесты универсальной генерации PDF."""

    def setUp(self):
        TEST_RESULTS_DIR.mkdir(exist_ok=True)
        self.template_path = TEST_RESULTS_DIR / "test_template.pdf"
        self.output_path = TEST_RESULTS_DIR / "test_output.pdf"
        _make_blank_pdf(self.template_path)

    def tearDown(self):
        self.template_path.unlink(missing_ok=True)
        self.output_path.unlink(missing_ok=True)

    def test_output_file_created(self):
        """PDF-файл создаётся по указанному пути."""
        generate_pdf(
            field_values={"ФИО": "Иванов Иван Иванович", "К оплате": "8 000.00"},
            template_path=self.template_path,
            output_path=self.output_path,
            config=MINIMAL_CONFIG,
        )
        self.assertTrue(self.output_path.exists())

    def test_output_file_not_empty(self):
        """Созданный PDF-файл не пустой."""
        generate_pdf(
            field_values={"ФИО": "Петров Пётр Петрович"},
            template_path=self.template_path,
            output_path=self.output_path,
            config=MINIMAL_CONFIG,
        )
        self.assertGreater(self.output_path.stat().st_size, 0)

    def test_multiline_field(self):
        """Многострочное поле (список) не вызывает исключений."""
        generate_pdf(
            field_values={"Вид платежа": ["Математика", "Физика", "Химия"]},
            template_path=self.template_path,
            output_path=self.output_path,
            config=MINIMAL_CONFIG,
        )
        self.assertTrue(self.output_path.exists())

    def test_empty_field_values(self):
        """Незаполненные роли не вызывают исключений — поля просто пропускаются."""
        generate_pdf(
            field_values={"ФИО": "Тест"},  # ← минимум одно поле
            template_path=self.template_path,
            output_path=self.output_path,
            config=MINIMAL_CONFIG,
        )
        self.assertTrue(self.output_path.exists())

    def test_missing_template_raises(self):
        """Отсутствующий шаблон вызывает FileNotFoundError."""
        with self.assertRaises(FileNotFoundError):
            generate_pdf(
                field_values={"ФИО": "Тест"},
                template_path=TEST_RESULTS_DIR / "no_template.pdf",
                output_path=self.output_path,
                config=MINIMAL_CONFIG,
            )

    def test_returns_absolute_path(self):
        """Функция возвращает строку с абсолютным путём."""
        result = generate_pdf(
            field_values={"ФИО": "Тест"},
            template_path=self.template_path,
            output_path=self.output_path,
            config=MINIMAL_CONFIG,
        )
        self.assertIsInstance(result, str)
        self.assertTrue(Path(result).is_absolute())


class TestGenerateReceipt(unittest.TestCase):
    """Тесты генерации квитанции через generate_receipt."""

    def setUp(self):
        TEST_RESULTS_DIR.mkdir(exist_ok=True)
        self.output_path = TEST_RESULTS_DIR / "test_receipt.pdf"
        self.template_path = TEST_RESULTS_DIR / "receipt_template.pdf"
        _make_blank_pdf(self.template_path)

        self.config_path = TEST_RESULTS_DIR / "receipt_coordinates.json"
        config = {**MINIMAL_CONFIG, "source_template": "receipt_template.pdf"}
        with open(self.config_path, "w", encoding="utf-8") as f:
            json.dump(config, f, ensure_ascii=False)

    def tearDown(self):
        self.output_path.unlink(missing_ok=True)
        self.template_path.unlink(missing_ok=True)
        self.config_path.unlink(missing_ok=True)

    def _call(self, **kwargs) -> str:
        defaults = {
            "student_name": "Иванов Иван Иванович",
            "courses": ["Математика", "Физика"],
            "contract_number": "2024-001",
            "month_year": "Январь/2025",
            "amount": 8000.0,
            "compensation": "",
            "output_path": str(self.output_path),
            "coordinates_path": self.config_path,
        }
        defaults.update(kwargs)
        return generate_receipt(**defaults)

    def test_receipt_file_created(self):
        """Квитанция создаётся и файл существует."""
        self._call()
        self.assertTrue(self.output_path.exists())

    def test_receipt_file_not_empty(self):
        """Созданная квитанция не пустая."""
        self._call()
        self.assertGreater(self.output_path.stat().st_size, 0)

    def test_empty_courses_raises(self):
        """Пустой список предметов вызывает ValueError."""
        with self.assertRaises(ValueError):
            self._call(courses=[])

    def test_courses_with_empty_strings_raises(self):
        """Список из пустых строк вызывает ValueError."""
        with self.assertRaises(ValueError):
            self._call(courses=["", " ", ""])

    def test_missing_config_raises(self):
        """Отсутствующий JSON конфига вызывает FileNotFoundError."""
        with self.assertRaises(FileNotFoundError):
            self._call(coordinates_path=TEST_RESULTS_DIR / "no_config.json")

    def test_single_course(self):
        """Один предмет не вызывает исключений."""
        self._call(courses=["Математика"])
        self.assertTrue(self.output_path.exists())

    def test_many_courses(self):
        """Длинный список предметов не вызывает исключений."""
        self._call(courses=["Математика", "Физика", "Химия", "Биология", "История"])
        self.assertTrue(self.output_path.exists())

    def test_compensation_empty(self):
        """Пустая компенсация не вызывает исключений."""
        self._call(compensation="")
        self.assertTrue(self.output_path.exists())

    def test_compensation_filled(self):
        """Заполненная компенсация не вызывает исключений."""
        self._call(compensation="1 000.00")
        self.assertTrue(self.output_path.exists())

    def test_amount_as_int(self):
        """Сумма в виде int нормализуется без ошибок."""
        self._call(amount=8000)
        self.assertTrue(self.output_path.exists())

    def test_returns_absolute_path(self):
        """Возвращается абсолютный путь."""
        result = self._call()
        self.assertTrue(Path(result).is_absolute())


class TestGenerateReceiptFromDict(unittest.TestCase):
    """Тесты генерации квитанции из словаря."""

    def setUp(self):
        TEST_RESULTS_DIR.mkdir(exist_ok=True)
        self.output_path = TEST_RESULTS_DIR / "test_dict_receipt.pdf"
        self.template_path = TEST_RESULTS_DIR / "receipt_template.pdf"
        _make_blank_pdf(self.template_path)

        self.config_path = TEST_RESULTS_DIR / "receipt_coordinates.json"
        config = {**MINIMAL_CONFIG, "source_template": "receipt_template.pdf"}
        with open(self.config_path, "w", encoding="utf-8") as f:
            json.dump(config, f, ensure_ascii=False)

    def tearDown(self):
        self.output_path.unlink(missing_ok=True)
        self.template_path.unlink(missing_ok=True)
        self.config_path.unlink(missing_ok=True)

    def test_receipt_from_dict_created(self):
        """Квитанция из словаря создаётся."""
        data = {
            "Ф.И.О": "Сидоров Сидор Сидорович",
            "Вид платежа": ["Информатика"],
            "№ договора": "2025-999",
            "Месяц/год": "Февраль/2026",
            "К оплате": 12000.0,
            "компенсация": "",
        }
        generate_receipt_from_dict(data, str(self.output_path))
        self.assertTrue(self.output_path.exists())

    def test_returns_absolute_path(self):
        """Возвращается абсолютный путь."""
        data = {
            "Ф.И.О": "Тестов Тест Тестович",
            "Вид платежа": ["Математика"],
            "№ договора": "T-001",
            "Месяц/год": "Январь/2026",
            "К оплате": 5000.0,
        }
        result = generate_receipt_from_dict(data, str(self.output_path))
        self.assertTrue(Path(result).is_absolute())


if __name__ == "__main__":
    unittest.main()
