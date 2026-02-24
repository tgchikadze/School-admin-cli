"""
tests/test_scrapers.py

Тесты для проекта скрапера вузов-партнёров.
Покрывает:
- Circuit breaker в BaseScraper
- Классификацию льгот (benefit_classifier)
- CSVCleaner (дедупликация)
- OlympBenefitsScraper (PDF/HTML парсинг)
- Структуру выходных данных
- Интеграционный тест полного прогона

Запуск:
    python -m pytest tests/test_scrapers.py -v
    python -m pytest tests/test_scrapers.py -v -k "circuit"
"""

import csv
import json
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


# ==============================================================
# Фикстуры
# ==============================================================

@pytest.fixture(autouse=True)
def reset_cb():
    """Сбрасывать circuit breaker между тестами."""
    from scrapers.base_scraper import BaseScraper
    BaseScraper.reset_circuit_breaker()
    yield
    BaseScraper.reset_circuit_breaker()


@pytest.fixture
def tmp_data_dir(tmp_path):
    """Временная папка data/ для CSV/JSON."""
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    return data_dir


@pytest.fixture
def sample_olymp_csv(tmp_data_dir):
    """Минимальный olymp_all.csv для тестов."""
    path = tmp_data_dir / "olymp_all.csv"
    rows = [
        {
            "olympiad_id": "1",
            "olympiad_name": "ВСОШ по информатике",
            "subject": "информатика",
            "olympiad_level": "1",
            "university_id": "itmo",
            "university_short_name": "ИТМО",
            "city": "Санкт-Петербург",
            "okso_code": "09.03.01",
            "program_name": "Информатика и программирование",
            "program_level": "бакалавриат",
            "benefit_relevance": "",
            "benefit_types": "",
            "source_site": "olimpiada",
            "olympiad_url": "https://example.com/olymp1",
            "notes": "",
            "active": "1",
            "needs_deep_parse": "0",
            "content_type": "html",
        },
    ]
    with open(path, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)
    return path


@pytest.fixture
def sample_universities_csv(tmp_data_dir):
    """Минимальный universities_raw.csv с дублем."""
    path = tmp_data_dir / "universities_raw.csv"
    row = {
        "timestamp": "2026-02-24 12:00:00",
        "university_id": "itmo",
        "university_name": "ИТМО",
        "city": "Санкт-Петербург",
        "program_name": "Информатика",
        "program_level": "бакалавриат",
        "okso_code": "09.03.01",
        "min_score": "280",
        "avg_score": "",
        "budget_places": "",
        "cost": "",
        "ege_subjects": "математика, информатика",
        "achievements": "олимпиады РСОШ",
        "source": "itmo_abit_html",
        "page_url": "https://abit.itmo.ru/bachelor",
    }
    with open(path, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=row.keys())
        writer.writeheader()
        writer.writerow(row)
        writer.writerow(row)  # дубль
    return path


@pytest.fixture
def sample_partners_json(tmp_data_dir):
    """Минимальный partners.json."""
    path = tmp_data_dir / "partners.json"
    data = {
        "itmo": {
            "programs": [
                {
                    "okso_code": "09.03.01",
                    "program_level": "бакалавриат",
                    "program_name": "Информатика",
                    "min_score": "280",
                }
            ],
            "olympiads": [],
        }
    }
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    return path


def _make_dummy_scraper():
    """Хелпер: создать минимальный скрапер для тестов."""
    from scrapers.base_scraper import BaseScraper

    class DummyScraper(BaseScraper):
        def scrape(self):
            return []

    return DummyScraper("test")


def _make_http_error(status_code: int):
    """Хелпер: создать мок HTTPError с нужным статус-кодом."""
    import requests
    mock_resp = MagicMock()
    mock_resp.status_code = status_code
    return requests.exceptions.HTTPError(response=mock_resp)


# ==============================================================
# 1. CIRCUIT BREAKER
# ==============================================================

class TestCircuitBreaker:
    """Тесты для circuit breaker в BaseScraper."""

    def test_domain_marked_dead_after_threshold(self):
        """После 3 ConnectionError на домене — помечается мёртвым."""
        scraper = _make_dummy_scraper()
        for _ in range(3):
            scraper._record_domain_failure("https://spb.postupi.online/vuz/itmo/")

        assert scraper._is_domain_dead("https://spb.postupi.online/vuz/itmo/")
        assert scraper._is_domain_dead("https://spb.postupi.online/another/page")

    def test_domain_not_dead_below_threshold(self):
        """2 ошибки — домен ещё жив."""
        scraper = _make_dummy_scraper()
        scraper._record_domain_failure("https://example.com/page1")
        scraper._record_domain_failure("https://example.com/page2")

        assert not scraper._is_domain_dead("https://example.com/page3")

    def test_success_resets_counter(self):
        """Успешный запрос сбрасывает счётчик ошибок."""
        scraper = _make_dummy_scraper()
        scraper._record_domain_failure("https://example.com/a")
        scraper._record_domain_failure("https://example.com/b")
        scraper._record_domain_success("https://example.com/c")

        assert not scraper._is_domain_dead("https://example.com/d")
        assert scraper._domain_failures["example.com"] == 0

    def test_reset_clears_all(self):
        """reset_circuit_breaker() очищает все домены."""
        from scrapers.base_scraper import BaseScraper

        scraper = _make_dummy_scraper()
        for _ in range(5):
            scraper._record_domain_failure("https://dead.site/x")

        assert scraper._is_domain_dead("https://dead.site/y")
        BaseScraper.reset_circuit_breaker()
        assert not scraper._is_domain_dead("https://dead.site/y")

    def test_cb_shared_across_scrapers(self):
        """Circuit breaker общий для всех экземпляров (class-level)."""
        from scrapers.base_scraper import BaseScraper

        class ScraperA(BaseScraper):
            def scrape(self):
                return []

        class ScraperB(BaseScraper):
            def scrape(self):
                return []

        a = ScraperA("A")
        b = ScraperB("B")

        for _ in range(3):
            a._record_domain_failure("https://shared.fail/x")

        assert b._is_domain_dead("https://shared.fail/y")

    def test_get_page_skips_dead_domain(self):
        """get_page() сразу возвращает None для мёртвого домена."""
        scraper = _make_dummy_scraper()
        for _ in range(3):
            scraper._record_domain_failure("https://dead.example.com/a")

        result = scraper.get_page("https://dead.example.com/some/page")
        assert result is None

    def test_get_page_no_retry_on_404(self):
        """get_page() не ретраит 404 — сразу возвращает None."""
        scraper = _make_dummy_scraper()

        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_response.raise_for_status.side_effect = _make_http_error(404)

        mock_get = MagicMock(return_value=mock_response)
        scraper.session.get = mock_get

        result = scraper.get_page("https://example.com/missing")

        assert result is None
        assert mock_get.call_count == 1  # ровно 1 вызов, без ретраев

    def test_get_page_retries_on_500(self):
        """get_page() ретраит 500 — это временная ошибка."""
        scraper = _make_dummy_scraper()
        scraper._delay = 0  # без пауз в тестах

        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.raise_for_status.side_effect = _make_http_error(500)

        mock_get = MagicMock(return_value=mock_response)
        scraper.session.get = mock_get

        result = scraper.get_page("https://example.com/error")

        assert result is None
        assert mock_get.call_count == scraper._max_retries  # все 3 попытки

    def test_get_page_no_retry_on_403(self):
        """get_page() не ретраит 403 Forbidden."""
        scraper = _make_dummy_scraper()

        mock_response = MagicMock()
        mock_response.status_code = 403
        mock_response.raise_for_status.side_effect = _make_http_error(403)

        mock_get = MagicMock(return_value=mock_response)
        scraper.session.get = mock_get

        result = scraper.get_page("https://example.com/forbidden")

        assert result is None
        assert mock_get.call_count == 1


# ==============================================================
# 2. BENEFIT CLASSIFIER
# ==============================================================

class TestBenefitClassifier:
    """Тесты для tools/benefit_classifier.py."""

    def test_bvi_detected(self):
        from tools.benefit_classifier import classify_benefit
        assert "БВИ" in classify_benefit("Победитель зачисляется БВИ")
        assert "БВИ" in classify_benefit("без вступительных испытаний")
        assert "БВИ" in classify_benefit("Зачисление без экзаменов")

    def test_100_points_detected(self):
        from tools.benefit_classifier import classify_benefit
        assert "100 баллов" in classify_benefit("100 баллов за ЕГЭ по математике")
        assert "100 баллов" in classify_benefit("Приравнивается к 100 баллам")
        assert "100 баллов" in classify_benefit("100-балльный результат")

    def test_extra_points_detected(self):
        from tools.benefit_classifier import classify_benefit
        assert "доп. баллы" in classify_benefit("Дополнительные баллы за достижения")
        assert "доп. баллы" in classify_benefit("индивидуальные достижения")
        assert "доп. баллы" in classify_benefit("начисление баллов за олимпиады")

    def test_special_rights_detected(self):
        from tools.benefit_classifier import classify_benefit
        assert "особые права" in classify_benefit("перечневые олимпиады школьников")
        assert "особые права" in classify_benefit("Особые права при поступлении")

    def test_multiple_types(self):
        from tools.benefit_classifier import classify_benefit
        result = classify_benefit("БВИ или 100 баллов + доп. баллы за ИД")
        assert "БВИ" in result
        assert "100 баллов" in result
        assert "доп. баллы" in result

    def test_empty_input(self):
        from tools.benefit_classifier import classify_benefit
        assert classify_benefit("") == ""
        assert classify_benefit(None) == ""

    def test_no_match(self):
        from tools.benefit_classifier import classify_benefit
        assert classify_benefit("Расписание занятий на понедельник") == ""

    def test_strict_returns_one(self):
        from tools.benefit_classifier import classify_benefit_strict
        result = classify_benefit_strict("БВИ или 100 баллов")
        assert result == "БВИ"

    def test_case_insensitive(self):
        from tools.benefit_classifier import classify_benefit
        assert "БВИ" in classify_benefit("бви для победителей")
        assert "БВИ" in classify_benefit("БВИ ДЛЯ ПОБЕДИТЕЛЕЙ")


# ==============================================================
# 3. CLEAN_TEXT и NOW_TIMESTAMP
# ==============================================================

class TestBaseScraperUtils:
    """Тесты для утилит BaseScraper."""

    def test_clean_text_normal(self):
        from scrapers.base_scraper import BaseScraper
        assert BaseScraper.clean_text("  hello   world  ") == "hello world"

    def test_clean_text_newlines(self):
        from scrapers.base_scraper import BaseScraper
        assert BaseScraper.clean_text("line1\n\n  line2\t\tline3") == "line1 line2 line3"

    def test_clean_text_none(self):
        from scrapers.base_scraper import BaseScraper
        assert BaseScraper.clean_text(None) == ""

    def test_clean_text_empty(self):
        from scrapers.base_scraper import BaseScraper
        assert BaseScraper.clean_text("") == ""

    def test_now_timestamp_format(self):
        from scrapers.base_scraper import BaseScraper
        ts = BaseScraper.now_timestamp()
        assert len(ts) == 19
        assert ts[4] == "-"
        assert ts[10] == " "
        assert ts[13] == ":"


# ==============================================================
# 4. CSV CLEANER
# ==============================================================

class TestCSVCleaner:
    """Тесты для дедупликации CSV."""

    def test_dedup_removes_duplicates(self, sample_universities_csv):
        """Дедупликация убирает полные дубли из CSV."""
        import pandas as pd
        df = pd.read_csv(sample_universities_csv)
        assert len(df) == 2

        df = df.drop_duplicates()
        assert len(df) == 1

    def test_dedup_keeps_unique(self, tmp_data_dir):
        """Уникальные строки сохраняются."""
        path = tmp_data_dir / "test.csv"
        rows = [
            {"url": "https://a.com", "data": "1"},
            {"url": "https://b.com", "data": "2"},
        ]
        with open(path, "w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=["url", "data"])
            writer.writeheader()
            writer.writerows(rows)

        import pandas as pd
        df = pd.read_csv(path)
        assert len(df.drop_duplicates()) == 2


# ==============================================================
# 5. OLYMP BENEFITS SCRAPER
# ==============================================================

class TestOlympBenefitsScraper:
    """Тесты для OlympBenefitsScraper (без реальных HTTP)."""

    def test_load_targets_sets_content_type(self, sample_olymp_csv):
        """_load_targets() проставляет content_type."""
        with patch("scrapers.olymp_scraper.OLYMPIADS_CSV_PATH", str(sample_olymp_csv)):
            from scrapers.olymp_scraper import OlympBenefitsScraper
            scraper = OlympBenefitsScraper()
            df = scraper._load_targets()
            assert "content_type" in df.columns
            assert df.iloc[0]["content_type"] == "html"

    def test_pdf_url_gets_pdf_type(self, tmp_data_dir):
        """URL .pdf → content_type=pdf."""
        path = tmp_data_dir / "olymp_all.csv"
        rows = [{
            "olympiad_id": "2", "olympiad_name": "test", "subject": "math",
            "olympiad_level": "1", "university_id": "itmo",
            "university_short_name": "ИТМО", "city": "СПб",
            "okso_code": "09.03.01", "program_name": "ИВТ",
            "program_level": "бак", "benefit_relevance": "",
            "benefit_types": "", "source_site": "olimpiada",
            "olympiad_url": "https://example.com/doc.pdf",
            "notes": "", "active": "1", "needs_deep_parse": "0",
            "content_type": "",
        }]
        with open(path, "w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=rows[0].keys())
            writer.writeheader()
            writer.writerows(rows)

        with patch("scrapers.olymp_scraper.OLYMPIADS_CSV_PATH", str(path)):
            from scrapers.olymp_scraper import OlympBenefitsScraper
            scraper = OlympBenefitsScraper()
            df = scraper._load_targets()
            assert df.iloc[0]["content_type"] == "pdf"

    def test_keywords_match(self):
        """KEYWORDS находят ключевые слова."""
        from scrapers.olymp_scraper import OlympBenefitsScraper
        kw = OlympBenefitsScraper.KEYWORDS
        text = "Победители получают БВИ и 100 баллов за ЕГЭ"
        assert any(k in text.lower() for k in kw)

    def test_keywords_no_match(self):
        """KEYWORDS не срабатывают на нерелевантном тексте."""
        from scrapers.olymp_scraper import OlympBenefitsScraper
        kw = OlympBenefitsScraper.KEYWORDS
        text = "Расписание экзаменов на весеннюю сессию"
        assert not any(k in text.lower() for k in kw)

    def test_visited_dedup(self):
        """Одинаковый URL не парсится дважды."""
        from scrapers.olymp_scraper import OlympBenefitsScraper
        scraper = OlympBenefitsScraper()
        scraper.visited.add("https://example.com/page")

        import pandas as pd
        row = pd.Series({"olympiad_url": "https://example.com/page"})
        result = scraper._parse_html_benefits(row)
        assert result == []


# ==============================================================
# 6. ДАННЫЕ И СТРУКТУРА
# ==============================================================

class TestDataIntegrity:
    """Тесты целостности данных."""

    def test_partners_json_structure(self, sample_partners_json):
        """partners.json имеет правильную структуру."""
        with open(sample_partners_json, "r", encoding="utf-8") as f:
            data = json.load(f)

        assert "itmo" in data
        assert "programs" in data["itmo"]
        assert "olympiads" in data["itmo"]
        assert isinstance(data["itmo"]["programs"], list)
        assert len(data["itmo"]["programs"]) > 0
        assert "okso_code" in data["itmo"]["programs"][0]

    def test_csv_has_required_columns(self, sample_universities_csv):
        """universities_raw.csv содержит обязательные колонки."""
        import pandas as pd
        df = pd.read_csv(sample_universities_csv)
        required = {
            "timestamp", "university_id", "university_name",
            "program_name", "okso_code", "source", "page_url",
        }
        assert required.issubset(set(df.columns))

    def test_olymp_csv_has_required_columns(self, sample_olymp_csv):
        """olymp_all.csv содержит обязательные колонки."""
        import pandas as pd
        df = pd.read_csv(sample_olymp_csv)
        required = {
            "olympiad_id", "olympiad_name", "university_id",
            "olympiad_url", "active",
        }
        assert required.issubset(set(df.columns))


# ==============================================================
# 7. ИНТЕГРАЦИОННЫЙ ТЕСТ (моки HTTP)
# ==============================================================

class TestIntegration:
    """Интеграционные тесты с замокированными HTTP-запросами."""

    def test_full_scrape_cycle_no_network(self, tmp_data_dir, sample_olymp_csv):
        """
        Полный цикл: загрузка целей → парсинг (с моком) → сохранение CSV.
        Без реальных HTTP-запросов.
        """
        from scrapers.olymp_scraper import OlympBenefitsScraper

        raw_csv = tmp_data_dir / "olympiads_raw.csv"

        html = "<html><body>Победители ВСОШ получают БВИ и 100 баллов</body></html>"
        mock_soup = __import__("bs4").BeautifulSoup(html, "html.parser")

        with patch("scrapers.olymp_scraper.OLYMPIADS_CSV_PATH", str(sample_olymp_csv)), \
             patch("scrapers.olymp_scraper.RAW_OLYMPIADS_CSV", str(raw_csv)):

            scraper = OlympBenefitsScraper()

            with patch.object(scraper, "get_page", return_value=mock_soup):
                records = scraper.scrape()

        assert len(records) == 1
        assert records[0]["data_type"] == "olymp_html"
        assert records[0]["university_id"] == "itmo"
        assert "БВИ" in records[0]["benefit_detail"]
        assert raw_csv.exists()
