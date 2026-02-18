"""
База данных классов и предметов.

Функциональность модуля:
- Инициализация файла classes.json с дефолтными данными при первом запуске.
- Чтение списка всех классов и поиск класса по ID.
- Получение списка предметов класса.
- Расчёт стоимости обучения (фиксированная / по количеству предметов ЕГЭ).
- Получение текстового описания ценообразования.

Структура записи класса в classes.json:
    {
        "id": str,              # Уникальный идентификатор класса
        "name": str,            # Отображаемое название класса
        "base_price": int,      # Базовая стоимость (отображение в UI)
        "subjects": list[str],  # Все предметы класса
        "pricing": {            # Блок ценообразования
            "type": str,                    # "fixed" | "per_subject"
            "base_price": float,            # Для fixed: итоговая сумма
            "base_subjects_price": float,   # Для per_subject: базовая часть
            "price_per_subject": float      # Для per_subject: цена за предмет ЕГЭ
        },
        # Только для 11 класса:
        "exam_subjects": list[str]  # Доступные предметы ЕГЭ для выбора
    }
"""

import json
from pathlib import Path


class ClassesDatabase:
    """
    База данных классов и учебных предметов.

    Хранит данные в JSON-файле classes.json рядом с модулем.
    Предоставляет методы чтения, поиска и расчёта стоимости.
    Запись в файл не предусмотрена — данные редактируются вручную.

    Атрибуты:
        file_path (Path): Абсолютный путь к файлу classes.json.
    """

    def __init__(self) -> None:
        """
        Инициализация базы данных классов.

        Определяет путь к classes.json рядом с текущим файлом и
        создаёт файл с дефолтными данными, если он отсутствует.
        """
        self.file_path: Path = Path(__file__).parent / "classes.json"
        self._ensure_file_exists()

    # =======================
    # Инициализация файла
    # =======================

    def _ensure_file_exists(self) -> None:
        """
        Создать файл classes.json с дефолтными данными, если он не существует.

        Дефолтные данные содержат четыре класса: 8, 9, 10 и 11.
        Классы 8–10 имеют фиксированную стоимость (pricing.type = 'fixed').
        Класс 11 имеет расчёт по предметам ЕГЭ (pricing.type = 'per_subject')
        и отдельный список exam_subjects для выбора через ExamSelectionPage.

        Каждая запись содержит блок 'pricing', который используется как
        calculate_price, так и get_price_info — оба метода согласованы
        и читают ценообразование из одного источника.
        """
        if not self.file_path.exists():
            default_data = {
                "classes": [
                    {
                        "id": "7",
                        "name": "7",
                        "base_price": 8500,
                        "subjects": [
                            "Математика",
                            "Русский язык",
                            "Английский язык",
                            "Физика",
                            "История",
                            "Биология",
                            "Химия",
                        ],
                        "pricing": {
                            "type": "fixed",
                            "base_price": 8500,
                        },
                    },
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
                            "Генетика",
                        ],
                        "pricing": {
                            "type": "fixed",
                            "base_price": 8000,
                        },
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
                            "Алгоритмы",
                        ],
                        "pricing": {
                            "type": "fixed",
                            "base_price": 7000,
                        },
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
                            "Микробиология",
                        ],
                        "pricing": {
                            "type": "fixed",
                            "base_price": 6500,
                        },
                    },
                    {
                        "id": "11",
                        "name": "11",
                        "base_price": 5000,
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
                            "Литература",
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
                            "Литература",
                        ],
                        "pricing": {
                            "type": "per_subject",
                            "base_subjects_price": 5000,
                            "price_per_subject": 3000,
                        },
                    },
                ],
            }
            self.file_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.file_path, "w", encoding="utf-8") as f:
                json.dump(default_data, f, ensure_ascii=False, indent=2)

    # =======================
    # Чтение данных
    # =======================

    def get_all_classes(self) -> list[dict]:
        """
        Получить список всех классов из файла.

        Возвращает:
            list[dict]: Список словарей с данными классов.
                При ошибке чтения или парсинга возвращает пустой список.
        """
        try:
            with open(self.file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            return data.get("classes", [])
        except Exception:  # noqa: BLE001
            return []

    def get_class_by_id(self, class_id: str) -> dict | None:
        """
        Найти и вернуть класс по его идентификатору.

        Параметры:
            class_id (str): Идентификатор класса (например, "8", "11").

        Возвращает:
            dict | None: Словарь с данными класса или None,
                если класс с таким ID не найден.
        """
        classes = self.get_all_classes()
        for cls in classes:
            if cls["id"] == class_id:
                return cls
        return None

    def get_subjects_by_class(self, class_id: str) -> list[str]:
        """
        Получить список всех предметов класса.

        Параметры:
            class_id (str): Идентификатор класса.

        Возвращает:
            list[str]: Список предметов класса или пустой список,
                если класс не найден.

        Примечание:
            Для 11 класса возвращает полный список subjects, включая
            «Русский язык», который отсутствует в exam_subjects.
            Для получения только предметов ЕГЭ используйте
            class_info.get('exam_subjects', []).
        """
        cls = self.get_class_by_id(class_id)
        return cls["subjects"] if cls else []

    # =======================
    # Расчёт стоимости
    # =======================

    def calculate_price(
        self,
        class_id: str,
        selected_subjects: list[str],
    ) -> float:
        """
        Рассчитать стоимость обучения для класса.

        Параметры:
            class_id (str): Идентификатор класса.
            selected_subjects (list[str]): Список выбранных предметов.
                Для классов с типом 'fixed' не влияет на результат.
                Для 11 класса (per_subject) определяет итоговую сумму.

        Возвращает:
            float: Рассчитанная стоимость обучения.
                0.0 — если класс не найден или тип ценообразования неизвестен.

        Логика расчёта:
            - 'fixed': возвращает pricing['base_price'].
            - 'per_subject': base_subjects_price
              + (кол-во выбранных предметов ЕГЭ × price_per_subject).
        """
        class_info = self.get_class_by_id(class_id)
        if not class_info:
            return 0.0

        pricing = class_info.get("pricing", {})
        pricing_type = pricing.get("type", "fixed")

        if pricing_type == "fixed":
            return float(pricing.get("base_price", 0))

        if pricing_type == "per_subject":
            base_price = float(pricing.get("base_subjects_price", 0))
            price_per_subject = float(pricing.get("price_per_subject", 0))
            exam_subjects = class_info.get("exam_subjects", [])
            selected_exam_count = sum(
                1 for s in selected_subjects if s in exam_subjects
            )
            return base_price + (selected_exam_count * price_per_subject)

        return 0.0

    def get_price_info(self, class_id: str) -> str:
        """
        Получить текстовое описание ценообразования класса.

        Параметры:
            class_id (str): Идентификатор класса.

        Возвращает:
            str: Читаемое описание стоимости. Примеры:
                - «Фиксированная: 8 000 ₽»
                - «Базовая: 5 000 ₽ + 3 000 ₽ за каждый предмет ЕГЭ»
                - «Стоимость не определена» — если класс не найден.

        Примечание:
            Читает ценообразование из блока 'pricing' — того же источника,
            что и calculate_price. Оба метода согласованы.
        """
        cls = self.get_class_by_id(class_id)
        if not cls:
            return "Стоимость не определена"

        pricing = cls.get("pricing", {})
        pricing_type = pricing.get("type", "fixed")

        if pricing_type == "per_subject":
            base = pricing.get("base_subjects_price", 0)
            per_subject = pricing.get("price_per_subject", 0)
            return (
                f"Базовая: {base:,.0f} ₽ "
                f"+ {per_subject:,.0f} ₽ за каждый предмет ЕГЭ"
            )

        return f"Фиксированная: {pricing.get('base_price', 0):,.0f} ₽"
