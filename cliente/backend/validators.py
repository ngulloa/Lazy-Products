"""Validaciones para entradas del cliente."""

from __future__ import annotations

from pathlib import Path

from shared.errors import ValidationError


def validate_output_dir(path: Path) -> None:
    """Valida que la ruta de salida sea utilizable para archivos CSV."""
    if path.exists() and not path.is_dir():
        raise ValidationError(f"La ruta no es un directorio: {path}")

    try:
        path.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        raise ValidationError(f"No se pudo crear/acceder al directorio: {path}") from exc



