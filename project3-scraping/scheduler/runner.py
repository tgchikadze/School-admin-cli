"""
Планировщик непрерывного скрапинга (имитация непрерывного процесса).

Использование:
    python -m scheduler.runner

Запускает скрапер каждые N часов (указано в SCRAPER_SETTINGS['schedule_interval_hours']).
Для проверки на защите достаточно запустить один раз, убедиться,
что появляются новые строки в CSV и обновляется partners.json.
"""

import time

import schedule

from scrapers.postupi_scraper import PostupiScraper
from scrapers.olymp_scraper import OlympScraper
from config import SCRAPER_SETTINGS


def job() -> None:
    print("⏱ Запуск очередного цикла скрапинга...")
    postupi = PostupiScraper()
    olymp   = OlympScraper()

    postupi.scrape()
    olymp.scrape()
    print("✅ Цикл скрапинга завершён.")


def main() -> None:
    interval = SCRAPER_SETTINGS.get("schedule_interval_hours", 6)
    print(f"🚀 Планировщик запущен. Интервал: каждые {interval} ч.")

    # Для тестов можно временно поменять на minutes=1
    schedule.every(interval).hours.do(job)
    # schedule.every(1).minutes.do(job)  # для быстрого теста

    job()  # первый запуск сразу

    while True:
        schedule.run_pending()
        time.sleep(1)


if __name__ == "__main__":
    main()
