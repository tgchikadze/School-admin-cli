"""Тесты для модуля file_manager"""
import unittest
import os
import tempfile
import shutil
from core.file_manager import search_files, analyze_directory, copy_file, get_file_info


class TestFileManager(unittest.TestCase):

    def setUp(self):
        """Создать временную директорию для тестов"""
        self.test_dir = tempfile.mkdtemp()

        # Создать тестовые файлы
        self.test_files = [
            'test_receipt_1.pdf',
            'test_receipt_2.pdf',
            'document.txt',
            'image.jpg'
        ]

        for filename in self.test_files:
            file_path = os.path.join(self.test_dir, filename)
            with open(file_path, 'w') as f:
                f.write("test content " * 100)  # ~1.3 KB

        # Создать поддиректорию
        self.subdir = os.path.join(self.test_dir, 'subdir')
        os.makedirs(self.subdir)

        subfile = os.path.join(self.subdir, 'nested_receipt.pdf')
        with open(subfile, 'w') as f:
            f.write("nested content " * 100)

    def tearDown(self):
        """Удалить временную директорию"""
        shutil.rmtree(self.test_dir)

    # ===== ТЕСТЫ ДЛЯ SEARCH_FILES =====

    def test_search_files_by_extension(self):
        """Тест поиска по расширению"""
        results = search_files(self.test_dir, '.pdf')
        self.assertEqual(len(results), 3)  # 2 в корне + 1 вложенный

        # Проверить, что все найденные файлы - PDF
        for file in results:
            self.assertTrue(file.endswith('.pdf'))

    def test_search_files_by_name(self):
        """Тест поиска по имени"""
        results = search_files(self.test_dir, 'receipt')
        self.assertEqual(len(results), 3)

        # Проверить, что в именах есть "receipt"
        for file in results:
            self.assertIn('receipt', os.path.basename(file).lower())

    def test_search_files_not_found(self):
        """Тест поиска несуществующих файлов"""
        results = search_files(self.test_dir, 'nonexistent')
        self.assertEqual(len(results), 0)

    def test_search_files_invalid_directory(self):
        """Тест поиска в несуществующей директории"""
        with self.assertRaises(FileNotFoundError):
            search_files('/nonexistent/path/12345', 'test')

    def test_search_files_txt_files(self):
        """Тест поиска TXT файлов"""
        results = search_files(self.test_dir, '.txt')
        self.assertEqual(len(results), 1)
        self.assertTrue(results[0].endswith('document.txt'))

    # ===== ТЕСТЫ ДЛЯ ANALYZE_DIRECTORY =====

    def test_analyze_directory(self):
        """Тест анализа директории"""
        info = analyze_directory(self.test_dir)

        # Проверить наличие ключей
        self.assertIn('total_files', info)
        self.assertIn('size_mb', info)
        self.assertIn('size_gb', info)
        self.assertIn('breakdown', info)

        # Должно быть 5 файлов (4 в корне + 1 вложенный)
        self.assertEqual(info['total_files'], 5)

        # Размер должен быть больше 0
        self.assertGreater(info['size_bytes'], 0)

    def test_analyze_directory_breakdown(self):
        """Тест детализации анализа"""
        info = analyze_directory(self.test_dir)

        # Проверить, что breakdown содержит файлы и папки
        has_file = any(item['type'] == 'file' for item in info['breakdown'])
        has_dir = any(item['type'] == 'directory' for item in info['breakdown'])

        self.assertTrue(has_file, "Должны быть файлы")
        self.assertTrue(has_dir, "Должны быть директории")

        # Проверить, что breakdown отсортирован по размеру
        sizes = [item['size_bytes'] for item in info['breakdown']]
        self.assertEqual(sizes, sorted(sizes, reverse=True))

    def test_analyze_directory_invalid(self):
        """Тест анализа несуществующей директории"""
        with self.assertRaises(FileNotFoundError):
            analyze_directory('/nonexistent/path/12345')

    def test_analyze_directory_size_calculation(self):
        """Тест правильности расчета размера"""
        info = analyze_directory(self.test_dir)

        # Проверить, что размеры согласованы
        self.assertEqual(
            info['size_mb'],
            round(info['size_bytes'] / (1024 * 1024), 2)
        )
        self.assertEqual(
            info['size_gb'],
            round(info['size_bytes'] / (1024 * 1024 * 1024), 3)
        )

    # ===== ТЕСТЫ ДЛЯ COPY_FILE =====

    def test_copy_file(self):
        """Тест копирования файла"""
        source = os.path.join(self.test_dir, self.test_files[0])
        destination = os.path.join(self.test_dir, 'copied_file.pdf')

        result = copy_file(source, destination)

        # Проверить, что файл скопирован
        self.assertTrue(os.path.exists(result))

        # Проверить, что исходный файл остался
        self.assertTrue(os.path.exists(source))

        # Проверить, что размеры совпадают
        self.assertEqual(
            os.path.getsize(source),
            os.path.getsize(destination)
        )

    def test_copy_file_to_new_directory(self):
        """Тест копирования с созданием новой директории"""
        source = os.path.join(self.test_dir, self.test_files[0])
        destination = os.path.join(self.test_dir, 'new', 'folder', 'file.pdf')

        result = copy_file(source, destination)

        # Проверить, что файл создан
        self.assertTrue(os.path.exists(result))

        # Проверить, что директория создана
        self.assertTrue(os.path.exists(os.path.dirname(result)))

    def test_copy_file_not_found(self):
        """Тест копирования несуществующего файла"""
        with self.assertRaises(FileNotFoundError):
            copy_file('/nonexistent/file.txt', 'destination.txt')

    def test_copy_file_directory_error(self):
        """Тест попытки скопировать директорию как файл"""
        with self.assertRaises(IsADirectoryError):
            copy_file(self.test_dir, 'destination')

    def test_copy_file_overwrites_existing(self):
        """Тест перезаписи существующего файла"""
        source = os.path.join(self.test_dir, self.test_files[0])
        destination = os.path.join(self.test_dir, 'existing.pdf')

        # Создать файл назначения
        with open(destination, 'w') as f:
            f.write("old content")

        # Скопировать
        result = copy_file(source, destination)

        # Проверить, что файл перезаписан (размеры совпадают с источником)
        self.assertEqual(
            os.path.getsize(source),
            os.path.getsize(destination)
        )

    # ===== ТЕСТЫ ДЛЯ GET_FILE_INFO =====

    def test_get_file_info(self):
        """Тест получения информации о файле"""
        test_file = os.path.join(self.test_dir, self.test_files[0])
        info = get_file_info(test_file)

        # Проверить наличие ключей
        self.assertIn('name', info)
        self.assertIn('extension', info)
        self.assertIn('size_bytes', info)
        self.assertIn('size_mb', info)
        self.assertIn('modified', info)
        self.assertIn('path', info)

        # Проверить значения
        self.assertEqual(info['name'], self.test_files[0])
        self.assertEqual(info['extension'], '.pdf')
        self.assertGreater(info['size_bytes'], 0)

    def test_get_file_info_invalid(self):
        """Тест получения информации о несуществующем файле"""
        with self.assertRaises(FileNotFoundError):
            get_file_info('/nonexistent/file.txt')


if __name__ == '__main__':
    unittest.main()
