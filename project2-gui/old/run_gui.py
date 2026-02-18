"""
Главный запускающий файл - БЕЗ content_area.update()
"""
import flet as ft
from gui.pages.receipts_page import ReceiptsPage
from gui.pages.batch_receipts_page import BatchReceiptsPage
from gui.pages.students_page import StudentsPage
from gui.pages.search_page import SearchPage

def main(page: ft.Page):
    """Главная функция приложения"""
    # Настройки окна
    page.title = "School Admin System"
    page.window_width = 1200
    page.window_height = 800
    page.window_min_width = 900
    page.window_min_height = 600
    page.padding = 0

    # Создать страницы
    receipts_page_obj = ReceiptsPage(page)
    batch_receipts_page_obj = BatchReceiptsPage(page)
    students_page_obj = StudentsPage(page)
    search_page_obj = SearchPage(page)

    # Контейнер для контента
    content_area = ft.Container(
        expand=True,
        padding=20,
    )

    def on_navigation_change(e):
        """Обработчик навигации"""
        selected_index = e.control.selected_index
        content_area.content = None
        page.update()

        if selected_index == 0:
            content_area.content = receipts_page_obj.build()

        elif selected_index == 1:
            content_area.content = batch_receipts_page_obj.build()

        elif selected_index == 2:
            content_area.content = students_page_obj.build()

        elif selected_index == 3:
            content_area.content = search_page_obj.build()
        page.update()
        # НЕ ВЫЗЫВАЕМ update()! Flet сделает это автоматически!
        # content_area.update() вызывает ошибку с students_page

    # Синий заголовок (2 строки)
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

    # Навигационное меню (УКОРОЧЕННЫЕ названия)
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
        ],
        on_change=on_navigation_change,
    )

    # Обернуть rail в Container с фоном
    rail_container = ft.Container(
        content=rail,
        width=220,
        expand=True,
        bgcolor=ft.colors.BLUE_50,
    )

    # Начальная страница
    content_area.content = receipts_page_obj.build()

    # Sidebar
    sidebar = ft.Column(
        controls=[
            header,
            rail_container,
        ],
        spacing=0,
        width=220,
    )

    # Layout приложения
    page.add(
        ft.Row(
            controls=[
                sidebar,
                ft.VerticalDivider(width=1),
                content_area,
            ],
            expand=True,
            spacing=0,
        )
    )

if __name__ == "__main__":
    ft.app(target=main)
