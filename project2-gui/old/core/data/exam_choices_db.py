"""
База данных выбранных ЕГЭ для 11 класса
"""
import json
from pathlib import Path
from typing import List, Dict, Optional


class ExamChoicesDatabase:
    """Класс для работы с выбором предметов ЕГЭ"""

    def __init__(self, data_file: str = "core/data/exam_choices.json"):
        """
        Инициализация базы данных выбора ЕГЭ

        Args:
            data_file: Путь к файлу с данными
        """
        self.data_file = Path(data_file)
        self._ensure_data_file()

    def _ensure_data_file(self):
        """Создать файл данных если его нет"""
        self.data_file.parent.mkdir(parents=True, exist_ok=True)
        if not self.data_file.exists():
            self._save({'exam_choices': []})

    def _load(self) -> Dict:
        """Загрузить данные из файла"""
        try:
            with open(self.data_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError) as e:
            print(f"Error reading exam choices: {e}")
            return {'exam_choices': []}

    def _save(self, data: Dict):
        """Сохранить данные в файл"""
        with open(self.data_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def get_student_exams(self, student_id: str) -> List[str]:
        """
        Получить выбранные экзамены ученика

        Args:
            student_id: ID ученика

        Returns:
            list: Список выбранных экзаменов
        """
        data = self._load()
        exam_choices = data.get('exam_choices', [])

        for choice in exam_choices:
            if choice.get('student_id') == student_id:
                return choice.get('selected_exams', [])

        return []

    def save_student_exams(self, student_id: str, selected_exams: List[str]):
        """
        Сохранить выбранные экзамены ученика

        Args:
            student_id: ID ученика
            selected_exams: Список выбранных экзаменов
        """
        data = self._load()
        exam_choices = data.get('exam_choices', [])

        # Найти существующую запись
        found = False
        for choice in exam_choices:
            if choice.get('student_id') == student_id:
                choice['selected_exams'] = selected_exams
                found = True
                break

        # Если не найдена, создать новую
        if not found:
            exam_choices.append({
                'student_id': student_id,
                'selected_exams': selected_exams
            })

        data['exam_choices'] = exam_choices
        self._save(data)

        print(f"✅ Сохранены ЕГЭ для ученика {student_id}: {len(selected_exams)} предметов")

    def delete_student_exams(self, student_id: str):
        """
        Удалить запись о выборе экзаменов ученика

        Args:
            student_id: ID ученика
        """
        data = self._load()
        exam_choices = data.get('exam_choices', [])

        exam_choices = [choice for choice in exam_choices if choice.get('student_id') != student_id]

        data['exam_choices'] = exam_choices
        self._save(data)

        print(f"✅ Удалены ЕГЭ для ученика {student_id}")

    def calculate_exam_cost(self, selected_exams: List[str], price_per_exam: float = 3000) -> float:
        """
        Рассчитать стоимость на основе количества экзаменов

        Args:
            selected_exams: Список выбранных экзаменов
            price_per_exam: Цена за один экзамен (по умолчанию 3000)

        Returns:
            float: Общая стоимость
        """
        return len(selected_exams) * price_per_exam
