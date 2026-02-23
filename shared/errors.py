"""Excepciones compartidas del proyecto."""

from __future__ import annotations


class ValidationError(Exception):
    """Error de validacion de datos de entrada."""


class ServiceError(Exception):
    """Error en la ejecucion de servicios."""
