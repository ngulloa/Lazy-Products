"""Servicio para generar archivos de importacion."""

from __future__ import annotations

import csv
import logging
from datetime import datetime
from pathlib import Path
from typing import TextIO

from parametros import INFO_PRODUCTS_DIR, INVENTORY_CATEGORIES_CSV
from servidor.services.inventory_utils import (
    build_barcode,
    build_image_url,
    build_nombre_base,
    build_nombre_comercial,
    compute_volumen,
    ean13_check_digit,
    format_clp,
    get_category_for_producto,
    load_category_mapping,
)
from shared.csv_schema import (
    IMPORT_HEADERS as CANONICAL_IMPORT_HEADERS,
    INFO_PRODUCTS_HEADERS as CANONICAL_INFO_PRODUCTS_HEADERS,
)
from shared.errors import ServiceError
from shared.protocol import ImportProductDraft

LOGGER = logging.getLogger(__name__)


class ImportBuilderService:
    """Construye archivos CSV para flujos de importacion."""

    TEMPLATE_HEADERS = ("sku", "nombre", "cantidad")
    IMPORT_HEADERS = CANONICAL_IMPORT_HEADERS
    CATEGORY_INVENTORY_HEADERS = CANONICAL_INFO_PRODUCTS_HEADERS
    TAGS_HEADER = "Etiquetas"
    IVA_RATE = 0.19

    def __init__(
        self,
        categories_csv_path: Path = INVENTORY_CATEGORIES_CSV,
        category_inventory_dir: Path = INFO_PRODUCTS_DIR,
        inventory_categories_csv: Path | None = None,
    ) -> None:
        # inventory_categories_csv se mantiene por compatibilidad con tests/callers anteriores.
        self._categories_csv_path = inventory_categories_csv or categories_csv_path
        self._category_inventory_dir = category_inventory_dir

    def create_template(self, output_dir: Path, filename: str) -> Path:
        """Crea un CSV plantilla y retorna su ruta."""
        if not filename.strip():
            raise ServiceError("El nombre del archivo de plantilla no puede estar vacio.")

        if output_dir.exists() and not output_dir.is_dir():
            raise ServiceError(f"La ruta de salida no es un directorio: {output_dir}")

        output_path = output_dir / filename

        try:
            output_dir.mkdir(parents=True, exist_ok=True)
            with output_path.open("w", newline="", encoding="utf-8") as csv_file:
                writer = csv.writer(csv_file)
                writer.writerow(self.TEMPLATE_HEADERS)
        except OSError as exc:
            raise ServiceError("No fue posible escribir el archivo de plantilla.") from exc

        LOGGER.info("Archivo de importacion creado: %s", output_path)
        return output_path

    def start_import_session(self, output_dir: Path, filename_stem: str) -> Path:
        """Inicia una sesion de importacion creando un CSV en progreso con headers."""
        stem = filename_stem.strip()
        if not stem:
            raise ServiceError("El prefijo de archivo para importacion no puede estar vacio.")

        if output_dir.exists() and not output_dir.is_dir():
            raise ServiceError(f"La ruta de salida no es un directorio: {output_dir}")

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        inprogress_path = output_dir / f"{stem}_{timestamp}.inprogress.csv"

        try:
            output_dir.mkdir(parents=True, exist_ok=True)
            inprogress_path = self._resolve_collision(inprogress_path)
            with inprogress_path.open("w", newline="", encoding="utf-8") as csv_file:
                writer = csv.writer(csv_file)
                writer.writerow(self.IMPORT_HEADERS)
        except OSError as exc:
            LOGGER.exception(
                "Error al iniciar sesion de importacion en archivo inprogress: %s",
                inprogress_path,
            )
            raise ServiceError("No fue posible iniciar la sesion de importacion.") from exc

        LOGGER.info("Archivo inprogress creado para sesion de importacion: %s", inprogress_path)
        LOGGER.debug(
            "Header de importacion escrito en %s con %d columnas",
            inprogress_path,
            len(self.IMPORT_HEADERS),
        )
        return inprogress_path

    def append_product(self, file_path: Path, product: ImportProductDraft) -> None:
        """Agrega fila de producto al archivo de sesion y al inventario por categoria."""
        if not file_path.exists() or not file_path.is_file():
            raise ServiceError(f"No existe archivo de sesion para importar: {file_path}")

        LOGGER.debug("Agregando fila a sesion de importacion en progreso: %s", file_path)
        session_headers = self._ensure_session_file(file_path)
        mapping = self._get_category_mapping()

        inventory_row = self._build_inventory_row(
            product=product,
            mapping=mapping,
            next_row_id=self._next_row_id(file_path),
        )
        row_by_header = {
            header: inventory_row[index]
            for index, header in enumerate(self.IMPORT_HEADERS)
        }
        session_row = [row_by_header.get(header, "") for header in session_headers]

        category_path = self._category_inventory_path(product.producto_slug)
        category_headers = self._ensure_inventory_file(category_path)
        category_row = [row_by_header.get(header, "") for header in category_headers]

        self._append_rows_with_rollback(
            session_path=file_path,
            session_row=session_row,
            category_path=category_path,
            category_row=category_row,
        )

        LOGGER.info(
            "Fila agregada en sesion de importacion: path=%s, row_id=%s",
            file_path,
            row_by_header.get(self.IMPORT_HEADERS[0], ""),
        )
        LOGGER.debug("Fila agregada en inventario por categoria: path=%s", category_path)

        LOGGER.info(
            "Fila agregada a sesion y categoria: session=%s, category=%s",
            file_path,
            category_path,
        )

    def _append_rows_with_rollback(
        self,
        session_path: Path,
        session_row: list[str],
        category_path: Path,
        category_row: list[str],
    ) -> None:
        """Escribe filas en sesion y categoria de forma transaccional."""
        try:
            with (
                session_path.open("r+", newline="", encoding="utf-8") as session_file,
                category_path.open("r+", newline="", encoding="utf-8") as category_file,
            ):
                session_file.seek(0, 2)
                category_file.seek(0, 2)
                session_offset = session_file.tell()
                category_offset = category_file.tell()

                session_written = False
                category_written = False
                try:
                    self._write_row(session_file, session_row)
                    session_written = True
                    self._write_row(category_file, category_row)
                    category_written = True
                except Exception as exc:
                    self._rollback_file_if_needed(
                        csv_file=session_file,
                        original_offset=session_offset,
                        should_rollback=session_written,
                        file_path=session_path,
                    )
                    self._rollback_file_if_needed(
                        csv_file=category_file,
                        original_offset=category_offset,
                        should_rollback=category_written,
                        file_path=category_path,
                    )
                    LOGGER.exception(
                        "Error al persistir fila de importacion. "
                        "Rollback ejecutado: session=%s, category=%s",
                        session_path,
                        category_path,
                    )
                    raise ServiceError(
                        "No fue posible agregar la fila de importacion. "
                        "Se revirtieron los cambios parciales."
                    ) from exc
        except ServiceError:
            raise
        except OSError as exc:
            LOGGER.exception(
                "Error al abrir archivos para append transaccional: session=%s, category=%s",
                session_path,
                category_path,
            )
            raise ServiceError(
                "No fue posible agregar la fila de importacion en los archivos de destino."
            ) from exc

    @staticmethod
    def _write_row(csv_file: TextIO, row: list[str]) -> None:
        """Escribe una fila CSV y fuerza flush para detectar errores temprano."""
        writer = csv.writer(csv_file, quoting=csv.QUOTE_ALL)
        writer.writerow(row)
        csv_file.flush()

    @staticmethod
    def _rollback_file_if_needed(
        csv_file: TextIO,
        original_offset: int,
        should_rollback: bool,
        file_path: Path,
    ) -> None:
        """Revierte escritura parcial truncando al offset original."""
        if not should_rollback:
            return

        try:
            csv_file.seek(original_offset)
            csv_file.truncate()
            csv_file.flush()
        except OSError:
            LOGGER.exception("Error al revertir archivo CSV tras fallo de append: %s", file_path)

    def finalize_import_session(self, file_path: Path) -> Path:
        """Finaliza una sesion renombrando el archivo en progreso a definitivo."""
        if not file_path.exists() or not file_path.is_file():
            raise ServiceError(f"No existe archivo de sesion para finalizar: {file_path}")

        if not file_path.name.endswith(".inprogress.csv"):
            raise ServiceError(
                "El archivo de sesion a finalizar debe terminar en '.inprogress.csv': "
                f"{file_path}"
            )

        final_name = file_path.name.replace(".inprogress.csv", ".csv")
        final_path = self._resolve_collision(file_path.with_name(final_name))

        LOGGER.info(
            "Finalizando sesion de importacion: origen=%s, destino=%s",
            file_path,
            final_path,
        )

        try:
            renamed_path = file_path.replace(final_path)
        except OSError as exc:
            LOGGER.exception(
                "Error al renombrar archivo de importacion: origen=%s, destino=%s",
                file_path,
                final_path,
            )
            raise ServiceError(
                "No fue posible finalizar la sesion de importacion. "
                f"No se pudo renombrar {file_path} a {final_path}."
            ) from exc

        LOGGER.info("Sesion de importacion finalizada: %s", renamed_path)
        return renamed_path

    def _build_inventory_row(
        self,
        product: ImportProductDraft,
        mapping: dict[str, tuple[str, str]],
        next_row_id: int,
    ) -> list[str]:
        """Construye una fila de inventario para cualquier destino CSV."""
        producto = self._clean_single_line(product.producto)
        marca = self._clean_single_line(product.marca)
        modelo = self._clean_single_line(product.modelo)
        atributo = self._clean_single_line(product.atributo)
        valores_atributo = self._clean_single_line(product.valores_atributo)
        base_ean13 = self._clean_single_line(product.id_externo)
        referencia_interna = self._clean_single_line(product.referencia_interna)
        descripcion_web = self._clean_multiline(product.descripcion_sitio_web)
        descripcion_seo = self._clean_multiline(product.descripcion_seo)
        dimensiones_producto = self._clean_single_line(product.dimensiones_producto)
        unidad_dimensiones = self._clean_single_line(product.unidad_medida_dimensiones)
        etiquetas = self._clean_single_line(product.etiquetas or "")
        material = self._clean_single_line(product.material or "")

        digito_verificador = ean13_check_digit(base_ean13)
        codigo_barras = build_barcode(base_ean13)

        nombre_base = build_nombre_base(producto, marca, modelo)
        nombre_comercial = build_nombre_comercial(
            nombre_base=nombre_base,
            valores_atributo=valores_atributo,
            dimensiones_producto=dimensiones_producto,
            unidad=unidad_dimensiones,
        )

        categoria, subcategoria = get_category_for_producto(mapping, producto)
        categoria_producto = f"{categoria} / {subcategoria}"

        volumen = compute_volumen(product.largo_envio, product.ancho_envio, product.alto_envio)
        venta_con_iva = round(product.venta_sin_iva * (1 + self.IVA_RATE))

        return [
            str(next_row_id),
            base_ean13,
            digito_verificador,
            codigo_barras,
            producto,
            marca,
            modelo,
            str(product.cantidad_inicial),
            atributo,
            valores_atributo,
            format_clp(venta_con_iva),
            format_clp(product.venta_sin_iva),
            referencia_interna,
            self._format_number(product.largo_envio),
            self._format_number(product.ancho_envio),
            self._format_number(product.alto_envio),
            self._format_number(product.peso_completo),
            dimensiones_producto,
            material,
            "",
            format_clp(product.precio_costo),
            str(product.numero_variantes),
            "",
            descripcion_web,
            descripcion_seo,
            referencia_interna,
            nombre_base,
            nombre_comercial,
            categoria,
            subcategoria,
            self._format_number(volumen),
            build_image_url(referencia_interna),
            categoria_producto,
            "1" if product.esta_publicado else "0",
            "1" if product.rastrear_inventario else "0",
            etiquetas,
            "Clubike",
            "TRUE" if product.disponible_punto_venta else "FALSE",
        ]

    def _category_inventory_path(self, producto_slug: str) -> Path:
        """Retorna la ruta del inventario por categoria."""
        slug = producto_slug.strip().lower()
        if not slug:
            raise ServiceError("producto_slug es obligatorio para registrar inventario por categoria.")
        return self._category_inventory_dir / f"{slug}.csv"

    def _ensure_session_file(self, path: Path) -> list[str]:
        """Valida sesion y retorna el header activo para escritura de filas."""
        if not path.exists() or not path.is_file():
            raise ServiceError(f"No existe archivo de sesion para importar: {path}")

        try:
            with path.open("r", newline="", encoding="utf-8-sig") as csv_file:
                rows = list(csv.reader(csv_file))
        except OSError as exc:
            raise ServiceError(f"No fue posible leer archivo de sesion: {path}") from exc

        header = [column.strip() for column in (rows[0] if rows else [])]
        if not header:
            try:
                with path.open("w", newline="", encoding="utf-8") as csv_file:
                    writer = csv.writer(csv_file)
                    writer.writerow(self.IMPORT_HEADERS)
            except OSError as exc:
                raise ServiceError(
                    f"No fue posible inicializar archivo de sesion: {path}"
                ) from exc
            return list(self.IMPORT_HEADERS)

        if header == list(self.IMPORT_HEADERS):
            return header

        legacy_without_tags = self._headers_without_tags(self.IMPORT_HEADERS)
        if header == legacy_without_tags:
            migrated_header = self._append_tags_column(path=path, rows=rows)
            LOGGER.info(
                "Sesion de importacion migrada agregando columna '%s' al final: %s",
                self.TAGS_HEADER,
                path,
            )
            return migrated_header

        if header == legacy_without_tags + [self.TAGS_HEADER]:
            return header

        raise ServiceError(f"Header invalido en archivo de sesion: {path}")

    def _ensure_inventory_file(self, path: Path) -> list[str]:
        """Asegura inventario por categoria y retorna el header activo."""
        if not path.exists():
            try:
                path.parent.mkdir(parents=True, exist_ok=True)
                with path.open("w", newline="", encoding="utf-8") as csv_file:
                    writer = csv.writer(csv_file)
                    writer.writerow(self.CATEGORY_INVENTORY_HEADERS)
            except OSError as exc:
                raise ServiceError(
                    f"No fue posible crear inventario de categoria: {path}"
                ) from exc
            return list(self.CATEGORY_INVENTORY_HEADERS)

        try:
            with path.open("r", newline="", encoding="utf-8-sig") as csv_file:
                reader = csv.reader(csv_file)
                rows = list(reader)
        except OSError as exc:
            raise ServiceError(f"No fue posible leer inventario de categoria: {path}") from exc

        header = [column.strip() for column in (rows[0] if rows else [])]
        if not header:
            try:
                with path.open("w", newline="", encoding="utf-8") as csv_file:
                    writer = csv.writer(csv_file)
                    writer.writerow(self.CATEGORY_INVENTORY_HEADERS)
            except OSError as exc:
                raise ServiceError(
                    f"No fue posible inicializar inventario de categoria: {path}"
                ) from exc
            return list(self.CATEGORY_INVENTORY_HEADERS)

        if header == list(self.CATEGORY_INVENTORY_HEADERS):
            return header

        legacy_without_tags = self._headers_without_tags(self.CATEGORY_INVENTORY_HEADERS)
        if header == legacy_without_tags:
            migrated_header = self._append_tags_column(path=path, rows=rows)
            LOGGER.info(
                "Inventario de categoria migrado agregando columna '%s' al final: %s",
                self.TAGS_HEADER,
                path,
            )
            return migrated_header

        if header == legacy_without_tags + [self.TAGS_HEADER]:
            return header

        legacy_import_without_tags = self._headers_without_tags(self.IMPORT_HEADERS)
        if header == legacy_import_without_tags:
            migrated_rows = [
                self._normalize_row_length(row[1:], len(legacy_without_tags)) + [""]
                for row in rows[1:]
                if len(row) > 1 and self._row_has_content(row[1:])
            ]
            migrated_header = [*legacy_without_tags, self.TAGS_HEADER]
            self._rewrite_csv(path, migrated_header, migrated_rows)
            LOGGER.info(
                "Inventario de categoria migrado removiendo ID y agregando columna '%s': %s",
                self.TAGS_HEADER,
                path,
            )
            return migrated_header

        if header == list(self.IMPORT_HEADERS):
            migrated_rows = [
                row[1:]
                for row in rows[1:]
                if len(row) > 1 and self._row_has_content(row[1:])
            ]
            self._write_inventory_file(path, migrated_rows)
            LOGGER.info("Inventario de categoria migrado removiendo columna ID: %s", path)
            return list(self.CATEGORY_INVENTORY_HEADERS)

        raise ServiceError(f"Header invalido en inventario de categoria: {path}")

    @classmethod
    def _write_inventory_file(cls, path: Path, rows: list[list[str]]) -> None:
        """Escribe inventario por categoria con header canonico sin columna ID."""
        cls._rewrite_csv(path, list(cls.CATEGORY_INVENTORY_HEADERS), rows)

    @classmethod
    def _append_tags_column(cls, path: Path, rows: list[list[str]]) -> list[str]:
        """Agrega columna Etiquetas al final y rellena filas existentes con vacio."""
        header = [column.strip() for column in (rows[0] if rows else [])]
        if cls.TAGS_HEADER in header:
            return header

        expected_columns = len(header)
        migrated_rows = []
        for row in rows[1:]:
            normalized_row = cls._normalize_row_length(row, expected_columns)
            normalized_row.append("")
            migrated_rows.append(normalized_row)

        migrated_header = [*header, cls.TAGS_HEADER]
        cls._rewrite_csv(path, migrated_header, migrated_rows)
        return migrated_header

    @classmethod
    def _rewrite_csv(cls, path: Path, header: list[str], rows: list[list[str]]) -> None:
        """Reescribe un CSV completo con header y filas normalizadas."""
        temp_path = path.with_name(f"{path.name}.tmp")
        try:
            with temp_path.open("w", newline="", encoding="utf-8") as csv_file:
                writer = csv.writer(csv_file)
                writer.writerow(header)
                writer.writerows(rows)
            temp_path.replace(path)
        except OSError as exc:
            raise ServiceError(f"No fue posible escribir archivo CSV: {path}") from exc
        finally:
            if temp_path.exists():
                temp_path.unlink(missing_ok=True)

    @classmethod
    def _headers_without_tags(cls, headers: tuple[str, ...]) -> list[str]:
        """Retorna una copia de headers sin la columna Etiquetas."""
        return [column for column in headers if column != cls.TAGS_HEADER]

    @staticmethod
    def _normalize_row_length(row: list[str], expected_columns: int) -> list[str]:
        """Normaliza largo de fila para que coincida con un header dado."""
        normalized_row = list(row[:expected_columns])
        if len(normalized_row) < expected_columns:
            normalized_row.extend([""] * (expected_columns - len(normalized_row)))
        return normalized_row

    @staticmethod
    def _row_has_content(row: list[str]) -> bool:
        """Retorna True cuando la fila contiene al menos una celda con datos."""
        return any(cell.strip() for cell in row)

    @staticmethod
    def _resolve_collision(path: Path) -> Path:
        """Resuelve colisiones de nombre para no sobrescribir archivos existentes."""
        if not path.exists():
            return path

        name = path.name
        suffix = ".csv" if name.endswith(".csv") else ""
        prefix = name[:-len(suffix)] if suffix else name

        counter = 1
        candidate = path
        while candidate.exists():
            candidate = path.with_name(f"{prefix}_{counter}{suffix}")
            counter += 1

        return candidate

    @staticmethod
    def _clean_multiline(text: str) -> str:
        """Normaliza texto multilinea para almacenamiento CSV."""
        cleaned = text.replace("\r\n", "\n").replace("\r", "\n").replace("\x00", "")
        return cleaned.strip()

    @staticmethod
    def _clean_single_line(text: str) -> str:
        """Normaliza texto en una sola linea para almacenamiento CSV."""
        cleaned = text.replace("\r\n", "\n").replace("\r", "\n").replace("\x00", "")
        cleaned = cleaned.replace("\n", " ")
        return cleaned.strip()

    def _get_category_mapping(self) -> dict[str, tuple[str, str]]:
        """Carga categorias de inventario desde CSV."""
        return load_category_mapping(self._categories_csv_path)

    @staticmethod
    def _format_number(value: float) -> str:
        """Formatea valores numericos evitando .0 innecesario."""
        numeric_value = float(value)
        if numeric_value.is_integer():
            return str(int(numeric_value))
        return f"{numeric_value:.2f}".rstrip("0").rstrip(".")

    @staticmethod
    def _next_row_id(file_path: Path) -> int:
        """Obtiene el siguiente ID correlativo basado en el archivo actual."""
        last_id = 0
        try:
            with file_path.open("r", newline="", encoding="utf-8-sig") as csv_file:
                reader = csv.reader(csv_file)
                next(reader, None)
                for row in reader:
                    if not row:
                        continue
                    raw_id = row[0].strip()
                    if raw_id.isdigit():
                        last_id = max(last_id, int(raw_id))
        except OSError as exc:
            raise ServiceError(
                "No fue posible leer el archivo de importacion para calcular el ID."
            ) from exc

        return last_id + 1

