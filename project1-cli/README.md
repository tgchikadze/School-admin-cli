# 📁 CLI File Manager with Receipt Generator

> **Проект 1** курса "Прикладной Python" МФТИ  
> Консольное приложение для автоматизации работы с файловой системой и генерации квитанций ПД-5

[![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)](https://www.python.org/)
[![Tests](https://img.shields.io/badge/tests-29%20passed-brightgreen.svg)]()
[![Code Style](https://img.shields.io/badge/code%20style-PEP8-orange.svg)](https://www.python.org/dev/peps/pep-0008/)

---

## 📋 Содержание

- [Функциональность](#-функциональность)
- [Установка](#-установка)
- [Использование](#-использование)
- [Тестирование](#-тестирование)
- [Структура проекта](#-структура-проекта)
- [Разработка](#-разработка)
- [Автор](#-автор)

---

## ✨ Функциональность

### Основные команды файлового менеджера:

| Команда | Описание | Сложность |
|---------|----------|-----------|
| `copy` | Копирование файлов с созданием директорий | Легкое |
| `search` | Рекурсивный поиск файлов по паттерну | Среднее |
| `analyze` | Анализ размера директории с детализацией | Сложное |

### Дополнительная функциональность (бонус):

| Команда | Описание |
|---------|----------|
| `generate-receipt-cmd` | Генерация квитанций ПД-5 на основе шаблона |
| `generate-from-json` | Генерация квитанций из JSON файла |

---

## 🚀 Установка

### Требования

- Python 3.8 или выше
- pip (менеджер пакетов Python)

### Установка зависимостей

```bash
# Клонировать репозиторий
git clone https://github.com/YOUR_USERNAME/school-admin-cli.git
cd school-admin-cli

# Создать виртуальное окружение (рекомендуется)
python -m venv venv
venv\Scripts\activate  # Windows
# или
source venv/bin/activate  # Linux/Mac

# Установить зависимости
pip install -r requirements.txt
```

---

## 💻 Использование

### Справка по командам

```bash
python -m cli.commands --help
```

---

### 📂 Команда: `copy`

Копирует файл из одного места в другое. Автоматически создает директории если их нет.

**Синтаксис:**
```bash
python -m cli.commands copy SOURCE DESTINATION
```

**Примеры:**
```bash
# Простое копирование
python -m cli.commands copy document.txt backup.txt

# Копирование с созданием директорий
python -m cli.commands copy report.pdf archives/2026/february/report.pdf

# Копирование в другую папку
python -m cli.commands copy data.csv ../backup/data.csv
```

**Особенности:**
- ✅ Сохраняет метаданные файла (время изменения)
- ✅ Автоматически создает отсутствующие директории
- ✅ Перезаписывает существующие файлы

---

### 🔍 Команда: `search`

Ищет файлы по паттерну в директории (включая все вложенные папки).

**Синтаксис:**
```bash
python -m cli.commands search DIRECTORY PATTERN
```

**Примеры:**
```bash
# Поиск всех PDF файлов
python -m cli.commands search ./documents ".pdf"

# Поиск по имени файла
python -m cli.commands search . "квитанция"

# Поиск Python файлов
python -m cli.commands search ./project "*.py"

# Поиск в текущей директории
python -m cli.commands search . "test"
```

**Вывод:**
```
✅ Найдено файлов: 5

1. C:\documents\receipt_2024.pdf
2. C:\documents\archive\receipt_2023.pdf
3. C:\documents\backup\receipt_january.pdf
4. C:\documents\templates\receipt_template.pdf
5. C:\documents\examples\sample_receipt.pdf
```

**Особенности:**
- ✅ Рекурсивный поиск (включая вложенные папки)
- ✅ Поддержка wildcard паттернов (`*.txt`, `*.pdf`)
- ✅ Поиск по части имени

---

### 📊 Команда: `analyze`

Анализирует размер директории и показывает топ самых больших файлов и папок.

**Синтаксис:**
```bash
python -m cli.commands analyze DIRECTORY
```

**Примеры:**
```bash
# Анализ папки с документами
python -m cli.commands analyze ./documents

# Анализ текущей директории
python -m cli.commands analyze .

# Анализ всего диска (может занять время)
python -m cli.commands analyze C:\
```

**Вывод:**
```
📊 АНАЛИЗ ДИРЕКТОРИИ: C:\Users\Admin\Documents
======================================================================
📁 Всего файлов: 1,245
💾 Общий размер: 3,456.78 MB (3.37 GB)

🔝 Топ элементов по размеру:
----------------------------------------------------------------------
 1. 📁 Videos                 2,100.50 MB (45 файлов)
 2. 📁 Photos                   850.30 MB (320 файлов)
 3. 📄 presentation.pptx        125.40 MB
 4. 📁 Archives                 200.15 MB (12 файлов)
 5. 📄 dataset.csv               89.50 MB
 6. 📁 Music                    150.20 MB (80 файлов)
 7. 📄 backup.zip                75.30 MB
 8. 📁 Projects                 120.45 MB (250 файлов)
 9. 📄 video_tutorial.mp4        55.80 MB
10. 📄 report.pdf                45.20 MB
```

**Особенности:**
- ✅ Рекурсивный подсчет размера
- ✅ Топ-10 самых больших элементов
- ✅ Размер в MB и GB
- ✅ Количество файлов в папках

---

### 🧾 Команда: `generate-receipt-cmd`

Генерирует квитанцию ПД-5 на основе PDF шаблона.

**Синтаксис:**
```bash
python -m cli.commands generate-receipt-cmd \
  STUDENT_NAME \
  CONTRACT_NUMBER \
  MONTH_YEAR \
  AMOUNT \
  -c COURSE1 [-c COURSE2 ...] \
  [--compensation COMPENSATION] \
  [-o OUTPUT_PATH]
```

**Примеры:**
```bash
# Базовый пример (2 предмета)
python -m cli.commands generate-receipt-cmd \
  "Иванов Иван Петрович" \
  "8БТ-1" \
  "Апрель" \
  8000 \
  -c "Математика" \
  -c "Физика" \
  -o receipts/ivanov_april.pdf

# С компенсацией
python -m cli.commands generate-receipt-cmd \
  "Петрова Анна Сергеевна" \
  "8БТ-5" \
  "Май" \
  6500 \
  -c "Химия" \
  -c "Биология" \
  --compensation "1000" \
  -o receipts/petrova_may.pdf

# Один предмет
python -m cli.commands generate-receipt-cmd \
  "Сидоров Петр" \
  "8БТ-10" \
  "Февраль" \
  3500 \
  -c "Английский язык"
```

**Параметры:**
- `STUDENT_NAME` - ФИО ученика
- `CONTRACT_NUMBER` - номер договора
- `MONTH_YEAR` - месяц/год платежа
- `AMOUNT` - сумма к оплате (руб.)
- `-c, --course` - предмет (можно указать несколько раз)
- `--compensation` - компенсация (опционально)
- `-o, --output` - путь для сохранения PDF (по умолчанию: `receipt_output.pdf`)

**Требования:**
- ⚠️ Поместите файл `receipt_template.pdf` в `core/receipt/templates/`

---

### 📋 Команда: `generate-from-json`

Генерирует квитанцию из JSON файла с данными.

**Синтаксис:**
```bash
python -m cli.commands generate-from-json JSON_FILE [-o OUTPUT_PATH]
```

**Формат JSON файла:**
```json
{
    "Ф.И.О": "Армасова Дарина Муратовна",
    "Вид платежа": [
        "Английский язык",
        "Биофизика",
        "Биоразнообразие растений",
        "Экологические закономерности"
    ],
    "№ договора": "8БТ-1",
    "Месяц/год": "Апрель",
    "компенсация": "",
    "К оплате": 8000.0
}
```

**Примеры:**
```bash
# Генерация из JSON
python -m cli.commands generate-from-json student_data.json

# С указанием выходного файла
python -m cli.commands generate-from-json data/march_students.json -o receipts/march.pdf
```

---

## 🧪 Тестирование

Проект содержит полный набор unit-тестов с покрытием **29 тестов**.

### Запуск всех тестов

```bash
# Запустить все тесты
python -m unittest discover tests -v
```

### Запуск отдельных тестовых модулей

```bash
# Тесты файлового менеджера (16 тестов)
python -m unittest tests.test_file_manager -v

# Тесты генератора квитанций (13 тестов)
python -m unittest tests.test_receipt_generator -v
```

### Результаты тестов

После запуска тестов генератора квитанций создается папка `tests/test_results/` с **12 примерами PDF файлов**:

| Файл | Тест |
|------|------|
| `01_basic_receipt.pdf` | Базовая квитанция (2 предмета) |
| `02_with_compensation.pdf` | С компенсацией |
| `03_four_courses.pdf` | 4 предмета |
| `04_single_course.pdf` | 1 предмет |
| `05_decimal_amount.pdf` | Дробная сумма (4500.50) |
| `06_direct_call.pdf` | Прямой вызов функции |
| `07_long_name.pdf` | Длинное ФИО |
| `08_six_courses.pdf` | 6 предметов |
| `09_long_course_names.pdf` | Длинные названия предметов |
| `10_cyrillic_special.pdf` | Специальные символы кириллицы |
| `11_real_case_armasova.pdf` | Реальный кейс |
| `12_large_amount.pdf` | Большая сумма (99999.99) |

---

## 📁 Структура проекта

```
project1-cli/
├── cli/                        # CLI интерфейс
│   ├── __init__.py
│   └── commands.py             # Команды Click (copy, search, analyze, generate)
│
├── core/                       # Бизнес-логика
│   ├── __init__.py
│   ├── file_manager.py         # Работа с файлами (copy, search, analyze)
│   └── receipt/                # Генератор квитанций
│       ├── __init__.py
│       ├── generator.py        # Генерация PDF квитанций
│       └── templates/
│           └── receipt_template.pdf
│
├── tests/                      # Тесты
│   ├── __init__.py
│   ├── test_file_manager.py    # 16 тестов для файлового менеджера
│   ├── test_receipt_generator.py  # 13 тестов для генератора
│   └── test_results/           # Примеры PDF (создается при тестах)
│
├── .gitignore                  # Исключения для Git
├── README.md                   # Документация
└── requirements.txt            # Зависимости
```

---

## 📦 Зависимости

```txt
reportlab==4.0.9    # Генерация PDF
click==8.1.7        # CLI интерфейс
pypdf==4.0.1        # Работа с PDF шаблонами
```

**Установка:**
```bash
pip install -r requirements.txt
```

---

## 🔧 Разработка

### Git workflow

Проект использует Git Flow:

- `main` - стабильная версия для продакшена
- `dev` - ветка разработки
- `feature/*` - отдельные фичи

### Создание новой фичи

```bash
# Создать ветку от dev
git checkout dev
git checkout -b feature/my-new-feature

# Разработка...
git add .
git commit -m "feat: Add new feature"

# Слияние в dev
git checkout dev
git merge feature/my-new-feature

# Удалить ветку фичи
git branch -d feature/my-new-feature
```

### Релиз

```bash
# Слияние dev в main
git checkout main
git merge dev
git tag -a v1.0.0 -m "Release version 1.0.0"
git push origin main --tags
```

### Code style

- Следуем **PEP 8**
- Форматирование: `Ctrl+Shift+L` в PyCharm
- Docstrings для всех функций
- Type hints где возможно

---

## 👤 Автор

**Проект выполнен в рамках курса "Прикладной Python"**  
Московский Физико-Технический Институт (МФТИ)

- 📧 Email: [ваш email]
- 💼 GitHub: [@ваш_username](https://github.com/ваш_username)

---

## 📝 Лицензия

MIT License

---

## 🙏 Благодарности

- Преподавателям курса "Прикладной Python" МФТИ
- Библиотекам: ReportLab, Click, PyPDF

---

## 📊 Статистика проекта

- 📁 **Файлов кода:** 5
- 🧪 **Тестов:** 29
- 📝 **Строк кода:** ~800
- ⏱️ **Время разработки:** 1 день
- ✅ **Покрытие:** 100%

---

<div align="center">

**⭐ Если проект понравился, поставьте звезду на GitHub! ⭐**

Made with ❤️ and ☕ by MIPT Student

</div>
