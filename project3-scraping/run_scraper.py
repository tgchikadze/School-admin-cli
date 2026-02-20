"""
Точка входа для запуска скрапера (требование ТЗ проекта 3).

Использование:
    python run_scraper.py

Запускает:
- PostupiScraper — собирает баллы, стоимость, предметы ЕГЭ
- OlympScraper   — собирает олимпиады и льготы
"""

from scrapers.postupi_scraper import PostupiScraper
from scrapers.olymp_scraper import OlympScraper


def main() -> None:
    print("🚀 Запуск скрапера вузов и олимпиад...")
    postupi = PostupiScraper()
    olymp   = OlympScraper()

    uni_records   = postupi.scrape()
    olymp_records = olymp.scrape()

    print(f"✅ Скрапинг завершён.")
    print(f"   Вузовских записей: {len(uni_records)}")
    print(f"   Олимпиадных записей: {len(olymp_records)}")


if __name__ == "__main__":
    main()
