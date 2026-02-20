"""
Анализ данных, собранных скрапером (проект 3).

Функции:
- Загрузка CSV с сырыми данными по вузам и олимпиадам
- Построение графика минимальных баллов по вузам/направлениям
- Формирование сводной таблицы олимпиад и льгот
"""

from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd

from config import (
    RAW_UNIVERSITIES_CSV,
    RAW_OLYMPIADS_CSV,
    REPORTS_DIR,
)


def analyze_universities() -> None:
    """Анализ данных по вузам: минимальные баллы и стоимость."""
    path = Path(RAW_UNIVERSITIES_CSV)
    if not path.exists():
        print(f"⚠️ Файл не найден: {path}")
        return

    df = pd.read_csv(path)

    # Оставляем только строки с нормальными значениями баллов
    df_scores = df.copy()
    df_scores["min_score_num"] = pd.to_numeric(df_scores["min_score"], errors="coerce")
    df_scores = df_scores.dropna(subset=["min_score_num"])

    if df_scores.empty:
        print("⚠️ Нет данных с минимальными баллами для анализа")
        return

    # Группируем по вузу и направлению — берём макс. минимальный балл (по последнему запуску)
    grouped = (
        df_scores.sort_values("timestamp")
        .groupby(["university_name", "program"], as_index=False)
        .last()
    )

    # Строим график: по оси X — направления (укороченные), по Y — мин. балл
    Path(REPORTS_DIR).mkdir(parents=True, exist_ok=True)
    plt.figure(figsize=(12, 6))

    labels = grouped["university_name"] + ": " + grouped["program"].str.slice(0, 20)
    plt.bar(labels, grouped["min_score_num"])

    plt.xticks(rotation=90, fontsize=8)
    plt.ylabel("Минимальный балл ЕГЭ")
    plt.title("Минимальные проходные баллы по целевым направлениям")

    plt.tight_layout()
    chart_path = Path(REPORTS_DIR) / "min_scores_chart.png"
    plt.savefig(chart_path, dpi=150)
    plt.close()

    # Сохраняем сводную таблицу в CSV
    table_path = Path(REPORTS_DIR) / "universities_summary.csv"
    grouped.to_csv(table_path, index=False)

    print(f"📊 График сохранён: {chart_path}")
    print(f"📄 Таблица сохранена: {table_path}")


def analyze_olympiads() -> None:
    """Анализ олимпиад и льгот вузов."""
    path = Path(RAW_OLYMPIADS_CSV)
    if not path.exists():
        print(f"⚠️ Файл не найден: {path}")
        return

    df = pd.read_csv(path)

    if df.empty:
        print("⚠️ Нет данных олимпиад для анализа")
        return

    # Фильтруем только записи с типом 'olympiad'
    df_ol = df[df["data_type"] == "olympiad"].copy()

    if df_ol.empty:
        print("⚠️ Нет записей о льготах олимпиад")
        return

    # Сводная таблица: вуз → список олимпиад с видом льготы
    summary = (
        df_ol[[
            "university_name",
            "olympiad_name",
            "olympiad_level",
            "subject",
            "benefit_type",
        ]]
        .drop_duplicates()
        .sort_values(["university_name", "olympiad_name"])
    )

    Path(REPORTS_DIR).mkdir(parents=True, exist_ok=True)
    table_path = Path(REPORTS_DIR) / "olympiads_summary.csv"
    summary.to_csv(table_path, index=False)

    print(f"📄 Сводная таблица олимпиад сохранена: {table_path}")


def main() -> None:
    print("🔎 Анализ данных вузов...")
    analyze_universities()
    print("🔎 Анализ данных олимпиад...")
    analyze_olympiads()
    print("✅ Анализ завершён.")


if __name__ == "__main__":
    main()
