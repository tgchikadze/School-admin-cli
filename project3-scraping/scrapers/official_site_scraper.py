import csv
import json
import re
from pathlib import Path
from typing import Any, Dict, List, Optional

import pdfplumber
from bs4 import BeautifulSoup  # если уже используешь, иначе добавить в requirements

from scrapers.basescraper import BaseScraper
from config import (
    UNIVERSITIES,
    PROGRAMS_CSV_PATH,
    OLYMPIADS_CSV_PATH,
    PARTNERS_JSON,
    RAW_UNIVERSITIES_CSV,
)


class OfficialSiteScraper(BaseScraper):
    """
    Скрапер официальных сайтов вузов (HTML + PDF).

    Задачи:
    - пройтись по official_url из UNIVERSITIES (активные вузы);
    - пройтись по urls_for_parsers_all.csv (programs_page_url + content_type);
    - для HTML:
        * собрать базовую инфу по приёму (по ключевым словам),
        * найти новые PDF-ссылки и добавить в urls_for_parsers_all.csv / olymp_all.csv;
    - для PDF:
        * извлечь текст и попытаться вытащить структурированные поля (min_score, ЕГЭ, ИД);
    - собрать структурированные записи и обновить partners.json.
    """

    def __init__(self) -> None:
        super().__init__("OfficialSiteScraper")

    # ---------- Публичный вход ----------

    def scrape(self) -> List[Dict[str, Any]]:
        records: List[Dict[str, Any]] = []

        # 1) HTML/PDF по official_url активных вузов
        for uni in UNIVERSITIES:
            if not uni.get("active", True):
                continue
            uni_id = uni["id"]
            official_url = uni.get("official_url")
            if not official_url:
                continue

            recs = self._scrape_university_official_page(uni, official_url)
            records.extend(recs)

        # 2) HTML/PDF по urls_for_parsers_all.csv (programs_page_url + content_type)
        url_rows = self._load_program_targets()
        for row in url_rows:
            if not row.get("active"):
                continue
            uni_id = row["university_id"]
            uni = self._get_university_by_id(uni_id)
            if not uni:
                continue

            programs_page_url = row.get("programs_page_url") or row.get("program_detail_url")
            if not programs_page_url:
                continue

            content_type = (row.get("content_type") or "html").lower()
            if content_type == "pdf":
                recs = self._parse_official_pdf(uni, row, programs_page_url)
            else:
                recs = self._parse_official_html(uni, row, programs_page_url)

            records.extend(recs)

        # 3) Обновляем partners.json структурированными данными
        if records:
            self._update_partners_json(records)

        self.logger.info(f"OfficialSiteScraper: собрано {len(records)} записей")
        return records

    # ---------- Вспомогательные загрузчики ----------

    def _load_program_targets(self) -> List[Dict[str, Any]]:
        """
        Читает urls_for_parsers_all.csv -> список словарей.
        """
        path = Path(PROGRAMS_CSV_PATH)
        if not path.exists():
            self.logger.warning(f"Нет файла целей программ: {path}")
            return []

        rows: List[Dict[str, Any]] = []
        with open(path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                # нормализуем флаг active
                row["active"] = str(row.get("active", "1")) in ("1", "true", "True")
                rows.append(row)
        return rows

    def _get_university_by_id(self, uni_id: str) -> Optional[Dict[str, Any]]:
        for uni in UNIVERSITIES:
            if uni["id"] == uni_id:
                return uni
        return None

    # ---------- Скрапинг по official_url вуза ----------

    def _scrape_university_official_page(
        self,
        uni: Dict[str, Any],
        url: str,
    ) -> List[Dict[str, Any]]:
        """
        Базовый проход по главной/приёмной странице вуза.
        Пока делаем упрощённо:
        - тянем HTML,
        - вытаскиваем крупный блок текста про приём,
        - ищем PDF-ссылки и дописываем их в urls_for_parsers_all.csv / olymp_all.csv.
        """
        soup = self.get_page(url)
        if soup is None:
            return []

        uni_id = uni["id"]
        uni_name = uni["short_name"]
        city = uni["city"]

        # 1) Найти текстовый блок про приём
        admission_text = self._extract_admission_text(soup)

        # 2) Найти PDF-ссылки в HTML и дописать их в конфиги
        new_pdf_links = self._extract_pdf_links(soup, base_url=url)
        if new_pdf_links:
            self._patch_programs_csv_with_pdfs(uni, new_pdf_links)
            self._patch_olymp_all_with_pdfs(uni, new_pdf_links)

        # 3) Пока формируем высокоуровневую запись без привязки к программе
        # (привязку по оксо/программе можно сделать, когда будем умнее парсить текст)
        if not admission_text:
            return []

        timestamp = self.now_timestamp()
        record = {
            "timestamp": timestamp,
            "university_id": uni_id,
            "university_name": uni_name,
            "city": city,
            "program_name": "",       # неизвестно на этом уровне
            "program_level": "",
            "okso_code": "",
            "min_score": "",
            "avg_score": "",
            "budget_places": "",
            "cost": "",
            "ege_subjects": "",
            "achievements": admission_text,  # пока сюда складываем общий текст
            "source": "official_site",
            "page_url": url,
        }
        return [record]

    def _extract_admission_text(self, soup: BeautifulSoup) -> str:
        """
        Простейшая эвристика: пытаемся найти блоки, связанные с приёмом.
        """
        candidates = []

        # Поиск по id/class с ключами типа 'abitur', 'priem', 'admission'
        selectors = [
            ("div", {"id": re.compile(r"(abitur|priem|admission)", re.I)}),
            ("section", {"id": re.compile(r"(abitur|priem|admission)", re.I)}),
            ("div", {"class": re.compile(r"(abitur|priem|admission)", re.I)}),
            ("section", {"class": re.compile(r"(abitur|priem|admission)", re.I)}),
            ("main", {}),
        ]

        for tag, attrs in selectors:
            el = soup.find(tag, attrs=attrs) if attrs else soup.find(tag)
            if el:
                text = self.clean_text(el.get_text(separator=" ", strip=True))
                if text and len(text) > 200:
                    candidates.append(text)

        if not candidates:
            # fallback: берём body целиком, но ограничиваем длину
            body = soup.body
            if body:
                text = self.clean_text(body.get_text(separator=" ", strip=True))
                return text[:5000]
            return ""

        # Берём самый длинный кандидат
        candidates.sort(key=len, reverse=True)
        return candidates[0][:5000]

    # ---------- HTML / PDF парсеры для targets CSV ----------

    def _parse_official_html(
        self,
        uni: Dict[str, Any],
        row: Dict[str, Any],
        url: str,
    ) -> List[Dict[str, Any]]:
        soup = self.get_page(url)
        if soup is None:
            return []

        uni_id = uni["id"]
        uni_name = uni["short_name"]
        city = uni["city"]

        admission_text = self._extract_admission_text(soup)

        # На этих страницах также ищем новые PDF-ссылки
        new_pdf_links = self._extract_pdf_links(soup, base_url=url)
        if new_pdf_links:
            self._patch_programs_csv_with_pdfs(uni, new_pdf_links)
            self._patch_olymp_all_with_pdfs(uni, new_pdf_links)

        if not admission_text:
            return []

        timestamp = self.now_timestamp()
        record = {
            "timestamp": timestamp,
            "university_id": uni_id,
            "university_name": uni_name,
            "city": city,
            "program_name": row.get("program_name", "") or "",
            "program_level": row.get("program_level", "") or "",
            "okso_code": row.get("okso_code", "") or "",
            "min_score": "",
            "avg_score": "",
            "budget_places": "",
            "cost": "",
            "ege_subjects": "",
            "achievements": admission_text,
            "source": "official_program_html",
            "page_url": url,
        }
        return [record]

    def _parse_official_pdf(
        self,
        uni: Dict[str, Any],
        row: Dict[str, Any],
        url: str,
    ) -> List[Dict[str, Any]]:
        """
        Простой парсинг PDF: вытаскиваем текст и потом по регуляркам/ключам
        можно будет доставать min_score, ЕГЭ и т.п.
        Пока — складываем текст целиком в achievements.
        """
        uni_id = uni["id"]
        uni_name = uni["short_name"]
        city = uni["city"]

        text_chunks: List[str] = []
        try:
            with pdfplumber.open(self.session.get(url, stream=True).raw) as pdf:
                for page in pdf.pages:
                    page_text = page.extract_text() or ""
                    if page_text:
                        text_chunks.append(page_text)
        except Exception as e:
            self.logger.warning(f"Не удалось распарсить PDF {url}: {e}")
            return []

        full_text = self.clean_text("\n".join(text_chunks))
        if not full_text:
            return []

        # TODO: здесь можно добавить мини-парсер для min_score, cost и т.п.
        timestamp = self.now_timestamp()
        record = {
            "timestamp": timestamp,
            "university_id": uni_id,
            "university_name": uni_name,
            "city": city,
            "program_name": row.get("program_name", "") or "",
            "program_level": row.get("program_level", "") or "",
            "okso_code": row.get("okso_code", "") or "",
            "min_score": "",
            "avg_score": "",
            "budget_places": "",
            "cost": "",
            "ege_subjects": "",
            "achievements": full_text[:10000],
            "source": "official_program_pdf",
            "page_url": url,
        }
        return [record]

    # ---------- Поиск PDF-ссылок и патч CSV ----------

    def _extract_pdf_links(self, soup: BeautifulSoup, base_url: str) -> List[str]:
        """
        Находим все <a> с href на .pdf, возвращаем список уникальных абсолютных ссылок.
        """
        links = set()
        for a in soup.find_all("a", href=True):
            href = a["href"].strip()
            if not href:
                continue
            href_lower = href.lower()
            if ".pdf" not in href_lower:
                continue
            # Простейшее приведение к абсолютному URL
            if href_lower.startswith("http://") or href_lower.startswith("https://"):
                full_url = href
            else:
                # относительный путь относительно base_url
                full_url = self.make_absolute_url(base_url, href)
            links.add(full_url)
        return list(links)

    def make_absolute_url(self, base_url: str, href: str) -> str:
        """
        Простейший helper для формирования абсолютного URL.
        Можно заменить на urljoin из urllib.parse.
        """
        from urllib.parse import urljoin

        return urljoin(base_url, href)

    def _patch_programs_csv_with_pdfs(
        self,
        uni: Dict[str, Any],
        pdf_urls: List[str],
    ) -> None:
        """
        Добавляет найденные PDF-ссылки в urls_for_parsers_all.csv как новые строки
        с content_type='pdf', если таких ссылок ещё нет.
        """
        path = Path(PROGRAMS_CSV_PATH)
        existing_rows: List[Dict[str, Any]] = []
        existing_urls: set[str] = set()

        if path.exists():
            with open(path, "r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                existing_rows = list(reader)
                for r in existing_rows:
                    url = r.get("programs_page_url") or r.get("program_detail_url")
                    if url:
                        existing_urls.add(url.strip())

        new_rows: List[Dict[str, Any]] = []
        for pdf_url in pdf_urls:
            if pdf_url in existing_urls:
                continue
            new_rows.append(
                {
                    "university_id": uni["id"],
                    "university_short_name": uni["short_name"],
                    "city": uni["city"],
                    "priority": uni.get("priority", 1),
                    "program_name": "",
                    "program_level": "",
                    "okso_code": "",
                    "profile_keywords": "",
                    "programs_page_url": pdf_url,
                    "program_detail_url": "",
                    "source_site": "official_program",
                    "notes": "auto: discovered admission PDF",
                    "needs_deep_parse": "1",
                    "active": "1",
                    "content_type": "pdf",
                }
            )

        if not new_rows:
            return

        fieldnames = (
            existing_rows[0].keys()
            if existing_rows
            else new_rows[0].keys()
        )

        with open(path, "w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            for r in existing_rows:
                writer.writerow(r)
            for r in new_rows:
                writer.writerow(r)

        self.logger.info(
            f"urls_for_parsers_all.csv дополнен {len(new_rows)} PDF-ссылками для {uni['short_name']}"
        )

    def _patch_olymp_all_with_pdfs(
        self,
        uni: Dict[str, Any],
        pdf_urls: List[str],
    ) -> None:
        """
        Опционально: если среди PDF есть явные документы про олимпиады/льготы,
        можно добавить их в olymp_all.csv как новые цели с content_type='pdf'.

        Пока добавляем все PDF этого вуза как low-priority записи без детализации.
        """
        path = Path(OLYMPIADS_CSV_PATH)
        existing_rows: List[Dict[str, Any]] = []
        existing_urls: set[str] = set()

        if path.exists():
            with open(path, "r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                existing_rows = list(reader)
                for r in existing_rows:
                    url = r.get("olympiad_url")
                    if url:
                        existing_urls.add(url.strip())

        new_rows: List[Dict[str, Any]] = []
        for pdf_url in pdf_urls:
            if pdf_url in existing_urls:
                continue
            new_rows.append(
                {
                    "olympiad_id": "",
                    "olympiad_name": "",
                    "subject": "",
                    "olympiad_level": "",
                    "university_id": uni["id"],
                    "university_short_name": uni["short_name"],
                    "city": uni["city"],
                    "okso_code": "",
                    "program_name": "",
                    "program_level": "",
                    "benefit_relevance": "",
                    "benefit_types": "",
                    "source_site": "official_program",
                    "olympiad_url": pdf_url,
                    "notes": "auto: discovered olymp/admission PDF",
                    "active": "1",
                    "needs_deep_parse": "1",
                    "content_type": "pdf",
                }
            )

        if not new_rows:
            return

        fieldnames = (
            existing_rows[0].keys()
            if existing_rows
            else new_rows[0].keys()
        )

        with open(path, "w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            for r in existing_rows:
                writer.writerow(r)
            for r in new_rows:
                writer.writerow(r)

        self.logger.info(
            f"olymp_all.csv дополнен {len(new_rows)} PDF-ссылками для {uni['short_name']}"
        )

    # ---------- Обновление partners.json ----------

    def _update_partners_json(self, records: List[Dict[str, Any]]) -> None:
        """
        Мержит записи official_* в partners.json, дополняя/уточняя программы.
        Логика:
        - ключ программы: university_id + okso_code + program_level + program_name (если есть);
        - если программа есть — заполняем пустые поля из official-данных;
        - если нет — добавляем новую.
        """
        path = Path(PARTNERS_JSON)
        if not path.exists():
            self.logger.warning(
                f"partners.json не найден по пути {path}, сначала должен отработать PostupiScraper"
            )
            return

        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)

        for r in records:
            uni_id = r["university_id"]
            if uni_id not in data:
                # если по этому вузу ещё нет блока — создаём
                data[uni_id] = {
                    "programs": [],
                    "olympiads": [],
                }

            programs = data[uni_id].setdefault("programs", [])

            # Ключ для поиска существующей программы
            key = (
                r.get("okso_code", ""),
                r.get("program_level", ""),
                r.get("program_name", ""),
            )

            existing = None
            for p in programs:
                p_key = (
                    p.get("okso_code", ""),
                    p.get("program_level", ""),
                    p.get("program_name", ""),
                )
                if p_key == key:
                    existing = p
                    break

            if existing is None:
                # Добавляем новую программу
                programs.append(r)
            else:
                # Обновляем только пустые/отсутствующие поля в existing
                for field in [
                    "min_score",
                    "avg_score",
                    "budget_places",
                    "cost",
                    "ege_subjects",
                    "achievements",
                ]:
                    if not existing.get(field) and r.get(field):
                        existing[field] = r[field]
                # Обновляем source/page_url при необходимости
                if r.get("source"):
                    existing["source"] = (
                        existing.get("source", "") + "+" + r["source"]
                        if existing.get("source")
                        else r["source"]
                    )
                if r.get("page_url"):
                    existing["page_url"] = r["page_url"]

        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        self.logger.info(f"partners.json обновлён official-данными ({len(records)} записей)")

    def _save_csv(self, records: list[dict[str, Any]]) -> None:
        """
        Сохранить данные с официальных сайтов в общий RAW-CSV по вузам.
        """
        if not records:
            self.logger.info("OfficialSiteScraper: нет данных для сохранения")
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

        self.logger.info(
            f"💾 OfficialSiteScraper: данные сохранены в {path} ({len(records)} строк)"
        )