"""Helpers de dialogos para frontend."""

from __future__ import annotations

from PyQt6.QtWidgets import QMessageBox, QWidget


def show_info(parent: QWidget | None, title: str, message: str) -> None:
    """Muestra un dialogo informativo."""
    QMessageBox.information(parent, title, message)


def show_error(parent: QWidget | None, title: str, message: str) -> None:
    """Muestra un dialogo de error."""
    QMessageBox.critical(parent, title, message)



