"""Ventana principal de Lazy Products."""

from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor, QFont, QGuiApplication
from PyQt6.QtWidgets import (
    QApplication,
    QFrame,
    QGraphicsDropShadowEffect,
    QLabel,
    QMainWindow,
    QPushButton,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from cliente.backend.controller import AppController
from cliente.frontend.create_product_dialog import CreateProductDialog
from cliente.frontend.dialogs import show_error
from cliente.frontend.import_dialog import ImportProductPage
from shared.errors import ServiceError, ValidationError


class MainWindow(QMainWindow):
    """Ventana principal con el menu de acciones del inventario."""

    def __init__(self, controller: AppController) -> None:
        super().__init__()
        self._controller = controller

        self._stack: QStackedWidget
        self._menu_page: QWidget
        self._import_page: ImportProductPage

        self._create_button: QPushButton
        self._create_product_button: QPushButton
        self._view_button: QPushButton
        self._search_button: QPushButton
        self._exit_button: QPushButton

        self.setWindowTitle("Lazy Products")
        screen = QGuiApplication.primaryScreen()
        geo = screen.availableGeometry()  # tamaño usable (sin taskbar/dock)
        w = int(geo.width() * 0.65)
        h = int(geo.height() * 0.85)
        self.resize(w, h)
        self.setMinimumSize(int(w * 0.70), int(h * 0.70))
        self._build_ui()
        self._apply_styles()
        self._connect_signals()

    def _build_ui(self) -> None:
        """Construye la estructura de paginas de la ventana principal."""
        self._stack = QStackedWidget(self)
        self.setCentralWidget(self._stack)

        self._menu_page = self._build_menu_page()
        self._import_page = ImportProductPage(
            controller=self._controller,
            on_back=self._show_menu_page,
            parent=self,
        )

        self._stack.addWidget(self._menu_page)
        self._stack.addWidget(self._import_page)
        self._show_menu_page()

    def _build_menu_page(self) -> QWidget:
        """Construye y retorna la pagina de menu principal."""
        page = QWidget(self)

        root_layout = QVBoxLayout(page)
        root_layout.setContentsMargins(40, 40, 40, 40)
        root_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        card = QFrame(page)
        card.setObjectName("mainCard")
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(40, 40, 40, 40)
        card_layout.setSpacing(16)

        title_label = QLabel(card)
        title_label.setObjectName("titleLabel")
        title_label.setFont(QFont("Segoe UI", 24, QFont.Weight.Bold))
        title_label.setTextFormat(Qt.TextFormat.RichText)
        title_label.setText(
            '<span style="color:#C80202;">L</span>'
            '<span style="color:#111827;">azy </span>'
            '<span style="color:#C80202;">P</span>'
            '<span style="color:#111827;">roducts</span>'
        )
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self._create_button = self._build_button("Crear archivo de importación")
        self._create_product_button = self._build_button("Crear producto")
        self._view_button = self._build_button("Visualizar productos")
        self._search_button = self._build_button("Buscar productos")
        self._exit_button = self._build_button("Salir")
        self._exit_button.setObjectName("exitButton")
        self._view_button.setEnabled(False)
        self._search_button.setEnabled(False)
        self._view_button.setToolTip("Funcionalidad en desarrollo")
        self._search_button.setToolTip("Funcionalidad en desarrollo")

        card_layout.addWidget(title_label)
        card_layout.addSpacing(18)
        card_layout.addWidget(self._create_button)
        card_layout.addWidget(self._create_product_button)
        card_layout.addWidget(self._view_button)
        card_layout.addWidget(self._search_button)
        card_layout.addSpacing(8)
        card_layout.addWidget(self._exit_button)

        shadow = QGraphicsDropShadowEffect(card)
        shadow.setBlurRadius(38)
        shadow.setOffset(0, 8)
        shadow.setColor(QColor(0, 0, 0, 38))
        card.setGraphicsEffect(shadow)

        root_layout.addWidget(card)
        return page

    def _apply_styles(self) -> None:
        """Aplica estilos QSS de la interfaz."""
        self.setStyleSheet(
            """
            QMainWindow {
                background-color: #eef1f4;
            }
            QFrame#mainCard {
                background-color: #ffffff;
                border-radius: 18px;
                min-width: 460px;
                max-width: 520px;
            }
            QPushButton {
                background-color: #C80202;
                border: none;
                border-radius: 10px;
                color: #ffffff;
                font-family: "Segoe UI";
                font-size: 15px;
                font-weight: 600;
                min-height: 52px;
                padding: 10px 14px;
            }
            QPushButton:hover {
                background-color: #A30202;
            }
            QPushButton:pressed {
                background-color: #820101;
            }
            QPushButton:disabled {
                background-color: #d5a3a3;
                color: #f5e8e8;
            }
            QPushButton#exitButton {
                background-color: #e5e7eb;
                color: #1f2937;
            }
            QPushButton#exitButton:hover {
                background-color: #d1d5db;
            }
            QPushButton#exitButton:pressed {
                background-color: #b9c0c9;
            }
            QPushButton#exitButton:disabled {
                background-color: #e5e7eb;
                color: #9ca3af;
            }
            """
        )

    def _connect_signals(self) -> None:
        """Conecta botones de UI con acciones del controller."""
        self._create_button.clicked.connect(self._on_create_import_clicked)
        self._create_product_button.clicked.connect(self._on_create_product_clicked)
        self._view_button.clicked.connect(self._controller.on_view_products)
        self._search_button.clicked.connect(self._controller.on_search_products)
        self._exit_button.clicked.connect(self._on_exit_clicked)

    def _show_menu_page(self) -> None:
        """Muestra la pagina de menu principal."""
        self._stack.setCurrentWidget(self._menu_page)

    def _show_import_page(self) -> None:
        """Muestra la pagina de formulario de importacion."""
        try:
            self._controller.start_import_session_if_needed()
            self._import_page.refresh_product_categories()
        except (ValidationError, ServiceError) as exc:
            show_error(self, "Error de importacion", str(exc))
            return

        self._stack.setCurrentWidget(self._import_page)

    def _on_create_import_clicked(self, _checked: bool = False) -> None:
        """Cambia desde el menu hacia la pagina de importacion."""
        self._controller.on_create_import_file()
        self._show_import_page()

    def _on_create_product_clicked(self, _checked: bool = False) -> None:
        """Abre dialogo modal para crear un nuevo producto/categoria."""
        self._controller.on_open_create_product()
        dialog = CreateProductDialog(controller=self._controller, parent=self)
        dialog.exec()

    def _on_exit_clicked(self) -> None:
        """Solicita al controller el cierre de la app."""
        self._controller.on_exit(QApplication.instance())

    @staticmethod
    def _build_button(text: str) -> QPushButton:
        """Construye un boton estandar del menu principal."""
        button = QPushButton(text)
        button.setCursor(Qt.CursorShape.PointingHandCursor)
        return button
