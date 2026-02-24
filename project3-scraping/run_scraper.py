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
from scrapers.olymp_scraper import OlympBenefitsScraper
from scrapers.official_site_scraper import OfficialSiteScraper



def main() -> None:
    print("🚀 Запуск скрапера вузов и олимпиад...")

    uni_records_postupi = []
    uni_records_official = []

    # Скрапер Поступить Онлайн (программы)
    try:
        postupi = PostupiScraper()
        uni_records_postupi = postupi.scrape()
        print(f"✅ PostupiScraper: {len(uni_records_postupi)} записей")
    except Exception as e:
        print(f"❌ Ошибка в PostupiScraper: {e}")

    # Скрапер официальных сайтов (HTML + PDF)
    try:
        official = OfficialSiteScraper()
        uni_records_official = official.scrape()
        print(f"✅ OfficialSiteScraper: {len(uni_records_official)} записей")
    except Exception as e:
        print(f"❌ Ошибка в OfficialSiteScraper: {e}")

    olymp_records_olimpiada = []
    olymp_records_benefits = []

    # Скрапер льгот по olymp_all.csv (PDF + HTML)
    try:
        benefits_scraper = OlympBenefitsScraper()
        olymp_records_benefits = benefits_scraper.scrape()
        print(
            f"✅ OlympBenefitsScraper (olymp_all.csv): "
            f"{len(olymp_records_benefits)} записей"
        )
    except Exception as e:
        print(f"❌ Ошибка в OlympBenefitsScraper: {e}")

    total_uni = len(uni_records_postupi) + len(uni_records_official)
    total_olymp = len(olymp_records_benefits)


    print("🏁 Скрапинг завершён.")
    print(f"   Вузовских записей: {total_uni}")
    print(f"   Олимпиадных записей: {total_olymp}")


if __name__ == "__main__":
    main()
