"""
База данных классов и предметов
"""
import json
from pathlib import Path


class ClassesDatabase:
    """Управление классами и предметами"""

    def __init__(self):
        self.file_path = Path(__file__).parent / "classes.json"
        self._ensure_file_exists()

    def _ensure_file_exists(self):
        """Создать файл если не существует"""
        if not self.file_path.exists():
            default_data = {
                "classes": [
                    {
                        "id": "8",
                        "name": "8",
                        "base_price": 8000,
                        "subjects": [
                            "Английский язык",
                            "Биофизика",
                            "Биоразнообразие растений",
                            "Экологические закономерности",
                            "Биохимия",
                            "Генетика"
                        ]
                    },
                    {
                        "id": "9",
                        "name": "9",
                        "base_price": 7000,
                        "subjects": [
                            "Математика",
                            "Физика",
                            "Информатика",
                            "Программирование",
                            "Алгоритмы"
                        ]
                    },
                    {
                        "id": "10",
                        "name": "10",
                        "base_price": 6500,
                        "subjects": [
                            "Химия",
                            "Биология",
                            "Экология",
                            "Органическая химия",
                            "Микробиология"
                        ]
                    },
                    {
                        "id": "11",
                        "name": "11",
                        "base_price": 5000,
                        "price_calculation": "per_subject",
                        "price_per_subject": 2500,
                        "subjects": [
                            "Математика (профиль)",
                            "Русский язык",
                            "Физика",
                            "Химия",
                            "Биология",
                            "История",
                            "Обществознание",
                            "Английский язык",
                            "Информатика",
                            "Литература"
                        ],
                        "exam_subjects": [
                            "Математика (профиль)",
                            "Физика",
                            "Химия",
                            "Биология",
                            "История",
                            "Обществознание",
                            "Английский язык",
                            "Информатика",
                            "Литература"
                        ]
                    }
                ]
            }
            self.file_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.file_path, 'w', encoding='utf-8') as f:
                json.dump(default_data, f, ensure_ascii=False, indent=2)

    def get_all_classes(self):
        """Получить все классы"""
        try:
            with open(self.file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return data.get('classes', [])
        except:
            return []

    def get_class_by_id(self, class_id):
        """Получить класс по ID"""
        classes = self.get_all_classes()
        for cls in classes:
            if cls['id'] == class_id:
                return cls
        return None

    def get_subjects_by_class(self, class_id):
        """Получить предметы класса"""
        cls = self.get_class_by_id(class_id)
        return cls['subjects'] if cls else []

    def calculate_price(self, class_id: str, selected_subjects: list) -> float:
        """
        Рассчитать стоимость обучения

        Args:
            class_id: ID класса
            selected_subjects: Список выбранных предметов (для 11 класса с ЕГЭ)

        Returns:
            float: Стоимость обучения
        """
        class_info = self.get_class_by_id(class_id)

        if not class_info:
            return 0.0

        pricing = class_info.get('pricing', {})
        pricing_type = pricing.get('type', 'fixed')

        if pricing_type == 'fixed':
            # Фиксированная стоимость
            return float(pricing.get('base_price', 0))

        elif pricing_type == 'per_subject':
            # Стоимость по предметам ЕГЭ
            base_price = float(pricing.get('base_subjects_price', 0))
            price_per_subject = float(pricing.get('price_per_subject', 0))

            # Получить предметы ЕГЭ
            exam_subjects = class_info.get('exam_subjects', [])

            # Подсчитать выбранные предметы ЕГЭ
            selected_exam_count = sum(1 for s in selected_subjects if s in exam_subjects)

            total = base_price + (selected_exam_count * price_per_subject)
            return total

        return 0.0

    def get_price_info(self, class_id):
        """
        Получить информацию о ценообразовании класса

        Returns:
            str: Описание ценообразования
        """
        cls = self.get_class_by_id(class_id)
        if not cls:
            return "Стоимость не определена"

        if cls.get('price_calculation') == 'per_subject':
            base = cls.get('base_price', 0)
            per_subject = cls.get('price_per_subject', 0)
            return f"Базовая: {base:,.0f} ₽ + {per_subject:,.0f} ₽ за каждый предмет ЕГЭ"

        return f"Фиксированная: {cls.get('base_price', 0):,.0f} ₽"
