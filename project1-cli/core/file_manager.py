"""
Модуль для работы с файлами и директориями.

Предоставляет функции поиска, копирования и анализа файловой системы.
"""

import os
import glob
import shutil
import time
from pathlib import Path


def search_files(directory: str, pattern: str) -> list[str]:
    """
    Ищет файлы по паттерну в директории рекурсивно.

    Args:
        directory: Путь к директории для поиска.
        pattern: Паттерн поиска (например, «*.pdf», «квитанция»).

    Returns:
        Отсортированный список абсолютных путей найденных файлов.

    Raises:
        FileNotFoundError: Если директория не существует.

    Examples:
        >>> search_files('./documents', '*.pdf')
        ['./documents/receipt1.pdf', './documents/subdir/receipt2.pdf']
    """
    if not os.path.exists(directory):
        raise FileNotFoundError(f"Директория не найдена: {directory}")

    search_pattern = pattern if pattern.startswith('*') else f'*{pattern}*'
    search_path = os.path.join(directory, '**', search_pattern)

    results = [
        os.path.abspath(fp)
        for fp in glob.glob(search_path, recursive=True)
        if os.path.isfile(fp)
    ]
    return sorted(results)


def analyze_directory(directory: str) -> dict:
    """
    Анализирует структуру и размер директории.

    Args:
        directory: Путь к директории для анализа.

    Returns:
        Словарь с полями:
            - total_files (int): Общее количество файлов.
            - size_bytes (int): Размер в байтах.
            - size_mb (float): Размер в мегабайтах.
            - size_gb (float): Размер в гигабайтах.
            - breakdown (list[dict]): Детализация по элементам, отсортированная
              по убыванию размера.

    Raises:
        FileNotFoundError: Если директория не существует.
    """
    if not os.path.exists(directory):
        raise FileNotFoundError(f"Директория не найдена: {directory}")

    total_size = 0
    total_files = 0
    breakdown = []

    try:
        items = os.listdir(directory)
    except PermissionError:
        return {
            'total_files': 0, 'size_bytes': 0,
            'size_mb': 0.0, 'size_gb': 0.0,
            'breakdown': [], 'error': 'Permission denied'
        }

    for item in items:
        item_path = os.path.join(directory, item)
        try:
            if os.path.isfile(item_path):
                size = os.path.getsize(item_path)
                total_size += size
                total_files += 1
                breakdown.append({
                    'name': item, 'type': 'file',
                    'size_bytes': size,
                    'size_mb': round(size / (1024 * 1024), 2),
                    'path': item_path
                })
            elif os.path.isdir(item_path):
                folder_size = 0
                folder_files = 0
                for root, dirs, files in os.walk(item_path):
                    for file in files:
                        try:
                            folder_size += os.path.getsize(os.path.join(root, file))
                            folder_files += 1
                        except (PermissionError, FileNotFoundError):
                            pass
                total_size += folder_size
                total_files += folder_files
                breakdown.append({
                    'name': item, 'type': 'directory',
                    'size_bytes': folder_size,
                    'size_mb': round(folder_size / (1024 * 1024), 2),
                    'files': folder_files,
                    'path': item_path
                })
        except (PermissionError, FileNotFoundError):
            continue

    return {
        'total_files': total_files,
        'size_bytes': total_size,
        'size_mb': round(total_size / (1024 * 1024), 2),
        'size_gb': round(total_size / (1024 * 1024 * 1024), 3),
        'breakdown': sorted(breakdown, key=lambda x: x['size_bytes'], reverse=True)
    }


def copy_file(source: str, destination: str) -> str:
    """
    Копирует файл из source в destination.

    Создаёт директорию назначения автоматически, если она не существует.

    Args:
        source: Путь к исходному файлу.
        destination: Путь назначения.

    Returns:
        Абсолютный путь к скопированному файлу.

    Raises:
        FileNotFoundError: Если исходный файл не существует.
        IsADirectoryError: Если source является директорией.
    """
    if not os.path.exists(source):
        raise FileNotFoundError(f"Файл не найден: {source}")
    if os.path.isdir(source):
        raise IsADirectoryError(
            f"Источник является директорией: {source}. Используйте copy_directory()"
        )

    dest_dir = os.path.dirname(destination)
    if dest_dir:
        os.makedirs(dest_dir, exist_ok=True)

    shutil.copy2(source, destination)
    return os.path.abspath(destination)


def get_file_info(file_path: str) -> dict:
    """
    Возвращает информацию о файле.

    Args:
        file_path: Путь к файлу.

    Returns:
        Словарь с полями: name, extension, size_bytes, size_mb, modified, path.

    Raises:
        FileNotFoundError: Если файл не существует.
        ValueError: Если путь не является файлом.
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"Файл не найден: {file_path}")
    if not os.path.isfile(file_path):
        raise ValueError(f"Путь не является файлом: {file_path}")

    size = os.path.getsize(file_path)
    modified_str = time.strftime(
        '%Y-%m-%d %H:%M:%S', time.localtime(os.path.getmtime(file_path))
    )
    name = os.path.basename(file_path)

    return {
        'name': name,
        'extension': os.path.splitext(name)[1],
        'size_bytes': size,
        'size_mb': round(size / (1024 * 1024), 2),
        'modified': modified_str,
        'path': os.path.abspath(file_path)
    }
