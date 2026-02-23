"""Pure formatter for product details clipboard text."""

from __future__ import annotations

import math
import re
import unicodedata

from shared.protocol import ImportProductDraft

_NUMERIC_PURE_PATTERN = re.compile(r"^[+-]?\d+(?:[.,]\d+)?$")
_NUMBER_PATTERN = re.compile(r"[+-]?\d+(?:[.,]\d+)?")
_NO_TIENE = "no tiene"


def format_product_details_clipboard_text(
    draft: ImportProductDraft,
    nombre_comercial: str,
    observaciones_raw: str,
) -> str:
    """Builds the clipboard block as ``Campo: valor`` lines."""
    nombre = (nombre_comercial or "").strip()
    categoria_principal = (draft.producto or "").strip()
    marca = (draft.marca or "").strip()
    modelo = (draft.modelo or "").strip()
    material = str(getattr(draft, "material", "") or "").strip()
    dimensiones = _normalize_dimensions_by_category(
        draft.dimensiones_producto,
        categoria_principal,
    )
    peso_completo = normalize_weight_to_grams(draft.peso_completo)
    observaciones = _friendly_observations(
        observaciones_raw,
        (draft.etiquetas or "").strip(),
    )

    lines = [
        f"Nombre Comercial: {nombre}",
        f"Categor\u00eda Principal: {categoria_principal}",
    ]
    if marca:
        lines.append(f"Marca: {marca}")
    if modelo:
        lines.append(f"Modelo: {modelo}")
    if material:
        lines.append(f"Material: {material}")

    lines.append(f"Dimensiones Producto: {dimensiones}")
    lines.append(f"Peso completo: {peso_completo}")

    valores_atributo = (draft.valores_atributo or "").strip()
    atributo = (draft.atributo or "").strip()
    if (
        draft.numero_variantes > 1
        and atributo.casefold() != _NO_TIENE
        and valores_atributo
    ):
        lines.append(f"Atributo: {atributo}")
        lines.append(f"Valores Atributo: {valores_atributo}")

    lines.append(f"Observaciones: {observaciones}")
    return "\n".join(lines)


def _is_numeric_pure(value: str) -> bool:
    """Returns True when value is a plain integer/decimal number."""
    return bool(_NUMERIC_PURE_PATTERN.fullmatch((value or "").strip()))


def _normalize_dimensions_by_category(
    dimensiones_producto: str,
    categoria_principal: str,
) -> str:
    """Normalizes dimension text according to product category rules."""
    dimensiones = (dimensiones_producto or "").strip()
    if not _is_numeric_pure(dimensiones):
        return dimensiones

    categoria_normalizada = _normalize_category(categoria_principal)
    category_tokens = {
        token for token in re.split(r"[^a-z0-9]+", categoria_normalizada) if token
    }
    if category_tokens & {"neumatico", "neumaticos", "camara", "camaras"}:
        return f'{dimensiones}"'

    return dimensiones


def normalize_weight_to_grams(value: float | int | str | None) -> str:
    """Normalizes different weight representations to grams."""
    grams: float | None = None

    if value is None:
        return ""

    if isinstance(value, (float, int)):
        grams = float(value)
    else:
        raw_text = value.strip()
        if not raw_text:
            return ""

        parsed_number = _extract_number(raw_text)
        if parsed_number is None:
            return ""

        text_lower = raw_text.casefold()
        if "kg" in text_lower:
            grams = parsed_number * 1000.0
        elif "g" in text_lower:
            grams = parsed_number
        elif _is_numeric_pure(raw_text):
            grams = parsed_number
        else:
            return ""

    if grams is None or not math.isfinite(grams):
        return ""

    return f"{_format_number(grams)} g"


def _friendly_observations(observaciones_raw: str, etiquetas: str = "") -> str:
    """Applies conservative cleanup to observations text."""
    text = (observaciones_raw or "").strip()
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"\n+", ", ", text)
    text = text.replace(";", ", ")
    text = re.sub(r"\s+", " ", text)
    text = re.sub(r"\s*,\s*", ", ", text)
    text = re.sub(r"\busb\b", "USB", text, flags=re.IGNORECASE)
    text = text.strip(" ,")

    tags_clean = (etiquetas or "").strip()
    if tags_clean:
        if text:
            return f"{text} Etiquetas: {tags_clean}."
        return f"Etiquetas: {tags_clean}."

    return text


def _normalize_category(value: str) -> str:
    """Normalizes category text for accent/case-insensitive comparisons."""
    normalized = unicodedata.normalize("NFKD", (value or "").strip())
    ascii_text = normalized.encode("ascii", "ignore").decode("ascii")
    return ascii_text.casefold()


def _extract_number(text: str) -> float | None:
    """Extracts first decimal number from text."""
    match = _NUMBER_PATTERN.search(text)
    if not match:
        return None

    try:
        return float(match.group(0).replace(",", "."))
    except ValueError:
        return None


def _format_number(value: float) -> str:
    """Formats number with at most two decimals and no trailing zeros."""
    rounded_integer = round(value)
    if math.isclose(value, rounded_integer, abs_tol=1e-9):
        return str(int(rounded_integer))

    formatted = f"{value:.2f}".rstrip("0").rstrip(".")
    if formatted == "-0":
        return "0"
    return formatted
