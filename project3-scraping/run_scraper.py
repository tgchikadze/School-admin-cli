"""
Точка входа для запуска скрапера (ТЗ проекта 3).

Использование:
    python run_scraper.py

Запускает:
- PostupiScraper        — собирает баллы, стоимость, предметы ЕГЭ
- OlympScraper          — собирает олимпиады и льготы с olimpiada.ru
- OlympBenefitsScraper  — парсит льготы по olymp_all.csv (PDF + HTML)
"""
from scrapers.postupi_scraper import PostupiScraper
from scrapers.olymp_scraper import OlympScraper, OlympBenefitsScraper


def main() -> None:
    print("🚀 Запуск скрапера вузов и олимпиад...")

    uni_records = []
    olymp_records_olimpiada = []
    olymp_records_benefits = []

    # Скрапер Поступить Онлайн (программы)
    try:
        postupi = PostupiScraper()
        uni_records = postupi.scrape()
        print(f"✅ PostupiScraper: {len(uni_records)} записей")
    except Exception as e:
        print(f"❌ Ошибка в PostupiScraper: {e}")

    # Скрапер олимпиад с olimpiada.ru
    try:
        olymp = OlympScraper()
        olymp_records_olimpiada = olymp.scrape()
        print(f"✅ OlympScraper (olimpiada.ru): {len(olymp_records_olimpiada)} записей")
    except Exception as e:
        print(f"❌ Ошибка в OlympScraper: {e}")

    # Скрапер льгот по olymp_all.csv (PDF + HTML)
    try:
        benefits_scraper = OlympBenefitsScraper()
        olymp_records_benefits = benefits_scraper.scrape()
        print(
            f"✅ OlympBenefitsScraper (olymp_all.csv): "
            f"{len(olymp_records_benefits)} записей"
        )
    except Exception as e:
        print(f"❌ OlympBenefitsScraper: {e}")

    total_olymp = len(olymp_records_olimpiada) + len(olymp_records_benefits)

    print("🏁 Скрапинг завершён.")
    print(f"   Вузовских записей: {len(uni_records)}")
    print(f"   Олимпиадных записей: {total_olymp}")


if __name__ == "__main__":
    main()
