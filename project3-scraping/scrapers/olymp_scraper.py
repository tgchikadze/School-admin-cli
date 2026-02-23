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
from pathlib import Path

import pandas as pd

from config import (
    UNIVERSITIES,
    RAW_OLYMPIADS_CSV,
    PARTNERS_JSON,
    OLYMPIADS_CSV_PATH,
    PROGRAMS_CSV_PATH,  # NEW
)


from scrapers.base_scraper import BaseScraper


# Предметы ЕГЭ, релевантные для наших направлений
TARGET_SUBJECTS = [
    "математика",
    "информатика",
    "химия",
    "биология",
    "физика",
    "русский язык",
    "английский язык",
]

# Slug-маппинг вузов на olimpiada.ru (для _scrape_achievements)
UNI_SLUGS_OLIMPIADA = {
    "spbgu": "spbgu",
    "itmo": "itmo",
    "spbpu": "spbpolitech",
    "hse_msk": "hse",     # ВШЭ Москва
    "hse_spb": "hse-spb", # при необходимости поправишь
    "msu": "mgu",
    "mipt": "mfti",
    "szgmu": "szgmu",     # СЗГМУ им. Мечникова
    "pavlov": "1spbgmu",
    "spbgpmu": "spbgpmu",
    "nsu": "nsu",
    "sphu": "sphfa",
    "herzen": "herzen",
    "spbau": "spbau",
    "sechenov": "sechenov",
    "rosbiotech": "rgau-msha",
}


class OlympScraper(BaseScraper):
    """
    Парсер страниц олимпиад и льгот с olimpiada.ru.

    Вместо жёсткого списка TARGET_OLYMPIAD_IDS использует olymp_all.csv:
    для каждой строки, где source_site == "olimpiada" и active == 1,
    парсит страницу льгот и берёт только релевантные вузы/льготы.
    """

    BASE_URL = "https://olimpiada.ru"

    def __init__(self) -> None:
        super().__init__("OlympScraper")

        # Множество id наших вузов для фильтрации
        self._our_uni_ids = {uni["id"] for uni in UNIVERSITIES}

        # Загружаем конфиг олимпиад из CSV
        self._targets_df = self._load_targets_from_csv()

        self._programs_df = pd.read_csv(PROGRAMS_CSV_PATH)

    # ==========================
    # Загрузка целей из CSV
    # ==========================

    def _load_targets_from_csv(self) -> pd.DataFrame:
        df = pd.read_csv(OLYMPIADS_CSV_PATH)

        if "active" in df.columns:
            df = df[df["active"] == 1]

        df = df[df["source_site"] == "olimpiada"]

        # отбрасываем заведомо мёртвые домены
        bad_domains = ["olimpiada.msu.ru"]
        mask_bad = df["olympiad_url"].str.contains("|".join(bad_domains), na=False)
        df = df[~mask_bad]

        self.logger.info(
            f"CSV-цели олимпиад загружены: {len(df)} строк для olimpiada.ru"
        )
        return df

    # ==========================
    # Основной метод
    # ==========================

    def scrape(self) -> list[dict]:
        """
        Координатор: проходит по строкам olymp_all.csv и
        отправляет каждую строку в подходящий обработчик.
        """
        all_records: list[dict] = []
        timestamp = self.now_timestamp()

        for _, row in self._targets_df.iterrows():
            url = row["olympiad_url"]
            source = row["source_site"]
            ctype = row.get("content_type", "html")

            self.logger.info(
                f"OlympScraper: обрабатываем {row['university_id']} "
                f"({row['okso_code']} {row['program_name']}) — {url} "
                f"[source={source}, content_type={ctype}]"
            )

            # PDF-документы с льготами/ИД
            if ctype == "pdf":
                records = self._parse_pdf_benefits(row, timestamp)

            # HTML-страницы: делим по типу источника/домену
            elif ctype == "html":
                if source == "official_program":
                    records = self._parse_official_html(row, timestamp)
                elif source == "olimpiada":
                    records = self._parse_olympiada_html(row, timestamp)
                else:
                    records = []
            else:
                records = []

            all_records.extend(records)

        # Индивидуальные достижения (если оставляем)
        achievements = self._scrape_achievements()
        all_records.extend(achievements)

        self._save_csv(all_records)
        self._update_partners_json(all_records)
        return all_records

    # ==========================
    # Парсинг одной страницы олимпиады
    # ==========================

    def _scrape_olympiad_page(
        self,
        url: str,
        target_university_id: str,
        okso_code: str,
        program_name: str,
        benefit_relevance: str,
        subject_hint: str,
        timestamp: str,
    ) -> list[dict]:
        """
        Спарсить страницу олимпиады/профиля на olimpiada.ru и собрать льготы
        для конкретного вуза и направления (okso_code, program_name).

        Параметры:
            url: URL страницы льгот на olimpiada.ru
            target_university_id: id вуза из config/CSV
            okso_code: код направления подготовки
            program_name: название программы
            benefit_relevance: 'bvi;ege_100;id_points' и т.п.
            subject_hint: предмет из CSV (если есть)
            timestamp: общая метка времени запуска
        """
        soup = self.get_page(url)
        if soup is None:
            return []

        records: list[dict] = []

        olymp_name = self._extract_olympiad_name(soup)
        olymp_level = self._extract_olympiad_level(soup)
        olymp_subject = subject_hint or self._extract_olympiad_subject(soup)

        # Фильтруем по профилю — берём только релевантные предметы
        if olymp_subject and not self._is_target_subject(olymp_subject):
            self.logger.info(
                f" Пропускаем олимпиаду по предмету '{olymp_subject}' — не в целевых"
            )
            return []

        # Таблица льгот: вуз → вид льготы
        benefits_table = (
            soup.find("table", class_="benefits_table")
            or soup.find("table", class_="vuz-benefits")
            or soup.find("div", class_="benefits-list")
        )
        if not benefits_table:
            self.logger.warning(f"Не найдена таблица льгот на странице {url}")
            return []

        rows = benefits_table.find_all("tr")[1:]  # пропускаем заголовок

        for row in rows:
            cells = row.find_all(["td", "th"])
            if len(cells) < 2:
                continue

            uni_name_raw = self.clean_text(cells[0].get_text())
            benefit_raw = self.clean_text(cells[1].get_text()) if len(cells) > 1 else ""
            profiles_raw = (
                self.clean_text(cells[2].get_text()) if len(cells) > 2 else ""
            )

            # Сопоставляем вуз по названию
            matched_uni = self._match_university(uni_name_raw)
            if not matched_uni:
                continue

            # Нас интересует только конкретный вуз из CSV
            if matched_uni["id"] != target_university_id:
                continue

            # Формируем запись
            records.append(
                {
                    "timestamp": timestamp,
                    "data_type": "olympiad",
                    "olympiad_id": "",  # при желании можно вытащить из URL
                    "olympiad_name": olymp_name,
                    "olympiad_level": olymp_level,
                    "subject": olymp_subject,
                    "university_id": matched_uni["id"],
                    "university_name": matched_uni["short_name"],
                    "city": matched_uni["city"],
                    "okso_code": okso_code,
                    "program_name": program_name,
                    "benefit_relevance": benefit_relevance,
                    "benefit_type": self._classify_benefit(benefit_raw),
                    "benefit_detail": benefit_raw,
                    "profiles": profiles_raw,
                }
            )

        return records

    # ==========================
    # Парсинг индивидуальных достижений (100 баллов)
    # ==========================

    def _scrape_achievements(self) -> list[dict]:
        """
        Спарсить страницы вузов/программ на предмет индивидуальных достижений
        (за что дают 100 баллов и доп. баллы).

        Берём URL из PROGRAMS_CSV_PATH, а не с olimpiada.ru/vuz/{slug}/.
        """
        records: list[dict] = []
        timestamp = self.now_timestamp()

        df = self._programs_df

        # только активные строки
        if "active" in df.columns:
            df = df[df["active"] == 1]

        # эвристика: ищем строки, где в notes упоминаются ИД / 100 баллов
        mask_id = df["notes"].str.contains(
            "ИД|индивидуальн|100 балл", case=False, na=False
        )
        df = df[mask_id].copy()
        if df.empty:
            return records

        # группируем по вузу, чтобы не дёргать по десятку страниц на каждый
        for uid, df_uni in df.groupby("university_id"):
            uni = next((u for u in UNIVERSITIES if u["id"] == uid), None)
            if not uni:
                continue

            # берём одну характерную страницу, где описаны ИД
            row = df_uni.iloc[0]
            url = row.get("program_detail_url") or row.get("programs_page_url")
            if not url:
                continue

            self.logger.info(f"Парсим ИД для {uid} из {url}")

            soup = self.get_page(url)
            if soup is None:
                continue

            achievements = self._extract_achievements_from_page(soup)
            score_100 = self._extract_score_100(soup)

            if achievements or score_100:
                records.append(
                    {
                        "timestamp": timestamp,
                        "data_type": "achievement",
                        "olympiad_id": "",
                        "olympiad_name": "",
                        "olympiad_level": "",
                        "subject": "",
                        "university_id": uid,
                        "university_name": uni["short_name"],
                        "city": uni["city"],
                        "benefit_type": "individual_achievement",
                        "benefit_detail": achievements,
                        "profiles": score_100,
                        "page_url": url,
                    }
                )

        return records

    # ==========================
    # Извлечение полей
    # ==========================

    def _extract_olympiad_name(self, soup) -> str:
        """Извлечь название олимпиады."""
        from bs4 import BeautifulSoup  # тип подсказки

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
            ("div", {"class": "olymp-level"}),
            ("td", {"class": "level"}),
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
            ("td", {"class": "subject"}),
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
            ("td", {"class": "ball100"}),
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
        subj_lower = (subject or "").lower()
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

            entry = {
                "olympiad_name": r["olympiad_name"],
                "olympiad_level": r["olympiad_level"],
                "subject": r["subject"],
                "benefit_type": r["benefit_type"],
                "benefit_detail": r["benefit_detail"],
                "profiles": r["profiles"],
                "okso_code": r.get("okso_code", ""),
                "program_name": r.get("program_name", ""),
                "benefit_relevance": r.get("benefit_relevance", ""),
                "updated_at": r["timestamp"],
            }

            existing_names = [o["olympiad_name"] for o in data[uid]["olympiads"]]
            if entry["olympiad_name"] not in existing_names:
                data[uid]["olympiads"].append(entry)

        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        self.logger.info(f"💾 partners.json обновлён олимпиадами: {path}")

    def _parse_official_html(self, row, timestamp: str) -> list[dict]:
        """
        Страницы приёмных комиссий вузов (official_program, HTML).
        Пока заглушка: просто логируем, что нужно реализовать парсер.
        """
        url = row["olympiad_url"]
        uni_id = row["university_id"]

        self.logger.info(
            f"OlympScraper: [TODO official_html] {uni_id} — {url}"
        )

        # TODO: здесь позже будет выбор стратегии по uni_id (msu, mipt, itmo, ...)

        return []

    def _parse_olympiada_html(self, row, timestamp: str) -> list[dict]:
        """
        Страницы с олимпиадами (olimpiada): могут быть как olimpiada.ru,
        так и страницы вузов/агрегаторов.
        Пока заглушка.
        """
        url = row["olympiad_url"]
        uni_id = row["university_id"]

        self.logger.info(
            f"OlympScraper: [TODO olimpiada_html] {uni_id} — {url}"
        )

        # TODO: позже — отдельные стратегии под olimpiada.ru, olymp.mipt.ru, olimpiada.spbu.ru и т.п.

        return []

    def _parse_pdf_benefits(self, row, timestamp: str) -> list[dict]:
        """
        PDF-документы с льготами. Пока только логируем факт наличия PDF.
        """
        url = row["olympiad_url"]
        uni_id = row["university_id"]

        self.logger.info(
            f"OlympScraper: [TODO pdf] {uni_id} — {url}"
        )

        # TODO: позже подключим pdfplumber / PyMuPDF и сделаем простой текстовый парсер

        return []
# =========================================
# Парсер льгот по olymp_all.csv (PDF + HTML)
# =========================================

import io
from typing import Any

import pdfplumber
import pandas as pd
import requests

from config import OLYMPIADS_CSV_PATH


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


