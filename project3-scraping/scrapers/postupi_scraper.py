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
import re
from bs4 import BeautifulSoup


import pandas as pd

from scrapers.base_scraper import BaseScraper
from config import (
    UNIVERSITIES,
    PROGRAMS_CSV_PATH,
    RAW_UNIVERSITIES_CSV,
    PARTNERS_JSON,
    SCRAPER_SETTINGS,
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
        self._timeout = SCRAPER_SETTINGS["request_timeout_sec_postupi"]

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

    # ==========================
    # Парсинг одной строки CSV
    # ==========================
    def _scrape_program_row(self, uni: dict, row: pd.Series) -> list[dict]:
        """
        Спарсить данные по одной программе из строки CSV.
        Postupi.online — SPA, поэтому основные данные в JS.
        Стратегия:
          1) Ищем JSON-LD / <meta> / <noscript> — там бывают базовые цифры.
          2) Ищем паттерны в сыром HTML (балл, стоимость, места) регулярками.
          3) Если ничего не найдено — оставляем пустые поля (честнее, чем выдумывать).
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
            f" → Программа: {uni_id} | {okso_code} {program_name} "
            f"({program_level}) — {url}"
        )

        # --- Скачиваем сырой HTML (не через get_page, а через session напрямую,
        #     чтобы получить и raw text для регулярок) ---
        try:
            resp = self.session.get(url, timeout=self._timeout)
            resp.raise_for_status()
            raw_html = resp.text
        except Exception as e:
            self.logger.error(f"Не удалось загрузить {url}: {e}")
            return []

        soup = BeautifulSoup(raw_html, "html.parser")
        timestamp = self.now_timestamp()

        # --- 1) JSON-LD ---
        json_ld_data = self._extract_json_ld(soup)

        # --- 2) <meta> теги ---
        meta_desc = self._extract_meta(soup, "description")
        meta_og_desc = self._extract_meta(soup, "og:description", attr="property")

        # --- 3) Регулярки по сырому HTML ---
        min_score = self._find_score(raw_html, pattern_type="min")
        avg_score = self._find_score(raw_html, pattern_type="avg")
        budget_places = self._find_budget_places(raw_html)
        cost = self._find_cost(raw_html)
        ege_subjects = self._find_ege_subjects(raw_html)

        # --- 4) Текст из <noscript> и всей страницы для achievements ---
        noscript_text = " ".join(
            tag.get_text(separator=" ", strip=True)
            for tag in soup.find_all("noscript")
        )
        # Собираем сниппет из meta + noscript для achievements
        achievements_parts = []
        if meta_desc:
            achievements_parts.append(meta_desc)
        if meta_og_desc and meta_og_desc != meta_desc:
            achievements_parts.append(meta_og_desc)
        if noscript_text:
            achievements_parts.append(noscript_text[:1000])
        achievements = " | ".join(achievements_parts)[:2000]

        # --- JSON-LD может содержать полезные данные ---
        if json_ld_data:
            if not min_score:
                min_score = json_ld_data.get("aggregateRating", {}).get("ratingValue", "")
            if not cost:
                cost_offers = json_ld_data.get("offers", {})
                if isinstance(cost_offers, dict):
                    cost = cost_offers.get("price", "")

        record = {
            "timestamp": timestamp,
            "university_id": uni_id,
            "university_name": uni["short_name"],
            "city": uni["city"],
            "program_name": program_name,
            "program_level": program_level,
            "okso_code": okso_code,
            "min_score": str(min_score) if min_score else "",
            "avg_score": str(avg_score) if avg_score else "",
            "budget_places": str(budget_places) if budget_places else "",
            "cost": str(cost) if cost else "",
            "ege_subjects": ege_subjects,
            "achievements": achievements,
            "source": "postupi",
            "page_url": url,
        }

        filled = sum(1 for k in ("min_score", "avg_score", "budget_places", "cost", "ege_subjects")
                      if record[k])
        self.logger.info(
            f"   Postupi result: {filled}/5 полей заполнено для {okso_code} {program_name}"
        )
        return [record]

    # ==========================
    # Вспомогательные экстракторы
    # ==========================
    def _extract_json_ld(self, soup: BeautifulSoup) -> dict:
        """Извлечь первый блок <script type='application/ld+json'>."""
        import json as _json
        for script in soup.find_all("script", type="application/ld+json"):
            try:
                data = _json.loads(script.string or "")
                if isinstance(data, dict):
                    return data
                if isinstance(data, list) and data:
                    return data[0]
            except Exception:
                continue
        return {}

    def _extract_meta(self, soup: BeautifulSoup, name: str,
                      attr: str = "name") -> str:
        """Извлечь содержимое <meta name=... content=...>."""
        tag = soup.find("meta", attrs={attr: name})
        if tag and tag.get("content"):
            return tag["content"].strip()
        return ""

    def _find_score(self, html: str, pattern_type: str = "min") -> str:
        """
        Ищет проходной балл в сыром HTML.
        Postupi.online часто содержит строки вида:
          'проходной балл: 245', 'средний балл — 267.5', 'Ср. проходной балл 2025'
        """
        if pattern_type == "min":
            patterns = [
                r'(?:мин(?:\.|имальн)?\s*(?:проходной\s*)?балл[:\s—–-]*?)(\d{2,3}(?:[.,]\d)?)',
                r'(?:проходной\s*балл[:\s—–-]*?)(\d{2,3}(?:[.,]\d)?)',
                r'(?:pass(?:ing)?[_\s]?score["\s:]+)(\d{2,3})',
            ]
        else:
            patterns = [
                r'(?:сред(?:\.|ний)?\s*(?:проходной\s*)?балл[:\s—–-]*?)(\d{2,3}(?:[.,]\d)?)',
                r'(?:avg[_\s]?score["\s:]+)(\d{2,3})',
            ]
        for pat in patterns:
            m = re.search(pat, html, re.IGNORECASE)
            if m:
                return m.group(1).replace(",", ".")
        return ""

    def _find_budget_places(self, html: str) -> str:
        """Ищет число бюджетных мест."""
        patterns = [
            r'(?:бюджетн\w*\s*мест\w*[:\s—–-]*?)(\d{1,4})',
            r'(?:budget[_\s]?places["\s:]+)(\d{1,4})',
            r'(?:мест[:\s]*на\s*бюджет[:\s—–-]*?)(\d{1,4})',
        ]
        for pat in patterns:
            m = re.search(pat, html, re.IGNORECASE)
            if m:
                return m.group(1)
        return ""

    def _find_cost(self, html: str) -> str:
        """Ищет стоимость обучения (руб/год)."""
        patterns = [
            r'(?:стоимость\w*[:\s—–-]*?)(\d[\d\s]{2,8}\d)\s*(?:руб|₽|р\.)',
            r'(?:price["\s:]+)(\d[\d\s]{2,8}\d)',
            r'(\d{3}[\s\xa0]?\d{3})\s*(?:руб|₽|р\.?\s*/?\s*год)',
        ]
        for pat in patterns:
            m = re.search(pat, html, re.IGNORECASE)
            if m:
                return m.group(1).replace(" ", "").replace("\xa0", "")
        return ""

    def _find_ege_subjects(self, html: str) -> str:
        """Ищет предметы ЕГЭ."""
        subjects = set()
        subject_map = {
            "русский": "Русский язык",
            "математик": "Математика",
            "информатик": "Информатика",
            "хими": "Химия",
            "биологи": "Биология",
            "физик": "Физика",
            "обществознани": "Обществознание",
            "иностранн": "Иностранный язык",
            "истори": "История",
            "литератур": "Литература",
            "географи": "География",
        }
        # Ищем блоки с перечислением ЕГЭ
        ege_blocks = re.findall(
            r'(?:ЕГЭ|егэ|предметы|экзамены|вступительн)[^<]{0,500}',
            html, re.IGNORECASE
        )
        search_text = " ".join(ege_blocks) if ege_blocks else html[:5000]
        for keyword, name in subject_map.items():
            if re.search(keyword, search_text, re.IGNORECASE):
                subjects.add(name)
        return " + ".join(sorted(subjects)) if subjects else ""

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
        path = Path(PARTNERS_JSON)
        existing = {}
        if path.exists():
            with open(path, "r", encoding="utf-8") as f:
                existing = json.load(f)

        for r in records:
            uni_id = r["university_id"]
            if uni_id not in existing:
                existing[uni_id] = {"programs": []}
            programs = existing[uni_id].setdefault("programs", [])
            key = (r.get("okso_code", ""), r.get("program_level", ""),
                   r.get("program_name", ""))
            found = False
            for p in programs:
                if (p.get("okso_code", ""), p.get("program_level", ""),
                    p.get("program_name", "")) == key:
                    for field in ("min_score", "avg_score", "budget_places",
                                  "cost", "ege_subjects", "achievements"):
                        if not p.get(field) and r.get(field):
                            p[field] = r[field]
                    found = True
                    break
            if not found:
                programs.append(r)

        with open(path, "a", encoding="utf-8") as f:
            json.dump(existing, f, ensure_ascii=False, indent=2)
