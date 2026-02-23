"""
Парсер данных о вузах с Postupi.Online.

Собирает для каждого вуза и направления:
- минимальный и средний проходной балл ЕГЭ
- стоимость обучения
- предметы ЕГЭ для поступления
- индивидуальные достижения (за что дают доп. баллы / 100 баллов)

Источником списка вузов/направлений служит CSV:
config.PROGRAMS_CSV_PATH (urls_for_parsers_all.csv).

Данные сохраняются в CSV с временной меткой каждого запуска —
это обеспечивает непрерывность сбора (требование ТЗ).
"""

import csv
import json
from pathlib import Path

import pandas as pd

from scrapers.base_scraper import BaseScraper
from config import (
    UNIVERSITIES,
    PROGRAMS_CSV_PATH,
    RAW_UNIVERSITIES_CSV,
    PARTNERS_JSON,
)


class PostupiScraper(BaseScraper):
    """
    Парсер страниц вузов на Postupi.Online.

    Работает только по тем строкам urls_for_parsers_all.csv,
    где source_site == "postupi" и active == 1.
    Для каждой строки идёт по program_detail_url (или programs_page_url)
    и вытаскивает данные по конкретной программе.
    """

    def __init__(self) -> None:
        super().__init__("PostupiScraper")
        self._targets = self._load_targets_from_csv()

    # ==========================
    # Загрузка целей из CSV
    # ==========================

    def _load_targets_from_csv(self) -> pd.DataFrame:
        """
        Прочитать urls_for_parsers_all.csv и взять только строки,
        где source_site == "postupi" и active == 1.
        """
        df = pd.read_csv(PROGRAMS_CSV_PATH)

        mask = (df["source_site"] == "postupi") & (df["active"] == 1)
        df = df[mask].copy()

        self.logger.info(
            f"CSV-цели Postupi загружены: {len(df)} строк, "
            f"{df['university_id'].nunique()} вузов с целевыми программами"
        )
        return df

    # ==========================
    # Основной метод
    # ==========================

    def scrape(self) -> list[dict]:
        """
        Запустить парсинг всех программ, описанных в CSV для Postupi.
        """
        all_records: list[dict] = []

        for uni in UNIVERSITIES:
            uni_id = uni["id"]

            df_uni = self._targets[self._targets["university_id"] == uni_id]
            if df_uni.empty:
                self.logger.info(
                    f"Для {uni_id} нет целевых программ Postupi в CSV, пропускаем"
                )
                continue

            self.logger.info(f"Парсим Postupi: {uni['short_name']} ({uni['city']})")

            for _, row in df_uni.iterrows():
                records = self._scrape_program_row(uni, row)
                all_records.extend(records)

            self.logger.info(
                f" → {uni['short_name']}: сохранено {len(df_uni)} программ "
                f"(сырых записей: {len(all_records)})"
            )

        self._save_csv(all_records)
        self._save_json(all_records)
        return all_records

    # ==========================
    # Парсинг одной строки CSV (одной программы)
    # ==========================

    def _scrape_program_row(self, uni: dict, row: pd.Series) -> list[dict]:
        """
        Спарсить данные по одной программе из строки CSV.

        Берёт URL:
        - сначала program_detail_url, если не пустой,
        - иначе programs_page_url.
        """
        uni_id = row["university_id"]
        program_name = row["program_name"]
        program_level = row["program_level"]
        okso_code = str(row["okso_code"])

        detail_url = row.get("program_detail_url") or ""
        list_url = row.get("programs_page_url") or ""
        url = detail_url or list_url

        if not url:
            self.logger.warning(
                f"Нет URL для программы {uni_id} {okso_code} {program_name}, пропускаем"
            )
            return []

        self.logger.info(
            f"  → Программа: {uni_id} | {okso_code} {program_name} "
            f"({program_level}) — {url}"
        )

        soup = self.get_page(url)
        if soup is None:
            self.logger.error(f"Не удалось загрузить страницу программы: {url}")
            return []

        timestamp = self.now_timestamp()

        # TODO: здесь нужно дописать реальную HTML-логику:
        # вытащить min_score, avg_score, budget_places, cost, ege_subjects, achievements
        # из soup. Пока вернём минимальный набор полей.

        record = {
            "timestamp": timestamp,
            "university_id": uni_id,
            "university_name": uni["short_name"],
            "city": uni["city"],
            "program_name": program_name,
            "program_level": program_level,
            "okso_code": okso_code,
            # Заглушки — позже заменим на реальные данные из HTML:
            "min_score": "",
            "avg_score": "",
            "budget_places": "",
            "cost": "",
            "ege_subjects": "",
            "achievements": "",
            "source": "postupi",
            "page_url": url,
        }

        return [record]

    # ==========================
    # Сохранение данных
    # ==========================

    def _save_csv(self, records: list[dict]) -> None:
        """Сохранить сырые данные по вузам в CSV с дозаписью (append)."""
        if not records:
            self.logger.warning("Нет данных по вузам для сохранения")
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

        self.logger.info(f"💾 Университеты CSV: {path} ({len(records)} строк)")

    def _save_json(self, records: list[dict]) -> None:
        """Обновить partners.json агрегированными данными по вузам."""
        if not records:
            self.logger.warning("Нет данных по вузам для JSON")
            return

        path = Path(PARTNERS_JSON)
        path.parent.mkdir(parents=True, exist_ok=True)

        data: dict = {}
        if path.exists():
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)

        for r in records:
            uid = r["university_id"]
            if uid not in data:
                data[uid] = {"programs": []}
            data[uid]["programs"].append(r)

        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        self.logger.info(f"💾 partners.json обновлён данными вузов: {path}")
