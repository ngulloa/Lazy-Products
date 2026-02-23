"""Esquema canonico de columnas CSV compartido por cliente/servidor."""

from __future__ import annotations

from collections.abc import Sequence

ID_HEADER = "ID"
TRACK_INVENTORY_HEADER = "Rastrear Inventario"
PUBLISHED_HEADER = "Est\u00e1 Publicado"

IMPORT_HEADERS: tuple[str, ...] = (
    ID_HEADER,
    "Base EAN13",
    "Digito verificador",
    "C\u00f3digo de Barras",
    "Producto",
    "Marca",
    "Modelo",
    "Cantidad a la mano",
    "Atributo",
    "Valores Atributo",
    "Venta con IVA",
    "Venta sin IVA",
    "SKU Proveedor",
    "Largo Envio",
    "Ancho Envio",
    "Alto Envio",
    "Peso completo",
    "Dimensiones Producto",
    "Material",
    "Proveedor",
    "Precio de Costo",
    "# Variantes de producto",
    "Observaciones",
    "Descripci\u00f3n para el sitio web",
    "Descripci\u00f3n SEO",
    "Referencia interna",
    "Nombre Base",
    "Nombre Comercial",
    "Categor\u00eda de Punto de venta",
    "Subcategor\u00eda",
    "Volumen",
    "Imagen",
    "Categor\u00eda del Producto",
    PUBLISHED_HEADER,
    TRACK_INVENTORY_HEADER,
    "Etiquetas",
    "Sitio web",
    "Disponible en PdV",
)

INFO_PRODUCTS_HEADERS: tuple[str, ...] = tuple(
    column for column in IMPORT_HEADERS if column.casefold() != ID_HEADER.casefold()
)

IMPORT_HEADERS_INDEX: dict[str, int] = {name: index for index, name in enumerate(IMPORT_HEADERS)}
INFO_PRODUCTS_HEADERS_INDEX: dict[str, int] = {
    name: index for index, name in enumerate(INFO_PRODUCTS_HEADERS)
}

INFO_PRODUCTS_HEADERS_LOOKUP: dict[str, str] = {
    header.casefold(): header for header in INFO_PRODUCTS_HEADERS
}


def normalize_header_name(header: str) -> str:
    """Normaliza un nombre de columna removiendo BOM y espacios extra."""
    return header.replace("\ufeff", "").strip()


def build_header_index(headers: Sequence[str]) -> dict[str, int]:
    """Construye indice por nombre para un conjunto de columnas."""
    return {name: index for index, name in enumerate(headers)}


def resolve_info_products_header(header: str) -> str | None:
    """Resuelve header canonico de info_products (ignora columna ID)."""
    normalized = normalize_header_name(header)
    if not normalized:
        return None
    if normalized.casefold() == ID_HEADER.casefold():
        return None
    return INFO_PRODUCTS_HEADERS_LOOKUP.get(normalized.casefold())
