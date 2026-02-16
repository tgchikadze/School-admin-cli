"""
Страница поиска
"""
import flet as ft


class SearchPage:
    """Страница поиска по базе"""

    def __init__(self, page: ft.Page):
        self.page = page

    def build(self) -> ft.Column:
        """Построить интерфейс страницы"""
        return ft.Column(
            controls=[
                ft.Text("🔍 Поиск", size=24, weight=ft.FontWeight.BOLD),
                ft.Divider(),
                ft.Text("Здесь будет поиск..."),
            ],
            spacing=20,
        )
