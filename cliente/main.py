"""Inicializacion de la aplicacion de cliente."""

from __future__ import annotations

import logging
import sys
from pathlib import Path

from PyQt6.QtGui import QIcon
from PyQt6.QtWidgets import QApplication

from cliente.backend.controller import AppController
from cliente.backend.gateway import LocalServerGateway
from cliente.backend.id_registry import IdRegistry
from cliente.frontend.main_window import MainWindow

LOGGER = logging.getLogger(__name__)


def main() -> int:
    """Ejecuta la aplicacion grafica."""
    app = QApplication(sys.argv)
    icon_path = Path(__file__).resolve().parent / "utilities" / "icono.ico"
    if icon_path.exists():
        app.setWindowIcon(QIcon(str(icon_path)))
    else:
        LOGGER.warning("No se encontro icono de aplicacion en: %s", icon_path)

    id_registry = IdRegistry()
    id_registry.ensure_initialized()
    LOGGER.info("Utilities inicializado en cliente.")

    gateway = LocalServerGateway()
    controller = AppController(gateway=gateway, id_registry=id_registry)
    window = MainWindow(controller=controller)
    if not app.windowIcon().isNull():
        window.setWindowIcon(app.windowIcon())
    window.showMaximized()

    LOGGER.info("Aplicacion iniciada.")
    return app.exec()
