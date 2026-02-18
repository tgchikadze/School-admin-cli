"""
Запуск всех юнит-тестов проекта School Admin System.

Использование:
    python run_tests.py           — запуск всех тестов
    python run_tests.py -v        — подробный вывод

Тестовые файлы обнаруживаются автоматически по шаблону test_*.py
в папке tests/.
"""

import sys
import unittest
from pathlib import Path


def main() -> None:
    """Обнаружить и запустить все тесты из папки tests/."""
    tests_dir = Path(__file__).parent / "tests"

    if not tests_dir.exists():
        print(f"❌ Папка тестов не найдена: {tests_dir}")
        sys.exit(1)

    verbosity = 2 if "-v" in sys.argv else 1

    loader = unittest.TestLoader()
    suite = loader.discover(
        start_dir=str(tests_dir),
        pattern="test_*.py",
        top_level_dir=str(Path(__file__).parent),
    )

    print("=" * 70)
    print("  SCHOOL ADMIN SYSTEM — ЗАПУСК ТЕСТОВ")
    print(f"  Папка: {tests_dir}")
    print("=" * 70)

    runner = unittest.TextTestRunner(verbosity=verbosity)
    result = runner.run(suite)

    print("\n" + "=" * 70)
    print(f"  📊 ИТОГО:")
    print(f"  Всего тестов:  {result.testsRun}")
    print(f"  ✅ Успешно:    {result.testsRun - len(result.failures) - len(result.errors)}")
    if result.failures:
        print(f"  ❌ Провалено:  {len(result.failures)}")
    if result.errors:
        print(f"  💥 Ошибок:     {len(result.errors)}")
    print("=" * 70)

    sys.exit(0 if result.wasSuccessful() else 1)


if __name__ == "__main__":
    main()
