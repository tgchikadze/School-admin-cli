"""
Главное окно приложения School Admin System
"""
import flet as ft
from gui.pages.receipts_page import ReceiptsPage
from gui.pages.students_page import StudentsPage
from gui.pages.search_page import SearchPage


class SchoolAdminApp:
    """Главное приложение с навигацией"""

    def __init__(self, page: ft.Page):
        self.page = page
        self.page.title = "🏫 School Admin System"
        self.page.window_width = 1000
        self.page.window_height = 700
        self.page.window_resizable = True
        self.page.padding = 0

        # Текущая страница
        self.current_page = None

        # Контейнер для содержимого страниц
        self.content_container = ft.Container(
            expand=True,
            padding=20,
        )

    def build(self):
        """Построить интерфейс"""
        # Боковое меню
        sidebar = self._create_sidebar()

        # Главный layout
        main_layout = ft.Row(
            controls=[
                sidebar,
                ft.VerticalDivider(width=1),
                self.content_container,
            ],
            expand=True,
            spacing=0,
        )

        self.page.add(main_layout)

        # Показать первую страницу по умолчанию
        self.show_receipts_page()

    def _create_sidebar(self) -> ft.Container:
        """Создать боковое меню"""
        return ft.Container(
            width=250,
            bgcolor=ft.colors.BLUE_GREY_50,
            padding=20,
            content=ft.Column(
                controls=[
                    # Заголовок
                    ft.Container(
                        content=ft.Column([
                            ft.Icon(
                                name=ft.icons.SCHOOL,
                                size=50,
                                color=ft.colors.BLUE_700,
                            ),
                            ft.Text(
                                "School Admin",
                                size=20,
                                weight=ft.FontWeight.BOLD,
                                color=ft.colors.BLUE_700,
                                text_align=ft.TextAlign.CENTER,
                            ),
                            ft.Text(
                                "Система управления",
                                size=12,
                                color=ft.colors.BLUE_GREY_700,
                                text_align=ft.TextAlign.CENTER,
                            ),
                        ],
                            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                        ),
                        padding=ft.padding.only(bottom=30),
                    ),

                    ft.Divider(),

                    # Меню
                    self._create_menu_button(
                        icon=ft.icons.RECEIPT_LONG,
                        text="Генерация квитанций",
                        on_click=lambda _: self.show_receipts_page(),
                    ),

                    self._create_menu_button(
                        icon=ft.icons.PEOPLE,
                        text="Управление учениками",
                        on_click=lambda _: self.show_students_page(),
                    ),

                    self._create_menu_button(
                        icon=ft.icons.SEARCH,
                        text="Поиск",
                        on_click=lambda _: self.show_search_page(),
                    ),

                    ft.Container(expand=True),  # Spacer

                    ft.Divider(),

                    # Информация
                    ft.Text(
                        "Проект 2: GUI\nМФТИ 2026",
                        size=10,
                        color=ft.colors.BLUE_GREY_400,
                        text_align=ft.TextAlign.CENTER,
                    ),
                ],
                spacing=10,
            ),
        )

    def _create_menu_button(self, icon, text, on_click) -> ft.Container:
        """Создать кнопку меню"""
        return ft.Container(
            content=ft.TextButton(
                content=ft.Row([
                    ft.Icon(name=icon, size=20),
                    ft.Text(text, size=14),
                ]),
                on_click=on_click,
                style=ft.ButtonStyle(
                    padding=15,
                    bgcolor={
                        ft.MaterialState.HOVERED: ft.colors.BLUE_100,
                    },
                ),
            ),
            border_radius=10,
        )

    def _clear_content(self):
        """Очистить контейнер содержимого"""
        self.content_container.content = None

    def show_receipts_page(self):
        """Показать страницу генерации квитанций"""
        self._clear_content()
        page = ReceiptsPage(self.page)
        self.content_container.content = page.build()
        self.current_page = "receipts"
        self.page.update()

    def show_students_page(self):
        """Показать страницу управления учениками"""
        self._clear_content()
        page = StudentsPage(self.page)
        self.content_container.content = page.build()
        self.current_page = "students"
        self.page.update()

    def show_search_page(self):
        """Показать страницу поиска"""
        self._clear_content()
        page = SearchPage(self.page)
        self.content_container.content = page.build()
        self.current_page = "search"
        self.page.update()
