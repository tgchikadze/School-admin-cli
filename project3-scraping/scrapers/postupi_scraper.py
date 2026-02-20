"""
Парсер данных о вузах с сайта tabiturient.ru.

Собирает для каждого вуза и направления:
- Минимальный и средний проходной балл ЕГЭ
- Стоимость обучения
- Предметы ЕГЭ для поступления
- Индивидуальные достижения (за что дают доп. баллы / 100 баллов)

Данные сохраняются в CSV с временной меткой каждого запуска —
это обеспечивает непрерывность сбора (требование ТЗ).
"""

import csv
import json
from pathlib import Path

from scrapers.base_scraper import BaseScraper
from config import UNIVERSITIES, TARGET_PROGRAMS, RAW_UNIVERSITIES_CSV, PARTNERS_JSON


class PostupiScraper(BaseScraper):
    """
    Парсер страниц вузов на tabiturient.ru.

    Для каждого вуза из config.UNIVERSITIES парсит страницу направлений,
    фильтрует по TARGET_PROGRAMS и собирает данные о баллах и стоимости.
    """

    BASE_URL = "https://tabiturient.ru"

    def __init__(self) -> None:
        super().__init__("PostupiScraper")
        # Slug-маппинг: id вуза из config → slug на tabiturient.ru
        self._slug_map = {
            "alferov":   "spbau",
            "sphfu":     "spkhfu",
            "herzen":    "rgpu-gercena",
            "spbpu":     "spbpu",
            "itmo":      "itmo",
            "spbgu":     "spbgu",
            "spbgpmu":   "spbgpmu",
            "pavlov":    "1spbgmu",
            "mechnikov": "szgmu",
            "hse":       "hse",
            "mgu":       "mgu",
            "mipt":      "mfti",
            "ngu":       "ngu",
        }

    # ==========================
    # Основной метод
    # ==========================

    def scrape(self) -> list[dict]:
        """
        Запустить парсинг всех вузов из config.UNIVERSITIES.

        Возвращает:
            list[dict]: Список записей с данными по направлениям.
            Каждая запись содержит: timestamp, university_id, university_name,
            city, program, min_score, avg_score, budget_places, cost,
            ege_subjects, achievements.
        """
        all_records = []

        for uni in UNIVERSITIES:
            uni_id = uni["id"]
            slug = self._slug_map.get(uni_id)

            if not slug:
                self.logger.warning(f"Нет slug для вуза {uni_id}, пропускаем")
                continue

            self.logger.info(f"Парсим {uni['short_name']} ({uni['city']})")
            records = self._scrape_university(uni, slug)
            all_records.extend(records)
            self.logger.info(
                f"  → {uni['short_name']}: найдено {len(records)} направлений"
            )

        self._save_csv(all_records)
        self._save_json(all_records)
        return all_records

    # ==========================
    # Парсинг одного вуза
    # ==========================

    def _scrape_university(self, uni: dict, slug: str) -> list[dict]:
        """
        Спарсить страницу направлений одного вуза.

        Параметры:
            uni:  Словарь вуза из config.UNIVERSITIES
            slug: Slug вуза на tabiturient.ru

        Возвращает:
            list[dict]: Записи по направлениям вуза
        """
        url = f"{self.BASE_URL}/vuzy/{slug}/"
        soup = self.get_page(url)

        if soup is None:
            self.logger.error(f"Не удалось загрузить страницу вуза: {url}")
            return []

        records = []
        timestamp = self.now_timestamp()

        # Ищем блоки направлений — на tabiturient.ru они в тегах
        # <div class="napravlenie"> или <tr> в таблице программ
        programs_blocks = (
            soup.find_all("div", class_="napravlenie")
            or soup.find_all("div", class_="program-row")
            or soup.find_all("tr", class_=lambda c: c and "program" in c)
        )

        if not programs_blocks:
            # Fallback: пробуем найти таблицу с направлениями
            table = soup.find("table", class_=lambda c: c and "napr" in str(c))
            if table:
                programs_blocks = table.find_all("tr")[1:]  # пропускаем заголовок

        if not programs_blocks:
            self.logger.warning(
                f"Не найдены блоки направлений для {uni['short_name']} — "
                f"возможно изменилась структура сайта. URL: {url}"
            )
            # Сохраняем запись-заглушку чтобы фиксировать факт запуска
            records.append(self._empty_record(uni, timestamp, note="no_data"))
            return records

        for block in programs_blocks:
            program_name = self._extract_program_name(block)

            # Фильтруем — берём только целевые направления
            if not self._is_target_program(program_name):
                continue

            record = {
                "timestamp":       timestamp,
                "university_id":   uni["id"],
                "university_name": uni["short_name"],
                "city":            uni["city"],
                "priority":        uni["priority"],
                "program":         program_name,
                "min_score":       self._extract_min_score(block),
                "avg_score":       self._extract_avg_score(block),
                "budget_places":   self._extract_budget_places(block),
                "cost":            self._extract_cost(block),
                "ege_subjects":    self._extract_ege_subjects(block),
                "achievements":    self._extract_achievements(block),
            }
            records.append(record)

        return records

    # ==========================
    # Извлечение полей
    # ==========================

    def _extract_program_name(self, block) -> str:
        """Извлечь название направления из блока."""
        # Пробуем разные селекторы — страховка от изменений верстки
        for selector in [
            ("a", {"class": "napr-name"}),
            ("td", {"class": "napr"}),
            ("div", {"class": "program-name"}),
            ("h3", {}),
            ("a", {}),
        ]:
            tag, attrs = selector
            el = block.find(tag, attrs) if attrs else block.find(tag)
            if el and el.get_text(strip=True):
                return self.clean_text(el.get_text())
        return "Не определено"

    def _extract_min_score(self, block) -> str:
        """Извлечь минимальный проходной балл."""
        for selector in [
            ("span", {"class": "min-ball"}),
            ("td", {"class": "min-score"}),
            ("div", {"class": "score-min"}),
        ]:
            tag, attrs = selector
            el = block.find(tag, attrs)
            if el:
                text = self.clean_text(el.get_text())
                if text.isdigit():
                    return text
        return ""

    def _extract_avg_score(self, block) -> str:
        """Извлечь средний балл поступивших."""
        for selector in [
            ("span", {"class": "avg-ball"}),
            ("td", {"class": "avg-score"}),
            ("div", {"class": "score-avg"}),
        ]:
            tag, attrs = selector
            el = block.find(tag, attrs)
            if el:
                text = self.clean_text(el.get_text())
                if text.replace(".", "").isdigit():
                    return text
        return ""

    def _extract_budget_places(self, block) -> str:
        """Извлечь количество бюджетных мест."""
        for selector in [
            ("span", {"class": "budget"}),
            ("td", {"class": "places"}),
            ("div", {"class": "budget-places"}),
        ]:
            tag, attrs = selector
            el = block.find(tag, attrs)
            if el:
                text = self.clean_text(el.get_text())
                if text.isdigit():
                    return text
        return ""

    def _extract_cost(self, block) -> str:
        """Извлечь стоимость платного обучения (руб/год)."""
        for selector in [
            ("span", {"class": "cost"}),
            ("td",   {"class": "price"}),
            ("div",  {"class": "edu-cost"}),
        ]:
            tag, attrs = selector
            el = block.find(tag, attrs)
            if el:
                return self.clean_text(el.get_text())
        return ""

    def _extract_ege_subjects(self, block) -> str:
        """Извлечь предметы ЕГЭ — через запятую."""
        subjects = []
        for selector in [
            ("span", {"class": "ege-subject"}),
            ("li",   {"class": "subject"}),
            ("div",  {"class": "ege-subjects"}),
        ]:
            tag, attrs = selector
            els = block.find_all(tag, attrs)
            if els:
                subjects = [self.clean_text(e.get_text()) for e in els]
                break
        return ", ".join(subjects)

    def _extract_achievements(self, block) -> str:
        """Извлечь информацию об индивидуальных достижениях."""
        for selector in [
            ("div", {"class": "achievements"}),
            ("div", {"class": "ind-dostizh"}),
            ("td",  {"class": "ach"}),
        ]:
            tag, attrs = selector
            el = block.find(tag, attrs)
            if el:
                return self.clean_text(el.get_text())
        return ""

    # ==========================
    # Фильтрация
    # ==========================

    def _is_target_program(self, program_name: str) -> bool:
        """
        Проверить, входит ли направление в список целевых.

        Сравнение регистронезависимое, по вхождению подстроки.
        """
        name_lower = program_name.lower()
        return any(target in name_lower for target in TARGET_PROGRAMS)

    # ==========================
    # Сохранение данных
    # ==========================

    def _save_csv(self, records: list[dict]) -> None:
        """
        Сохранить записи в CSV с дозаписью (append).

        Временная метка в каждой строке обеспечивает
        непрерывность сбора данных (требование ТЗ).
        """
        if not records:
            self.logger.warning("Нет данных для сохранения в CSV")
            return

        path = Path(RAW_UNIVERSITIES_CSV)
        path.parent.mkdir(parents=True, exist_ok=True)

        file_exists = path.exists()
        fieldnames = list(records[0].keys())

        with open(path, "a", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            if not file_exists:
                writer.writeheader()
            writer.writerows(records)

        self.logger.info(f"💾 CSV сохранён: {path} ({len(records)} строк)")

    def _save_json(self, records: list[dict]) -> None:
        """
        Сохранить обработанные данные в partners.json для проекта 4 (API).

        JSON перезаписывается при каждом запуске — хранит актуальный срез.
        Структура: { university_id: { program: {...данные...} } }
        """
        if not records:
            return

        path = Path(PARTNERS_JSON)
        path.parent.mkdir(parents=True, exist_ok=True)

        # Группируем по вузу
        result: dict = {}
        for r in records:
            uid = r["university_id"]
            if uid not in result:
                result[uid] = {
                    "name":     r["university_name"],
                    "city":     r["city"],
                    "priority": r["priority"],
                    "programs": {},
                }
            result[uid]["programs"][r["program"]] = {
                "min_score":     r["min_score"],
                "avg_score":     r["avg_score"],
                "budget_places": r["budget_places"],
                "cost":          r["cost"],
                "ege_subjects":  r["ege_subjects"],
                "achievements":  r["achievements"],
                "updated_at":    r["timestamp"],
            }

        with open(path, "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)

        self.logger.info(f"💾 JSON сохранён: {path}")

    # ==========================
    # Заглушка при ошибке
    # ==========================

    @staticmethod
    def _empty_record(uni: dict, timestamp: str, note: str = "") -> dict:
        """Вернуть пустую запись для фиксации факта запуска."""
        return {
            "timestamp":       timestamp,
            "university_id":   uni["id"],
            "university_name": uni["short_name"],
            "city":            uni["city"],
            "priority":        uni["priority"],
            "program":         note,
            "min_score":       "",
            "avg_score":       "",
            "budget_places":   "",
            "cost":            "",
            "ege_subjects":    "",
            "achievements":    "",
        }
