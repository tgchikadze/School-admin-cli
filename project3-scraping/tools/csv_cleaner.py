"""
csv_cleaner.py — Универсальный чистильщик olymp_all.csv и urls_for_parsers_all.csv.

Запускается ПОСЛЕ каждой сессии скрапинга (из scheduler / run_all.py).
Идемпотентен: можно запускать многократно без побочных эффектов.

Что делает:
 1. Удаление полных дубликатов (по ключевым колонкам)
 2. Удаление строк с пустыми / битыми URL
 3. Удаление PDF из PDF_BLOCKLIST
 4. Исправление university_id по домену URL (проблема «всё записано как itmo»)
 5. Удаление строк, чей домен не принадлежит ни одному вузу из UNIVERSITIES
 6. Нормализация полей (strip пробелов, приведение active к 0/1)
 7. Удаление устаревших/нерелевантных строк (priority = -1 + notes содержит "auto discovered" + url из blocklist)
 8. Отчёт в лог: сколько строк было → стало, что удалено

Использование:
    from utils.csv_cleaner import CSVCleaner
    cleaner = CSVCleaner()
    cleaner.run()              # чистит оба CSV
    cleaner.clean_olymp()      # только olymp_all.csv
    cleaner.clean_programs()   # только urls_for_parsers_all.csv
"""

import csv
import logging
import re
from copy import deepcopy
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse

from config import (
    UNIVERSITIES,
    PROGRAMS_CSV_PATH,
    OLYMPIADS_CSV_PATH,
    PDF_BLOCKLIST,
)

logger = logging.getLogger("CSVCleaner")


# ============================================================
#  Справочник доменов вузов (строится один раз из UNIVERSITIES)
# ============================================================

def _build_domain_to_uni_map() -> dict[str, dict]:
    """
    {домен_без_www: uni_dict, ...}
    Один вуз может иметь несколько доменов (official_url, admission_url, и т.д.)
    """
    d2u: dict[str, dict] = {}
    for uni in UNIVERSITIES:
        for key in ("official_url", "admission_url", "olympiad_url"):
            raw = uni.get(key, "") or ""
            if not raw:
                continue
            domain = urlparse(raw).netloc.replace("www.", "").lower()
            if domain:
                d2u[domain] = uni
    return d2u


DOMAIN_TO_UNI = _build_domain_to_uni_map()

# Известные агрегаторы — URL на них НЕ резолвятся в вуз,
# и это нормально: их НЕ удаляем, НЕ перекрашиваем.
AGGREGATOR_DOMAINS = frozenset({
    "olimpiada.ru",
    "postupi.online",
    "ucheba.ru",
    "tabiturient.ru",
    "vuzoteka.ru",
    "gidvuz.com",
    "vuzopedia.com",
    "edunetwork.ru",
    "diplometa.ru",
    "azbukauma.ru",
    "provuz.ru",
    "abiturient-uga.ru",
    "vuzlist.com",
    "mir-vuzov.ru",
    "education.yandex.ru",
    # social
    "vk.com",
    "t.me",
})


def _is_aggregator(url: str) -> bool:
    domain = urlparse(url).netloc.replace("www.", "").lower()
    return any(agg in domain for agg in AGGREGATOR_DOMAINS)


def _resolve_uni_by_url(url: str) -> dict | None:
    """По домену URL найти вуз из UNIVERSITIES. None если не наш."""
    domain = urlparse(url).netloc.replace("www.", "").lower()
    if not domain:
        return None
    # Точное совпадение
    if domain in DOMAIN_TO_UNI:
        return DOMAIN_TO_UNI[domain]
    # Вхождение: abit.itmo.ru содержит itmo.ru
    for known_domain, uni in DOMAIN_TO_UNI.items():
        if known_domain in domain or domain in known_domain:
            return uni
    return None


def _is_blocklisted(url: str) -> bool:
    """Проверить URL по PDF_BLOCKLIST (case-insensitive)."""
    url_lower = url.lower()
    return any(b.lower() in url_lower for b in PDF_BLOCKLIST)


def _is_junk_auto_pdf(row: dict) -> bool:
    """
    Мусорные auto-discovered PDF:
    priority = -1 + notes содержит 'auto discovered' + URL в blocklist.
    """
    priority = str(row.get("priority", "")).strip()
    notes = str(row.get("notes", "")).lower()
    if priority != "-1":
        return False
    if "auto discovered" not in notes and "auto_discovered" not in notes:
        return False
    # Проверяем URL в blocklist
    for url_key in ("programs_page_url", "program_detail_url", "olympiad_url"):
        url = str(row.get(url_key, "")).strip()
        if url and _is_blocklisted(url):
            return True
    return False


# ============================================================
#  Главный класс
# ============================================================

class CSVCleaner:
    """
    Универсальный чистильщик CSV-файлов проекта.
    """

    def __init__(self, dry_run: bool = False):
        """
        dry_run=True: только считает, ничего не пишет на диск.
        """
        self.dry_run = dry_run
        self.stats: dict[str, dict] = {}

    # -------------------- Публичный API --------------------

    def run(self) -> dict[str, dict]:
        """Почистить оба CSV. Вернуть статистику."""
        self.clean_programs()
        self.clean_olymp()
        self._log_summary()
        return self.stats

    def clean_programs(self) -> None:
        """Чистка urls_for_parsers_all.csv"""
        path = Path(PROGRAMS_CSV_PATH)
        if not path.exists():
            logger.warning(f"Файл не найден: {path}")
            return
        rows = self._read_csv(path)
        before = len(rows)

        rows = self._step_strip_fields(rows)
        rows = self._step_normalize_active(rows)
        rows = self._step_remove_empty_urls(rows, url_keys=["programs_page_url", "program_detail_url"])
        rows = self._step_remove_blocklisted(rows, url_keys=["programs_page_url", "program_detail_url"])
        rows = self._step_remove_junk_auto_pdfs(rows)
        rows = self._step_fix_university_id(rows, url_keys=["programs_page_url", "program_detail_url"])
        rows = self._step_remove_foreign_auto_pdfs(rows, url_keys=["programs_page_url", "program_detail_url"])
        rows = self._step_dedup(rows, key_cols=[
            "university_id", "okso_code", "program_level",
            "programs_page_url", "program_detail_url", "source_site",
        ])

        after = len(rows)
        self.stats["urls_for_parsers_all.csv"] = {
            "before": before, "after": after, "removed": before - after,
        }
        logger.info(
            f"urls_for_parsers_all.csv: {before} → {after} "
            f"(удалено {before - after})"
        )
        if not self.dry_run:
            self._write_csv(path, rows)

    def clean_olymp(self) -> None:
        """Чистка olymp_all.csv"""
        path = Path(OLYMPIADS_CSV_PATH)
        if not path.exists():
            logger.warning(f"Файл не найден: {path}")
            return
        rows = self._read_csv(path)
        before = len(rows)

        rows = self._step_strip_fields(rows)
        rows = self._step_normalize_active(rows)
        rows = self._step_remove_empty_urls(rows, url_keys=["olympiad_url"])
        rows = self._step_remove_blocklisted(rows, url_keys=["olympiad_url"])
        rows = self._step_fix_university_id(rows, url_keys=["olympiad_url"])
        rows = self._step_remove_foreign_auto_pdfs(rows, url_keys=["olympiad_url"])
        rows = self._step_dedup(rows, key_cols=[
            "university_id", "olympiad_name", "subject",
            "okso_code", "olympiad_url",
        ])

        after = len(rows)
        self.stats["olymp_all.csv"] = {
            "before": before, "after": after, "removed": before - after,
        }
        logger.info(
            f"olymp_all.csv: {before} → {after} "
            f"(удалено {before - after})"
        )
        if not self.dry_run:
            self._write_csv(path, rows)

    # -------------------- Шаги чистки --------------------

    def _step_strip_fields(self, rows: list[dict]) -> list[dict]:
        """1. Strip пробелов во всех полях."""
        for row in rows:
            for k, v in row.items():
                if isinstance(v, str):
                    row[k] = v.strip()
        return rows

    def _step_normalize_active(self, rows: list[dict]) -> list[dict]:
        """2. Привести active к строгому 0 или 1."""
        for row in rows:
            val = str(row.get("active", "1")).strip().lower()
            row["active"] = "1" if val in ("1", "true", "yes") else "0"
        return rows

    def _step_remove_empty_urls(
        self, rows: list[dict], url_keys: list[str],
    ) -> list[dict]:
        """3. Удалить строки, где ВСЕ url_keys пустые."""
        result = []
        for row in rows:
            has_url = any(
                str(row.get(k, "")).strip()
                for k in url_keys
            )
            if has_url:
                result.append(row)
            else:
                logger.debug(f"  DEL empty-url: {row.get('university_id')} {row.get('okso_code')}")
        return result

    def _step_remove_blocklisted(
        self, rows: list[dict], url_keys: list[str],
    ) -> list[dict]:
        """4. Удалить строки, где ЛЮБОЙ url содержит PDF_BLOCKLIST слово."""
        result = []
        for row in rows:
            blocked = False
            for k in url_keys:
                url = str(row.get(k, "")).strip()
                if url and _is_blocklisted(url):
                    blocked = True
                    break
            if blocked:
                logger.debug(f"  DEL blocklist: {row.get(url_keys[0], '')[:80]}")
            else:
                result.append(row)
        return result

    def _step_remove_junk_auto_pdfs(self, rows: list[dict]) -> list[dict]:
        """5. Удалить мусорные auto-discovered PDF (priority=-1 + blocklist)."""
        result = []
        for row in rows:
            if _is_junk_auto_pdf(row):
                logger.debug(f"  DEL junk-auto: {row.get('programs_page_url', '')[:80]}")
            else:
                result.append(row)
        return result

    def _step_fix_university_id(
        self, rows: list[dict], url_keys: list[str],
    ) -> list[dict]:
        """
        6. КЛЮЧЕВОЙ ШАГ: если домен URL принадлежит другому вузу из UNIVERSITIES,
        исправить university_id / university_short_name / city.

        Не трогаем строки, где URL — агрегатор (postupi.online и т.д.),
        т.к. у них university_id задан вручную и корректен.
        """
        fixed = 0
        for row in rows:
            # Берём первый непустой URL
            url = ""
            for k in url_keys:
                url = str(row.get(k, "")).strip()
                if url:
                    break
            if not url:
                continue

            # Агрегаторы не трогаем
            if _is_aggregator(url):
                continue

            resolved = _resolve_uni_by_url(url)
            if resolved is None:
                continue  # домен не наш — разберёмся в следующем шаге

            current_id = str(row.get("university_id", "")).strip()
            resolved_id = resolved["id"]

            if current_id and current_id != resolved_id:
                logger.info(
                    f"  FIX uni_id: {current_id} → {resolved_id} "
                    f"(url: {url[:60]})"
                )
                row["university_id"] = resolved_id
                row["university_short_name"] = resolved.get("short_name", "")
                row["city"] = resolved.get("city", "")
                fixed += 1

        if fixed:
            logger.info(f"  Исправлено university_id: {fixed} строк")
        return rows

    def _step_remove_foreign_auto_pdfs(
        self, rows: list[dict], url_keys: list[str],
    ) -> list[dict]:
        """
        7. Удалить auto-discovered строки, чей домен не принадлежит
        ни одному вузу из UNIVERSITIES и не является агрегатором.

        Ручные строки (без 'auto discovered' в notes) НЕ удаляем.
        """
        result = []
        for row in rows:
            notes = str(row.get("notes", "")).lower()
            is_auto = "auto discovered" in notes or "auto_discovered" in notes

            if not is_auto:
                result.append(row)
                continue

            # Берём URL
            url = ""
            for k in url_keys:
                url = str(row.get(k, "")).strip()
                if url:
                    break

            if not url:
                result.append(row)
                continue

            if _is_aggregator(url):
                result.append(row)
                continue

            resolved = _resolve_uni_by_url(url)
            if resolved is None:
                # Домен чужой — удаляем
                logger.debug(
                    f"  DEL foreign-auto: {row.get('university_id')} "
                    f"url={url[:60]}"
                )
            else:
                result.append(row)
        return result

    def _step_dedup(
        self, rows: list[dict], key_cols: list[str],
    ) -> list[dict]:
        """8. Удалить дубликаты по составному ключу."""
        seen: set[tuple] = set()
        result = []
        for row in rows:
            key = tuple(str(row.get(c, "")).strip().lower() for c in key_cols)
            if key in seen:
                logger.debug(f"  DEL dup: {key[:3]}...")
                continue
            seen.add(key)
            result.append(row)
        return result

    # -------------------- I/O --------------------

    @staticmethod
    def _read_csv(path: Path) -> list[dict]:
        with open(path, "r", encoding="utf-8") as f:
            return list(csv.DictReader(f))

    @staticmethod
    def _write_csv(path: Path, rows: list[dict]) -> None:
        if not rows:
            logger.warning(f"Пустой результат, не перезаписываем {path}")
            return
        # Бэкап
        backup = path.with_suffix(f".bak.{datetime.now():%Y%m%d_%H%M%S}.csv")
        if path.exists():
            import shutil
            shutil.copy2(path, backup)
            logger.info(f"  Бэкап → {backup.name}")

        fieldnames = list(rows[0].keys())
        with open(path, "w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)

    def _log_summary(self) -> None:
        logger.info("=" * 50)
        logger.info("CSVCleaner — итоги:")
        for fname, st in self.stats.items():
            logger.info(
                f"  {fname}: {st['before']} → {st['after']} "
                f"(−{st['removed']})"
            )
        logger.info("=" * 50)


# ============================================================
#  CLI: python -m utils.csv_cleaner [--dry-run]
# ============================================================

if __name__ == "__main__":
    import sys
    logging.basicConfig(
        level=logging.DEBUG if "--verbose" in sys.argv else logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )
    dry = "--dry-run" in sys.argv
    if dry:
        logger.info("*** DRY RUN — файлы НЕ будут изменены ***")
    cleaner = CSVCleaner(dry_run=dry)
    stats = cleaner.run()
    print(stats)
