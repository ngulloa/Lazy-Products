"""Fuente unica y helpers para etiquetas de productos."""

from __future__ import annotations

AVAILABLE_TAGS: tuple[str, ...] = (
    "MTB",
    "Ruta",
    "BMX",
    "Enduro",
    "Descenso",
    "Urbano",
    "Cicloturismo",
    "Infantil",
    "E-Bike",
    "Montaña",
    "Seguridad",
    "Visibilidad",
    "Reflectante",
    "Nocturno",
    "Lluvia",
    "Invierno",
    "Verano",
    "Cómodo",
    "Ergonómico",
    "Ligero",
    "Compacto",
    "Antipinchazos",
    "Tubeless",
    "Recargable USB",
    "Mantenimiento",
    "Reparación",
    "Limpieza",
    "Lubricación",
    "Transporte",
    "Almacenamiento",
    "Bolsos",
    "Squeeze",
)


def normalize_selected_tags(tags: list[str]) -> str:
    """Normaliza una lista de tags para guardarla en CSV."""
    normalized: list[str] = []
    seen: set[str] = set()

    for raw_tag in tags:
        tag = raw_tag.strip()
        if not tag or tag in seen:
            continue
        seen.add(tag)
        normalized.append(tag)

    return ", ".join(normalized)


def parse_tags_csv(value: str) -> list[str]:
    """Parsea una cadena CSV de etiquetas y retorna tags limpios."""
    return [tag for tag in (part.strip() for part in value.split(",")) if tag]
