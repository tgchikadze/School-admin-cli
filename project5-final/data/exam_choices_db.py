"""
База данных выбранных предметов ЕГЭ для учеников 11 класса.

Функциональность модуля:
- Инициализация файла exam_choices.json при первом запуске.
- Получение списка выбранных предметов ЕГЭ по ID ученика.
- Сохранение и обновление выбора предметов ЕГЭ ученика.
- Удаление записи о выборе предметов при отчислении ученика.
- Расчёт стоимости обучения по количеству выбранных предметов ЕГЭ.

Структура файла exam_choices.json:
    {
        "exam_choices": [
            {
                "student_id": str,          # ID ученика из students.json
                "selected_exams": list[str] # Список выбранных предметов ЕГЭ
            },
            ...
        ]
    }

Файл создаётся автоматически как пустой при первом запуске.
Данные записываются через save_student_exams при работе с ExamSelectionPage.
Предзаполнять файл вручную не требуется.
"""

import json
from pathlib import Path
from typing import Dict, List


class ExamChoicesDatabase:
    """
    База данных выбора предметов ЕГЭ для учеников 11 класса.

    Хранит данные в файле exam_choices.json рядом с модулем в папке data/.
    Поддерживает чтение, запись, обновление и удаление записей.

    Атрибуты:
        data_file (Path): Абсолютный путь к файлу exam_choices.json.
    """

    def __init__(self, data_file: str | None = None) -> None:
        """
        Инициализация базы данных выбора ЕГЭ.

        Параметры:
            data_file (str | None): Путь к файлу данных.
                Если не передан — используется data/exam_choices.json
                рядом с текущим файлом модуля.
                Явный путь полезен в тестах или нестандартных конфигурациях.
        """
        if data_file is None:
            self.data_file: Path = (
                Path(__file__).parent / "exam_choices.json"
            )
        else:
            self.data_file = Path(data_file)
        self._ensure_data_file()

    # =======================
    # Инициализация файла
    # =======================

    def _ensure_data_file(self) -> None:
        """
        Создать файл exam_choices.json, если он не существует.

        Создаёт все промежуточные директории при необходимости.
        Новый файл содержит пустой список выборов: {"exam_choices": []}.
        """
        self.data_file.parent.mkdir(parents=True, exist_ok=True)
        if not self.data_file.exists():
            self._save({"exam_choices": []})

    # =======================
    # Внутренние методы I/O
    # =======================

    def _load(self) -> Dict:
        """
        Загрузить данные из файла exam_choices.json.

        Возвращает:
            Dict: Словарь с ключом 'exam_choices'.
                При ошибке чтения или парсинга возвращает
                {"exam_choices": []} и выводит сообщение об ошибке.
        """
        try:
            with open(self.data_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError) as e:
            print(f"Ошибка чтения файла выбора ЕГЭ: {e}")
            return {"exam_choices": []}

    def _save(self, data: Dict) -> None:
        """
        Сохранить данные в файл exam_choices.json.

        Параметры:
            data (Dict): Словарь с ключом 'exam_choices' для записи.
        """
        with open(self.data_file, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    # =======================
    # Работа с записями
    # =======================

    def get_student_exams(self, student_id: str) -> List[str]:
        """
        Получить список выбранных предметов ЕГЭ ученика.

        Параметры:
            student_id (str): ID ученика.

        Возвращает:
            List[str]: Список выбранных предметов ЕГЭ.
                Пустой список, если запись для ученика не найдена.
        """
        data = self._load()
        for choice in data.get("exam_choices", []):
            if choice.get("student_id") == student_id:
                return choice.get("selected_exams", [])
        return []

    def save_student_exams(
        self,
        student_id: str,
        selected_exams: List[str],
    ) -> None:
        """
        Сохранить или обновить выбранные предметы ЕГЭ ученика.

        Если запись для ученика уже существует — обновляет список предметов.
        Если записи нет — создаёт новую.

        Параметры:
            student_id (str): ID ученика.
            selected_exams (List[str]): Список выбранных предметов ЕГЭ.
        """
        data = self._load()
        exam_choices = data.get("exam_choices", [])

        found = False
        for choice in exam_choices:
            if choice.get("student_id") == student_id:
                choice["selected_exams"] = selected_exams
                found = True
                break

        if not found:
            exam_choices.append(
                {
                    "student_id": student_id,
                    "selected_exams": selected_exams,
                }
            )

        data["exam_choices"] = exam_choices
        self._save(data)
        print(
            f"✅ Сохранены ЕГЭ для ученика {student_id}: "
            f"{len(selected_exams)} предметов"
        )

    def delete_student_exams(self, student_id: str) -> None:
        """
        Удалить запись о выборе предметов ЕГЭ ученика.

        Вызывается при удалении ученика из системы, чтобы не оставлять
        «висячих» записей в exam_choices.json.

        Параметры:
            student_id (str): ID ученика, чья запись будет удалена.
                Если запись не найдена — операция проходит без ошибок.
        """
        data = self._load()
        exam_choices = data.get("exam_choices", [])
        exam_choices = [
            c for c in exam_choices if c.get("student_id") != student_id
        ]
        data["exam_choices"] = exam_choices
        self._save(data)
        print(f"✅ Удалены ЕГЭ для ученика {student_id}")

    # =======================
    # Расчёт стоимости
    # =======================

    def calculate_exam_cost(
        self,
        selected_exams: List[str],
        price_per_exam: float = 3000,
    ) -> float:
        """
        Рассчитать стоимость обучения по количеству выбранных предметов ЕГЭ.

        Формула: кол-во предметов × цена за предмет.
        Дефолтная цена 3000 ₽ согласована с pricing.price_per_subject
        класса 11 в classes.json.

        Параметры:
            selected_exams (List[str]): Список выбранных предметов ЕГЭ.
            price_per_exam (float): Цена за один предмет ЕГЭ.
                По умолчанию 3000 ₽.

        Возвращает:
            float: Итоговая стоимость обучения.
        """
        return len(selected_exams) * price_per_exam
