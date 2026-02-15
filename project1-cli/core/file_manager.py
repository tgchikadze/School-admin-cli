"""Модуль для работы с файлами и директориями"""
import os
import glob
from pathlib import Path


def search_files(directory, pattern):
    """
    Ищет файлы по паттерну в директории (рекурсивно)

    Args:
        directory (str): Путь к директории для поиска
        pattern (str): Паттерн поиска (например, "*.pdf", "квитанция", ".txt")

    Returns:
        list: Список найденных файлов с полными путями

    Raises:
        FileNotFoundError: Если директория не существует

    Examples:
        >>> search_files('./documents', '*.pdf')
        ['./documents/receipt1.pdf', './documents/subdir/receipt2.pdf']

        >>> search_files('./documents', 'квитанция')
        ['./documents/квитанция_2024.pdf', './documents/old/квитанция_2023.pdf']
    """
    if not os.path.exists(directory):
        raise FileNotFoundError(f"Директория не найдена: {directory}")

    results = []

    # Построить паттерн для поиска
    if not pattern.startswith('*'):
        search_pattern = f'*{pattern}*'
    else:
        search_pattern = pattern

    search_path = os.path.join(directory, '**', search_pattern)

    # Рекурсивный поиск
    for file_path in glob.glob(search_path, recursive=True):
        if os.path.isfile(file_path):
            results.append(os.path.abspath(file_path))

    return sorted(results)


def analyze_directory(directory):
    """
    Анализирует структуру и размер директории

    Args:
        directory (str): Путь к директории для анализа

    Returns:
        dict: Информация о директории {
            'total_files': int,           # Общее количество файлов
            'size_bytes': int,            # Размер в байтах
            'size_mb': float,             # Размер в мегабайтах
            'size_gb': float,             # Размер в гигабайтах
            'breakdown': list[dict]       # Детализация по файлам/папкам
        }

    Raises:
        FileNotFoundError: Если директория не существует

    Examples:
        >>> info = analyze_directory('./documents')
        >>> print(f"Всего файлов: {info['total_files']}")
        >>> print(f"Размер: {info['size_mb']} MB")
    """
    if not os.path.exists(directory):
        raise FileNotFoundError(f"Директория не найдена: {directory}")

    total_size = 0
    total_files = 0
    breakdown = []

    # Анализ содержимого на первом уровне
    try:
        items = os.listdir(directory)
    except PermissionError:
        return {
            'total_files': 0,
            'size_bytes': 0,
            'size_mb': 0.0,
            'size_gb': 0.0,
            'breakdown': [],
            'error': 'Permission denied'
        }

    for item in items:
        item_path = os.path.join(directory, item)

        try:
            if os.path.isfile(item_path):
                # Обработка файла
                size = os.path.getsize(item_path)
                total_size += size
                total_files += 1

                breakdown.append({
                    'name': item,
                    'type': 'file',
                    'size_bytes': size,
                    'size_mb': round(size / (1024 * 1024), 2),
                    'path': item_path
                })

            elif os.path.isdir(item_path):
                # Рекурсивный подсчет размера папки
                folder_size = 0
                folder_files = 0

                for root, dirs, files in os.walk(item_path):
                    for file in files:
                        file_path = os.path.join(root, file)
                        try:
                            file_size = os.path.getsize(file_path)
                            folder_size += file_size
                            folder_files += 1
                        except (PermissionError, FileNotFoundError):
                            # Пропускаем файлы без доступа
                            pass

                total_size += folder_size
                total_files += folder_files

                breakdown.append({
                    'name': item,
                    'type': 'directory',
                    'size_bytes': folder_size,
                    'size_mb': round(folder_size / (1024 * 1024), 2),
                    'files': folder_files,
                    'path': item_path
                })

        except (PermissionError, FileNotFoundError):
            # Пропускаем элементы без доступа
            continue

    # Сортировка по размеру (от большего к меньшему)
    breakdown_sorted = sorted(breakdown, key=lambda x: x['size_bytes'], reverse=True)

    return {
        'total_files': total_files,
        'size_bytes': total_size,
        'size_mb': round(total_size / (1024 * 1024), 2),
        'size_gb': round(total_size / (1024 * 1024 * 1024), 3),
        'breakdown': breakdown_sorted
    }


def copy_file(source, destination):
    """
    Копирует файл из source в destination

    Args:
        source (str): Путь к исходному файлу
        destination (str): Путь назначения

    Returns:
        str: Путь к скопированному файлу

    Raises:
        FileNotFoundError: Если исходный файл не существует
        IsADirectoryError: Если source - директория

    Examples:
        >>> copy_file('test.txt', 'backup/test.txt')
        'backup/test.txt'
    """
    import shutil

    # Проверки
    if not os.path.exists(source):
        raise FileNotFoundError(f"Файл не найден: {source}")

    if os.path.isdir(source):
        raise IsADirectoryError(f"Источник является директорией: {source}. Используйте copy_directory()")

    # Создать директорию назначения если нужно
    dest_dir = os.path.dirname(destination)
    if dest_dir and not os.path.exists(dest_dir):
        os.makedirs(dest_dir, exist_ok=True)

    # Копировать
    shutil.copy2(source, destination)

    return os.path.abspath(destination)


def get_file_info(file_path):
    """
    Получает информацию о конкретном файле

    Args:
        file_path (str): Путь к файлу

    Returns:
        dict: Информация о файле {
            'name': str,
            'extension': str,
            'size_bytes': int,
            'size_mb': float,
            'modified': str,
            'path': str
        }

    Raises:
        FileNotFoundError: Если файл не существует
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"Файл не найден: {file_path}")

    if not os.path.isfile(file_path):
        raise ValueError(f"Путь не является файлом: {file_path}")

    import time

    size = os.path.getsize(file_path)
    modified_time = os.path.getmtime(file_path)
    modified_str = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(modified_time))

    name = os.path.basename(file_path)
    extension = os.path.splitext(name)[1]

    return {
        'name': name,
        'extension': extension,
        'size_bytes': size,
        'size_mb': round(size / (1024 * 1024), 2),
        'modified': modified_str,
        'path': os.path.abspath(file_path)
    }


if __name__ == "__main__":
    # Тестирование функций
    print("🧪 ТЕСТИРОВАНИЕ FILE_MANAGER")
    print("=" * 60)

    # Тест 1: Поиск файлов
    print("\n📁 Тест 1: Поиск PDF файлов в текущей директории")
    try:
        results = search_files('.', '.pdf')
        print(f"✅ Найдено файлов: {len(results)}")
        for i, file in enumerate(results[:5], 1):
            print(f"   {i}. {file}")
        if len(results) > 5:
            print(f"   ... и еще {len(results) - 5} файлов")
    except Exception as e:
        print(f"❌ Ошибка: {e}")

    # Тест 2: Анализ директории
    print("\n📊 Тест 2: Анализ текущей директории")
    try:
        info = analyze_directory('.')
        print(f"✅ Всего файлов: {info['total_files']}")
        print(f"✅ Общий размер: {info['size_mb']} MB ({info['size_gb']} GB)")
        print("\nТоп-5 самых больших элементов:")
        for i, item in enumerate(info['breakdown'][:5], 1):
            icon = "📄" if item['type'] == 'file' else "📁"
            print(f"   {i}. {icon} {item['name']}: {item['size_mb']} MB")
    except Exception as e:
        print(f"❌ Ошибка: {e}")

    # Тест 3: Информация о файле
    print("\n📄 Тест 3: Информация о файле")
    try:
        # Попробовать найти любой файл в текущей директории
        files = [f for f in os.listdir('.') if os.path.isfile(f)]
        if files:
            test_file = files[0]
            file_info = get_file_info(test_file)
            print(f"✅ Файл: {file_info['name']}")
            print(f"   Расширение: {file_info['extension']}")
            print(f"   Размер: {file_info['size_mb']} MB")
            print(f"   Изменен: {file_info['modified']}")
        else:
            print("⚠️  Нет файлов для тестирования")
    except Exception as e:
        print(f"❌ Ошибка: {e}")

    print("\n" + "=" * 60)
    print("✅ Тестирование завершено")
