# Project 1 – CLI File Manager

CLI-утилита для работы с файлами и квитанциями в рамках монорепозитория **School Admin System**. Проект позволяет анализировать директории, искать и копировать файлы, а также генерировать PDF‑квитанции по данным о студентах и предметах.

## Возможности

- Анализ директории:
  - расчет общего размера
  - подсчет количества файлов и папок
  - детализация по расширениям
- Поиск файлов:
  - по имени (подстрока, без учета регистра)
  - по расширению
- Операции с файлами:
  - копирование в существующую или новую директорию
  - обработка ошибок (нет файла, попытка скопировать директорию и т.п.)
- Генерация квитанций:
  - создание PDF по данным словаря
  - поддержка кириллицы и длинных ФИО
  - несколько предметов, компенсации, большие суммы
  - пакетное создание квитанций для разных сценариев тестов

## Структура проекта 1

```text
├── project1-cli/                         
│   ├── cli/
│   └── core/
│   │      ├── file_manager.py                         # Логика анализа и поиска файлов
│   │      ├── commands.py                             # Обработка CLI-команд
│   │      └── receipt/
│   │            ├── generator.py                      # Генерация PDF-квитанций
│   │            └── templates/
│   │                     ├── receipt_template.pdf     # PDF-шаблон квитанции
│   │                     └── receipt_coordinates.json # словарь координат для формы
│   └── tests/
│   │      ├── test_file_manager.py
│   │      ├── test_receipt_generator.py
│   │      └── test_results/                           # Папка для сохранения сгенерированных PDF
│   └── README.md                                     # Специфичный для проекта 1
 ```
## Установка и запуск

1. Клонируйте монорепозиторий и перейдите в ветку `dev`:
   ```bash
   git clone <URL вашего репозитория> school-admin-system
   cd school-admin-system
   git checkout dev
   ```

2. Создайте и активируйте виртуальное окружение (по желанию):
   ```bash
   python -m venv venv
   venv\Scripts\activate
   ```

3. Установите зависимости:
   ```bash
   pip install -r /requirements.txt
   ```

4. Запуск тестов проекта 1:
   ```bash
   cd project1-cli
   python -m unittest discover tests -v
   ```

## Использование

### Анализ директории

```bash
python -m core.commands analyse "<путь_к_директории>"
```

Пример вывода:
- общий размер директории
- количество файлов и папок
- разбивка по расширениям.

### Поиск файлов

```bash
python -m core.commands search --name "report"
python -m core.commands search --ext ".txt"
```

### Копирование файла

```bash
python -m core.commands copy "<источник>" "<папка_назначения>"
```

При необходимости целевая директория будет создана автоматически.

### Генерация квитанции

В проекте предусмотрены функции высокого уровня в `core/receipt/generator.py`:

- генерация из словаря:
  ```python
  from core.receipt.generator import generate_receipt_from_dict

  data = {
      "student_name": "Иванов Иван Иванович",
      "class_name": "10А",
      "courses": ["Математика", "Физика"],
      "amount": 12345.67,
  }

  generate_receipt_from_dict(data, "output.pdf")
  ```

- прямой вызов:
  ```python
  from core.receipt.generator import generate_receipt

  generate_receipt(field_values, "core/receipt/templates/receipt_template.pdf", "output.pdf")
  ```

PDF‑файлы сохраняются в указанную директорию, а в тестах — в `tests/test_results/`.

## Тестирование

- Покрытие тестами:
  - `test_file_manager.py` проверяет анализ директорий, поиск и копирование
  - `test_receipt_generator.py` проверяет генерацию PDF для различных сценариев
- Пример успешного прогона:
  ```text
  Ran 29 tests in 0.333s
  OK
  ```

