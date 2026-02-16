"""
Страница управления учениками
"""
import flet as ft


class StudentsPage:
    """Страница для управления базой учеников"""

    def __init__(self, page: ft.Page):
        self.page = page

    def build(self) -> ft.Column:
        """Построить интерфейс страницы"""
        return ft.Column(
            controls=[
                ft.Text("👥 Управление учениками", size=24, weight=ft.FontWeight.BOLD),
                ft.Divider(),
                ft.Text("Здесь будет таблица учеников..."),
            ],
            spacing=20,
        )
