"""
Конфигурация парсера вузов-партнёров школы.
Список вузов, направлений, URL и ключевые слова для фильтрации.
"""

# ==========================
# Целевые направления
# ==========================

TARGET_PROGRAMS = [
    # Химия и биохимия
    "химия", "биохимия", "органическая химия", "инфохимия",
    # Биология и биотехнологии
    "биология", "биотехнология", "молекулярная биология",
    "биоинформатика", "биомедицина",
    # Медицина и фармация
    "медицина", "лечебное дело", "педиатрия", "фармация",
    "медицинская биохимия", "медицинская биофизика",
    # IT и компьютерные науки
    "компьютерные науки", "прикладная математика и информатика",
    "программная инженерия", "информатика и вычислительная техника",
]

# Коды ОКСО для фильтрации (направления подготовки)
TARGET_OKSO_CODES = [
    "04.",   # Химия
    "06.",   # Биологические науки
    "09.",   # Информатика и вычислительная техника
    "19.",   # Биотехнология
    "30.",   # Фундаментальная медицина
    "31.",   # Клиническая медицина
    "33.",   # Фармация
]

# ==========================
# Список вузов
# ==========================

UNIVERSITIES = [

    # ==============================
    # САНКТ-ПЕТЕРБУРГ (приоритет)
    # ==============================
    {
        "id": "alferov",
        "short_name": "Университет Алфёрова",
        "full_name": "Академический университет им. Жореса Алфёрова РАН",
        "city": "Санкт-Петербург",
        "priority": 1,
        "programs": [
            "Биоинформатика",
            "Нанобиотехнологии",
            "Физика и нанотехнологии",
        ],
        "postupi_url": "https://spb.postupi.online/vuz/akademicheskiy-universitet-im-zh-i-alferova/",
        "official_url": "https://spbau.ru",
    },
    {
        "id": "sphfu",
        "short_name": "СПХФУ",
        "full_name": "Санкт-Петербургский химико-фармацевтический университет",
        "city": "Санкт-Петербург",
        "priority": 1,
        "programs": [
            "Фармация",
            "Биотехнология",
            "Медицинская химия",
            "Химия лекарственных соединений",
        ],
        "postupi_url": "https://spb.postupi.online/vuz/spkhfu/",
        "official_url": "https://pharminnotech.com",
    },
    {
        "id": "herzen",
        "short_name": "РГПУ им. Герцена",
        "full_name": "Российский государственный педагогический университет им. А.И. Герцена",
        "city": "Санкт-Петербург",
        "priority": 1,
        "programs": [
            "Биология и химия (педагогическое)",
            "Биологическое образование",
            "Химическое образование",
        ],
        "postupi_url": "https://spb.postupi.online/vuz/rgpu-im-gercena/",
        "official_url": "https://www.herzen.spb.ru",
    },
    {
        "id": "spbpu",
        "short_name": "СПбПУ Петра Великого",
        "full_name": "Санкт-Петербургский политехнический университет Петра Великого",
        "city": "Санкт-Петербург",
        "priority": 1,
        "programs": [
            "Компьютерные науки и технологии",
            "Биомедицинская инженерия",
            "Прикладная математика и информатика",
        ],
        "postupi_url": "https://spb.postupi.online/vuz/spbpu/",
        "official_url": "https://www.spbstu.ru",
    },
    {
        "id": "itmo",
        "short_name": "ИТМО",
        "full_name": "Национальный исследовательский университет ИТМО",
        "city": "Санкт-Петербург",
        "priority": 1,
        "programs": [
            "Компьютерные науки",
            "Инфохимия",
            "Биоинформатика и молекулярная биология",
            "Прикладная математика и информатика",
        ],
        "postupi_url": "https://spb.postupi.online/vuz/itmo/",
        "official_url": "https://itmo.ru",
    },
    {
        "id": "spbgu",
        "short_name": "СПбГУ",
        "full_name": "Санкт-Петербургский государственный университет",
        "city": "Санкт-Петербург",
        "priority": 1,
        "programs": [
            "Биоинформатика",
            "Биология",
            "Химия",
            "Лечебное дело",
            "Молекулярная биология",
        ],
        "postupi_url": "https://spb.postupi.online/vuz/spbgu/",
        "official_url": "https://spbu.ru",
    },
    {
        "id": "spbgpmu",
        "short_name": "СПбГПМУ (Педиатрический)",
        "full_name": "Санкт-Петербургский государственный педиатрический медицинский университет",
        "city": "Санкт-Петербург",
        "priority": 1,
        "programs": [
            "Педиатрия",
            "Лечебное дело",
            "Медицинская биохимия",
        ],
        "postupi_url": "https://spb.postupi.online/vuz/spbgpmu/",
        "official_url": "https://gpmu.org",
    },
    {
        "id": "pavlov",
        "short_name": "ПСПбГМУ им. Павлова (1 Мед)",
        "full_name": "Первый Санкт-Петербургский государственный медицинский университет им. акад. И.П. Павлова",
        "city": "Санкт-Петербург",
        "priority": 1,
        "programs": [
            "Лечебное дело",
            "Стоматология",
            "Медицинская биохимия",
            "Медицинская биофизика",
        ],
        "postupi_url": "https://spb.postupi.online/vuz/pervyy-spbgmu-im-akad-ip-pavlova/",
        "official_url": "https://www.1spbgmu.ru",
    },
    {
        "id": "mechnikov",
        "short_name": "СЗГМУ им. Мечникова",
        "full_name": "Северо-Западный государственный медицинский университет им. И.И. Мечникова",
        "city": "Санкт-Петербург",
        "priority": 1,
        "programs": [
            "Лечебное дело",
            "Медицинская биохимия",
            "Педиатрия",
        ],
        "postupi_url": "https://spb.postupi.online/vuz/szgmu-im-mechnikova/",
        "official_url": "https://szgmu.ru",
    },

    # ==============================
    # МОСКВА
    # ==============================
    {
        "id": "hse",
        "short_name": "ВШЭ",
        "full_name": "Национальный исследовательский университет «Высшая школа экономики»",
        "city": "Москва",
        "priority": 2,
        "programs": [
            "Биоинформатика",
            "Компьютерные науки",
            "Химия",
        ],
        "postupi_url": "https://postupi.online/vuz/vshe/",
        "official_url": "https://hse.ru",
    },
    {
        "id": "mgu",
        "short_name": "МГУ",
        "full_name": "Московский государственный университет им. М.В. Ломоносова",
        "city": "Москва",
        "priority": 2,
        "programs": [
            "Биоинформатика",
            "Биология",
            "Химия",
            "Биотехнология",
            "Лечебное дело (ФФМ)",
        ],
        "postupi_url": "https://postupi.online/vuz/mgu/",
        "official_url": "https://msu.ru",
    },
    {
        "id": "mipt",
        "short_name": "МФТИ",
        "full_name": "Московский физико-технический институт",
        "city": "Москва",
        "priority": 2,
        "programs": [
            "Биотехнология",
            "Биоинформатика",
            "Прикладная математика и информатика",
        ],
        "postupi_url": "https://postupi.online/vuz/mfti/",
        "official_url": "https://mipt.ru",
    },

    # ==============================
    # ДРУГИЕ
    # ==============================
    {
        "id": "ngu",
        "short_name": "НГУ",
        "full_name": "Новосибирский национальный исследовательский государственный университет",
        "city": "Новосибирск",
        "priority": 3,
        "programs": [
            "Биология",
            "Биоинформатика",
            "Медицина",
            "Компьютерные науки",
        ],
        "postupi_url": "https://postupi.online/vuz/ngu/",
        "official_url": "https://www.nsu.ru",
    },
]

# ==========================
# Источники данных
# ==========================

SOURCES = {
    "postupi_base_url": "https://postupi.online",
    "postupi_spb_base_url": "https://spb.postupi.online",
    "olymp_base_url": "https://olimpiada.ru",
    "rsr_olymp_url": "https://rsr-olymp.ru/benefits",
}

# ==========================
# Настройки скрапера
# ==========================

SCRAPER_SETTINGS = {
    "request_delay_sec": 2,       # Задержка между запросами (вежливость)
    "request_timeout_sec": 15,
    "max_retries": 3,
    "schedule_interval_hours": 6, # Интервал планировщика
    "user_agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
}

# ==========================
# Пути к файлам данных
# ==========================

DATA_DIR = "data"
RAW_UNIVERSITIES_CSV = f"{DATA_DIR}/universities_raw.csv"
RAW_OLYMPIADS_CSV    = f"{DATA_DIR}/olympiads_raw.csv"
PARTNERS_JSON        = f"{DATA_DIR}/partners.json"
REPORTS_DIR          = "analysis/reports"
