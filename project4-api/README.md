# Project 4 — Web-интерфейс БД биотех-направлений для выпускников школы "БиоТех 225"
###  Web-приложение для просмотра и управления данными о вузах, программах обучения и олимпиадных льготах, собранными скрапером (Project 3).

## Стек

- **Backend:** FastAPI + SQLAlchemy + SQLite
- **Frontend:** HTML + JavaScript + Pico CSS
- **Документация API:** автогенерация Swagger UI

## Быстрый старт

```bash
# Клонировать репозиторий
git clone https://github.com/tgchikadze/School-admin-cli/tree/features/api/project4-api
cd project4-api

# Создать виртуальное окружение
python -m venv venv
source venv/bin/activate  # Linux/Mac
venv\Scripts\activate     # Windows

# Установить зависимости
pip install -r requirements.txt

# Запустить сервер
python run.py
Приложение будет доступно по адресу: http://localhost:8000
````
## Структура проекта
```text
project4-web/
├── screenshots/                 # Скриншоты интерфейса
│    └── ...                     
├── run.py                       # Точка входа: запуск uvicorn
├── requirements.txt             # Зависимости проекта
├── .gitignore                   # Исключения для Git
├── README.md                    # Документация проекта
├── data/
│   ├── school.db                # SQLite база данных (создаётся при запуске)
│   └── partners.json            # Исходные данные из скрапера (Project 3)
├── api/
│   ├── routers/                 # Роутеры API (по сущностям)
│   │   ├── admin.py             # /api/admin/* — управление БД
│   │   ├── olimpiads.py         # /api/olympiads/* — CRUD олимпиад
│   │   ├── programs.py          # /api/programs — список программ
│   │   └── universities.py      # /api/universities — список вузов
│   ├── database.py              # SQLAlchemy engine + SessionLocal
│   ├── dependencies.py          # Зависимости FastAPI (get_db и др.)
│   ├── main.py                  # FastAPI app, подключение роутеров
│   ├── models.py                # ORM-модели (University, Program, Olympiad)
│   └── schemas.py               # Pydantic-схемы запросов/ответов
└── web/
    ├── static/
    │   └── css/                 # Локальные стили (если есть)
    └── templates/
        ├── index.html           # Главная — список вузов
        ├── programs.html        # Программы обучения с фильтрами
        ├── olympiads.html       # Олимпиадные льготы
        ├── review.html          # Ревизия данных (CRUD-интерфейс)
        └── admin.html           # Админ-панель: статистика + пересборка БД
````
## API эндпоинты

### Университеты
| Метод | URL | Описание |
|-------|-----|----------|
| GET | `/api/universities` | Список вузов (пагинация, поиск) |

### Программы
| Метод | URL | Описание |
|-------|-----|----------|
| GET | `/api/programs` | Список программ (фильтры: вуз, направление) |

### Олимпиады
| Метод | URL | Описание |
|-------|-----|----------|
| GET | `/api/olympiads` | Список олимпиад (фильтр: reviewed) |
| POST | `/api/olympiads` | Создать запись |
| PATCH | `/api/olympiads/{id}` | Обновить запись |
| DELETE | `/api/olympiads/{id}` | Удалить запись |

### Админ
| Метод | URL | Описание |
|-------|-----|----------|
| GET | `/api/admin/status` | Статистика БД |
| POST | `/api/admin/rebuild` | Пересоздать БД из JSON |
| POST | `/api/admin/clear` | Очистить БД |

Полная интерактивная документация: http://localhost:8000/docs

## Страницы интерфейса

- **Вузы** (`/`) — карточки университетов с поиском
- **Программы** (`/programs.html`) — таблица программ с фильтрами
- **Олимпиады** (`/olympiads.html`) — олимпиадные льготы
- **Ревизия** (`/review.html`) — проверка и редактирование данных
- **Админ-панель** (`/admin.html`) — управление БД, статистика, логи

## Скриншоты

> см. папку `screenshots/`
```

## Что дальше

Три файла готовы — **скопируй их в проект**. Дальше по плану:

1. ~~requirements.txt~~ ✅
2. ~~.gitignore~~ ✅
3. ~~README.md~~ ✅
4. **Скриншоты** — запусти сервер, сделай скриншоты 5 страниц + `/docs`, положи в папку `screenshots/`
5. **PEP8** — прогони `black .` в корне проекта
6. **Git** — ветки и PR (это последний шаг, подскажу когда будешь готов)

Готов к шагу 5 (форматирование) или хочешь сначала разобраться со скриншотами?
