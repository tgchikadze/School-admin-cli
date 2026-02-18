"""
Главный запускающий файл GUI-приложения School Admin System на Flet.

Задачи модуля:
- Создать и настроить главное окно Flet-приложения.
- Инициализировать страницы GUI (квитанции, генератор, БД, поиск).
- Организовать навигацию через NavigationRail в левом сайдбаре.
"""

import flet as ft

from gui.pages.receipts_page import ReceiptsPage
from gui.pages.batch_receipts_page import BatchReceiptsPage
from gui.pages.students_page import StudentsPage
from gui.pages.search_page import SearchPage
from gui.pages.exam_selection_page import ExamSelectionPage



def main(page: ft.Page) -> None:
    """
    Точка входа Flet-приложения.

    Параметры:
        page (ft.Page): Объект страницы Flet, предоставляемый рантаймом.
            Хранит состояние окна, тему, корневое дерево контролов,
            а также используется для обновления интерфейса (page.update).

    Функция:
        - Настраивает параметры окна (размеры, заголовок, отступы).
        - Создаёт объекты страниц ReceiptsPage, BatchReceiptsPage,
          StudentsPage, SearchPage, передавая им page.
        - Собирает основной layout: левый сайдбар с NavigationRail
          и правую область content_area для контента текущей страницы.
        - Назначает обработчик on_navigation_change для переключения
          страниц при клике по пунктам меню.
    """
    # ==========================
    # Настройки окна приложения
    # ==========================
    page.title = "School Admin System"
    page.window_width = 1200
    page.window_height = 800
    page.window_min_width = 900
    page.window_min_height = 600
    page.padding = 0

    # =====================
    # Инициализация страниц
    # =====================
    receipts_page_obj = ReceiptsPage(page)
    batch_receipts_page_obj = BatchReceiptsPage(page)
    students_page_obj = StudentsPage(page)
    search_page_obj = SearchPage(page)
    exam_selection_page_obj = ExamSelectionPage(page)

    # ====================
    # Область для контента
    # ====================
    content_area = ft.Container(
        expand=True,
        padding=20,
    )

    def on_navigation_change(e: ft.ControlEvent) -> None:
        """
        Обработчик смены пункта NavigationRail.

        Параметры:
            e (ft.ControlEvent): Событие Flet, содержащее control и
                selected_index (индекс выбранной вкладки).

        Логика:
            - Очищает текущий контент content_area.
            - В зависимости от selected_index вызывает build() нужной
              страницы и подставляет результат в content_area.content.
            - Вызывает page.update() для перерисовки интерфейса.
        """
        selected_index: int = e.control.selected_index

        # Очистить старый контент перед загрузкой нового
        content_area.content = None
        page.update()

        # Выбор страницы по индексу вкладки
        if selected_index == 0:
            content_area.content = receipts_page_obj.build()
        elif selected_index == 1:
            content_area.content = batch_receipts_page_obj.build()
        elif selected_index == 2:
            content_area.content = students_page_obj.build()
        elif selected_index == 3:
            content_area.content = search_page_obj.build()
        elif selected_index == 4:
            content_area.content = exam_selection_page_obj.build()

        # Обновление страницы после замены контента
        page.update()

    # =========================
    # Сайдбар: заголовок + меню
    # =========================

    # Заголовок приложения в синей плашке
    header = ft.Container(
        content=ft.Column(
            controls=[
                ft.Icon(
                    ft.icons.SCHOOL,
                    size=28,
                    color=ft.colors.WHITE,
                ),
                ft.Text(
                    "School",
                    size=14,
                    weight=ft.FontWeight.BOLD,
                    color=ft.colors.WHITE,
                    text_align=ft.TextAlign.CENTER,
                ),
                ft.Text(
                    "Admin System",
                    size=14,
                    weight=ft.FontWeight.BOLD,
                    color=ft.colors.WHITE,
                    text_align=ft.TextAlign.CENTER,
                ),
            ],
            spacing=3,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        ),
        padding=10,
        bgcolor=ft.colors.BLUE_700,
        width=220,
    )

    # Навигационное меню (укороченные названия пунктов)
    rail = ft.NavigationRail(
        selected_index=0,
        label_type=ft.NavigationRailLabelType.ALL,
        min_width=100,
        min_extended_width=220,
        destinations=[
            ft.NavigationRailDestination(
                icon=ft.icons.RECEIPT_OUTLINED,
                selected_icon=ft.icons.RECEIPT,
                label="Одна квитанция",
            ),
            ft.NavigationRailDestination(
                icon=ft.icons.ASSIGNMENT_OUTLINED,
                selected_icon=ft.icons.ASSIGNMENT,
                label="Генератор",
            ),
            ft.NavigationRailDestination(
                icon=ft.icons.PEOPLE_OUTLINED,
                selected_icon=ft.icons.PEOPLE,
                label="База данных",
            ),
            ft.NavigationRailDestination(
                icon=ft.icons.SEARCH,
                selected_icon=ft.icons.SEARCH,
                label="Поиск",
            ),
            ft.NavigationRailDestination(
                icon=ft.icons.SCHOOL_OUTLINED,
                selected_icon=ft.icons.SCHOOL,
                label="Выбор ЕГЭ",
            ),

        ],
        on_change=on_navigation_change,
    )

    # Обёртка для NavigationRail с фоновым цветом и фиксированной шириной
    rail_container = ft.Container(
        content=rail,
        width=220,
        expand=True,
        bgcolor=ft.colors.BLUE_50,
    )

    # ==========================
    # Стартовая страница контента
    # ==========================
    content_area.content = receipts_page_obj.build()

    # Колонка сайдбара: заголовок + меню
    sidebar = ft.Column(
        controls=[
            header,
            rail_container,
        ],
        spacing=0,
        width=220,
    )

    # ==================
    # Основной layout Row
    # ==================
    page.add(
        ft.Row(
            controls=[
                sidebar,
                ft.VerticalDivider(width=1),
                content_area,
            ],
            expand=True,
            spacing=0,
        ),
    )


if __name__ == "__main__":
    # Запуск Flet-приложения с функцией main в качестве целевой
    ft.app(target=main)
