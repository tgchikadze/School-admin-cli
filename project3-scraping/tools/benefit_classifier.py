"""
utils/benefit_classifier.py

Извлечение типа олимпиадной льготы (БВИ, 100 баллов, доп. баллы)
из текстового фрагмента (snippet из PDF/HTML).

Используется в OlympBenefitsScraper для автоматического заполнения
поля benefit_type, которое раньше оставалось пустым в 90% записей.
"""

import re


# Паттерны для каждого типа льготы (порядок = приоритет)
BENEFIT_PATTERNS: list[tuple[str, re.Pattern]] = [
    ("БВИ", re.compile(
        r"(?:бви|без\s*вступительных|без\s*вступ\.\s*испыт|"
        r"зачисление\s*без\s*экзамен|приём\s*без\s*вступ)",
        re.IGNORECASE,
    )),
    ("100 баллов", re.compile(
        r"(?:100\s*балл|максимальн\w*\s*балл|100-балл|"
        r"приравн\w*\s*к\s*100|засчит\w*\s*100)",
        re.IGNORECASE,
    )),
    ("доп. баллы", re.compile(
        r"(?:доп\w*\.?\s*балл|индивидуальн\w*\s*достиж|"
        r"дополнительн\w*\s*балл|\bИД\b|"
        r"портфолио|начисл\w*\s*балл\w*\s*за\s*олимп)",
        re.IGNORECASE,
    )),
    ("особые права", re.compile(
        r"(?:особ\w*\s*прав\w*|преимущ\w*\s*прав\w*|"
        r"перечнев\w*\s*олимп|перечень\s*олимпиад)",
        re.IGNORECASE,
    )),
]


def classify_benefit(text: str) -> str:
    """
    Определить тип(ы) льготы из текста.

    Возвращает строку с найденными типами через "; ".
    Если ничего не найдено, возвращает пустую строку.

    Примеры:
        >>> classify_benefit("Победитель зачисляется БВИ")
        'БВИ'
        >>> classify_benefit("100 баллов за ЕГЭ + доп. баллы за ИД")
        '100 баллов; доп. баллы'
        >>> classify_benefit("Расписание занятий")
        ''
    """
    if not text:
        return ""

    found: list[str] = []
    for label, pattern in BENEFIT_PATTERNS:
        if pattern.search(text):
            found.append(label)

    return "; ".join(found)


def classify_benefit_strict(text: str) -> str:
    """
    Как classify_benefit(), но возвращает только ОДИН (самый приоритетный) тип.
    БВИ > 100 баллов > доп. баллы > особые права.
    """
    if not text:
        return ""
    for label, pattern in BENEFIT_PATTERNS:
        if pattern.search(text):
            return label
    return ""
