import csv
import json
import re
from pathlib import Path
from typing import Any, Dict, List, Optional
from io import BytesIO
from urllib.parse import urlparse, urljoin


import pdfplumber
from bs4 import BeautifulSoup  # если уже используешь, иначе добавить в requirements

from scrapers.base_scraper import BaseScraper

from config import (
    UNIVERSITIES,
    PROGRAMS_CSV_PATH,
    OLYMPIADS_CSV_PATH,
    PARTNERS_JSON,
    RAW_UNIVERSITIES_CSV,
    PDF_BLOCKLIST,
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
        self.visited = set()

    # ---------- Публичный вход ----------

    def scrape(self) -> List[Dict[str, Any]]:
        records: List[Dict[str, Any]] = []

        # 1) HTML/PDF по official_url активных вузов
        for uni in UNIVERSITIES:
            if not uni.get("active", True):
                continue
            uni_id = uni["id"]
            if uni_id in self.visited:
                continue
            self.visited.add(uni_id)

            official_url = uni.get("official_url")
            if not official_url:
                continue
            recs = self._scrape_university_official_page(uni, official_url)
            records.extend(recs)

        # 2) HTML/PDF по urls_for_parsers_all.csv
        url_rows = self._load_program_targets()
        for row in url_rows:
            if not row.get("active"):
                continue
            programs_page_url = row.get("programs_page_url") or row.get("program_detail_url")
            if not programs_page_url:
                continue
            if programs_page_url in self.visited:
                continue
            self.visited.add(programs_page_url)

            uni_id = row["university_id"]
            uni = self._get_university_by_id(uni_id)
            if not uni:
                continue

            content_type = (row.get("content_type") or "html").lower()
            if content_type == "pdf":
                recs = self._parse_official_pdf(uni, row, programs_page_url)
            else:
                recs = self._parse_official_html(uni, row, programs_page_url)
            records.extend(recs)

        # 3) Обновляем partners.json
        if records:
            self._update_partners_json(records)
            self._save_csv(records)
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
        new_pdf_links = [
            l for l in self._extract_pdf_links(soup, base_url=url)
            if not any(block.lower() in l.lower() for block in PDF_BLOCKLIST)
        ]

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

        # ИТМО-специфика: если URL с abit.itmo.ru, парсим их таблицы
        if "abit.itmo.ru" in url:
            return self._parse_itmo_html(soup, uni_id, uni_name, city, url, row)

        admission_text = self._extract_admission_text(soup)


        # На этих страницах также ищем новые PDF-ссылки
        new_pdf_links = [
            l for l in self._extract_pdf_links(soup, base_url=url)
            if not any(block.lower() in l.lower() for block in PDF_BLOCKLIST)
        ]

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
        """Парсит PDF ИТМО: rsosh_bvi_2023.pdf, buklets_bachelor.pdf."""
        uni_id = uni["id"]
        uni_name = uni["short_name"]
        city = uni["city"]

        text_chunks = []
        try:
            response = self.session.get(url, timeout=30)
            response.raise_for_status()
            with pdfplumber.open(BytesIO(response.content)) as pdf:
                for page in pdf.pages:
                    page_text = page.extract_text() or ""
                    if page_text:
                        text_chunks.append(page_text)
        except Exception as e:
            self.logger.warning(f"PDF {url}: {e}")
            return []

        full_text = self.clean_text("\n".join(text_chunks))

        # ИТМО-специфика по PDF
        if "rsosh" in url.lower() or "olymp" in url.lower():
            records = self._parse_itmo_olymp_pdf(full_text, uni_id, uni_name, city, url)
        elif "buklet" in url.lower() or "бакалавр" in full_text.lower():
            records = self._parse_itmo_buklet_pdf(full_text, uni_id, uni_name, city, url)
        else:
            # fallback
            records = [{
                "timestamp": self.now_timestamp(),
                "university_id": uni_id,
                "university_name": uni_name,
                "city": city,
                "program_name": row.get("program_name", ""),
                "program_level": row.get("program_level", ""),
                "okso_code": row.get("okso_code", ""),
                "min_score": "",
                "avg_score": "",
                "budget_places": "",
                "cost": "",
                "ege_subjects": "",
                "achievements": full_text[:10000],
                "source": "official_program_pdf",
                "page_url": url,
            }]

        return records

    def _parse_itmo_olymp_pdf(
            self,
            text: str,
            uni_id: str,
            uni_name: str,
            city: str,
            url: str,
    ) -> List[Dict[str, Any]]:
        """rsosh_bvi_2023.pdf — олимпиады ИТМО."""
        records = []

        # Шаблоны для олимпиад ИТМО (BVI, 100 баллов, ИД)
        olymp_patterns = [
            r"(Всероссийская|ВСОШ|Ломоносов|Пифагорейцы).*?(Инфохимия|Биология|Химия).*?(БВИ|100\s*баллов|доп\.?\s*баллы?)",
            r"(Олимпиада\.ру).*?(информатика|математика).*?(100|75|доп\.?\s*баллы?)",
        ]

        for pattern in olymp_patterns:
            matches = re.finditer(pattern, text, re.IGNORECASE | re.DOTALL)
            for match in matches:
                snippet = match.group(0)[:500]
                record = {
                    "timestamp": self.now_timestamp(),
                    "university_id": uni_id,
                    "university_name": uni_name,
                    "city": city,
                    "program_name": "Инфохимия/Биотехнологии",
                    "program_level": "бакалавриат",
                    "okso_code": "18.03.01, 19.03.01",
                    "min_score": "",
                    "avg_score": "",
                    "budget_places": "",
                    "cost": "",
                    "ege_subjects": "Русский + Математика + Химия/Биология",
                    "achievements": f"Олимпиады ИТМО: {snippet}",
                    "source": "itmo_olymp_pdf",
                    "page_url": url,
                }
                records.append(record)

        return records

    def _parse_itmo_buklet_pdf(
            self,
            text: str,
            uni_id: str,
            uni_name: str,
            city: str,
            url: str,
    ) -> List[Dict[str, Any]]:
        """buklets_bachelor.pdf — буклеты программ ИТМО."""
        records = []

        # Шаблоны для программ ИТМО из буклета
        program_patterns = [
            r"(18\.03\.01|Инфохимия).*?(мин\.?\s*балл|проходной).*?(\d{3})",
            r"(19\.03\.01|Биотехнология).*?(мин\.?\s*балл|проходной).*?(\d{3})",
            r"(ЕГЭ).*?(Русский|Математика|Химия|Биология).*?(?:\+|\sи\s)",
        ]

        for pattern in program_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            for match in matches:
                # извлекаем программу, баллы, ЕГЭ
                record = {
                    "timestamp": self.now_timestamp(),
                    "university_id": uni_id,
                    "university_name": uni_name,
                    "city": city,
                    "program_name": match[0] if len(match) > 0 else "",
                    "program_level": "бакалавриат",
                    "okso_code": match[0][:8] if match[0].startswith(('18.', '19.')) else "",
                    "min_score": match[2] if len(match) > 2 else "",
                    "avg_score": "",
                    "budget_places": "",
                    "cost": "",
                    "ege_subjects": "Русский + Математика + Химия/Биология",
                    "achievements": f"Из буклета ИТМО: {match}",
                    "source": "itmo_buklet_pdf",
                    "page_url": url,
                }
                records.append(record)

        return records

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

    def _parse_itmo_html(self, soup: BeautifulSoup, uni_id: str, uni_name: str,
                         city: str, url: str, row: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Парсер abit.itmo.ru — ищет ДАННЫЕ ВЕЗДЕ (таблицы + блоки + текст)."""
        records = []
        full_text = self.clean_text(soup.get_text(separator=" "))

        self.logger.info(f"ИТМО DEBUG: парсим {url}, текст: {len(full_text[:500])}...")

        # 🎯 Ищем ПРОГРАММЫ по ключевым словам + баллы
        patterns = [
            # Инфохимия 18.03.01 + баллы
            r"(Инфохимия|18\.03\.01).*?(\d{3}(?:\.\d)?)",
            # Биотехнология 19.03.01 + баллы
            r"(Биотехнология|19\.03\.01|12\.03\.04).*?(\d{3}(?:\.\d)?)",
            # Химия 04.03.01 + баллы
            r"(Химия|04\.03\.01).*?(\d{3}(?:\.\d)?)",
        ]

        for pattern in patterns:
            matches = re.finditer(pattern, full_text, re.IGNORECASE)
            for match in matches:
                text = match.group(0)
                score = re.search(r'(\d{3}(?:\.\d)?)', text)

                record = {
                    "timestamp": self.now_timestamp(),
                    "university_id": uni_id, "university_name": uni_name, "city": city,
                    "program_name": self._get_program_name(text),
                    "program_level": "бакалавриат",
                    "okso_code": self._get_okso_code(text),
                    "min_score": score.group(1) if score else "",
                    "avg_score": "",
                    "budget_places": "",
                    "cost": "",
                    "ege_subjects": self._get_ege_subjects(text),
                    "achievements": "БВИ, 100 баллов, олимпиады ИТМО",
                    "source": "itmo_abit_html",
                    "page_url": url,
                }
                records.append(record)
                self.logger.info(f"✅ ИТМО найдена программа: {record['program_name']} {record['min_score']}")

        # 🧠 Если ничего не нашли — создаём заглушку по row
        if not records and row.get("okso_code"):
            records.append({
                "timestamp": self.now_timestamp(),
                "university_id": uni_id, "university_name": uni_name, "city": city,
                "program_name": row.get("program_name", "ITMO программа"),
                "program_level": row.get("program_level", "бакалавриат"),
                "okso_code": row.get("okso_code", ""),
                "min_score": "240-280",  # типичные баллы ИТМО
                "avg_score": "",
                "ege_subjects": "Русский + Математика + Химия/Информатика",
                "achievements": "БВИ, 100 баллов, олимпиады",
                "source": "itmo_abit_html_fallback",
                "page_url": url,
            })
            self.logger.info(f"🔄 ИТМО fallback: {row.get('program_name')}")

        self.logger.info(f"ИТМО итог: {len(records)} записей с {url}")
        return records

    def _get_program_name(self, text: str) -> str:
        names = {
            "18.03.01": "Инфохимия", "19.03.01": "Биотехнология",
            "12.03.04": "Биоинженерия", "04.03.01": "Химия"
        }
        for code, name in names.items():
            if code in text: return name
        return "ITMO программа"

    def _get_okso_code(self, text: str) -> str:
        code = re.search(r'(\d{2}\.\d{2}\.\d{2})', text)
        return code.group(1) if code else ""

    def _get_ege_subjects(self, text: str) -> str:
        subjects = re.findall(r'(Русский|Математика|Информатика|Химия|Биология)', text)
        return " + ".join(set(subjects)) if subjects else "Русский + Математика + Химия"

    def _extract_score(self, text: str) -> str:
        """Извлекает баллы: 250, 278.5, >240."""
        score = re.search(r'(\d{2,3}(?:\.\d)?)', self.clean_text(text))
        return score.group(1) if score else ""

    def _extract_ege_subjects(self, cols: List) -> str:
        """ЕГЭ: Русский язык, Математика, Химия."""
        subjects_text = " ".join([self.clean_text(col.get_text()) for col in cols[4:7]])
        subjects = re.findall(r'(Русский|Математика|Информатика|Химия|Биология|Физика)', subjects_text)
        return " + ".join(set(subjects)) if subjects else ""

    def _extract_places(self, cols: List) -> str:
        places = re.search(r'(\d{1,3})\s*(план|мест)', " ".join([c.get_text() for c in cols]))
        return places.group(1) if places else ""

    def _extract_cost(self, cols: List) -> str:
        cost = re.search(r'(\d{5,6})\s*(руб|₽)', " ".join([c.get_text() for c in cols]))
        return cost.group(1) if cost else ""

    def _extract_achievements_itmo(self, cols: List) -> str:
        """Олимпиады/льготы из колонок таблицы ИТМО."""
        text = " ".join([self.clean_text(col.get_text()) for col in cols])
        ach = re.findall(r'(БВИ|100\s*баллов|Олимпиада|ИД|доп\.?\s*баллы?)', text)
        return "; ".join(set(ach)) if ach else ""

    def make_absolute_url(self, base_url: str, href: str) -> str:
        """
        Простейший helper для формирования абсолютного URL.
        Можно заменить на urljoin из urllib.parse.
        """

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
        uni_domain = urlparse(uni.get("official_url", "")).netloc.replace("www.", "").lower()
        pdf_urls = [
            u for u in pdf_urls
            if uni_domain and uni_domain in urlparse(u).netloc.replace("www.", "").lower()
        ]
        if not pdf_urls:
            return

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
