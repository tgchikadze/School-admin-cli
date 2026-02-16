"""
Класс для работы с базой данных учеников (JSON)
В будущем (проект 4-5) заменим на PostgreSQL
"""
import json
import os
from typing import List, Dict, Optional


class StudentDatabase:
    """Класс для работы с базой данных учеников"""

    def __init__(self, db_path: str = None):
        """
        Инициализация базы данных

        Args:
            db_path: Путь к JSON файлу с данными
        """
        if db_path is None:
            # Путь по умолчанию относительно этого файла
            current_dir = os.path.dirname(os.path.abspath(__file__))
            db_path = os.path.join(current_dir, 'students.json')

        self.db_path = db_path
        self._ensure_db_exists()

    def _ensure_db_exists(self):
        """Создать файл БД если его нет"""
        if not os.path.exists(self.db_path):
            self._save_data({'students': []})

    def _load_data(self) -> Dict:
        """Загрузить данные из JSON"""
        try:
            with open(self.db_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"Ошибка загрузки данных: {e}")
            return {'students': []}

    def _save_data(self, data: Dict):
        """Сохранить данные в JSON"""
        try:
            with open(self.db_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"Ошибка сохранения данных: {e}")
            raise

    def get_all(self) -> List[Dict]:
        """Получить всех учеников"""
        data = self._load_data()
        return data.get('students', [])

    def get_by_id(self, student_id: str) -> Optional[Dict]:
        """
        Получить ученика по ID

        Args:
            student_id: ID ученика

        Returns:
            Словарь с данными ученика или None
        """
        students = self.get_all()
        for student in students:
            if student.get('id') == student_id:
                return student
        return None

    def search(self, query: str) -> List[Dict]:
        """
        Поиск учеников по ФИО

        Args:
            query: Поисковый запрос

        Returns:
            Список найденных учеников
        """
        query_lower = query.lower()
        students = self.get_all()

        results = []
        for student in students:
            fio = student.get('fio', '').lower()
            if query_lower in fio:
                results.append(student)

        return results

    def add(self, student: Dict) -> bool:
        """
        Добавить нового ученика

        Args:
            student: Словарь с данными ученика

        Returns:
            True если успешно, False если ошибка
        """
        try:
            data = self._load_data()
            students = data.get('students', [])

            # Генерировать новый ID
            if students:
                max_id = max(int(s['id']) for s in students)
                new_id = str(max_id + 1).zfill(3)
            else:
                new_id = "001"

            student['id'] = new_id
            students.append(student)

            data['students'] = students
            self._save_data(data)
            return True

        except Exception as e:
            print(f"Ошибка добавления ученика: {e}")
            return False

    def update(self, student_id: str, updated_data: Dict) -> bool:
        """
        Обновить данные ученика

        Args:
            student_id: ID ученика
            updated_data: Обновленные данные

        Returns:
            True если успешно, False если ошибка
        """
        try:
            data = self._load_data()
            students = data.get('students', [])

            for i, student in enumerate(students):
                if student.get('id') == student_id:
                    # Обновить данные, сохранив ID
                    updated_data['id'] = student_id
                    students[i] = updated_data

                    data['students'] = students
                    self._save_data(data)
                    return True

            return False  # Ученик не найден

        except Exception as e:
            print(f"Ошибка обновления ученика: {e}")
            return False

    def delete(self, student_id: str) -> bool:
        """
        Удалить ученика

        Args:
            student_id: ID ученика

        Returns:
            True если успешно, False если ошибка
        """
        try:
            data = self._load_data()
            students = data.get('students', [])

            # Найти и удалить ученика
            students = [s for s in students if s.get('id') != student_id]

            data['students'] = students
            self._save_data(data)
            return True

        except Exception as e:
            print(f"Ошибка удаления ученика: {e}")
            return False

    def get_count(self) -> int:
        """Получить количество учеников"""
        return len(self.get_all())
