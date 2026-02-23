"""Dialogo para visualizar y copiar detalles de producto."""

from __future__ import annotations

from PyQt6.QtGui import QColor
from PyQt6.QtWidgets import (
    QApplication,
    QDialog,
    QGraphicsDropShadowEffect,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)


class ProductDetailsDialog(QDialog):
    """Dialogo para mostrar nombre comercial y observaciones."""

    def __init__(self, nombre_comercial: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._nombre_comercial = nombre_comercial.strip()

        self.setWindowTitle("Detalles del producto")
        self.setModal(True)
        self.resize(620, 420)

        self._build_ui()
        self._apply_styles()

    def _build_ui(self) -> None:
        """Construye layout y widgets del dialogo."""
        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(18, 18, 18, 18)
        root_layout.setSpacing(12)

        title_label = QLabel("Nombre Comercial", self)
        title_label.setObjectName("detailsTitle")

        self._nombre_comercial_view = QTextEdit(self)
        self._nombre_comercial_view.setReadOnly(True)
        self._nombre_comercial_view.setPlainText(self._nombre_comercial)
        self._nombre_comercial_view.setMinimumHeight(92)

        observations_label = QLabel("Observaciones", self)
        observations_label.setObjectName("detailsTitle")

        self._observaciones_input = QTextEdit(self)
        self._observaciones_input.setPlaceholderText("Escribe observaciones...")

        buttons_layout = QHBoxLayout()
        buttons_layout.setSpacing(10)

        copy_button = QPushButton("Copiar", self)
        back_button = QPushButton("Regresar", self)
        back_button.setObjectName("backButton")

        copy_button.clicked.connect(self._copy_to_clipboard)
        back_button.clicked.connect(self.close)

        buttons_layout.addWidget(copy_button)
        buttons_layout.addWidget(back_button)

        root_layout.addWidget(title_label)
        root_layout.addWidget(self._nombre_comercial_view)
        root_layout.addWidget(observations_label)
        root_layout.addWidget(self._observaciones_input)
        root_layout.addLayout(buttons_layout)

        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(22)
        shadow.setOffset(0, 4)
        shadow.setColor(QColor(0, 0, 0, 24))
        self.setGraphicsEffect(shadow)

    def _apply_styles(self) -> None:
        """Aplica estilos alineados al look general de la app."""
        self.setStyleSheet(
            """
            QDialog {
                background-color: #ffffff;
                border: 1px solid #dbe2ea;
                border-radius: 14px;
            }
            QLabel#detailsTitle {
                color: #334155;
                font-family: "Segoe UI";
                font-size: 14px;
                font-weight: 600;
            }
            QTextEdit {
                background-color: #f8fafc;
                border: 1px solid #d1d5db;
                border-radius: 8px;
                color: #111827;
                font-family: "Segoe UI";
                font-size: 14px;
                padding: 10px;
            }
            QTextEdit:focus {
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
                min-height: 36px;
                padding: 6px 12px;
            }
            QPushButton:hover {
                background-color: #1d4ed8;
            }
            QPushButton:pressed {
                background-color: #1e40af;
            }
            QPushButton#backButton {
                background-color: #e5e7eb;
                color: #1f2937;
            }
            QPushButton#backButton:hover {
                background-color: #d1d5db;
            }
            QPushButton#backButton:pressed {
                background-color: #b9c0c9;
            }
            """
        )

    def _copy_to_clipboard(self) -> None:
        """Copia nombre comercial y observaciones al portapapeles."""
        observaciones = self._observaciones_input.toPlainText().strip()
        text = f"{self._nombre_comercial}\n{observaciones}"
        QApplication.clipboard().setText(text)
