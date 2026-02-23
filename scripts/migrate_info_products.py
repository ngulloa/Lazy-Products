"""Migra CSV de inventario auxiliar al esquema canonico de info_products."""

from __future__ import annotations

import argparse
import csv
import logging
import re
import shutil
from dataclasses import dataclass
from datetime import datetime
from io import StringIO
from pathlib import Path
from typing import Sequence

from shared.csv_schema import INFO_PRODUCTS_HEADERS, TRACK_INVENTORY_HEADER

LOGGER = logging.getLogger(__name__)

SOURCE_DIRECTORY_NAME = "infor_prodcts_aux"
DESTINATION_DIRECTORY = Path("data") / "utilities" / "info_products"
REPORTS_DIRECTORY_NAME = "_migration_reports"
BACKUP_DIRECTORY_PREFIX = "_backup_"
REPO_MARKERS = (".git", "pyproject.toml", "requirements.txt")
READ_ENCODINGS = ("utf-8-sig", "cp1252")
TRACK_INVENTORY_COLUMN = TRACK_INVENTORY_HEADER

SOURCE_FILENAME_PATTERN = re.compile(r"^Inventario\((?P<category>.+)\)\.csv$")

CANONICAL_HEADERS = list(INFO_PRODUCTS_HEADERS)

HEADER_ALIASES = {
    "subcaregoría": "Subcategoría",
    "subcaregoria": "Subcategoría",
}

CANONICAL_LOOKUP = {column.casefold(): column for column in CANONICAL_HEADERS}


@dataclass(frozen=True)
class InventorySourceFile:
    """Representa un archivo fuente de inventario por categoria."""

    category: str
    path: Path


@dataclass(frozen=True)
class CsvTable:
    """Representa una tabla CSV cargada desde disco."""

    header: list[str]
    rows: list[list[str]]
    encoding: str
    delimiter: str


@dataclass(frozen=True)
class SourceAnalysis:
    """Agrupa metadata de columnas al analizar un CSV fuente."""

    index_by_canonical: dict[str, int]
    missing_columns: list[str]
    ignored_columns: list[str]


@dataclass(frozen=True)
class VerificationMismatch:
    """Representa una diferencia detectada entre source y destino."""

    row_index: int
    column: str
    source_value: str
    dest_value: str


@dataclass(frozen=True)
class VerificationResult:
    """Resume el resultado de verificacion de un archivo migrado."""

    passed: bool
    mismatches: list[VerificationMismatch]
    report_path: Path | None


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    """Parsea argumentos CLI para ejecutar dry-run o migracion."""
    parser = argparse.ArgumentParser(
        description=(
            "Migra Inventario(<categoria>).csv desde infor_prodcts_aux "
            "hacia data/utilities/info_products/<categoria>.csv."
        )
    )
    mode_group = parser.add_mutually_exclusive_group(required=True)
    mode_group.add_argument(
        "--dry-run",
        action="store_true",
        help="Valida lectura y plan de migracion sin escribir archivos.",
    )
    mode_group.add_argument(
        "--migrate",
        action="store_true",
        help="Ejecuta migracion, escribe destino y verifica linea por linea.",
    )
    parser.add_argument(
        "--delete-source",
        action="store_true",
        help=(
            "Borra infor_prodcts_aux al final, solo si la verificacion global "
            "fue exitosa."
        ),
    )
    return parser.parse_args(argv)


def configure_logging() -> None:
    """Configura logging para salida en consola."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(message)s",
    )


def find_repo_root(start: Path | None = None) -> Path:
    """Detecta repo root buscando marcadores desde el directorio actual."""
    current = (start or Path.cwd()).resolve()
    for candidate in (current, *current.parents):
        if any((candidate / marker).exists() for marker in REPO_MARKERS):
            return candidate
    return current


def discover_source_files(source_dir: Path) -> list[InventorySourceFile]:
    """Descubre archivos Inventario(<categoria>).csv en el directorio fuente."""
    if not source_dir.exists():
        raise FileNotFoundError(f"No existe el directorio fuente: {source_dir}")
    if not source_dir.is_dir():
        raise NotADirectoryError(f"La ruta fuente no es directorio: {source_dir}")

    discovered: list[InventorySourceFile] = []
    for path in sorted(source_dir.glob("Inventario(*).csv"), key=lambda item: item.name):
        match = SOURCE_FILENAME_PATTERN.fullmatch(path.name)
        if not match:
            continue
        category = match.group("category")
        discovered.append(InventorySourceFile(category=category, path=path))
    return discovered


def read_csv_table(path: Path) -> CsvTable:
    """Lee un CSV con fallback de encoding y deteccion de delimitador."""
    content, encoding = read_text_with_fallback(path)
    delimiter = detect_delimiter(content)
    reader = csv.reader(StringIO(content), delimiter=delimiter)
    rows = list(reader)

    if not rows:
        return CsvTable(header=[], rows=[], encoding=encoding, delimiter=delimiter)

    header = rows[0]
    data_rows = rows[1:]
    return CsvTable(header=header, rows=data_rows, encoding=encoding, delimiter=delimiter)


def read_text_with_fallback(path: Path) -> tuple[str, str]:
    """Intenta leer texto con utf-8-sig y fallback cp1252."""
    last_error: UnicodeDecodeError | None = None
    for encoding in READ_ENCODINGS:
        try:
            return path.read_text(encoding=encoding), encoding
        except UnicodeDecodeError as exc:
            last_error = exc
    if last_error is not None:
        raise last_error
    raise RuntimeError(f"No fue posible leer el archivo: {path}")


def detect_delimiter(content: str) -> str:
    """Detecta delimitador CSV con Sniffer y fallback a coma."""
    if not content.strip():
        return ","

    sample = content[:8192]
    try:
        dialect = csv.Sniffer().sniff(sample)
        delimiter = getattr(dialect, "delimiter", ",")
        return delimiter or ","
    except csv.Error:
        return ","


def normalize_header(header: str) -> str:
    """Normaliza un header removiendo BOM y espacios extremos."""
    return header.replace("\ufeff", "").strip()


def resolve_canonical_header(header: str) -> str | None:
    """Mapea un header del source hacia el nombre canonico."""
    normalized = normalize_header(header)
    if not normalized:
        return None

    alias_target = HEADER_ALIASES.get(normalized.casefold(), normalized)
    return CANONICAL_LOOKUP.get(alias_target.casefold())


def analyze_source_columns(header: Sequence[str]) -> SourceAnalysis:
    """Determina columnas presentes, faltantes y extras ignoradas."""
    index_by_canonical: dict[str, int] = {}
    ignored_columns: list[str] = []

    for index, raw_header in enumerate(header):
        canonical_header = resolve_canonical_header(raw_header)
        if canonical_header is None:
            cleaned_header = normalize_header(raw_header)
            if cleaned_header:
                ignored_columns.append(cleaned_header)
            continue

        if canonical_header not in index_by_canonical:
            index_by_canonical[canonical_header] = index

    unique_ignored = list(dict.fromkeys(ignored_columns))
    missing_columns = [
        column for column in CANONICAL_HEADERS if column not in index_by_canonical
    ]
    return SourceAnalysis(
        index_by_canonical=index_by_canonical,
        missing_columns=missing_columns,
        ignored_columns=unique_ignored,
    )


def build_destination_rows(
    source_rows: Sequence[Sequence[str]],
    index_by_canonical: dict[str, int],
) -> list[list[str]]:
    """Construye filas destino respetando orden canonico de columnas."""
    destination_rows: list[list[str]] = []

    for source_row in source_rows:
        row_values: list[str] = []
        for canonical_column in CANONICAL_HEADERS:
            source_index = index_by_canonical.get(canonical_column)
            value = value_from_source(
                source_row=source_row,
                source_index=source_index,
                canonical_column=canonical_column,
            )
            row_values.append(value)
        destination_rows.append(row_values)

    return destination_rows


def value_from_source(
    source_row: Sequence[str],
    source_index: int | None,
    canonical_column: str,
) -> str:
    """Obtiene valor desde source y aplica defaults de columnas faltantes."""
    if source_index is None:
        if canonical_column == TRACK_INVENTORY_COLUMN:
            return "1"
        return ""

    source_value = safe_row_value(source_row, source_index)
    if canonical_column == TRACK_INVENTORY_COLUMN and not source_value.strip():
        return "1"
    return source_value


def safe_row_value(row: Sequence[str], index: int) -> str:
    """Retorna el valor de una celda o string vacio si no existe."""
    if index >= len(row):
        return ""

    value = row[index]
    if value is None:
        return ""
    return value


def write_destination_csv(destination_path: Path, rows: Sequence[Sequence[str]]) -> None:
    """Escribe CSV destino con header canonico."""
    destination_path.parent.mkdir(parents=True, exist_ok=True)
    with destination_path.open("w", newline="", encoding="utf-8-sig") as csv_file:
        writer = csv.writer(csv_file, delimiter=",")
        writer.writerow(CANONICAL_HEADERS)
        writer.writerows(rows)


def create_destination_backup(destination_dir: Path) -> Path:
    """Crea backup timestamped copiando CSV existentes del destino."""
    destination_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_dir = destination_dir / f"{BACKUP_DIRECTORY_PREFIX}{timestamp}"
    backup_dir.mkdir(parents=True, exist_ok=False)

    copied_files = 0
    for csv_path in sorted(destination_dir.glob("*.csv"), key=lambda item: item.name):
        shutil.copy2(csv_path, backup_dir / csv_path.name)
        copied_files += 1

    LOGGER.info(
        "Backup creado en %s (%s archivos CSV copiados).",
        backup_dir,
        copied_files,
    )
    return backup_dir


def verify_migrated_file(
    source_file: InventorySourceFile,
    destination_path: Path,
    reports_dir: Path,
) -> VerificationResult:
    """Verifica source vs destino linea por linea y genera reporte si aplica."""
    source_table = read_csv_table(source_file.path)
    source_analysis = analyze_source_columns(source_table.header)

    destination_table = read_csv_table(destination_path)
    destination_analysis = analyze_source_columns(destination_table.header)

    mismatches: list[VerificationMismatch] = []
    source_rows_count = len(source_table.rows)
    destination_rows_count = len(destination_table.rows)

    if source_rows_count != destination_rows_count:
        mismatches.append(
            VerificationMismatch(
                row_index=0,
                column="__row_count__",
                source_value=str(source_rows_count),
                dest_value=str(destination_rows_count),
            )
        )

    comparable_rows = min(source_rows_count, destination_rows_count)
    for row_offset in range(comparable_rows):
        source_row = source_table.rows[row_offset]
        destination_row = destination_table.rows[row_offset]
        row_index = row_offset + 1

        for column, source_column_index in source_analysis.index_by_canonical.items():
            source_value = safe_row_value(source_row, source_column_index)
            destination_column_index = destination_analysis.index_by_canonical.get(column)
            if destination_column_index is None:
                destination_value = ""
            else:
                destination_value = safe_row_value(destination_row, destination_column_index)

            if (
                column == TRACK_INVENTORY_COLUMN
                and not source_value.strip()
                and destination_value == "1"
            ):
                continue

            if source_value != destination_value:
                mismatches.append(
                    VerificationMismatch(
                        row_index=row_index,
                        column=column,
                        source_value=source_value,
                        dest_value=destination_value,
                    )
                )

    report_path = reports_dir / f"{source_file.category}_mismatches.csv"
    if mismatches:
        write_mismatch_report(report_path, mismatches)
        return VerificationResult(
            passed=False,
            mismatches=mismatches,
            report_path=report_path,
        )

    if report_path.exists():
        report_path.unlink()
    return VerificationResult(passed=True, mismatches=[], report_path=None)


def write_mismatch_report(
    report_path: Path,
    mismatches: Sequence[VerificationMismatch],
) -> None:
    """Escribe archivo CSV de diferencias detectadas durante verificacion."""
    report_path.parent.mkdir(parents=True, exist_ok=True)
    with report_path.open("w", newline="", encoding="utf-8-sig") as csv_file:
        writer = csv.writer(csv_file, delimiter=",")
        writer.writerow(["row_index", "column", "source_value", "dest_value"])
        for mismatch in mismatches:
            writer.writerow(
                [
                    mismatch.row_index,
                    mismatch.column,
                    mismatch.source_value,
                    mismatch.dest_value,
                ]
            )


def validate_delete_source_guard(
    repo_root: Path,
    source_dir: Path,
    source_files: Sequence[InventorySourceFile],
) -> None:
    """Valida guardas estrictas antes de borrar directorio fuente."""
    if source_dir.name != SOURCE_DIRECTORY_NAME:
        raise ValueError(
            "Borrado abortado: el directorio fuente no se llama "
            f"{SOURCE_DIRECTORY_NAME}."
        )

    if not is_relative_to(source_dir.resolve(), repo_root.resolve()):
        raise ValueError("Borrado abortado: directorio fuente fuera del repo root.")

    if not source_dir.exists() or not source_dir.is_dir():
        raise ValueError("Borrado abortado: directorio fuente inexistente o invalido.")

    entries = sorted(source_dir.iterdir(), key=lambda item: item.name)
    if any(not entry.is_file() for entry in entries):
        raise ValueError("Borrado abortado: source contiene subdirectorios.")

    actual_names = {entry.name for entry in entries}
    expected_names = {source.path.name for source in source_files}

    if any(SOURCE_FILENAME_PATTERN.fullmatch(name) is None for name in actual_names):
        raise ValueError(
            "Borrado abortado: source contiene archivos fuera del patron "
            "Inventario(<categoria>).csv."
        )

    if actual_names != expected_names:
        raise ValueError(
            "Borrado abortado: contenido de source no coincide con los archivos "
            "esperados de la migracion."
        )


def is_relative_to(path: Path, base: Path) -> bool:
    """Compatibilidad para verificar si un path esta dentro de otro."""
    try:
        path.relative_to(base)
        return True
    except ValueError:
        return False


def run_migration(
    repo_root: Path,
    *,
    dry_run: bool,
    migrate: bool,
    delete_source: bool,
) -> int:
    """Ejecuta dry-run o migracion completa segun flags."""
    source_dir = repo_root / SOURCE_DIRECTORY_NAME
    destination_dir = repo_root / DESTINATION_DIRECTORY
    reports_dir = destination_dir / REPORTS_DIRECTORY_NAME

    source_files = discover_source_files(source_dir)
    if not source_files:
        LOGGER.warning("No se encontraron archivos fuente en %s.", source_dir)
        return 0

    LOGGER.info(
        "Categorias detectadas para migracion: %s",
        ", ".join(source.category for source in source_files),
    )

    if dry_run:
        dry_run_failed = False
        for source_file in source_files:
            try:
                source_table = read_csv_table(source_file.path)
                source_analysis = analyze_source_columns(source_table.header)
                destination_path = destination_dir / f"{source_file.category}.csv"

                LOGGER.info(
                    "DRY-RUN %s -> %s | filas=%s | faltantes=%s | "
                    "extra_ignoradas=%s",
                    source_file.path,
                    destination_path,
                    len(source_table.rows),
                    source_analysis.missing_columns,
                    source_analysis.ignored_columns,
                )
            except (OSError, csv.Error, UnicodeDecodeError, ValueError):
                LOGGER.exception(
                    "Fallo en dry-run para %s.",
                    source_file.path,
                )
                dry_run_failed = True
        return 1 if dry_run_failed else 0

    if not migrate:
        LOGGER.error("Debe indicar --dry-run o --migrate.")
        return 1

    create_destination_backup(destination_dir)

    all_verified = True
    for source_file in source_files:
        destination_path = destination_dir / f"{source_file.category}.csv"
        try:
            source_table = read_csv_table(source_file.path)
            source_analysis = analyze_source_columns(source_table.header)
            destination_rows = build_destination_rows(
                source_rows=source_table.rows,
                index_by_canonical=source_analysis.index_by_canonical,
            )
            write_destination_csv(destination_path=destination_path, rows=destination_rows)

            verification = verify_migrated_file(
                source_file=source_file,
                destination_path=destination_path,
                reports_dir=reports_dir,
            )
            verification_status = "OK" if verification.passed else "CON DIFERENCIAS"
            if not verification.passed:
                all_verified = False

            LOGGER.info(
                "MIGRATE %s -> %s | filas=%s | faltantes=%s | "
                "extra_ignoradas=%s | verificacion=%s",
                source_file.path,
                destination_path,
                len(source_table.rows),
                source_analysis.missing_columns,
                source_analysis.ignored_columns,
                verification_status,
            )

            if verification.report_path is not None:
                LOGGER.warning(
                    "Reporte de diferencias generado: %s (%s mismatches).",
                    verification.report_path,
                    len(verification.mismatches),
                )
        except (OSError, csv.Error, UnicodeDecodeError, ValueError):
            LOGGER.exception("Fallo migrando %s.", source_file.path)
            all_verified = False

    if delete_source:
        if not all_verified:
            LOGGER.error(
                "No se borra %s porque la verificacion global no fue exitosa.",
                source_dir,
            )
            return 1

        try:
            validate_delete_source_guard(
                repo_root=repo_root,
                source_dir=source_dir,
                source_files=source_files,
            )
            shutil.rmtree(source_dir)
            LOGGER.info("Directorio fuente eliminado: %s", source_dir)
        except (OSError, ValueError):
            LOGGER.exception("No fue posible borrar %s.", source_dir)
            return 1

    return 0 if all_verified else 1


def main(argv: Sequence[str] | None = None) -> int:
    """Punto de entrada CLI."""
    configure_logging()
    args = parse_args(argv)
    if args.delete_source and not args.migrate:
        LOGGER.error("--delete-source requiere --migrate.")
        return 1

    repo_root = find_repo_root()
    LOGGER.info("Repo root detectado: %s", repo_root)
    return run_migration(
        repo_root=repo_root,
        dry_run=args.dry_run,
        migrate=args.migrate,
        delete_source=args.delete_source,
    )


if __name__ == "__main__":
    raise SystemExit(main())


