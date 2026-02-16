"""
Страница генерации квитанций
"""
import flet as ft


class ReceiptsPage:
    """Страница для генерации квитанций ПД-5"""

    def __init__(self, page: ft.Page):
        self.page = page

    def build(self) -> ft.Column:
        """Построить интерфейс страницы"""
        return ft.Column(
            controls=[
                ft.Text("🧾 Генерация квитанций", size=24, weight=ft.FontWeight.BOLD),
                ft.Divider(),
                ft.Text("Здесь будет форма генерации квитанций..."),
            ],
            spacing=20,
        )
