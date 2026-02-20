import unittest
from unittest.mock import patch

from scrapers.base_scraper import BaseScraper
from scrapers.postupi_scraper import PostupiScraper
from scrapers.olymp_scraper import OlympScraper


class DummyScraper(BaseScraper):
    """Тестовый скрапер для проверки базового функционала."""

    def scrape(self):
        return []


class TestScrapers(unittest.TestCase):
    def test_base_scraper_timestamp_format(self):
        scraper = DummyScraper("Dummy")
        ts = scraper.now_timestamp()
        # Простейшая проверка формата YYYY-MM-DD HH:MM:SS
        self.assertEqual(len(ts), 19)
        self.assertEqual(ts[4], "-")
        self.assertEqual(ts[7], "-")
        self.assertEqual(ts[10], " ")

    @patch.object(PostupiScraper, "get_page", return_value=None)
    def test_postupi_scraper_handles_no_page(self, mock_get_page):
        scraper = PostupiScraper()
        records = scraper.scrape()
        # Если страницы не загрузились, метод всё равно должен вернуть список
        self.assertIsInstance(records, list)

    @patch.object(OlympScraper, "get_page", return_value=None)
    def test_olymp_scraper_handles_no_page(self, mock_get_page):
        scraper = OlympScraper()
        records = scraper.scrape()
        self.assertIsInstance(records, list)


if __name__ == "__main__":
    unittest.main()
