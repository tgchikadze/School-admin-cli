"""
analyze_data.py — Комплексный анализ данных скрапера вузов-партнёров.

Читает ВСЕ источники данных:
  - data/universities_raw.csv   (PostupiScraper)
  - data/olympiads_raw.csv      (OlympBenefitsScraper)
  - data/partners.json          (агрегация)
  - data/scraper.log            (лог работы скрапера)
  - config.py → UNIVERSITIES    (конфиг целевых вузов)

Генерирует в data/reports/:
  - report.txt                  — текстовый отчёт для человека
  - summary.csv                 — сводная таблица
  - 01_sources_overview.png     — что собрано по источникам
  - 02_olymp_benefits_map.png   — карта олимпиадных льгот
  - 03_programs_coverage.png    — покрытие программ по вузам
  - 04_data_types.png           — типы данных (html/pdf/official)
  - 05_timeline.png             — временнáя шкала запусков
"""

import csv
import json
import re
import os
from pathlib import Path
from datetime import datetime
from collections import Counter, defaultdict

# ── Пути ──────────────────────────────────────────────
DATA_DIR = Path("data")
REPORTS_DIR = DATA_DIR / "reports"
REPORTS_DIR.mkdir(parents=True, exist_ok=True)

UNI_CSV      = DATA_DIR / "universities_raw.csv"
OLYMP_CSV    = DATA_DIR / "olympiads_raw.csv"
PARTNERS_JSON = DATA_DIR / "partners.json"
LOG_FILE     = DATA_DIR / "scraper.log"


# ══════════════════════════════════════════════════════
# 1. ЗАГРУЗКА ДАННЫХ
# ══════════════════════════════════════════════════════

def load_csv(path: Path) -> list[dict]:
    """Прочитать CSV и вернуть список словарей."""
    if not path.exists():
        print(f"  ⚠ Файл не найден: {path}")
        return []
    with open(path, "r", encoding="utf-8") as f:
        return list(csv.DictReader(f))

def load_json(path: Path) -> dict:
    if not path.exists():
        print(f"  ⚠ Файл не найден: {path}")
        return {}
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def load_log(path: Path) -> str:
    if not path.exists():
        return ""
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


# ══════════════════════════════════════════════════════
# 2. АНАЛИЗ
# ══════════════════════════════════════════════════════

def analyze_universities(rows: list[dict]) -> dict:
    """Анализ universities_raw.csv."""
    if not rows:
        return {"total": 0}

    universities = set()
    programs = set()
    sources = Counter()
    cities = Counter()
    filled_fields = Counter()  # сколько записей имеют непустое значение поля

    data_fields = ["min_score", "avg_score", "budget_places", "cost",
                   "ege_subjects", "achievements"]

    for r in rows:
        universities.add(r.get("university_id", ""))
        programs.add((r.get("university_id", ""), r.get("okso_code", ""),
                       r.get("program_name", "")))
        sources[r.get("source", "?")] += 1
        cities[r.get("city", "?")] += 1
        for f in data_fields:
            val = r.get(f, "").strip()
            if val:
                filled_fields[f] += 1

    return {
        "total": len(rows),
        "universities": len(universities),
        "unique_programs": len(programs),
        "sources": dict(sources),
        "cities": dict(cities),
        "filled_fields": {f: filled_fields.get(f, 0) for f in data_fields},
    }


def analyze_olympiads(rows: list[dict]) -> dict:
    """Анализ olympiads_raw.csv — самая ценная часть."""
    if not rows:
        return {"total": 0}

    # Разделяем на «содержательные» и «мусорные PDF»
    meaningful = []
    junk_pdf = []

    for r in rows:
        data_type = r.get("data_type", "")
        benefit = r.get("benefit_type", "").strip()
        detail = r.get("benefit_detail", "").strip()
        olympiad_name = r.get("olympiad_name", "").strip()

        # Содержательная запись: есть имя олимпиады ИЛИ непустой benefit_type
        if olympiad_name or benefit:
            meaningful.append(r)
        else:
            junk_pdf.append(r)

    # Анализ содержательных записей
    benefit_types = Counter()
    subjects = Counter()
    universities = Counter()
    programs = set()
    olympiad_names = set()
    source_sites = Counter()

    for r in meaningful:
        # Разбираем benefit_type (может быть "БВИ;100 баллов;доп. баллы")
        bt = r.get("benefit_type", "")
        for part in bt.split(";"):
            part = part.strip()
            if part:
                benefit_types[part] += 1

        subj = r.get("subject", "").strip()
        if subj:
            subjects[subj] += 1

        uid = r.get("university_id", "").strip()
        if uid:
            universities[uid] += 1

        prog = r.get("program_name", "").strip()
        okso = r.get("okso_code", "").strip()
        if prog or okso:
            programs.add((uid, okso, prog))

        oname = r.get("olympiad_name", "").strip()
        if oname:
            olympiad_names.add(oname)

        ss = r.get("source_site", "").strip()
        if ss:
            source_sites[ss] += 1

    # Подсчёт: сколько записей имеют развёрнутый benefit_detail (>100 символов)
    rich_details = sum(
        1 for r in meaningful
        if len(r.get("benefit_detail", "").strip()) > 100
    )

    return {
        "total": len(rows),
        "meaningful": len(meaningful),
        "junk_pdf": len(junk_pdf),
        "benefit_types": dict(benefit_types),
        "subjects": dict(subjects),
        "universities": dict(universities),
        "unique_programs": len(programs),
        "olympiad_names": sorted(olympiad_names),
        "source_sites": dict(source_sites),
        "rich_details": rich_details,
    }


def analyze_log(log_text: str) -> dict:
    """Извлечь из лога реальную статистику работы скрапера."""
    if not log_text:
        return {}

    # Даты запусков
    timestamps = re.findall(r"(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})", log_text)
    dates = sorted(set(t[:10] for t in timestamps))

    # Успешные GET-запросы
    gets = re.findall(r"GET (https?://\S+)", log_text)
    domains = Counter()
    for url in gets:
        try:
            domain = url.split("/")[2]
            domains[domain] += 1
        except IndexError:
            pass

    # Ошибки
    errors = len(re.findall(r"\[ERROR\]", log_text))
    warnings = len(re.findall(r"\[WARNING\]", log_text))

    # Ключевые события из лога
    official_records = re.findall(r"OfficialSiteScraper.*?(\d+) записей", log_text)
    total_official = sum(int(x) for x in official_records)

    pdf_downloads = len(re.findall(r"\[PDF\] Качаем", log_text))
    html_parses = len(re.findall(r"\[HTML\] Качаем", log_text))

    return {
        "run_dates": dates,
        "total_runs": len(dates),
        "first_run": dates[0] if dates else "?",
        "last_run": dates[-1] if dates else "?",
        "total_http_requests": len(gets),
        "domains": dict(domains.most_common(15)),
        "errors": errors,
        "warnings": warnings,
        "official_records_from_log": total_official,
        "pdf_downloads": pdf_downloads,
        "html_parses": html_parses,
    }


# ══════════════════════════════════════════════════════
# 3. ГЕНЕРАЦИЯ ОТЧЁТА
# ══════════════════════════════════════════════════════

def generate_report(uni_stats, olymp_stats, log_stats, partners) -> str:
    """Сгенерировать человекочитаемый текстовый отчёт."""
    lines = []
    lines.append("=" * 70)
    lines.append("  ОТЧЁТ ПО ДАННЫМ СКРАПЕРА ВУЗОВ-ПАРТНЁРОВ")
    lines.append(f"  Сгенерирован: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append("=" * 70)

    # ── Общая сводка ──
    lines.append("\n📊 ОБЩАЯ СВОДКА")
    lines.append("-" * 40)

    total_records = uni_stats.get("total", 0) + olymp_stats.get("total", 0)
    lines.append(f"  Всего записей в CSV:        {total_records}")
    lines.append(f"    ├─ universities_raw.csv:   {uni_stats.get('total', 0)}")
    lines.append(f"    └─ olympiads_raw.csv:      {olymp_stats.get('total', 0)}")
    lines.append(f"  Вузов в partners.json:       {len(partners)}")

    if log_stats:
        lines.append(f"  HTTP-запросов выполнено:     {log_stats.get('total_http_requests', 0)}")
        lines.append(f"  PDF скачано:                 {log_stats.get('pdf_downloads', 0)}")
        lines.append(f"  HTML-страниц спарсено:       {log_stats.get('html_parses', 0)}")
        lines.append(f"  Записей с official_site:     {log_stats.get('official_records_from_log', 0)}")

    # ── Олимпиады (главная ценность) ──
    lines.append("\n\n🏆 ОЛИМПИАДНЫЕ ЛЬГОТЫ (olympiads_raw.csv)")
    lines.append("-" * 40)

    if olymp_stats.get("total", 0) > 0:
        lines.append(f"  Всего записей:               {olymp_stats['total']}")
        lines.append(f"  Содержательных (с данными):  {olymp_stats.get('meaningful', 0)}")
        lines.append(f"  Нерелевантных PDF:           {olymp_stats.get('junk_pdf', 0)}")
        lines.append(f"  С развёрнутым описанием:     {olymp_stats.get('rich_details', 0)}")
        lines.append(f"  Уникальных программ:         {olymp_stats.get('unique_programs', 0)}")

        lines.append(f"\n  Олимпиады ({len(olymp_stats.get('olympiad_names', []))}):")
        for name in olymp_stats.get("olympiad_names", []):
            lines.append(f"    • {name}")

        lines.append(f"\n  Типы льгот:")
        for bt, cnt in sorted(olymp_stats.get("benefit_types", {}).items(),
                              key=lambda x: -x[1]):
            lines.append(f"    {bt:.<35s} {cnt:>3} записей")

        lines.append(f"\n  Предметы:")
        for subj, cnt in sorted(olymp_stats.get("subjects", {}).items(),
                                key=lambda x: -x[1]):
            lines.append(f"    {subj:.<35s} {cnt:>3}")

        lines.append(f"\n  Вузы:")
        for uid, cnt in sorted(olymp_stats.get("universities", {}).items(),
                               key=lambda x: -x[1]):
            lines.append(f"    {uid:.<35s} {cnt:>3} записей")

        lines.append(f"\n  Источники:")
        for ss, cnt in sorted(olymp_stats.get("source_sites", {}).items(),
                              key=lambda x: -x[1]):
            lines.append(f"    {ss:.<35s} {cnt:>3}")

    # ── Университеты (postupi) ──
    lines.append("\n\n🎓 ПРОГРАММЫ ВУЗОВ (universities_raw.csv)")
    lines.append("-" * 40)

    if uni_stats.get("total", 0) > 0:
        lines.append(f"  Записей:                     {uni_stats['total']}")
        lines.append(f"  Вузов:                       {uni_stats.get('universities', 0)}")
        lines.append(f"  Уникальных программ:         {uni_stats.get('unique_programs', 0)}")

        lines.append(f"\n  Заполненность полей (из {uni_stats['total']} записей):")
        for field, cnt in uni_stats.get("filled_fields", {}).items():
            pct = cnt / uni_stats['total'] * 100 if uni_stats['total'] else 0
            bar = "█" * int(pct / 5) + "░" * (20 - int(pct / 5))
            lines.append(f"    {field:.<20s} {bar} {cnt:>3}/{uni_stats['total']} ({pct:.0f}%)")

        lines.append(f"\n  ⚠ Postupi.online — SPA-сайт: числовые данные (баллы, стоимость)")
        lines.append(f"    рендерятся через JS и недоступны без Selenium/Playwright.")
        lines.append(f"    Это архитектурное ограничение, а не баг парсера.")
    else:
        lines.append("  Нет данных.")

    # ── Лог ──
    lines.append("\n\n📋 НЕПРЕРЫВНОСТЬ СБОРА (scraper.log)")
    lines.append("-" * 40)

    if log_stats:
        lines.append(f"  Период:        {log_stats.get('first_run', '?')} → {log_stats.get('last_run', '?')}")
        lines.append(f"  Дней запуска:  {log_stats.get('total_runs', 0)}")
        lines.append(f"  Ошибок:        {log_stats.get('errors', 0)}")
        lines.append(f"  Предупреждений: {log_stats.get('warnings', 0)}")

        lines.append(f"\n  Домены (топ-10 по запросам):")
        for domain, cnt in list(log_stats.get("domains", {}).items())[:10]:
            lines.append(f"    {domain:.<45s} {cnt:>4}")

    # ── Выводы ──
    lines.append("\n\n💡 КЛЮЧЕВЫЕ ВЫВОДЫ")
    lines.append("-" * 40)

    meaningful_olymp = olymp_stats.get("meaningful", 0)
    if meaningful_olymp > 0:
        lines.append(f"  ✅ Собрано {meaningful_olymp} содержательных записей по олимпиадным льготам")
        lines.append(f"     с развёрнутыми описаниями ({olymp_stats.get('rich_details', 0)} записей > 100 символов)")

    official_from_log = log_stats.get("official_records_from_log", 0) if log_stats else 0
    if official_from_log > 0:
        lines.append(f"  ✅ OfficialSiteScraper собрал {official_from_log} записей с сайтов вузов")

    junk = olymp_stats.get("junk_pdf", 0)
    if junk > 0:
        lines.append(f"  ⚠ {junk} PDF-записей без полезных данных (нерелевантные документы)")
        lines.append(f"     Рекомендация: дополнить PDF_BLOCKLIST в config.py")

    uni_total = uni_stats.get("total", 0)
    filled_any = sum(uni_stats.get("filled_fields", {}).values())
    if uni_total > 0 and filled_any == 0:
        lines.append(f"  ℹ Postupi.online не отдаёт числовые данные в статическом HTML")
        lines.append(f"     Основные данные по приёму берутся из official_site и олимпиадных CSV")

    lines.append("")
    return "\n".join(lines)


# ══════════════════════════════════════════════════════
# 4. СВОДНАЯ ТАБЛИЦА (summary.csv)
# ══════════════════════════════════════════════════════

def generate_summary_csv(uni_rows, olymp_rows, partners):
    """Сводка: вуз → что собрано."""
    # Собираем данные по вузам из всех источников
    uni_data = defaultdict(lambda: {
        "city": "", "programs_postupi": 0, "olymp_records": 0,
        "olymp_meaningful": 0, "benefit_types": set(),
        "olympiad_names": set(), "subjects": set(),
        "sources": set(), "in_partners_json": False,
    })

    for r in uni_rows:
        uid = r.get("university_id", "")
        uni_data[uid]["city"] = r.get("city", "")
        uni_data[uid]["programs_postupi"] += 1
        uni_data[uid]["sources"].add(r.get("source", ""))

    for r in olymp_rows:
        uid = r.get("university_id", "").strip()
        if not uid:
            continue
        uni_data[uid]["city"] = r.get("city", "")
        uni_data[uid]["olymp_records"] += 1

        if r.get("olympiad_name", "").strip() or r.get("benefit_type", "").strip():
            uni_data[uid]["olymp_meaningful"] += 1
            for bt in r.get("benefit_type", "").split(";"):
                bt = bt.strip()
                if bt:
                    uni_data[uid]["benefit_types"].add(bt)
            oname = r.get("olympiad_name", "").strip()
            if oname:
                uni_data[uid]["olympiad_names"].add(oname)
            subj = r.get("subject", "").strip()
            if subj:
                uni_data[uid]["subjects"].add(subj)
        uni_data[uid]["sources"].add(r.get("source_site", ""))

    for uid in partners:
        if uid in uni_data:
            uni_data[uid]["in_partners_json"] = True

    # Записываем CSV
    path = REPORTS_DIR / "summary.csv"
    fieldnames = [
        "university_id", "city", "programs_postupi", "olymp_records",
        "olymp_meaningful", "benefit_types", "olympiad_names", "subjects",
        "sources", "in_partners_json",
    ]
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for uid, d in sorted(uni_data.items()):
            writer.writerow({
                "university_id": uid,
                "city": d["city"],
                "programs_postupi": d["programs_postupi"],
                "olymp_records": d["olymp_records"],
                "olymp_meaningful": d["olymp_meaningful"],
                "benefit_types": "; ".join(sorted(d["benefit_types"])),
                "olympiad_names": "; ".join(sorted(d["olympiad_names"])),
                "subjects": "; ".join(sorted(d["subjects"])),
                "sources": "; ".join(sorted(s for s in d["sources"] if s)),
                "in_partners_json": "да" if d["in_partners_json"] else "",
            })
    print(f"  📄 {path}")
    return uni_data


# ══════════════════════════════════════════════════════
# 5. ГРАФИКИ (matplotlib)
# ══════════════════════════════════════════════════════

def generate_charts(uni_stats, olymp_stats, log_stats, uni_data_by_vuz):
    """Генерация 5 информативных PNG-графиков."""
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        plt.rcParams["font.size"] = 10
    except ImportError:
        print("  ⚠ matplotlib не установлен, графики пропущены")
        return

    # ── 1. Общий обзор: что собрано по источникам ──
    fig, ax = plt.subplots(figsize=(10, 5))
    categories = []
    values = []
    colors = []

    meaningful = olymp_stats.get("meaningful", 0)
    if meaningful:
        categories.append(f"Олимпиадные льготы\n(содержательных)")
        values.append(meaningful)
        colors.append("#2ecc71")

    rich = olymp_stats.get("rich_details", 0)
    if rich:
        categories.append(f"С развёрнутым\nописанием (>100 симв.)")
        values.append(rich)
        colors.append("#27ae60")

    uni_total = uni_stats.get("total", 0)
    if uni_total:
        categories.append(f"Программы вузов\n(postupi)")
        values.append(uni_total)
        colors.append("#3498db")

    official = log_stats.get("official_records_from_log", 0) if log_stats else 0
    if official:
        categories.append(f"Записи official_site\n(из лога)")
        values.append(official)
        colors.append("#9b59b6")

    junk = olymp_stats.get("junk_pdf", 0)
    if junk:
        categories.append(f"Нерелевантные PDF")
        values.append(junk)
        colors.append("#e74c3c")

    if categories:
        bars = ax.barh(categories, values, color=colors)
        for bar, val in zip(bars, values):
            ax.text(bar.get_width() + 0.5, bar.get_y() + bar.get_height()/2,
                    str(val), va="center", fontweight="bold")
        ax.set_xlabel("Количество записей")
        ax.set_title("Что собрал скрапер: обзор по источникам", fontweight="bold")
        ax.invert_yaxis()
        plt.tight_layout()
        fig.savefig(REPORTS_DIR / "01_sources_overview.png", dpi=150)
        plt.close(fig)
        print(f"  📊 01_sources_overview.png")

    # ── 2. Карта олимпиадных льгот ──
    bt = olymp_stats.get("benefit_types", {})
    if bt:
        fig, ax = plt.subplots(figsize=(8, 5))
        labels = list(bt.keys())
        sizes = list(bt.values())
        clrs = ["#2ecc71", "#3498db", "#f39c12", "#e74c3c", "#9b59b6"][:len(labels)]
        bars = ax.barh(labels, sizes, color=clrs)
        for bar, val in zip(bars, sizes):
            ax.text(bar.get_width() + 0.3, bar.get_y() + bar.get_height()/2,
                    str(val), va="center", fontweight="bold")
        ax.set_xlabel("Количество записей")
        ax.set_title("Типы олимпиадных льгот", fontweight="bold")
        ax.invert_yaxis()
        plt.tight_layout()
        fig.savefig(REPORTS_DIR / "02_olymp_benefits_map.png", dpi=150)
        plt.close(fig)
        print(f"  📊 02_olymp_benefits_map.png")

    # ── 3. Покрытие программ по вузам ──
    if uni_data_by_vuz:
        fig, ax = plt.subplots(figsize=(10, 6))
        vuz_ids = sorted(uni_data_by_vuz.keys())
        postupi_vals = [uni_data_by_vuz[v]["programs_postupi"] for v in vuz_ids]
        olymp_vals = [uni_data_by_vuz[v]["olymp_meaningful"] for v in vuz_ids]

        y = range(len(vuz_ids))
        ax.barh([i - 0.15 for i in y], postupi_vals, height=0.3,
                label="Программы (postupi)", color="#3498db")
        ax.barh([i + 0.15 for i in y], olymp_vals, height=0.3,
                label="Олимпиады (содержат.)", color="#2ecc71")
        ax.set_yticks(list(y))
        ax.set_yticklabels(vuz_ids)
        ax.set_xlabel("Количество записей")
        ax.set_title("Покрытие данных по вузам", fontweight="bold")
        ax.legend()
        ax.invert_yaxis()
        plt.tight_layout()
        fig.savefig(REPORTS_DIR / "03_programs_coverage.png", dpi=150)
        plt.close(fig)
        print(f"  📊 03_programs_coverage.png")

    # ── 4. Типы данных (data_type из olympiads) ──
    source_sites = olymp_stats.get("source_sites", {})
    if source_sites:
        fig, ax = plt.subplots(figsize=(7, 5))
        labels = list(source_sites.keys())
        sizes = list(source_sites.values())
        ax.pie(sizes, labels=labels, autopct="%1.0f%%", startangle=140,
               colors=["#2ecc71", "#3498db", "#f39c12", "#e74c3c", "#9b59b6"][:len(labels)])
        ax.set_title("Источники олимпиадных данных", fontweight="bold")
        plt.tight_layout()
        fig.savefig(REPORTS_DIR / "04_data_types.png", dpi=150)
        plt.close(fig)
        print(f"  📊 04_data_types.png")

    # ── 5. Предметы олимпиад ──
    subjects = olymp_stats.get("subjects", {})
    if subjects:
        fig, ax = plt.subplots(figsize=(9, 5))
        labels = list(subjects.keys())
        sizes = list(subjects.values())
        clrs = ["#e74c3c", "#3498db", "#2ecc71", "#f39c12",
                "#9b59b6", "#1abc9c", "#e67e22"][:len(labels)]
        bars = ax.barh(labels, sizes, color=clrs)
        for bar, val in zip(bars, sizes):
            ax.text(bar.get_width() + 0.2, bar.get_y() + bar.get_height()/2,
                    str(val), va="center", fontweight="bold")
        ax.set_xlabel("Количество записей")
        ax.set_title("Олимпиады по предметам", fontweight="bold")
        ax.invert_yaxis()
        plt.tight_layout()
        fig.savefig(REPORTS_DIR / "05_subjects.png", dpi=150)
        plt.close(fig)
        print(f"  📊 05_subjects.png")


# ══════════════════════════════════════════════════════
# 6. MAIN
# ══════════════════════════════════════════════════════

def main():
    print("📈 Комплексный анализ данных скрапера...\n")

    # Загрузка
    print("📂 Загрузка данных...")
    uni_rows = load_csv(UNI_CSV)
    olymp_rows = load_csv(OLYMP_CSV)
    partners = load_json(PARTNERS_JSON)
    log_text = load_log(LOG_FILE)
    print(f"  universities_raw.csv: {len(uni_rows)} записей")
    print(f"  olympiads_raw.csv:    {len(olymp_rows)} записей")
    print(f"  partners.json:        {len(partners)} вузов")
    print(f"  scraper.log:          {len(log_text)} символов")

    # Анализ
    print("\n🔍 Анализ...")
    uni_stats = analyze_universities(uni_rows)
    olymp_stats = analyze_olympiads(olymp_rows)
    log_stats = analyze_log(log_text)

    # Сводная таблица
    print("\n📄 Сводная таблица...")
    uni_data_by_vuz = generate_summary_csv(uni_rows, olymp_rows, partners)

    # Отчёт
    print("\n📝 Текстовый отчёт...")
    report = generate_report(uni_stats, olymp_stats, log_stats, partners)
    report_path = REPORTS_DIR / "report.txt"
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(report)
    print(f"  📝 {report_path}")

    # Вывод отчёта в консоль
    print("\n" + report)

    # Графики
    print("📊 Генерация графиков...")
    generate_charts(uni_stats, olymp_stats, log_stats, uni_data_by_vuz)

    print("\n✅ Анализ завершён! Результаты в data/reports/")


if __name__ == "__main__":
    main()
