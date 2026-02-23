"""Modelos de dominio de inventario."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class Producto:
    """Representa un producto en inventario."""

    sku: str
    nombre: str
    cantidad: int



