"""
Парсер олимпиад и льгот при поступлении с сайта olimpiada.ru.

Работает по конфигурации из CSV:
config.OLYMPIADS_CSV_PATH (olymp_all.csv).

Для каждой строки, где source_site == "olimpiada" и active == 1:
- открывает указанную страницу олимпиады/профиля,
- вытаскивает название, уровень, предмет,
- проходит по таблице льгот и берёт только наши вузы (из config.UNIVERSITIES),
- сохраняет вид льготы (БВИ / 100 баллов / доп. баллы и т.п.)
  с привязкой к university_id, okso_code, program_name.

Отдельно собирает индивидуальные достижения (100 баллов, ИД) со страниц вузов.

Данные сохраняются в CSV с временной меткой каждого запуска.
"""

import csv
import json
import io
import pdfplumber
import pandas as pd
import requests
import pandas as pd

from typing import Any
from pathlib import Path
from scrapers.base_scraper import BaseScraper


from config import (
    UNIVERSITIES,
    RAW_OLYMPIADS_CSV,
    PARTNERS_JSON,
    OLYMPIADS_CSV_PATH,
    PROGRAMS_CSV_PATH,  # NEW
    PDF_BLOCKLIST, # NEW
)


# =========================================
# Парсер льгот по olymp_all.csv (PDF + HTML)
# =========================================

class OlympBenefitsScraper(BaseScraper):
    """
    Парсер льгот по заранее подготовленному конфигу olymp_all.csv.

    Для каждой строки:
    - определяет тип контента по olympiad_url (pdf / html),
    - для PDF вытягивает текст и ищет упоминания БВИ / 100 баллов / ИД,
    - формирует одну агрегированную запись по программе.
    """

    KEYWORDS = ["бви", "без вступительных", "100 балл", "100-балл", "индивидуальн"]

    def __init__(self) -> None:
        super().__init__("OlympBenefitsScraper")
        self.visited = set()

    # --------------------------
    # Публичный метод
    # --------------------------
    def scrape(self) -> list[dict]:
        """
        Пройти по всем строкам olymp_all.csv и собрать льготы.
        """
        df = self._load_targets()
        all_records: list[dict[str, Any]] = []

        for _, row in df.iterrows():
            if not row.get("active", 1):
                continue

            content_type = row.get("content_type", "html")

            if content_type == "pdf":
                records = self._parse_pdf_benefits(row)
            else:
                records = self._parse_html_benefits(row)

            all_records.extend(records)

        # Сохраняем в общий CSV по олимпиадам
        self._save_csv(all_records)
        return all_records

    # --------------------------
    # Загрузка и нормализация целей
    # --------------------------
    def _load_targets(self) -> pd.DataFrame:
        """
        Загрузить olymp_all.csv и автоматически проставить content_type.
        """
        df = pd.read_csv(OLYMPIADS_CSV_PATH)

        if "content_type" not in df.columns:
            df["content_type"] = ""

        df["content_type"] = df["content_type"].fillna("")

        # Если в URL явно PDF — считаем типом pdf (не меняя сам файл на диске)
        mask_pdf = df["olympiad_url"].astype(str).str.lower().str.endswith(".pdf")
        df.loc[mask_pdf, "content_type"] = "pdf"

        # Остальным проставим html по умолчанию
        df.loc[df["content_type"] == "", "content_type"] = "html"

        return df

    # --------------------------
    # Парсинг PDF
    # --------------------------
    def _parse_pdf_benefits(self, row: "pd.Series") -> list[dict[str, Any]]:
        """
        Спарсить PDF по одной строке из olymp_all.csv и вернуть одну агрегированную запись.
        """
        url = str(row["olympiad_url"]).strip()
        self.logger.info(f"[PDF] Качаем {url}")

        try:
            resp = requests.get(url, timeout=30)
            resp.raise_for_status()
        except Exception as e:
            self.logger.error(f"Не удалось скачать PDF {url}: {e}")
            return []

        try:
            with pdfplumber.open(io.BytesIO(resp.content)) as pdf:
                parts: list[str] = []
                for page in pdf.pages:
                    page_text = page.extract_text() or ""
                    parts.append(page_text)
                full_text = "\n".join(parts)
        except Exception as e:
            self.logger.error(f"Ошибка разбора PDF {url}: {e}")
            return []

        full_text_lower = full_text.lower()
        if any(k in full_text_lower for k in self.KEYWORDS):
            lines = [
                ln
                for ln in full_text.splitlines()
                if any(k in ln.lower() for k in self.KEYWORDS)
            ]
            snippet = "\n".join(lines)[:2000]
        else:
            self.logger.warning(f"В PDF {url} не найдены ключевые слова по льготам")
            snippet = full_text[:1000]

        timestamp = self.now_timestamp()

        record: dict[str, Any] = {
            "timestamp": timestamp,
            "data_type": "olymp_pdf",
            "olympiad_id": row.get("olympiad_id", ""),
            "olympiad_name": row.get("olympiad_name", ""),
            "olympiad_level": row.get("olympiad_level", ""),
            "subject": row.get("subject", ""),
            "university_id": row.get("university_id", ""),
            "university_name": row.get("university_short_name", ""),
            "city": row.get("city", ""),
            "okso_code": row.get("okso_code", ""),
            "program_name": row.get("program_name", ""),
            "program_level": row.get("program_level", ""),
            # Ожидаемый тип льготы берём из csv (bvi;ege_100;id_points),
            # а подробности — из PDF.
            "benefit_type": row.get("benefit_types", ""),
            "benefit_detail": snippet,
            "profiles": "",
            "source_site": row.get("source_site", ""),
            "olympiad_url": url,
            "notes": row.get("notes", ""),
        }

        return [record]

    # --------------------------
    # Парсинг HTML (заглушка)
    # --------------------------
    def _parse_html_benefits(self, row: "pd.Series") -> list[dict[str, Any]]:
        """
        Временный простой HTML-парсер: просто сохраняем ссылку и описание из CSV.
        Позже можно заменить на специализированный парсер для конкретных вузов.
        """
        url = str(row["olympiad_url"]).strip()
        timestamp = self.now_timestamp()

        record: dict[str, Any] = {
            "timestamp": timestamp,
            "data_type": "olymp_html",
            "olympiad_id": row.get("olympiad_id", ""),
            "olympiad_name": row.get("olympiad_name", ""),
            "olympiad_level": row.get("olympiad_level", ""),
            "subject": row.get("subject", ""),
            "university_id": row.get("university_id", ""),
            "university_name": row.get("university_short_name", ""),
            "city": row.get("city", ""),
            "okso_code": row.get("okso_code", ""),
            "program_name": row.get("program_name", ""),
            "program_level": row.get("program_level", ""),
            "benefit_type": row.get("benefit_types", ""),
            # Пока без реального HTML-парсинга — просто описание из csv.
            "benefit_detail": row.get("notes", ""),
            "profiles": "",
            "source_site": row.get("source_site", ""),
            "olympiad_url": url,
            "notes": row.get("notes", ""),
        }

        return [record]

    # --------------------------
    # Сохранение данных
    # --------------------------
    def _save_csv(self, records: list[dict[str, Any]]) -> None:
        """
        Сохранить данные льгот из olymp_all в общий CSV по олимпиадам.
        """
        if not records:
            self.logger.warning("Нет данных льгот для сохранения (OlympBenefitsScraper)")
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

        self.logger.info(f"💾 Льготы по olymp_all CSV: {path} ({len(records)} строк)")


