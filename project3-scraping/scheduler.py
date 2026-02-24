"""
scheduler.py — Единый планировщик всех задач проекта.

Управляет:
 - периодическим запуском скраперов
 - очисткой CSV после каждой сессии
 - бэкапами перед каждым запуском
 - ротацией бэкапов (хранить N последних)
 - логированием всего цикла

Запуск:
    python scheduler.py                    # фоновый режим, по расписанию
    python scheduler.py --once             # один прогон и выход
    python scheduler.py --dry-run          # показать план без выполнения
"""

import argparse
import logging
import shutil
import sys
import time
from datetime import datetime
from pathlib import Path

from config import (
    UNIVERSITIES,
    PROGRAMS_CSV_PATH,
    OLYMPIADS_CSV_PATH,
    RAW_UNIVERSITIES_CSV,
    RAW_OLYMPIADS_CSV,
    PARTNERS_JSON,
)

# ============================================================
#  Настройки расписания (можно вынести в config.py)
# ============================================================

SCHEDULE = {
    # Полный прогон всех скраперов
    "full_scrape": {
        "cron_hour": 2,          # запуск в 2:00
        "cron_minute": 0,
        "interval_hours": 24,    # каждые 24 часа
    },
    # Быстрый прогон: только olimpiada.ru + официальные сайты
    "quick_scrape": {
        "cron_hour": 14,         # запуск в 14:00
        "cron_minute": 0,
        "interval_hours": 24,
    },
    # Очистка CSV (после каждого скрапинга запускается автоматически,
    # но можно и отдельно по расписанию)
    "cleanup": {
        "cron_hour": 3,
        "cron_minute": 30,
        "interval_hours": 24,
    },
}

# Бэкапы
BACKUP_DIR = Path("data/backups")
MAX_BACKUPS = 14  # хранить 14 последних бэкапов (~2 недели)

# Файлы, которые нужно бэкапить
BACKUP_TARGETS = [
    PROGRAMS_CSV_PATH,       # urls_for_parsers_all.csv
    OLYMPIADS_CSV_PATH,      # olymp_all.csv
    RAW_UNIVERSITIES_CSV,    # raw_universities.csv
    RAW_OLYMPIADS_CSV,       # raw_olympiads.csv
    PARTNERS_JSON,           # partners.json
]

# ============================================================
#  Логирование
# ============================================================

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("data/scheduler.log", encoding="utf-8"),
    ],
)
logger = logging.getLogger("Scheduler")


# ============================================================
#  Бэкапы
# ============================================================

def make_backup(label: str = "auto") -> Path | None:
    """
    Создать бэкап всех ключевых файлов.
    Возвращает путь к папке бэкапа.
    """
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_subdir = BACKUP_DIR / f"{ts}_{label}"
    backup_subdir.mkdir(parents=True, exist_ok=True)

    backed_up = 0
    for filepath_str in BACKUP_TARGETS:
        src = Path(filepath_str)
        if src.exists():
            dst = backup_subdir / src.name
            shutil.copy2(src, dst)
            backed_up += 1

    if backed_up == 0:
        logger.warning("Нет файлов для бэкапа")
        backup_subdir.rmdir()
        return None

    logger.info(f"Бэкап создан: {backup_subdir.name} ({backed_up} файлов)")
    return backup_subdir


def rotate_backups() -> None:
    """Удалить старые бэкапы, оставить MAX_BACKUPS последних."""
    if not BACKUP_DIR.exists():
        return
    dirs = sorted(
        [d for d in BACKUP_DIR.iterdir() if d.is_dir()],
        key=lambda d: d.name,
        reverse=True,
    )
    for old_dir in dirs[MAX_BACKUPS:]:
        shutil.rmtree(old_dir)
        logger.info(f"Удалён старый бэкап: {old_dir.name}")


# ============================================================
#  Задачи скрапинга
# ============================================================

def run_full_scrape() -> dict:
    """
    Полный прогон: все скраперы → очистка → бэкап.
    Возвращает статистику.
    """
    stats = {"started": datetime.now().isoformat(), "scrapers": {}}

    # 0. Бэкап ДО начала
    make_backup(label="pre_full")

    # 1. Импортируем скраперы (ленивый импорт — чтобы scheduler
    #    мог запуститься даже если какой-то скрапер сломан)
    scrapers_to_run = [
        ("OlympBenefitsScraper", "scrapers.olymp_scraper", "OlympBenefitsScraper"),
        ("OfficialSiteScraper", "scrapers.official_site_scraper", "OfficialSiteScraper"),
        ("PostupiScraper", "scrapers.postupi_scraper", "PostupiScraper"),
    ]

    for name, module_path, class_name in scrapers_to_run:
        try:
            import importlib
            module = importlib.import_module(module_path)
            scraper_cls = getattr(module, class_name)
            scraper = scraper_cls()

            logger.info(f"▶ Запуск {name}...")
            t0 = time.time()
            records = scraper.scrape()
            elapsed = time.time() - t0

            stats["scrapers"][name] = {
                "records": len(records) if records else 0,
                "elapsed_sec": round(elapsed, 1),
                "status": "ok",
            }
            logger.info(
                f"✅ {name}: {len(records) if records else 0} записей "
                f"за {elapsed:.1f} сек"
            )

        except Exception as e:
            logger.error(f"❌ {name}: {e}", exc_info=True)
            stats["scrapers"][name] = {
                "records": 0,
                "elapsed_sec": 0,
                "status": f"error: {e}",
            }

    # 2. Очистка CSV
    try:
        from utils.csv_cleaner import CSVCleaner
        cleaner = CSVCleaner()
        clean_stats = cleaner.run()
        stats["cleanup"] = clean_stats
        logger.info(f"🧹 Очистка завершена: {clean_stats}")
    except Exception as e:
        logger.error(f"❌ CSVCleaner: {e}", exc_info=True)
        stats["cleanup"] = {"error": str(e)}

    # 3. Бэкап ПОСЛЕ завершения (чистые данные)
    make_backup(label="post_full")
    rotate_backups()

    stats["finished"] = datetime.now().isoformat()
    logger.info(f"Полный прогон завершён: {stats}")
    return stats


def run_quick_scrape() -> dict:
    """
    Быстрый прогон: только olymp + official (без postupi).
    """
    stats = {"started": datetime.now().isoformat(), "scrapers": {}}

    make_backup(label="pre_quick")

    scrapers_to_run = [
        ("OlympBenefitsScraper", "scrapers.olymp_scraper", "OlympBenefitsScraper"),
        ("OfficialSiteScraper", "scrapers.official_site_scraper", "OfficialSiteScraper"),
    ]

    for name, module_path, class_name in scrapers_to_run:
        try:
            import importlib
            module = importlib.import_module(module_path)
            scraper_cls = getattr(module, class_name)
            scraper = scraper_cls()

            logger.info(f"▶ Запуск {name}...")
            t0 = time.time()
            records = scraper.scrape()
            elapsed = time.time() - t0

            stats["scrapers"][name] = {
                "records": len(records) if records else 0,
                "elapsed_sec": round(elapsed, 1),
                "status": "ok",
            }
        except Exception as e:
            logger.error(f"❌ {name}: {e}", exc_info=True)
            stats["scrapers"][name] = {"status": f"error: {e}"}

    try:
        from utils.csv_cleaner import CSVCleaner
        CSVCleaner().run()
    except Exception as e:
        logger.error(f"❌ CSVCleaner: {e}", exc_info=True)

    make_backup(label="post_quick")
    rotate_backups()

    stats["finished"] = datetime.now().isoformat()
    return stats


def run_cleanup_only() -> dict:
    """Только очистка CSV + бэкап."""
    make_backup(label="pre_cleanup")
    from utils.csv_cleaner import CSVCleaner
    stats = CSVCleaner().run()
    make_backup(label="post_cleanup")
    rotate_backups()
    return stats


# ============================================================
#  Планировщик (APScheduler)
# ============================================================

def start_scheduler() -> None:
    """Запуск APScheduler в блокирующем режиме."""
    try:
        from apscheduler.schedulers.blocking import BlockingScheduler
    except ImportError:
        logger.error(
            "APScheduler не установлен. Установите: pip install apscheduler"
        )
        sys.exit(1)

    sched = BlockingScheduler()

    # Полный прогон — ежедневно в 2:00
    sched.add_job(
        run_full_scrape,
        trigger="cron",
        hour=SCHEDULE["full_scrape"]["cron_hour"],
        minute=SCHEDULE["full_scrape"]["cron_minute"],
        id="full_scrape",
        name="Полный прогон всех скраперов",
        misfire_grace_time=3600,   # если пропустили окно — запустить в течение часа
        max_instances=1,           # не допускать параллельных прогонов
    )

    # Быстрый прогон — ежедневно в 14:00
    sched.add_job(
        run_quick_scrape,
        trigger="cron",
        hour=SCHEDULE["quick_scrape"]["cron_hour"],
        minute=SCHEDULE["quick_scrape"]["cron_minute"],
        id="quick_scrape",
        name="Быстрый прогон (olymp + official)",
        misfire_grace_time=3600,
        max_instances=1,
    )

    # Резервная очистка — ежедневно в 3:30 (на случай если cleanup
    # внутри скрапера не отработал)
    sched.add_job(
        run_cleanup_only,
        trigger="cron",
        hour=SCHEDULE["cleanup"]["cron_hour"],
        minute=SCHEDULE["cleanup"]["cron_minute"],
        id="cleanup",
        name="Резервная очистка CSV",
        misfire_grace_time=3600,
        max_instances=1,
    )

    logger.info("=" * 50)
    logger.info("Scheduler запущен. Расписание:")
    for job in sched.get_jobs():
        logger.info(f"  {job.id}: {job.name} — {job.trigger}")
    logger.info("=" * 50)

    try:
        sched.start()
    except (KeyboardInterrupt, SystemExit):
        logger.info("Scheduler остановлен")


# ============================================================
#  CLI
# ============================================================

def main():
    parser = argparse.ArgumentParser(description="Scheduler для скраперов")
    parser.add_argument(
        "--once", action="store_true",
        help="Запустить полный прогон один раз и выйти",
    )
    parser.add_argument(
        "--quick", action="store_true",
        help="Запустить быстрый прогон один раз и выйти",
    )
    parser.add_argument(
        "--cleanup", action="store_true",
        help="Запустить только очистку CSV",
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Показать расписание без запуска",
    )
    args = parser.parse_args()

    if args.dry_run:
        logger.info("DRY RUN — показ расписания:")
        for task, conf in SCHEDULE.items():
            logger.info(f"  {task}: каждые {conf['interval_hours']}ч, "
                        f"в {conf['cron_hour']:02d}:{conf['cron_minute']:02d}")
        logger.info(f"  Бэкапы: {BACKUP_DIR}, хранить {MAX_BACKUPS} последних")
        logger.info(f"  Файлы для бэкапа: {len(BACKUP_TARGETS)}")
        return

    if args.once:
        run_full_scrape()
        return

    if args.quick:
        run_quick_scrape()
        return

    if args.cleanup:
        run_cleanup_only()
        return

    # По умолчанию: запуск планировщика
    start_scheduler()


if __name__ == "__main__":
    main()
