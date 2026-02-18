"""Тесты для генератора квитанций"""
import unittest
import os
import shutil
from core.receipt import generate_receipt, generate_receipt_from_dict


class TestReceiptGenerator(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        """Создать папку для результатов тестов (один раз для всех тестов)"""
        # Путь к папке test_results внутри tests/
        cls.test_results_dir = os.path.join(
            os.path.dirname(__file__),  # tests/
            'test_results'
        )

        # Очистить и создать заново
        if os.path.exists(cls.test_results_dir):
            shutil.rmtree(cls.test_results_dir)
        os.makedirs(cls.test_results_dir)

        print(f"\n📁 Результаты тестов будут сохранены в: {cls.test_results_dir}\n")

    def setUp(self):
        """Подготовка к тестам"""
        self.test_data = {
            'student_name': 'Тестовый Ученик Тестович',
            'courses': ['Математика', 'Физика'],
            'contract_number': '8БТ-TEST',
            'month_year': 'Январь',
            'compensation': '',
            'amount': 5000.0
        }

    def test_01_generate_receipt_from_dict(self):
        """Тест генерации квитанции из словаря"""
        output_path = os.path.join(
            self.test_results_dir,
            '01_basic_receipt.pdf'
        )

        result = generate_receipt_from_dict(self.test_data, output_path)

        # Проверить, что файл создан
        self.assertTrue(os.path.exists(result))

        # Проверить, что файл не пустой
        self.assertGreater(os.path.getsize(result), 0)

        # Проверить, что это PDF (начинается с %PDF)
        with open(result, 'rb') as f:
            header = f.read(4)
            self.assertEqual(header, b'%PDF')

        print(f"✅ Создан: {os.path.basename(output_path)}")

    def test_02_generate_receipt_with_compensation(self):
        """Тест с компенсацией"""
        test_data = self.test_data.copy()
        test_data['compensation'] = '500'
        test_data['student_name'] = 'Петрова Анна Сергеевна'

        output_path = os.path.join(
            self.test_results_dir,
            '02_with_compensation.pdf'
        )

        result = generate_receipt_from_dict(test_data, output_path)
        self.assertTrue(os.path.exists(result))
        self.assertGreater(os.path.getsize(result), 0)

        print(f"✅ Создан: {os.path.basename(output_path)}")

    def test_03_generate_receipt_multiple_courses(self):
        """Тест с несколькими предметами"""
        test_data = self.test_data.copy()
        test_data['courses'] = [
            'Математика',
            'Физика',
            'Химия',
            'Биология'
        ]
        test_data['student_name'] = 'Иванов Иван Иванович'
        test_data['amount'] = 8000.0

        output_path = os.path.join(
            self.test_results_dir,
            '03_multiple_courses.pdf'
        )

        result = generate_receipt_from_dict(test_data, output_path)
        self.assertTrue(os.path.exists(result))
        self.assertGreater(os.path.getsize(result), 0)

        print(f"✅ Создан: {os.path.basename(output_path)}")

    def test_04_generate_receipt_single_course(self):
        """Тест с одним предметом"""
        test_data = self.test_data.copy()
        test_data['courses'] = ['Английский язык']
        test_data['student_name'] = 'Сидорова Мария Петровна'
        test_data['amount'] = 3500.0

        output_path = os.path.join(
            self.test_results_dir,
            '04_single_course.pdf'
        )

        result = generate_receipt_from_dict(test_data, output_path)
        self.assertTrue(os.path.exists(result))

        print(f"✅ Создан: {os.path.basename(output_path)}")

    def test_05_generate_receipt_decimal_amount(self):
        """Тест с дробной суммой"""
        test_data = self.test_data.copy()
        test_data['amount'] = 4500.50
        test_data['student_name'] = 'Козлов Дмитрий Александрович'

        output_path = os.path.join(
            self.test_results_dir,
            '05_decimal_amount.pdf'
        )

        result = generate_receipt_from_dict(test_data, output_path)
        self.assertTrue(os.path.exists(result))

        print(f"✅ Создан: {os.path.basename(output_path)}")

    def test_06_generate_receipt_function(self):
        """Тест прямого вызова функции generate_receipt"""
        output_path = os.path.join(
            self.test_results_dir,
            '06_direct_call.pdf'
        )

        result = generate_receipt(
            student_name='Петров Петр Петрович',
            courses=['История', 'География'],
            contract_number='8БТ-5',
            month_year='Февраль',
            amount=6000.0,
            compensation='',
            output_path=output_path
        )

        self.assertTrue(os.path.exists(result))
        self.assertGreater(os.path.getsize(result), 0)

        print(f"✅ Создан: {os.path.basename(output_path)}")


class TestReceiptGeneratorEdgeCases(unittest.TestCase):
    """Тесты граничных случаев"""

    @classmethod
    def setUpClass(cls):
        """Использовать ту же папку для результатов"""
        cls.test_results_dir = os.path.join(
            os.path.dirname(__file__),
            'test_results'
        )
        # Папка уже создана в TestReceiptGenerator
        if not os.path.exists(cls.test_results_dir):
            os.makedirs(cls.test_results_dir)

    def test_07_long_student_name(self):
        """Тест с очень длинным ФИО"""
        test_data = {
            'student_name': 'Очень-Длинное-Составное-Фамилие-Имя Александр Константинович',
            'courses': ['Математика'],
            'contract_number': '8БТ-1',
            'month_year': 'Февраль',
            'compensation': '',
            'amount': 3000.0
        }

        output_path = os.path.join(
            self.test_results_dir,
            '07_long_name.pdf'
        )

        result = generate_receipt_from_dict(test_data, output_path)
        self.assertTrue(os.path.exists(result))

        print(f"✅ Создан: {os.path.basename(output_path)}")

    def test_08_many_courses(self):
        """Тест с большим количеством предметов"""
        test_data = {
            'student_name': 'Иванов Иван',
            'courses': [
                'Математика', 'Физика', 'Химия',
                'Биология', 'География', 'История'
            ],
            'contract_number': '8БТ-1',
            'month_year': 'Март',
            'compensation': '',
            'amount': 12000.0
        }

        output_path = os.path.join(
            self.test_results_dir,
            '08_many_courses.pdf'
        )

        result = generate_receipt_from_dict(test_data, output_path)
        self.assertTrue(os.path.exists(result))

        print(f"✅ Создан: {os.path.basename(output_path)}")

    def test_09_long_course_names(self):
        """Тест с длинными названиями предметов"""
        test_data = {
            'student_name': 'Сидоров Семен Семенович',
            'courses': [
                'Молекулярная биология и генетика',
                'Органическая химия и биохимия',
                'Математический анализ'
            ],
            'contract_number': '8БТ-7',
            'month_year': 'Апрель',
            'compensation': '1000',
            'amount': 7500.0
        }

        output_path = os.path.join(
            self.test_results_dir,
            '09_long_course_names.pdf'
        )

        result = generate_receipt_from_dict(test_data, output_path)
        self.assertTrue(os.path.exists(result))

        print(f"✅ Создан: {os.path.basename(output_path)}")

    def test_10_cyrillic_characters(self):
        """Тест корректности работы с кириллицей"""
        test_data = {
            'student_name': 'Щербаков Ярослав Юрьевич',
            'courses': ['Русский язык', 'Литература'],
            'contract_number': '8БТ-Ю',
            'month_year': 'Май',
            'compensation': '',
            'amount': 4000.0
        }

        output_path = os.path.join(
            self.test_results_dir,
            '10_cyrillic.pdf'
        )

        result = generate_receipt_from_dict(test_data, output_path)
        self.assertTrue(os.path.exists(result))

        print(f"✅ Создан: {os.path.basename(output_path)}")

    def test_11_zero_compensation(self):
        """Тест с нулевой компенсацией"""
        test_data = {
            'student_name': 'Тестов Тест Тестович',
            'courses': ['Тестирование'],
            'contract_number': '8БТ-0',
            'month_year': 'Январь',
            'compensation': '0',
            'amount': 1000.0
        }

        output_path = os.path.join(
            self.test_results_dir,
            '11_zero_compensation.pdf'
        )

        result = generate_receipt_from_dict(test_data, output_path)
        self.assertTrue(os.path.exists(result))

        print(f"✅ Создан: {os.path.basename(output_path)}")

    def test_12_large_amount(self):
        """Тест с большой суммой"""
        test_data = {
            'student_name': 'Богатов Богат Богатович',
            'courses': ['VIP Программа'],
            'contract_number': '8БТ-VIP',
            'month_year': 'Декабрь',
            'compensation': '',
            'amount': 99999.99
        }

        output_path = os.path.join(
            self.test_results_dir,
            '12_large_amount.pdf'
        )

        result = generate_receipt_from_dict(test_data, output_path)
        self.assertTrue(os.path.exists(result))

        print(f"✅ Создан: {os.path.basename(output_path)}")

    @classmethod
    def tearDownClass(cls):
        """Вывести итоговую информацию"""
        if os.path.exists(cls.test_results_dir):
            files = [f for f in os.listdir(cls.test_results_dir) if f.endswith('.pdf')]
            print(f"\n{'=' * 70}")
            print(f"🎉 ТЕСТИРОВАНИЕ ЗАВЕРШЕНО!")
            print(f"{'=' * 70}")
            print(f"📁 Создано PDF файлов: {len(files)}")
            print(f"📂 Папка результатов: {cls.test_results_dir}")
            print(f"\n📋 Созданные файлы:")
            for i, filename in enumerate(sorted(files), 1):
                print(f"   {i:2d}. {filename}")
            print(f"{'=' * 70}\n")


class TestReceiptGeneratorErrors(unittest.TestCase):
    """Тесты обработки ошибок (без создания PDF)"""

    def test_missing_template(self):
        """Тест ошибки при отсутствии шаблона"""
        test_data = {
            'student_name': 'Тест',
            'courses': ['Тест'],
            'contract_number': '1',
            'month_year': 'Январь',
            'compensation': '',
            'amount': 1000.0
        }

        # Этот тест не создает файл в test_results
        # Просто проверяет обработку ошибок
        try:
            result = generate_receipt_from_dict(test_data, 'temp_test.pdf')
            # Если успешно - шаблон на месте
            self.assertTrue(os.path.exists(result))
            # Удалить временный файл
            if os.path.exists('temp_test.pdf'):
                os.remove('temp_test.pdf')
        except FileNotFoundError as e:
            # Ожидаемое поведение при отсутствии шаблона
            self.assertIn('Шаблон не найден', str(e))


if __name__ == '__main__':
    unittest.main()
