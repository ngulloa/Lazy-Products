"""Dialogo para crear nuevas categorias de producto."""

from __future__ import annotations

from typing import TYPE_CHECKING

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor
from PyQt6.QtWidgets import (
    QDialog,
    QFrame,
    QGraphicsDropShadowEffect,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from cliente.frontend.dialogs import show_error, show_info
from shared.errors import ServiceError, ValidationError

if TYPE_CHECKING:
    from cliente.backend.controller import AppController


class CreateProductDialog(QDialog):
    """Dialogo modal para crear una categoria y su archivo de IDs."""

    def __init__(
        self,
        controller: AppController,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._controller = controller
        self._slug_input: QLineEdit

        self.setWindowTitle("Crear producto")
        self.setModal(True)
        self.setMinimumSize(460, 300)
        self.resize(500, 320)

        self._build_ui()
        self._apply_styles()

    def _build_ui(self) -> None:
        """Construye widgets del dialogo."""
        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(18, 18, 18, 18)

        card = QFrame(self)
        card.setObjectName("dialogCard")
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(24, 24, 24, 24)
        card_layout.setSpacing(12)

        title_label = QLabel("Crear producto", card)
        title_label.setObjectName("titleLabel")
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        slug_label = QLabel("Nombre (slug)", card)
        slug_label.setObjectName("fieldLabel")

        self._slug_input = QLineEdit(card)
        self._slug_input.setPlaceholderText("manillas-de-freno")

        help_label = QLabel(
            "Reglas:\n"
            "- minusculas\n"
            "- letras/numeros/guiones\n"
            "- sin espacios\n"
            '- ejemplo: "manillas-de-freno"',
            card,
        )
        help_label.setObjectName("helpLabel")
        help_label.setWordWrap(True)

        buttons_layout = QHBoxLayout()
        buttons_layout.addStretch(1)

        cancel_button = QPushButton("Cancelar", card)
        cancel_button.setObjectName("cancelButton")
        create_button = QPushButton("Crear", card)

        cancel_button.clicked.connect(self.reject)
        create_button.clicked.connect(self._on_create_clicked)

        buttons_layout.addWidget(cancel_button)
        buttons_layout.addWidget(create_button)

        card_layout.addWidget(title_label)
        card_layout.addSpacing(4)
        card_layout.addWidget(slug_label)
        card_layout.addWidget(self._slug_input)
        card_layout.addWidget(help_label)
        card_layout.addSpacing(4)
        card_layout.addLayout(buttons_layout)

        shadow = QGraphicsDropShadowEffect(card)
        shadow.setBlurRadius(30)
        shadow.setOffset(0, 6)
        shadow.setColor(QColor(0, 0, 0, 35))
        card.setGraphicsEffect(shadow)

        root_layout.addWidget(card)
        self._slug_input.setFocus()

    def _apply_styles(self) -> None:
        """Aplica estilos visuales consistentes con la app."""
        self.setStyleSheet(
            """
            QDialog {
                background-color: #eef1f4;
            }
            QFrame#dialogCard {
                background-color: #ffffff;
                border-radius: 16px;
            }
            QLabel#titleLabel {
                color: #20232a;
                font-family: "Segoe UI";
                font-size: 22px;
                font-weight: 700;
            }
            QLabel#fieldLabel {
                color: #334155;
                font-family: "Segoe UI";
                font-size: 13px;
                font-weight: 600;
            }
            QLabel#helpLabel {
                color: #475569;
                font-family: "Segoe UI";
                font-size: 12px;
                line-height: 1.35;
                background-color: #f8fafc;
                border: 1px solid #d1d5db;
                border-radius: 8px;
                padding: 10px;
            }
            QLineEdit {
                background-color: #f8fafc;
                border: 1px solid #d1d5db;
                border-radius: 8px;
                color: #111827;
                font-family: "Segoe UI";
                font-size: 13px;
                padding: 10px;
            }
            QLineEdit:focus {
                border: 1px solid #2563eb;
                background-color: #ffffff;
            }
            QPushButton {
                background-color: #2563eb;
                border: none;
                border-radius: 10px;
                color: #ffffff;
                font-family: "Segoe UI";
                font-size: 13px;
                font-weight: 600;
                min-height: 40px;
                min-width: 100px;
                padding: 8px 12px;
            }
            QPushButton:hover {
                background-color: #1d4ed8;
            }
            QPushButton:pressed {
                background-color: #1e40af;
            }
            QPushButton#cancelButton {
                background-color: #e5e7eb;
                color: #1f2937;
            }
            QPushButton#cancelButton:hover {
                background-color: #d1d5db;
            }
            QPushButton#cancelButton:pressed {
                background-color: #b9c0c9;
            }
            """
        )

    def _on_create_clicked(self) -> None:
        """Valida y crea la categoria usando el controller."""
        slug = self._slug_input.text()
        try:
            self._controller.on_create_product(slug)
        except (ValidationError, ServiceError) as exc:
            show_error(self, "Error al crear producto", str(exc))
            return

        slug_clean = slug.strip().lower()
        show_info(self, "Producto creado", f"Categoria creada: {slug_clean}")
        self.accept()
