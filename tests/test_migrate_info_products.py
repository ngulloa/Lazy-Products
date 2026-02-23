"""Tests para la utilidad de migracion de info_products."""

from __future__ import annotations

import csv
import tempfile
import unittest
from pathlib import Path

from scripts.migrate_info_products import CANONICAL_HEADERS, run_migration


class MigrateInfoProductsTests(unittest.TestCase):
    """Valida reglas de migracion y verificacion del script CLI."""

    def test_missing_track_inventory_defaults_to_one(self) -> None:
        """Debe defaultear Rastrear Inventario a '1' si falta la columna."""
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_root = Path(temp_dir)
            source_dir, destination_dir = self._prepare_repo(repo_root)

            self._write_csv(
                source_dir / "Inventario(camaras).csv",
                header=["ID", "Producto"],
                rows=[["100", "Camara Enduro"]],
            )

            status_code = run_migration(
                repo_root=repo_root,
                dry_run=False,
                migrate=True,
                delete_source=False,
            )

            self.assertEqual(status_code, 0)
            migrated_rows = self._read_csv_as_dicts(destination_dir / "camaras.csv")
            self.assertEqual(migrated_rows[0]["Rastrear Inventario"], "1")

    def test_alias_subcaregoria_maps_to_subcategoria(self) -> None:
        """Debe mapear alias Subcaregoría hacia Subcategoría."""
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_root = Path(temp_dir)
            source_dir, destination_dir = self._prepare_repo(repo_root)

            self._write_csv(
                source_dir / "Inventario(porta-caramagiola).csv",
                header=["ID", "Subcaregoría", "Producto"],
                rows=[["7", "Porta", "Porta Caramagiola"]],
            )

            status_code = run_migration(
                repo_root=repo_root,
                dry_run=False,
                migrate=True,
                delete_source=False,
            )

            self.assertEqual(status_code, 0)
            migrated_rows = self._read_csv_as_dicts(destination_dir / "porta-caramagiola.csv")
            self.assertEqual(migrated_rows[0]["Subcategoría"], "Porta")

    def test_verification_passes_without_mismatch_report(self) -> None:
        """Debe validar fila/columna y no generar reporte cuando todo coincide."""
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_root = Path(temp_dir)
            source_dir, destination_dir = self._prepare_repo(repo_root)

            self._write_csv(
                source_dir / "Inventario(neumaticos).csv",
                header=["ID", "Producto", "Rastrear Inventario", "Subcategoría"],
                rows=[
                    ["1", "Neumatico XC", "0", "MTB"],
                    ["2", "Neumatico Ruta", "1", "Ruta"],
                ],
            )

            status_code = run_migration(
                repo_root=repo_root,
                dry_run=False,
                migrate=True,
                delete_source=False,
            )

            self.assertEqual(status_code, 0)
            report_path = (
                destination_dir
                / "_migration_reports"
                / "neumaticos_mismatches.csv"
            )
            self.assertFalse(report_path.exists())

            destination_path = destination_dir / "neumaticos.csv"
            with destination_path.open("r", newline="", encoding="utf-8-sig") as csv_file:
                reader = csv.reader(csv_file)
                header = next(reader)
            self.assertEqual(header, CANONICAL_HEADERS)

    def _prepare_repo(self, repo_root: Path) -> tuple[Path, Path]:
        """Crea estructura minima de repo para ejecutar migracion."""
        (repo_root / "requirements.txt").write_text("", encoding="utf-8")
        source_dir = repo_root / "infor_prodcts_aux"
        source_dir.mkdir(parents=True, exist_ok=True)
        destination_dir = repo_root / "data" / "utilities" / "info_products"
        destination_dir.mkdir(parents=True, exist_ok=True)
        return source_dir, destination_dir

    def _write_csv(self, path: Path, header: list[str], rows: list[list[str]]) -> None:
        """Escribe un CSV temporal con header y filas."""
        with path.open("w", newline="", encoding="utf-8-sig") as csv_file:
            writer = csv.writer(csv_file, delimiter=",")
            writer.writerow(header)
            writer.writerows(rows)

    def _read_csv_as_dicts(self, path: Path) -> list[dict[str, str]]:
        """Retorna filas de CSV como lista de diccionarios."""
        with path.open("r", newline="", encoding="utf-8-sig") as csv_file:
            reader = csv.DictReader(csv_file)
            return list(reader)


if __name__ == "__main__":
    unittest.main()

