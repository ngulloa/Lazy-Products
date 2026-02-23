"""Utilidades para construir filas de inventario en CSV."""

from __future__ import annotations

import csv
import unicodedata
from pathlib import Path

from shared.errors import ServiceError


def ean13_check_digit(base12: str) -> str:
    """Calcula el digito verificador de un codigo EAN-13 a partir de 12 digitos."""
    normalized = base12.strip()
    if len(normalized) != 12 or not normalized.isdigit():
        raise ServiceError("base12 debe contener exactamente 12 digitos.")

    digits = [int(char) for char in normalized]
    odd_sum = sum(digits[::2])
    even_sum = sum(digits[1::2])
    total = odd_sum + (3 * even_sum)
    check_digit = (10 - (total % 10)) % 10
    return str(check_digit)


def build_barcode(base12: str) -> str:
    """Construye un EAN-13 completo usando 12 digitos base."""
    normalized = base12.strip()
    return f"{normalized}{ean13_check_digit(normalized)}"


def format_clp(amount: float) -> str:
    """Formatea un monto en pesos chilenos sin decimales."""
    rounded_amount = int(round(amount))
    return f"${rounded_amount:,}"


def build_nombre_base(producto: str, marca: str, modelo: str) -> str:
    """Construye nombre base a partir de producto, marca y modelo."""
    parts = [producto.strip(), marca.strip(), modelo.strip()]
    return " ".join(part for part in parts if part)


def build_nombre_comercial(
    nombre_base: str,
    valores_atributo: str,
    dimensiones_producto: str,
    unidad: str,
) -> str:
    """Construye nombre comercial evitando espacios dobles."""
    parts = [nombre_base.strip(), valores_atributo.strip()]

    dimensiones = dimensiones_producto.strip()
    unidad_normalizada = unidad.strip()
    if dimensiones and unidad_normalizada:
        parts.append(f"{dimensiones}{unidad_normalizada}")

    return " ".join(part for part in parts if part)


def compute_volumen(largo: float, ancho: float, alto: float) -> float:
    """Calcula el volumen del producto."""
    return largo * ancho * alto


def build_image_url(sku: str) -> str:
    """Construye la URL de imagen para un SKU."""
    return f"https://clubike.cl/imagenes/{sku.strip()}.jpg"


def load_category_mapping(path: Path) -> dict[str, tuple[str, str]]:
    """Carga mapeo Producto -> (Categoria, Subcategoria) desde CSV."""
    expected_headers = {"Producto", "Categoría", "Subcategoría"}

    try:
        with path.open("r", newline="", encoding="utf-8-sig") as csv_file:
            reader = csv.DictReader(csv_file)
            fieldnames = set(reader.fieldnames or [])
            if not expected_headers.issubset(fieldnames):
                raise ServiceError(
                    "El CSV de categorias debe contener headers: "
                    "Producto,Categoría,Subcategoría."
                )

            mapping: dict[str, tuple[str, str]] = {}
            for row in reader:
                producto = (row.get("Producto") or "").strip()
                if not producto:
                    continue

                categoria = (row.get("Categoría") or "").strip()
                subcategoria = (row.get("Subcategoría") or "").strip()

                if producto not in mapping:
                    mapping[producto] = (categoria, subcategoria)
    except OSError as exc:
        raise ServiceError(f"No fue posible leer el CSV de categorias: {path}") from exc

    return mapping


def get_category_for_producto(
    mapping: dict[str, tuple[str, str]],
    producto: str,
) -> tuple[str, str]:
    """Obtiene categoria y subcategoria para un producto."""
    producto_normalizado = producto.strip()
    if producto_normalizado in mapping:
        return mapping[producto_normalizado]

    producto_decodificado = _decode_mojibake(producto_normalizado)
    if producto_decodificado in mapping:
        return mapping[producto_decodificado]

    target_keys = {
        _normalize_lookup_key(producto_normalizado),
        _normalize_lookup_key(producto_decodificado),
    }
    for key, value in mapping.items():
        if _normalize_lookup_key(key) in target_keys:
            return value

    raise ServiceError(
        f"No se encontro categoria/subcategoria para el producto: {producto_normalizado}"
    )


def _decode_mojibake(text: str) -> str:
    """Intenta corregir texto UTF-8 mal decodificado como latin-1/cp1252."""
    try:
        return text.encode("latin-1").decode("utf-8")
    except UnicodeError:
        return text


def _normalize_lookup_key(text: str) -> str:
    """Normaliza texto para comparaciones tolerantes de claves."""
    normalized = unicodedata.normalize("NFKD", text)
    ascii_text = normalized.encode("ascii", "ignore").decode("ascii")
    return "".join(char for char in ascii_text.lower() if char.isalnum())
