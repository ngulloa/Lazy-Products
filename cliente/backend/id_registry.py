"""Registro local de categorias e inventario por categoria para importacion."""

from __future__ import annotations

import csv
import json
import logging
import re
import unicodedata
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from parametros import CATEGORIES_JSON, INFO_PRODUCTS_DIR, INVENTORY_CATEGORIES_CSV
from servidor.services.inventory_utils import build_barcode, ean13_check_digit
from shared.csv_schema import (
    ID_HEADER,
    INFO_PRODUCTS_HEADERS,
    TRACK_INVENTORY_HEADER,
    resolve_info_products_header,
)
from shared.errors import ServiceError, ValidationError

LOGGER = logging.getLogger(__name__)

INVENTORY_HEADERS: tuple[str, ...] = INFO_PRODUCTS_HEADERS

LEGACY_INVENTORY_HEADERS: tuple[str, ...] = tuple(
    header for header in INVENTORY_HEADERS if header != TRACK_INVENTORY_HEADER
)


@dataclass(slots=True)
class Category:
    """Representa una categoria con slug, nombre visible y codigo interno."""

    slug: str
    display_name: str
    code: int


class IdRegistry:
    """Administra categorias persistentes y correlativos de IDs por categoria."""

    _DEFAULT_CATEGORIES: tuple[Category, ...] = (
        Category(slug="punos", display_name="PuÃ±os", code=0),
        Category(slug="sillin", display_name="SillÃ­n", code=1),
        Category(slug="luces", display_name="Luces", code=2),
        Category(slug="camaras", display_name="CÃ¡maras", code=3),
        Category(slug="neumatico", display_name="NeumÃ¡tico", code=4),
        Category(slug="pedales", display_name="Pedales", code=5),
        Category(slug="caramagiola", display_name="Caramagiola", code=6),
        Category(slug="porta-caramagiola", display_name="Porta-caramagiola", code=7),
        Category(slug="cascos", display_name="Cascos", code=8),
        Category(slug="cadenas", display_name="Cadenas", code=9),
        Category(slug="manillas-de-freno", display_name="Manillas de freno", code=10),
        Category(slug="manillas-de-cambio", display_name="Manillas de cambio", code=11),
        Category(slug="tricota", display_name="Tricota", code=12),
    )
    _SLUG_ALIAS_LOOKUP: dict[str, tuple[str, ...]] = {
        "neumatico": ("neumatico", "neumaticos"),
        "neumaticos": ("neumatico", "neumaticos"),
        "casco": ("casco", "cascos"),
        "cascos": ("casco", "cascos"),
    }
    _INVENTORY_CATEGORIES_HEADERS: tuple[str, str, str] = (
        "Producto",
        "Categoría",
        "Subcategoría",
    )
    _DEFAULT_CATEGORY_LABEL = "Sin clasificar"

    def __init__(
        self,
        categories_json: Path = CATEGORIES_JSON,
        info_products_dir: Path = INFO_PRODUCTS_DIR,
        ids_dir: Path | None = None,
        inventory_categories_csv: Path | None = None,
    ) -> None:
        # ids_dir se mantiene por compatibilidad con tests/callers anteriores.
        self._categories_json = categories_json
        self._info_products_dir = ids_dir or info_products_dir
        self._inventory_categories_csv = (
            inventory_categories_csv
            if inventory_categories_csv is not None
            else self._categories_json.parent / INVENTORY_CATEGORIES_CSV.name
        )
        self._warned_legacy_paths: set[Path] = set()

    def ensure_initialized(self) -> None:
        """Crea utilitarios base si no existen y asegura esquema de CSVs."""
        self._categories_json.parent.mkdir(parents=True, exist_ok=True)
        self._info_products_dir.mkdir(parents=True, exist_ok=True)

        if not self._categories_json.exists():
            data = {
                "next_code": 13,
                "categories": [asdict(category) for category in self._DEFAULT_CATEGORIES],
            }
            self._write_categories_data(data)
            LOGGER.info("categories.json inicializado en: %s", self._categories_json)

        data = self._read_categories_data()
        categories = self._parse_categories(data.get("categories", []))
        self._consolidate_noncanonical_category_files(categories)
        for category in categories:
            self._ensure_category_csv(category.slug)

        # Normaliza tambien archivos adicionales ya presentes en el directorio.
        for csv_path in sorted(self._info_products_dir.glob("*.csv")):
            self._normalize_csv_schema(csv_path)

        LOGGER.info("Utilities inicializado: %s", self._categories_json.parent)

    def _consolidate_noncanonical_category_files(self, categories: list[Category]) -> None:
        """Consolida archivos CSV no canonicos (ej. con acentos) al slug oficial."""
        valid_slugs = {category.slug for category in categories}
        for csv_path in sorted(self._info_products_dir.glob("*.csv")):
            candidate_slug = self._slug_from_filename(csv_path.stem)
            if candidate_slug not in valid_slugs:
                continue

            canonical_path = self._category_csv_path(candidate_slug)
            if csv_path == canonical_path:
                continue

            self._normalize_csv_schema(csv_path)
            source_rows = self._read_csv_rows(csv_path)
            source_data = [row for row in source_rows[1:] if self._row_has_content(row)]
            if not source_data:
                csv_path.unlink(missing_ok=True)
                LOGGER.info("CSV alternativo vacio eliminado: %s", csv_path)
                continue

            if not canonical_path.exists():
                csv_path.replace(canonical_path)
                LOGGER.info(
                    "CSV alternativo consolidado por rename: %s -> %s",
                    csv_path,
                    canonical_path,
                )
                continue

            self._normalize_csv_schema(canonical_path)
            canonical_rows = self._read_csv_rows(canonical_path)
            canonical_has_data = any(
                self._row_has_content(row) for row in canonical_rows[1:]
            )
            if canonical_has_data:
                LOGGER.warning(
                    "CSV alternativo con datos no consolidado para evitar sobreescritura: %s",
                    csv_path,
                )
                continue

            self._write_inventory_csv(canonical_path, source_data)
            csv_path.unlink(missing_ok=True)
            LOGGER.info(
                "CSV alternativo consolidado en archivo canonico: %s -> %s",
                csv_path,
                canonical_path,
            )

    def list_categories(self) -> list[Category]:
        """Retorna categorias registradas."""
        self.ensure_initialized()
        data = self._read_categories_data()
        categories = self._parse_categories(data.get("categories", []))
        categories.sort(key=lambda category: category.code)
        return categories

    def get_next_id(self, slug: str) -> str:
        """Calcula el siguiente ID para una categoria sin persistirlo."""
        category = self._get_category(slug)
        self._ensure_category_csv(category.slug)
        csv_paths = self._category_csv_read_paths(category.slug)

        last_ids = [self._read_last_registered_id(csv_path) for csv_path in csv_paths]
        non_empty_last_ids = [value for value in last_ids if value is not None]
        last_id = (
            max(non_empty_last_ids, key=self._extract_sequence_from_tail)
            if non_empty_last_ids
            else None
        )
        prefix = f"7809990{category.code:02d}"
        sequence = 0 if last_id is None else self._extract_sequence_from_tail(last_id) + 1

        if sequence > 999:
            raise ServiceError(
                "Se alcanzo el maximo correlativo (999) para la categoria solicitada."
            )

        return f"{prefix}{sequence:03d}"

    def load_rows(self, slug: str) -> list[dict[str, str]]:
        """Carga filas de inventario para una categoria."""
        category = self._get_category(slug)
        self._ensure_category_csv(category.slug)
        csv_paths = self._category_csv_read_paths(category.slug)

        rows: list[dict[str, str]] = []
        for csv_path in csv_paths:
            try:
                with csv_path.open("r", newline="", encoding="utf-8-sig") as csv_file:
                    reader = csv.DictReader(csv_file)
                    for raw_row in reader:
                        row: dict[str, str] = {}
                        for key, value in raw_row.items():
                            if key is None:
                                continue
                            row[key] = (value or "").strip()
                        rows.append(row)
            except OSError as exc:
                raise ServiceError(
                    f"No fue posible leer inventario de categoria: {csv_path}"
                ) from exc

        return rows

    def load_duplicate_index(self, slug: str) -> tuple[set[str], set[str]]:
        """Carga en una pasada los sets de SKU y Nombre Base para una categoria."""
        category = self._get_category(slug)
        self._ensure_category_csv(category.slug)
        csv_paths = self._category_csv_read_paths(category.slug)

        sku_values: set[str] = set()
        nombre_base_values: set[str] = set()
        for csv_path in csv_paths:
            try:
                with csv_path.open("r", newline="", encoding="utf-8-sig") as csv_file:
                    reader = csv.DictReader(csv_file)
                    for row in reader:
                        sku = (row.get("Referencia interna") or "").strip()
                        if sku:
                            sku_values.add(sku)

                        nombre_base = (row.get("Nombre Base") or "").strip()
                        if nombre_base:
                            nombre_base_values.add(nombre_base)
            except OSError as exc:
                raise ServiceError(
                    f"No fue posible leer inventario de categoria: {csv_path}"
                ) from exc

        return sku_values, nombre_base_values

    def sku_exists(self, slug: str, sku: str) -> bool:
        """Indica si la referencia interna (SKU) existe en una categoria."""
        expected_sku = sku.strip()
        if not expected_sku:
            return False

        sku_values, _ = self.load_duplicate_index(slug)
        return expected_sku in sku_values

    def nombre_base_exists(self, slug: str, nombre_base: str) -> bool:
        """Indica si existe un Nombre Base en una categoria."""
        expected_name = nombre_base.strip()
        if not expected_name:
            return False

        _, nombre_base_values = self.load_duplicate_index(slug)
        return expected_name in nombre_base_values

    def register_id(self, slug: str, used_id: str) -> None:
        """Registra un ID usado en el CSV de la categoria indicada."""
        category = self._get_category(slug)
        used_id_clean = used_id.strip()
        if not used_id_clean:
            raise ValidationError("used_id no puede estar vacio.")

        csv_path = self._category_csv_path(category.slug)
        self._ensure_category_csv(category.slug)
        row = self._build_placeholder_row(used_id_clean)

        try:
            with csv_path.open("a", newline="", encoding="utf-8") as csv_file:
                writer = csv.writer(csv_file)
                writer.writerow(row)
        except OSError as exc:
            raise ServiceError(f"No fue posible registrar ID en archivo: {csv_path}") from exc

    def create_category(self, slug: str, display_name: str) -> None:
        """Crea una nueva categoria con codigo correlativo y su CSV de inventario."""
        self.ensure_initialized()

        display_name_clean = display_name.strip()
        if not display_name_clean:
            raise ValidationError("display_name no puede estar vacio.")

        data = self._read_categories_data()
        categories = self._parse_categories(data.get("categories", []))
        normalized_slug = self._normalize_slug(slug, categories)
        if not normalized_slug:
            raise ValidationError("slug no puede estar vacio.")

        if any(category.slug == normalized_slug for category in categories):
            raise ValidationError(f"La categoria ya existe: {normalized_slug}")

        next_code = self._parse_next_code(data.get("next_code"))
        categories.append(
            Category(slug=normalized_slug, display_name=display_name_clean, code=next_code)
        )

        updated_data = {
            "next_code": next_code + 1,
            "categories": [asdict(category) for category in categories],
        }
        self._write_categories_data(updated_data)
        self._ensure_category_csv(normalized_slug)
        self._ensure_inventory_category_mapping(display_name_clean)

        LOGGER.info("Categoria creada: %s (%s)", normalized_slug, display_name_clean)

    def _get_category(self, slug: str) -> Category:
        """Retorna una categoria existente o levanta ValidationError."""
        categories = self.list_categories()
        normalized_slug = self._normalize_slug(slug, categories)
        for category in categories:
            if category.slug == normalized_slug:
                return category

        raise ValidationError(f"Categoria no encontrada: {normalized_slug}")

    def _ensure_category_csv(self, slug: str) -> None:
        """Crea o migra el CSV de una categoria al esquema completo de inventario."""
        csv_path = self._category_csv_path(slug)
        if not csv_path.exists():
            self._write_inventory_csv(csv_path, [])
            LOGGER.info("CSV de inventario creado: %s", csv_path)
            return

        self._normalize_csv_schema(csv_path)

    def _normalize_csv_schema(self, csv_path: Path) -> None:
        """Normaliza un CSV al esquema final de inventario."""
        rows = self._read_csv_rows(csv_path)
        if not rows:
            self._write_inventory_csv(csv_path, [])
            LOGGER.info("CSV vacio normalizado con header final: %s", csv_path)
            return

        header = [column.strip() for column in rows[0]]
        data_rows = rows[1:]

        if self._is_legacy_ids_header(header):
            migrated_rows: list[list[str]] = []
            for row in data_rows:
                legacy_id = row[0].strip() if row else ""
                if legacy_id:
                    migrated_rows.append(self._build_placeholder_row(legacy_id))
            self._write_inventory_csv(csv_path, migrated_rows)
            LOGGER.info("CSV legado migrado a esquema final: %s", csv_path)
            return

        if header == list(INVENTORY_HEADERS):
            return

        had_id_column = self._header_contains_id_column(header)
        force_track_inventory = not self._header_contains_column(
            header,
            TRACK_INVENTORY_HEADER,
        )
        normalized_rows = [
            self._normalize_full_row(
                source_header=header,
                source_row=row,
                force_track_inventory=force_track_inventory,
            )
            for row in data_rows
            if self._row_has_content(row)
        ]
        self._write_inventory_csv(csv_path, normalized_rows)

        if had_id_column:
            LOGGER.info("CSV migrado removiendo columna 'ID': %s", csv_path)
            return

        LOGGER.info("CSV normalizado a header canonico de inventario: %s", csv_path)

    def _normalize_full_row(
        self,
        source_header: list[str],
        source_row: list[str],
        force_track_inventory: bool,
    ) -> list[str]:
        """Normaliza una fila desde un schema existente al schema final."""
        source_values: dict[str, str] = {}
        for index, column in enumerate(source_header):
            canonical_column = self._resolve_inventory_header(column)
            if canonical_column is None or canonical_column in source_values:
                continue
            source_values[canonical_column] = (
                source_row[index] if index < len(source_row) else ""
            )

        normalized = {column: source_values.get(column, "") for column in INVENTORY_HEADERS}
        if force_track_inventory:
            normalized[TRACK_INVENTORY_HEADER] = "1"

        return [normalized[column] for column in INVENTORY_HEADERS]

    def _read_last_registered_id(self, csv_path: Path) -> str | None:
        """Obtiene el ultimo Base EAN13 registrado en el CSV de categoria."""
        last_id: str | None = None
        try:
            with csv_path.open("r", newline="", encoding="utf-8-sig") as csv_file:
                reader = csv.DictReader(csv_file)
                for row in reader:
                    value = (row.get("Base EAN13") or "").strip()
                    if value:
                        last_id = value
        except OSError as exc:
            raise ServiceError(f"No fue posible leer IDs registrados: {csv_path}") from exc

        return last_id

    @staticmethod
    def _extract_sequence_from_tail(used_id: str) -> int:
        """Extrae secuencia desde los ultimos 3 digitos del ID registrado."""
        cleaned_id = used_id.strip()
        if len(cleaned_id) < 3:
            raise ServiceError(f"Formato de ID invalido en registro: {used_id}")

        numeric_tail = cleaned_id[-3:]
        if not numeric_tail.isdigit():
            raise ServiceError(f"Formato de ID invalido en registro: {used_id}")

        return int(numeric_tail)

    def _read_categories_data(self) -> dict[str, Any]:
        """Lee el archivo categories.json."""
        try:
            raw_text = self._categories_json.read_text(encoding="utf-8")
        except OSError as exc:
            raise ServiceError("No fue posible leer categories.json.") from exc

        try:
            data = json.loads(raw_text)
        except json.JSONDecodeError as exc:
            raise ServiceError("categories.json tiene formato invalido.") from exc

        if not isinstance(data, dict):
            raise ServiceError("categories.json debe ser un objeto JSON.")
        return data

    def _write_categories_data(self, data: dict[str, Any]) -> None:
        """Escribe categories.json de manera segura (temp + replace)."""
        temp_path = self._categories_json.with_name(f"{self._categories_json.name}.tmp")
        try:
            serialized = json.dumps(data, ensure_ascii=False, indent=2)
            temp_path.write_text(serialized + "\n", encoding="utf-8")
            temp_path.replace(self._categories_json)
        except OSError as exc:
            raise ServiceError("No fue posible persistir categories.json.") from exc
        finally:
            if temp_path.exists():
                temp_path.unlink(missing_ok=True)

    @staticmethod
    def _parse_categories(raw_categories: Any) -> list[Category]:
        """Parsea categorias desde JSON a dataclasses tipadas."""
        if not isinstance(raw_categories, list):
            raise ServiceError("categories debe ser una lista en categories.json.")

        parsed: list[Category] = []
        for item in raw_categories:
            if not isinstance(item, dict):
                raise ServiceError("Cada categoria debe ser un objeto JSON.")
            try:
                category = Category(
                    slug=str(item["slug"]).strip(),
                    display_name=str(item["display_name"]).strip(),
                    code=int(item["code"]),
                )
            except (KeyError, TypeError, ValueError) as exc:
                raise ServiceError("Categoria invalida en categories.json.") from exc

            if not category.slug or not category.display_name:
                raise ServiceError("slug y display_name no pueden estar vacios.")
            parsed.append(category)

        return parsed

    @staticmethod
    def _parse_next_code(raw_next_code: Any) -> int:
        """Valida y retorna next_code como entero no negativo."""
        try:
            next_code = int(raw_next_code)
        except (TypeError, ValueError) as exc:
            raise ServiceError("next_code invalido en categories.json.") from exc

        if next_code < 0:
            raise ServiceError("next_code no puede ser negativo.")
        return next_code

    def _category_csv_path(self, slug: str) -> Path:
        """Retorna ruta CSV asociada al slug."""
        return self._info_products_dir / f"{slug}.csv"

    def _ensure_inventory_category_mapping(self, display_name: str) -> None:
        """Asegura mapeo de categoria/subcategoria para producto recien creado."""
        product_name = display_name.strip()
        if not product_name:
            return

        csv_path = self._inventory_categories_csv
        if not csv_path.exists():
            self._create_inventory_categories_csv(csv_path, product_name)
            return

        try:
            with csv_path.open("r", newline="", encoding="utf-8-sig") as csv_file:
                rows = list(csv.reader(csv_file))
        except OSError as exc:
            raise ServiceError(
                f"No fue posible leer inventario_categorias.csv: {csv_path}"
            ) from exc

        if not rows:
            self._create_inventory_categories_csv(csv_path, product_name)
            return

        header = [value.strip() for value in rows[0]]
        if len(header) < 3:
            raise ServiceError(
                "inventario_categorias.csv tiene un header invalido. "
                "Se esperaban al menos 3 columnas."
            )
        header_index = {name: index for index, name in enumerate(header)}
        missing_columns = [
            name for name in self._INVENTORY_CATEGORIES_HEADERS if name not in header_index
        ]
        if missing_columns:
            missing_str = ", ".join(missing_columns)
            raise ServiceError(
                "inventario_categorias.csv no contiene columnas requeridas: "
                f"{missing_str}"
            )

        product_index = header_index["Producto"]
        category_index = header_index["Categoría"]
        subcategory_index = header_index["Subcategoría"]

        for row in rows[1:]:
            existing_name = row[product_index].strip() if product_index < len(row) else ""
            if existing_name.casefold() == product_name.casefold():
                return

        category_label = self._DEFAULT_CATEGORY_LABEL
        subcategory_label = product_name
        row_to_append = [""] * len(header)
        row_to_append[product_index] = product_name
        row_to_append[category_index] = category_label
        row_to_append[subcategory_index] = subcategory_label
        try:
            with csv_path.open("a", newline="", encoding="utf-8") as csv_file:
                writer = csv.writer(csv_file)
                writer.writerow(row_to_append)
        except OSError as exc:
            raise ServiceError(
                f"No fue posible actualizar inventario_categorias.csv: {csv_path}"
            ) from exc

        LOGGER.info(
            "Mapeo de categoria agregado en inventario_categorias.csv: producto=%s, "
            "categoria=%s, subcategoria=%s",
            product_name,
            category_label,
            subcategory_label,
        )

    def _create_inventory_categories_csv(self, csv_path: Path, product_name: str) -> None:
        """Crea inventario_categorias.csv con header canonico y una fila inicial."""
        header = list(self._INVENTORY_CATEGORIES_HEADERS)
        category_label = self._DEFAULT_CATEGORY_LABEL
        subcategory_label = product_name
        try:
            csv_path.parent.mkdir(parents=True, exist_ok=True)
            with csv_path.open("w", newline="", encoding="utf-8") as csv_file:
                writer = csv.writer(csv_file)
                writer.writerow(header)
                writer.writerow([product_name, category_label, subcategory_label])
        except OSError as exc:
            raise ServiceError(
                f"No fue posible crear inventario_categorias.csv: {csv_path}"
            ) from exc

        LOGGER.info("inventario_categorias.csv inicializado en: %s", csv_path)

    def _category_csv_read_paths(self, canonical_slug: str) -> list[Path]:
        """Retorna rutas de lectura: canonico mas legados existentes."""
        canonical_path = self._category_csv_path(canonical_slug)
        read_paths = [canonical_path]
        alias_group = self._SLUG_ALIAS_LOOKUP.get(canonical_slug)
        if alias_group is None:
            return read_paths

        for alias_slug in alias_group:
            if alias_slug == canonical_slug:
                continue
            legacy_path = self._category_csv_path(alias_slug)
            if not legacy_path.exists():
                continue
            self._warn_legacy_slug_path(legacy_path=legacy_path, canonical_path=canonical_path)
            read_paths.append(legacy_path)

        return read_paths

    def _warn_legacy_slug_path(self, legacy_path: Path, canonical_path: Path) -> None:
        """Registra advertencia una sola vez por ruta legacy detectada."""
        if legacy_path in self._warned_legacy_paths:
            return
        self._warned_legacy_paths.add(legacy_path)
        LOGGER.warning(
            "CSV legacy detectado para info_products: %s. Se recomienda migrar/merge a %s.",
            legacy_path,
            canonical_path,
        )

    def _normalize_slug(
        self,
        slug: str,
        categories: list[Category] | None = None,
    ) -> str:
        """Normaliza slug y lo resuelve al canonico definido en categories.json."""
        normalized_slug = slug.strip().lower()
        if not normalized_slug:
            return normalized_slug

        alias_group = self._SLUG_ALIAS_LOOKUP.get(normalized_slug)
        if alias_group is None:
            return normalized_slug

        if categories is None:
            data = self._read_categories_data()
            categories = self._parse_categories(data.get("categories", []))

        category_slugs = {category.slug for category in categories}
        if normalized_slug in category_slugs:
            return normalized_slug

        for alias_slug in alias_group:
            if alias_slug in category_slugs:
                return alias_slug

        return normalized_slug

    @staticmethod
    def _slug_from_filename(stem: str) -> str:
        """Normaliza nombre de archivo a slug canonico."""
        normalized = unicodedata.normalize("NFKD", stem)
        ascii_stem = normalized.encode("ascii", "ignore").decode("ascii").lower()
        slug = []
        for char in ascii_stem:
            if char.isalnum() or char == "-":
                slug.append(char)
            elif char in {" ", "_"}:
                slug.append("-")
        collapsed = re.sub(r"-{2,}", "-", "".join(slug)).strip("-")
        return collapsed

    @staticmethod
    def _is_legacy_ids_header(header: list[str]) -> bool:
        """Indica si el header corresponde al esquema legado de una sola columna id."""
        return len(header) == 1 and header[0].strip().casefold() == ID_HEADER.casefold()

    @staticmethod
    def _resolve_inventory_header(header: str) -> str | None:
        """Resuelve un header hacia su nombre canonico para inventario."""
        return resolve_info_products_header(header)

    @classmethod
    def _header_contains_column(cls, header: list[str], column_name: str) -> bool:
        """Retorna True si el header contiene la columna indicada (case-insensitive)."""
        target = column_name.casefold()
        return any(column.strip().casefold() == target for column in header)

    @classmethod
    def _header_contains_id_column(cls, header: list[str]) -> bool:
        """Retorna True si el header incluye columna ID exacta (case-insensitive)."""
        return cls._header_contains_column(header, ID_HEADER)

    @staticmethod
    def _row_has_content(row: list[str]) -> bool:
        """Indica si una fila contiene datos significativos."""
        return any(cell.strip() for cell in row)

    @staticmethod
    def _read_csv_rows(csv_path: Path) -> list[list[str]]:
        """Lee todas las filas de un CSV."""
        try:
            with csv_path.open("r", newline="", encoding="utf-8-sig") as csv_file:
                return list(csv.reader(csv_file))
        except OSError as exc:
            raise ServiceError(f"No fue posible leer CSV de categoria: {csv_path}") from exc

    @staticmethod
    def _write_inventory_csv(csv_path: Path, rows: list[list[str]]) -> None:
        """Escribe header final y filas en un CSV de inventario."""
        temp_path = csv_path.with_name(f"{csv_path.name}.tmp")
        try:
            with temp_path.open("w", newline="", encoding="utf-8") as csv_file:
                writer = csv.writer(csv_file)
                writer.writerow(INVENTORY_HEADERS)
                writer.writerows(rows)
            temp_path.replace(csv_path)
        except OSError as exc:
            raise ServiceError(f"No fue posible escribir CSV de categoria: {csv_path}") from exc
        finally:
            if temp_path.exists():
                temp_path.unlink(missing_ok=True)

    @staticmethod
    def _build_placeholder_row(base_ean13: str) -> list[str]:
        """Construye fila placeholder para registrar Base EAN13."""
        base = base_ean13.strip()
        check_digit = ""
        barcode = ""
        if base:
            try:
                check_digit = ean13_check_digit(base)
                barcode = build_barcode(base)
            except ServiceError:
                LOGGER.warning("Base EAN13 invalida al migrar/registrar: %s", base)

        row = {column: "" for column in INVENTORY_HEADERS}
        row["Base EAN13"] = base
        row["Digito verificador"] = check_digit
        row["Código de Barras"] = barcode
        row[TRACK_INVENTORY_HEADER] = "1"
        return [row[column] for column in INVENTORY_HEADERS]


if __name__ == "__main__":
    registry = IdRegistry()
    registry.ensure_initialized()
    print(f"info_products: {registry._info_products_dir}")  # noqa: SLF001
    for csv_path in sorted(registry._info_products_dir.glob("*.csv")):  # noqa: SLF001
        rows = registry._read_csv_rows(csv_path)  # noqa: SLF001
        header = rows[0] if rows else []
        same_header = header == list(INVENTORY_HEADERS)
        has_tracking = TRACK_INVENTORY_HEADER in header
        print(
            f"{csv_path.name}: cols={len(header)} "
            f"same_header={same_header} has_tracking={has_tracking}"
        )

