"""
База данных учеников
"""
import json
from pathlib import Path
from typing import List, Dict, Optional


class StudentDatabase:
    """Класс для работы с базой данных учеников"""

    def __init__(self, data_file: str = "core/data/students.json"):
        """
        Инициализация базы данных

        Args:
            data_file: Путь к файлу с данными
        """
        self.data_file = Path(data_file)
        self._ensure_data_file()

    def _ensure_data_file(self):
        """Создать файл данных если его нет"""
        self.data_file.parent.mkdir(parents=True, exist_ok=True)
        if not self.data_file.exists():
            self._save([])

    def _load(self) -> List[Dict]:
        """Загрузить данные из файла"""
        try:
            with open(self.data_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError) as e:
            print(f"Error reading students: {e}")
            return []

    def _save(self, data: List[Dict]):
        """Сохранить данные в файл"""
        with open(self.data_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def get_all(self) -> List[Dict]:
        """Получить всех учеников"""
        return self._load()

    def get_by_id(self, student_id: str) -> Optional[Dict]:
        """
        Получить ученика по ID

        Args:
            student_id: ID ученика

        Returns:
            dict или None если не найдено
        """
        students = self.get_all()
        for student in students:
            if student['id'] == student_id:
                return student
        return None

    def add(self, fio, contract_number, class_id, monthly_payment, compensation=""):
        """
        Добавить ученика в базу

        Args:
            fio: ФИО ученика
            contract_number: Номер договора
            class_id: ID класса
            monthly_payment: Ежемесячная оплата
            compensation: Компенсация (опционально)

        Returns:
            dict: Добавленный ученик или None при ошибке
        """
        students = self.get_all()

        # Проверка на дубликаты
        if self.check_duplicate(fio, contract_number):
            print(f"⚠️ Ученик с таким ФИО или номером договора уже существует")
            return None

        # Генерация ID
        if students:
            last_id = max(int(s['id']) for s in students)
            new_id = f"{last_id + 1:03d}"
        else:
            new_id = "001"

        # Создать запись ученика
        student = {
            'id': new_id,
            'fio': fio,
            'contract_number': contract_number,
            'class_id': class_id,
            'monthly_payment': monthly_payment,
            'compensation': compensation
        }

        students.append(student)
        self._save(students)

        print(f"✅ Добавлен ученик: {fio} (ID: {new_id})")
        return student

    def update(self, student_id, fio=None, contract_number=None, class_id=None,
               monthly_payment=None, compensation=None):
        """
        Обновить данные ученика

        Args:
            student_id: ID ученика
            fio: Новое ФИО (опционально)
            contract_number: Новый номер договора (опционально)
            class_id: Новый ID класса (опционально)
            monthly_payment: Новая оплата (опционально)
            compensation: Новая компенсация (опционально)

        Returns:
            bool: True если обновлено, False если не найдено
        """
        students = self.get_all()

        for student in students:
            if student['id'] == student_id:
                if fio is not None:
                    student['fio'] = fio
                if contract_number is not None:
                    student['contract_number'] = contract_number
                if class_id is not None:
                    student['class_id'] = class_id
                if monthly_payment is not None:
                    student['monthly_payment'] = monthly_payment
                if compensation is not None:
                    student['compensation'] = compensation

                self._save(students)
                print(f"✅ Обновлен ученик: {student['fio']} (ID: {student_id})")
                return True

        return False

    def delete(self, student_id: str) -> bool:
        """
        Удалить ученика

        Args:
            student_id: ID ученика

        Returns:
            bool: True если удалено, False если не найдено
        """
        students = self.get_all()

        for i, student in enumerate(students):
            if student['id'] == student_id:
                deleted_student = students.pop(i)
                self._save(students)
                print(f"✅ Удален ученик: {deleted_student['fio']} (ID: {student_id})")
                return True

        return False

    def search(self, query: str) -> List[Dict]:
        """
        Поиск учеников по ФИО

        Args:
            query: Поисковый запрос

        Returns:
            list: Список найденных учеников
        """
        students = self.get_all()
        query_lower = query.lower()

        results = [
            s for s in students
            if query_lower in s['fio'].lower()
        ]

        return results

    def check_duplicate(self, fio: str, contract_number: str, exclude_id: str = None) -> bool:
        """
        Проверить наличие дубликата

        Args:
            fio: ФИО для проверки
            contract_number: Номер договора для проверки
            exclude_id: ID ученика, который нужно исключить из проверки

        Returns:
            bool: True если дубликат найден
        """
        students = self.get_all()

        for student in students:
            # Пропустить ученика с exclude_id
            if exclude_id and student['id'] == exclude_id:
                continue

            # Проверка на совпадение ФИО или номера договора
            if student['fio'] == fio or student['contract_number'] == contract_number:
                return True

        return False

    def clear_all(self):
        """Очистить всю базу данных"""
        self._save([])
        print("✅ База данных очищена")
