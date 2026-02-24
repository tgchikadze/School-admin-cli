"""
Базовый класс скрапера.
Общая логика: сессия requests, заголовки, задержки, повторные попытки,
логирование, circuit breaker по доменам.
Все конкретные парсеры наследуются от BaseScraper.
"""

import logging
import time
from abc import ABC, abstractmethod
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse

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
    - Circuit breaker: после N ошибок подряд на домене — skip
    - Не ретраит 404/403/410 (постоянные ошибки)
    - Логирование всех операций
    """

    # Circuit breaker: общий для ВСЕХ скраперов в одном прогоне
    _domain_failures: dict[str, int] = {}
    DOMAIN_FAIL_THRESHOLD = 3

    # HTTP-коды, которые не имеет смысла ретраить
    NO_RETRY_CODES = {403, 404, 410, 451}

    def __init__(self, name: str) -> None:
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
        Path("data").mkdir(exist_ok=True)

    # ==========================
    # Circuit Breaker
    # ==========================

    def _get_domain(self, url: str) -> str:
        """Извлечь домен из URL."""
        return urlparse(url).netloc.lower()

    def _is_domain_dead(self, url: str) -> bool:
        """Проверить, помечен ли домен как недоступный."""
        domain = self._get_domain(url)
        return self._domain_failures.get(domain, 0) >= self.DOMAIN_FAIL_THRESHOLD

    def _record_domain_failure(self, url: str) -> None:
        """Записать ошибку для домена; при пороге — залогировать circuit break."""
        domain = self._get_domain(url)
        self._domain_failures[domain] = self._domain_failures.get(domain, 0) + 1
        if self._domain_failures[domain] == self.DOMAIN_FAIL_THRESHOLD:
            self.logger.warning(
                f"⚡ Circuit breaker: домен {domain} помечен как недоступный "
                f"({self.DOMAIN_FAIL_THRESHOLD} ошибок подряд), "
                f"все дальнейшие URL на этом домене будут пропущены"
            )

    def _record_domain_success(self, url: str) -> None:
        """Сбросить счётчик ошибок при успешном запросе."""
        domain = self._get_domain(url)
        if domain in self._domain_failures:
            self._domain_failures[domain] = 0

    @classmethod
    def reset_circuit_breaker(cls) -> None:
        """Сбросить все circuit breaker'ы (между прогонами)."""
        cls._domain_failures.clear()

    # ==========================
    # HTTP-запрос
    # ==========================

    def get_page(self, url: str) -> BeautifulSoup | None:
        """
        Загрузить страницу по URL и вернуть BeautifulSoup-объект.

        Улучшения относительно предыдущей версии:
        - Circuit breaker: пропускает URL если домен помечен мёртвым
        - Не ретраит 404/403/410 — это постоянные ошибки
        - Записывает успех/ошибку для circuit breaker
        """
        # --- Circuit breaker ---
        if self._is_domain_dead(url):
            self.logger.info(f"⏭️ Пропуск {url} (домен недоступен — circuit breaker)")
            return None

        for attempt in range(1, self._max_retries + 1):
            try:
                self.logger.info(f"GET {url} (попытка {attempt})")
                response = self.session.get(url, timeout=self._timeout)
                response.raise_for_status()
                time.sleep(self._delay)
                self._record_domain_success(url)
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
                status_code = e.response.status_code if e.response is not None else 0
                self.logger.warning(f"HTTP ошибка {status_code} ({e}) — {url}")

                # Не ретраить постоянные ошибки
                if status_code in self.NO_RETRY_CODES:
                    self.logger.error(
                        f"Постоянная ошибка {status_code}, ретраи бессмысленны: {url}"
                    )
                    return None

            except requests.exceptions.ConnectionError:
                self.logger.warning(f"Нет соединения — {url}")
                self._record_domain_failure(url)

                # Проверяем CB после записи ошибки
                if self._is_domain_dead(url):
                    return None

            except requests.exceptions.Timeout:
                self.logger.warning(f"Таймаут — {url}")
                self._record_domain_failure(url)

                if self._is_domain_dead(url):
                    return None

            except requests.exceptions.RequestException as e:
                self.logger.error(f"Неизвестная ошибка запроса: {e}")

            if attempt < self._max_retries:
                wait = self._delay * attempt
                self.logger.info(f"Повтор через {wait} сек...")
                time.sleep(wait)

        self.logger.error(
            f"Не удалось загрузить страницу после {self._max_retries} попыток: {url}"
        )
        self._record_domain_failure(url)
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
        """Запустить парсинг и вернуть список словарей с данными."""
        ...
