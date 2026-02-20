"""
Парсер олимпиад и льгот при поступлении с сайта olimpiada.ru.

Собирает для каждой олимпиады из Перечня Минобрнауки:
- Название олимпиады и уровень (1/2/3)
- Профиль / предмет
- Вузы из нашего списка, которые дают льготы
- Вид льготы: БВИ (без вступительных испытаний) / 100 баллов / доп. баллы
- За что дают 100 баллов к ЕГЭ (индивидуальные достижения)

Данные сохраняются в CSV с временной меткой каждого запуска.
"""

import csv
import json
from pathlib import Path

from scrapers.base_scraper import BaseScraper
from config import UNIVERSITIES, RAW_OLYMPIADS_CSV, PARTNERS_JSON, TARGET_PROGRAMS

# Предметы ЕГЭ, релевантные для наших направлений
TARGET_SUBJECTS = [
    "математика", "информатика", "химия", "биология",
    "физика", "русский язык", "английский язык",
]

# Slug-маппинг вузов на olimpiada.ru
UNI_SLUGS_OLIMPIADA = {
    "spbgu":     "spbgu",
    "itmo":      "itmo",
    "spbpu":     "spbpolitech",
    "hse":       "hse",
    "mgu":       "mgu",
    "mipt":      "mfti",
    "mechnikov": "szgmu",
    "pavlov":    "1spbgmu",
    "spbgpmu":   "spbgpmu",
    "ngu":       "nsu",
    "sphfu":     "sphfa",
    "herzen":    "herzen",
    "alferov":   "spbau",
}

# ID олимпиад на olimpiada.ru, релевантных нашим направлениям
# (химия, биология, информатика, математика, биохимия)
TARGET_OLYMPIAD_IDS = [
    2,    # Всероссийская олимпиада школьников по химии
    3,    # Всероссийская олимпиада школьников по биологии
    5,    # Всероссийская олимпиада школьников по математике
    6,    # Всероссийская олимпиада школьников по информатике
    119,  # Олимпиада «Ломоносов» (химия, биология)
    120,  # Олимпиада «Ломоносов» (математика, информатика)
    131,  # Олимпиада СПбГУ
    143,  # Олимпиада ИТМО
    147,  # Олимпиада ВШЭ
    438,  # Биологическая олимпиада СПБГУ
    441,  # Химическая олимпиада им. Менделеева
    588,  # Олимпиада «Курчатов» (биология, химия)
    636,  # Олимпиада по биоинформатике
]


class OlympScraper(BaseScraper):
    """
    Парсер страниц олимпиад и льгот с olimpiada.ru.

    Парсит страницы конкретных олимпиад из TARGET_OLYMPIAD_IDS,
    собирает список вузов с льготами и вид льготы.
    Фильтрует по вузам из нашего config.UNIVERSITIES.
    """

    BASE_URL = "https://olimpiada.ru"

    def __init__(self) -> None:
        super().__init__("OlympScraper")
        # Множество коротких имён наших вузов для фильтрации
        self._our_unis = {uni["short_name"].lower() for uni in UNIVERSITIES}
        self._our_uni_ids = {uni["id"] for uni in UNIVERSITIES}

    # ==========================
    # Основной метод
    # ==========================

    def scrape(self) -> list[dict]:
        """
        Запустить парсинг всех целевых олимпиад.

        Возвращает:
            list[dict]: Список записей об олимпиадах и льготах.
        """
        all_records = []

        for olymp_id in TARGET_OLYMPIAD_IDS:
            self.logger.info(f"Парсим олимпиаду ID={olymp_id}")
            records = self._scrape_olympiad(olymp_id)
            all_records.extend(records)
            self.logger.info(f"  → найдено {len(records)} записей")

        # Отдельно парсим страницу с 100 баллами за ЕГЭ
        achievements = self._scrape_achievements()
        all_records.extend(achievements)

        self._save_csv(all_records)
        self._update_partners_json(all_records)
        return all_records

    # ==========================
    # Парсинг олимпиады
    # ==========================

    def _scrape_olympiad(self, olymp_id: int) -> list[dict]:
        """
        Спарсить страницу олимпиады и собрать льготы по вузам.

        Параметры:
            olymp_id: ID олимпиады на olimpiada.ru

        Возвращает:
            list[dict]: Записи вида {олимпиада, уровень, вуз, льгота, ...}
        """
        url = f"{self.BASE_URL}/activity/{olymp_id}/benefits"
        soup = self.get_page(url)
        if soup is None:
            return []

        timestamp = self.now_timestamp()
        records = []

        # Название и уровень олимпиады
        olymp_name = self._extract_olympiad_name(soup)
        olymp_level = self._extract_olympiad_level(soup)
        olymp_subject = self._extract_olympiad_subject(soup)

        # Фильтруем по профилю — берём только релевантные предметы
        if olymp_subject and not self._is_target_subject(olymp_subject):
            self.logger.info(
                f"  Пропускаем олимпиаду по предмету '{olymp_subject}' — не в целевых"
            )
            return []

        # Таблица льгот: вуз → вид льготы
        benefits_table = (
            soup.find("table", class_="benefits_table")
            or soup.find("table", class_="vuz-benefits")
            or soup.find("div", class_="benefits-list")
        )

        if not benefits_table:
            self.logger.warning(f"Не найдена таблица льгот для ID={olymp_id}")
            return []

        rows = benefits_table.find_all("tr")[1:]  # пропускаем заголовок
        for row in rows:
            cells = row.find_all(["td", "th"])
            if len(cells) < 2:
                continue

            uni_name_raw = self.clean_text(cells[0].get_text())
            benefit_raw  = self.clean_text(cells[1].get_text()) if len(cells) > 1 else ""
            profiles_raw = self.clean_text(cells[2].get_text()) if len(cells) > 2 else ""

            # Проверяем — это наш вуз?
            matched_uni = self._match_university(uni_name_raw)
            if not matched_uni:
                continue

            records.append({
                "timestamp":      timestamp,
                "data_type":      "olympiad",
                "olympiad_id":    olymp_id,
                "olympiad_name":  olymp_name,
                "olympiad_level": olymp_level,
                "subject":        olymp_subject,
                "university_id":  matched_uni["id"],
                "university_name": matched_uni["short_name"],
                "city":           matched_uni["city"],
                "benefit_type":   self._classify_benefit(benefit_raw),
                "benefit_detail": benefit_raw,
                "profiles":       profiles_raw,
            })

        return records

    # ==========================
    # Парсинг индивидуальных достижений (100 баллов)
    # ==========================

    def _scrape_achievements(self) -> list[dict]:
        """
        Спарсить страницы вузов на olimpiada.ru на предмет
        индивидуальных достижений (за что дают 100 баллов к ЕГЭ).

        Возвращает:
            list[dict]: Записи с данными об ИД по каждому вузу.
        """
        records = []
        timestamp = self.now_timestamp()

        for uni in UNIVERSITIES:
            slug = UNI_SLUGS_OLIMPIADA.get(uni["id"])
            if not slug:
                continue

            url = f"{self.BASE_URL}/vuz/{slug}/"
            soup = self.get_page(url)
            if soup is None:
                continue

            achievements = self._extract_achievements_from_page(soup)
            score_100    = self._extract_score_100(soup)

            if achievements or score_100:
                records.append({
                    "timestamp":        timestamp,
                    "data_type":        "achievement",
                    "olympiad_id":      "",
                    "olympiad_name":    "",
                    "olympiad_level":   "",
                    "subject":          "",
                    "university_id":    uni["id"],
                    "university_name":  uni["short_name"],
                    "city":             uni["city"],
                    "benefit_type":     "individual_achievement",
                    "benefit_detail":   achievements,
                    "profiles":         score_100,
                })

        return records

    # ==========================
    # Извлечение полей
    # ==========================

    def _extract_olympiad_name(self, soup) -> str:
        """Извлечь название олимпиады."""
        for selector in [
            ("h1", {"class": "activity_title"}),
            ("h1", {"class": "olimp-title"}),
            ("h1", {}),
        ]:
            tag, attrs = selector
            el = soup.find(tag, attrs) if attrs else soup.find(tag)
            if el:
                return self.clean_text(el.get_text())
        return "Не определено"

    def _extract_olympiad_level(self, soup) -> str:
        """Извлечь уровень олимпиады (1/2/3) из Перечня Минобрнауки."""
        for selector in [
            ("span", {"class": "level"}),
            ("div",  {"class": "olymp-level"}),
            ("td",   {"class": "level"}),
        ]:
            tag, attrs = selector
            el = soup.find(tag, attrs)
            if el:
                text = self.clean_text(el.get_text())
                for lvl in ["1", "2", "3"]:
                    if lvl in text:
                        return lvl
        return ""

    def _extract_olympiad_subject(self, soup) -> str:
        """Извлечь предмет / профиль олимпиады."""
        for selector in [
            ("div", {"class": "subject"}),
            ("span", {"class": "predmet"}),
            ("td",  {"class": "subject"}),
        ]:
            tag, attrs = selector
            el = soup.find(tag, attrs)
            if el:
                return self.clean_text(el.get_text())
        return ""

    def _extract_achievements_from_page(self, soup) -> str:
        """Извлечь список индивидуальных достижений (доп. баллы)."""
        for selector in [
            ("div", {"class": "achievements"}),
            ("div", {"class": "ind-dostizheniya"}),
            ("section", {"id": "achievements"}),
        ]:
            tag, attrs = selector
            el = soup.find(tag, attrs)
            if el:
                return self.clean_text(el.get_text())
        return ""

    def _extract_score_100(self, soup) -> str:
        """Извлечь информацию о том, за что дают 100 баллов."""
        for selector in [
            ("div", {"class": "score100"}),
            ("div", {"class": "hundred-points"}),
            ("td",  {"class": "ball100"}),
        ]:
            tag, attrs = selector
            el = soup.find(tag, attrs)
            if el:
                return self.clean_text(el.get_text())
        return ""

    # ==========================
    # Вспомогательные методы
    # ==========================

    def _match_university(self, raw_name: str) -> dict | None:
        """
        Найти вуз из нашего списка по названию со страницы олимпиады.
        Сравнение нечёткое — по вхождению ключевых слов.
        """
        name_lower = raw_name.lower()
        for uni in UNIVERSITIES:
            keywords = [
                uni["short_name"].lower(),
                uni["full_name"].lower()[:20],  # первые 20 символов полного названия
            ]
            if any(kw in name_lower for kw in keywords):
                return uni
        return None

    def _classify_benefit(self, benefit_text: str) -> str:
        """Классифицировать вид льготы по тексту."""
        text = benefit_text.lower()
        if "без вступительных" in text or "бви" in text:
            return "БВИ"
        if "100" in text and "балл" in text:
            return "100 баллов"
        if "преимущественное" in text:
            return "преимущественное право"
        if "дополнительные" in text or "доп" in text:
            return "доп. баллы"
        return "льгота"

    def _is_target_subject(self, subject: str) -> bool:
        """Проверить, входит ли предмет олимпиады в целевые."""
        subj_lower = subject.lower()
        return any(t in subj_lower for t in TARGET_SUBJECTS)

    # ==========================
    # Сохранение данных
    # ==========================

    def _save_csv(self, records: list[dict]) -> None:
        """Сохранить данные об олимпиадах в CSV с дозаписью (append)."""
        if not records:
            self.logger.warning("Нет данных олимпиад для сохранения")
            return

        path = Path(RAW_OLYMPIADS_CSV)
        path.parent.mkdir(parents=True, exist_ok=True)

        file_exists = path.exists()
        fieldnames = list(records[0].keys())

        with open(path, "a", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            if not file_exists:
                writer.writeheader()
            writer.writerows(records)

        self.logger.info(f"💾 Олимпиады CSV: {path} ({len(records)} строк)")

    def _update_partners_json(self, records: list[dict]) -> None:
        """
        Добавить данные об олимпиадах в partners.json.
        Читает существующий файл и дополняет секцию 'olympiads' для каждого вуза.
        """
        path = Path(PARTNERS_JSON)
        if not path.exists():
            self.logger.warning(
                "partners.json не найден — сначала запустите PostupiScraper"
            )
            return

        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)

        for r in records:
            uid = r["university_id"]
            if uid not in data:
                continue
            if "olympiads" not in data[uid]:
                data[uid]["olympiads"] = []

            # Добавляем только уникальные записи
            entry = {
                "olympiad_name":  r["olympiad_name"],
                "olympiad_level": r["olympiad_level"],
                "subject":        r["subject"],
                "benefit_type":   r["benefit_type"],
                "benefit_detail": r["benefit_detail"],
                "profiles":       r["profiles"],
                "updated_at":     r["timestamp"],
            }
            # Дедупликация по названию олимпиады
            existing_names = [o["olympiad_name"] for o in data[uid]["olympiads"]]
            if entry["olympiad_name"] not in existing_names:
                data[uid]["olympiads"].append(entry)

        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        self.logger.info(f"💾 partners.json обновлён олимпиадами: {path}")
