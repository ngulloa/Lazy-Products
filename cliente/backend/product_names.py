"""Utilidades para resolver nombres visibles de categorias de producto."""

from __future__ import annotations

import unicodedata


KNOWN_PRODUCT_DISPLAY_NAMES: dict[str, str] = {
    "punos": "Pu\u00f1os",
    "sillin": "Sill\u00edn",
    "luces": "Luces",
    "camaras": "C\u00e1maras",
    "neumatico": "Neum\u00e1tico",
    "pedales": "Pedales",
    "caramagiola": "Caramagiola",
    "porta-caramagiola": "Porta-caramagiola",
    "cascos": "Cascos",
    "cadenas": "Cadenas",
    "manillas-de-freno": "Manillas de freno",
    "manillas-de-cambio": "Manillas de cambio",
    "tricota": "Tricota",
}

KNOWN_PRODUCT_SKU_PREFIXES: dict[str, str] = {
    "punos": "PUÑ",
}


def slug_to_display_name(slug: str) -> str:
    """Retorna nombre visible desde slug usando traducciones conocidas o fallback."""
    normalized_slug = slug.strip().lower()
    known_display_name = KNOWN_PRODUCT_DISPLAY_NAMES.get(normalized_slug)
    if known_display_name is not None:
        return known_display_name

    return normalized_slug.replace("-", " ").title()


def slug_to_sku_prefix(slug: str) -> str:
    """Retorna prefijo de 3 caracteres para SKU segun categoria."""
    normalized_slug = slug.strip().lower()
    known_prefix = KNOWN_PRODUCT_SKU_PREFIXES.get(normalized_slug)
    if known_prefix is not None:
        return known_prefix

    display_name = slug_to_display_name(normalized_slug)
    return build_reference_segment(display_name, length=3)


def build_reference_segment(raw_value: str, length: int) -> str:
    """Normaliza texto alfanumerico y construye un segmento de largo fijo."""
    normalized = unicodedata.normalize("NFKD", raw_value or "")
    ascii_text = normalized.encode("ascii", "ignore").decode("ascii")
    cleaned = "".join(char for char in ascii_text if char.isalnum()).upper()

    if not cleaned:
        return "X" * length

    return cleaned[:length].ljust(length, "X")


def build_internal_reference(
    producto_slug: str,
    marca: str,
    modelo: str,
    valores_atributo: str,
) -> str:
    """Construye referencia interna en formato TIP-MAR-MOD-A."""
    tip = slug_to_sku_prefix(producto_slug)
    mar = build_reference_segment(marca, length=3)
    mod = build_reference_segment(modelo, length=3)
    atributo = build_reference_segment(valores_atributo, length=1)
    return f"{tip}-{mar}-{mod}-{atributo}"
