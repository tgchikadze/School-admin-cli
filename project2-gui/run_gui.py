"""
Точка входа для GUI приложения School Admin System
"""
import flet as ft
from gui.app import SchoolAdminApp


def main(page: ft.Page):
    """Главная функция приложения"""
    app = SchoolAdminApp(page)
    app.build()


if __name__ == '__main__':
    # Запуск приложения
    ft.app(target=main)
