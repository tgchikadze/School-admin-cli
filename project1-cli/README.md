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
project1-cli/
│
├── cli/
│   ├── __init__.py          # Группа Click и регистрация команд (cli.add_command)
│   ├── __main__.py          # Точка входа для `python -m cli`
│   └── commands.py          # Реализация CLI-команд (copy, search, analyze, generate...)
│
├── core/
│   ├── __init__.py
│   ├── file_manager.py      # Логика анализа, поиска и копирования файлов
│   └── receipt/
│       ├── __init__.py
│       ├── generator.py     # Генерация PDF-квитанций
│       └── templates/
│           ├── receipt_template.pdf
│           └── receipt_coordinates.json
│
├── tests/
│   ├── test_file_manager.py         # Тесты для core.file_manager
│   ├── test_receipt_generator.py    # Тесты для core.receipt.generator
│   └── test_results/                # Папка для сохранения сгенерированных PDF
│
└── README.md                # Специфичный для проекта 1
```
## Установка и запуск

1. Клонируйте монорепозиторий и перейдите в ветку `dev`:
   ```bash
   git clone https://github.com/tgchikadze/School-admin-cli
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

## Использование CLI

Все команды запускаются из папки `project1-cli` через пакет `cli`:

```bash
cd project1-cli
python -m cli --help
```

Доступные команды (см. `python -m cli --help`):

- `copy`
- `search`
- `analyze`
- `generate-receipt-cmd` (или `generate-receipt`, если переименуешь `name=` в декораторе)
- `generate-from-json`

### Анализ директории

```bash
python -m cli analyze "."
python -m cli analyze "./core"
python -m cli analyze "./tests"
```

Вывод включает:

- абсолютный путь директории;
- общее количество файлов;
- суммарный размер (в байтах, MB и GB);
- топ крупнейших файлов и подпапок.

### Поиск файлов

```bash
# Поиск по расширению
python -m cli search "." "*.py"

# Поиск по подстроке в имени
python -m cli search "." "receipt"

# Поиск в конкретной директории
python -m cli search "./core" "*.py"
```

Если файлы не найдены, выводится предупреждение:

```text
⚠️ Файлы не найдены по паттерну: <pattern>
```

### Копирование файла

```bash
# Копирование файла в текущую директорию
python -m cli copy "README.md" "backup_README.md"

# Копирование в подпапку (будет создана, если не существует)
python -m cli copy "README.md" "backup/README.md"
```

Ошибки (например, несуществующий источник) обрабатываются Click через `click.Path(exists=True)` с понятным сообщением.

### Генерация квитанции из аргументов

Команда `generate-receipt-cmd` (или `generate-receipt`, если задано `name="generate-receipt"` в декораторе):

```bash
python -m cli generate-receipt-cmd \
  "Иванов Иван" "8БТ-1" "Апрель 2025" 8000 \
  -c "Математика" -c "Физика" \
  --compensation "1000" \
  -o "receipt.pdf"
```

Параметры:

- `student_name` — ФИО ученика;
- `contract_number` — номер/обозначение договора/класса;
- `month_year` — месяц/период;
- `amount` — сумма (float);
- `-c/--course` — предмет (можно указывать несколько раз, опция обязательная);
- `--compensation` — компенсация (опционально);
- `-o/--output` — путь к выходному PDF.

### Генерация квитанции из JSON

Создайте `student.json` (например, в `project1-cli`):

```json
{
  "student_name": "Иванов Иван",
  "contract_number": "8БТ-1",
  "month_year": "Апрель 2025",
  "amount": 8000,
  "courses": ["Математика", "Физика"],
  "compensation": ""
}
```

Вызов:

```bash
python -m cli generate-from-json "student.json" -o "receipt_json.pdf"
```

Ошибки:

- несуществующий файл — стандартная ошибка Click для `Path(exists=True)`;
- некорректный JSON — обрабатывается в `generate_from_json` и выводит понятное сообщение.

## Тестирование

- `tests/test_file_manager.py` проверяет:
  - поиск файлов (по имени и расширению);
  - анализ директории (структура `breakdown`, размеры, ошибки);
  - копирование файлов, в т.ч. с несуществующим источником и перезаписью [file:24].
- `tests/test_receipt_generator.py` проверяет:
  - генерацию квитанций для разных сценариев (несколько предметов, компенсация, разные суммы);
  - корректность формата PDF (проверка заголовка `%PDF`);
  - сохранение результатов в `tests/test_results/` [file:25].

Запуск всех тестов проекта 1:

```bash
cd project1-cli
python -m unittest discover tests -v
```
