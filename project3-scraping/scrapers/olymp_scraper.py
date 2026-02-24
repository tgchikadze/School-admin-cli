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
from urllib.parse import urljoin, urlparse


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
    # Парсинг HTML (реальный)
    # --------------------------
    def _parse_html_benefits(self, row: "pd.Series") -> list[dict[str, Any]]:
        """
        Скачать HTML-страницу, извлечь текст, найти строки с ключевыми
        словами по льготам (БВИ, 100 баллов, ИД) — аналогично PDF-ветке.
        Также ищет PDF-ссылки на странице и добавляет их в olymp_all / programs CSV.
        """
        url = str(row["olympiad_url"]).strip()

        # --- дедупликация: не ходим на один URL дважды ---
        if url in self.visited:
            self.logger.info(f"[HTML] Уже посещали {url}, пропуск")
            return []
        self.visited.add(url)

        # --- скачиваем страницу ---
        self.logger.info(f"[HTML] Качаем {url}")
        soup = self.get_page(url)
        if soup is None:
            self.logger.warning(f"[HTML] Не удалось загрузить {url}")
            return []

        # --- извлекаем текст страницы ---
        full_text = self.clean_text(
            soup.get_text(separator="\n", strip=True)
        )
        if not full_text:
            self.logger.warning(f"[HTML] Пустой текст на {url}")
            return []

        # --- ищем строки с ключевыми словами (как в PDF-ветке) ---
        full_text_lower = full_text.lower()
        if any(kw in full_text_lower for kw in self.KEYWORDS):
            lines = [
                ln
                for ln in full_text.splitlines()
                if any(kw in ln.lower() for kw in self.KEYWORDS)
            ]
            snippet = "\n".join(lines)[:2000]
        else:
            self.logger.warning(
                f"[HTML] Ключевые слова не найдены на {url}, берём начало текста"
            )
            snippet = full_text[:1000]

        # --- ищем PDF-ссылки и добавляем в CSV (с фильтром) ---
        pdf_links = self._extract_and_filter_pdfs(soup, url)
        if pdf_links:
            self._append_pdf_links_to_olymp_csv(row, pdf_links)

        # --- формируем запись ---
        timestamp = self.now_timestamp()
        record: dict[str, Any] = {
            "timestamp":       timestamp,
            "data_type":       "olymp_html",
            "olympiad_id":     row.get("olympiad_id", ""),
            "olympiad_name":   row.get("olympiad_name", ""),
            "olympiad_level":  row.get("olympiad_level", ""),
            "subject":         row.get("subject", ""),
            "university_id":   row.get("university_id", ""),
            "university_name": row.get("university_short_name", ""),
            "city":            row.get("city", ""),
            "okso_code":       row.get("okso_code", ""),
            "program_name":    row.get("program_name", ""),
            "program_level":   row.get("program_level", ""),
            "benefit_type":    row.get("benefit_types", ""),
            "benefit_detail":  snippet,
            "profiles":        "",
            "source_site":     row.get("source_site", ""),
            "olympiad_url":    url,
            "notes":           row.get("notes", ""),
        }
        return [record]

    # --------------------------
    # Вспомогательные методы
    # --------------------------
    def _resolve_uni_by_url(self, pdf_url: str) -> dict | None:
        """
        По домену PDF-ссылки найти вуз из UNIVERSITIES.
        Возвращает dict вуза или None, если домен не наш.
        """
        pdf_domain = urlparse(pdf_url).netloc.replace("www.", "").lower()

        for uni in UNIVERSITIES:
            # Собираем все домены вуза: official_url + другие известные
            for key in ("official_url", "admission_url"):
                uni_url = uni.get(key, "")
                if not uni_url:
                    continue
                uni_domain = urlparse(uni_url).netloc.replace("www.", "").lower()
                if not uni_domain:
                    continue
                # Проверяем вхождение: abit.itmo.ru содержит itmo.ru
                if uni_domain in pdf_domain or pdf_domain in uni_domain:
                    return uni

        return None  # PDF чужого вуза — пропустить ИЛИ обработать
    def _extract_and_filter_pdfs(self, soup, base_url: str) -> list[str]:
        """Найти PDF-ссылки на странице, отфильтровать стоп-список."""

        links: list[str] = []
        for a in soup.find_all("a", href=True):
            href = a["href"].strip()
            if ".pdf" not in href.lower():
                continue
            full = href if href.startswith("http") else urljoin(base_url, href)
            if any(block in full.lower() for block in PDF_BLOCKLIST):
                continue
            links.append(full)
        return list(set(links))

    def _append_pdf_links_to_olymp_csv(
            self, row: "pd.Series", pdf_urls: list[str]
    ) -> None:
        """Дописать новые PDF-ссылки в olymp_all.csv с ПРАВИЛЬНЫМИ метаданными вуза."""
        import csv as _csv
        path = Path(OLYMPIADS_CSV_PATH)

        existing_urls: set[str] = set()
        existing_rows: list[dict] = []
        if path.exists():
            with open(path, "r", encoding="utf-8") as f:
                reader = _csv.DictReader(f)
                existing_rows = list(reader)
            for r in existing_rows:
                u = r.get("olympiad_url", "")
                if u:
                    existing_urls.add(u.strip())

        new_rows: list[dict] = []
        for pdf_url in pdf_urls:
            if pdf_url in existing_urls:
                continue

            # ---- КЛЮЧЕВОЕ ИЗМЕНЕНИЕ: резолвим вуз по домену PDF ----
            resolved_uni = self._resolve_uni_by_url(pdf_url)

            if resolved_uni is None:
                # PDF с домена, которого нет в UNIVERSITIES — пропускаем
                self.logger.debug(f"PDF {pdf_url} — домен не в UNIVERSITIES, пропуск")
                continue

            # Метаданные берём из resolved_uni, а НЕ из row
            new_rows.append({
                "olympiad_id": "",
                "olympiad_name": row.get("olympiad_name", ""),
                "subject": row.get("subject", ""),
                "olympiad_level": "",
                "university_id": resolved_uni["id"],
                "university_short_name": resolved_uni["short_name"],
                "city": resolved_uni["city"],
                "okso_code": "",  # ← пусто: мы не знаем ОКСО чужого вуза
                "program_name": "",  # ← пусто: определится при парсинге PDF
                "program_level": "",
                "benefit_relevance": "",
                "benefit_types": "",
                "source_site": "olymp_html_discovered",
                "olympiad_url": pdf_url,
                "notes": f"auto: PDF found on {row.get('olympiad_url', '')}",
                "active": "1",
                "needs_deep_parse": "1",
                "content_type": "pdf",
            })

        if not new_rows:
            return

        fieldnames = existing_rows[0].keys() if existing_rows else new_rows[0].keys()
        with open(path, "w", encoding="utf-8", newline="") as f:
            writer = _csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            for r in existing_rows:
                writer.writerow(r)
            for r in new_rows:
                writer.writerow(r)

        self.logger.info(
            f"olymp_all.csv дополнен {len(new_rows)} PDF из HTML-страницы"
        )

    # --------------------------
    # Сохранение данных
    # --------------------------
    def _save_csv(self, records: list[dict]) -> None:
        """Дописать записи в raw CSV, но с дедупликацией по timestamp+url."""
        if not records:
            return

        path = Path(RAW_OLYMPIADS_CSV)  # или RAW_UNIVERSITIES_CSV
        path.parent.mkdir(parents=True, exist_ok=True)

        # Читаем существующие URL, чтобы не дублировать
        existing_keys: set[str] = set()
        if path.exists():
            with open(path, "r", encoding="utf-8") as f:
                for row in csv.DictReader(f):
                    key = row.get("olympiad_url", "") or row.get("page_url", "")
                    existing_keys.add(key.strip())

        # Фильтруем новые записи
        new_records = [
            r for r in records
            if (r.get("olympiad_url", "") or r.get("page_url", "")).strip()
               not in existing_keys
        ]

        if not new_records:
            self.logger.info("Нет новых записей для raw CSV")
            return

        file_exists = path.exists()
        fieldnames = list(new_records[0].keys())
        with open(path, "a", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            if not file_exists:
                writer.writeheader()
            writer.writerows(new_records)

        self.logger.info(f"raw CSV += {len(new_records)} новых записей")


