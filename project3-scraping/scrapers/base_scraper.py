"""
Базовый класс скрапера.
Общая логика: сессия requests, заголовки, задержки, повторные попытки,
логирование. Все конкретные парсеры наследуются от BaseScraper.
"""

import logging
import time
from abc import ABC, abstractmethod
from datetime import datetime
from pathlib import Path

import requests
from bs4 import BeautifulSoup

from config import SCRAPER_SETTINGS

# ==========================
# Настройка логирования
# ==========================

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("data/scraper.log", encoding="utf-8"),
    ],
)


class BaseScraper(ABC):
    """
    Базовый класс для всех скраперов проекта.

    Предоставляет:
    - HTTP-сессию с заголовками и таймаутом
    - Метод get_page() с повторными попытками и задержками
    - Метод parse() — точка входа, реализуется в подклассах
    - Логирование всех операций
    """

    def __init__(self, name: str) -> None:
        """
        Параметры:
            name: Имя скрапера для логов (например, 'PostupiScraper')
        """

        self.name = name
        self.logger = logging.getLogger(name)

        self.session = requests.Session()
        self.session.max_redirects = 30
        self.session.headers.update({
            "User-Agent": SCRAPER_SETTINGS["user_agent"],
            "Accept-Language": "ru-RU,ru;q=0.9,en;q=0.8",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        })


        self._delay = SCRAPER_SETTINGS["request_delay_sec"]
        self._timeout = SCRAPER_SETTINGS["request_timeout_sec"]
        self._max_retries = SCRAPER_SETTINGS["max_retries"]

        # Создать папку data/ если нет (нужна для лога)
        Path("data").mkdir(exist_ok=True)

    # ==========================
    # HTTP-запрос
    # ==========================

    def get_page(self, url: str) -> BeautifulSoup | None:
        """
        Загрузить страницу по URL и вернуть BeautifulSoup-объект.
        Повторяет запрос до max_retries раз при ошибке.
        Делает паузу между запросами согласно SCRAPER_SETTINGS.

        Параметры:
            url: Полный URL страницы

        Возвращает:
            BeautifulSoup | None: Разобранный HTML или None при ошибке
        """
        for attempt in range(1, self._max_retries + 1):
            try:
                self.logger.info(f"GET {url} (попытка {attempt})")
                response = self.session.get(url, timeout=self._timeout)
                response.raise_for_status()
                time.sleep(self._delay)
                return BeautifulSoup(response.text, "html.parser")
            except requests.TooManyRedirects:
                self.session = requests.Session()
                self.session.headers.update({
                    "User-Agent": SCRAPER_SETTINGS["user_agent"],
                    "Accept-Language": "ru-RU,ru;q=0.9,en;q=0.8",
                    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                })
                self.logger.error(f"TooManyRedirects — сессия сброшена, пропускаем: {url}")
                return None
            except requests.exceptions.HTTPError as e:
                self.logger.warning(f"HTTP ошибка {e} — {url}")
            except requests.exceptions.ConnectionError:
                self.logger.warning(f"Нет соединения — {url}")
            except requests.exceptions.Timeout:
                self.logger.warning(f"Таймаут — {url}")
            except requests.exceptions.RequestException as e:
                self.logger.error(f"Неизвестная ошибка запроса: {e}")

            if attempt < self._max_retries:
                wait = self._delay * attempt
                self.logger.info(f"Повтор через {wait} сек...")
                time.sleep(wait)

        self.logger.error(f"Не удалось загрузить страницу после {self._max_retries} попыток: {url}")
        return None

    # ==========================
    # Утилиты
    # ==========================

    @staticmethod
    def clean_text(text: str | None) -> str:
        """Очистить текст от лишних пробелов и переносов строк."""
        if not text:
            return ""
        return " ".join(text.strip().split())

    @staticmethod
    def now_timestamp() -> str:
        """Вернуть текущее время в формате ISO для записи в CSV."""
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # ==========================
    # Точка входа (в подклассах)
    # ==========================

    @abstractmethod
    def scrape(self) -> list[dict]:
        """
        Запустить парсинг и вернуть список словарей с данными.
        Реализуется в каждом конкретном скрапере.
        """
        ...
