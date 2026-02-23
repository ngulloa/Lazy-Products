"""Tests para migracion y lectura de IDs en IdRegistry."""

from __future__ import annotations

import csv
import json
import tempfile
import unittest
from pathlib import Path

from cliente.backend.id_registry import (
    INVENTORY_HEADERS,
    LEGACY_INVENTORY_HEADERS,
    TRACK_INVENTORY_HEADER,
    IdRegistry,
)


class IdRegistryTests(unittest.TestCase):
    """Valida migracion de CSV legado y calculo de siguiente ID."""

    def test_migrate_legacy_single_column_csv_preserves_existing_ids(self) -> None:
        """Debe migrar CSV legado `id` sin perder IDs existentes."""
        with tempfile.TemporaryDirectory() as temp_dir:
            base_path = Path(temp_dir)
            categories_json = base_path / "utilities" / "categories.json"
            info_products_dir = base_path / "utilities" / "info_products"
            info_products_dir.mkdir(parents=True, exist_ok=True)
            self._write_categories_json(categories_json)

            legacy_path = info_products_dir / "punos.csv"
            legacy_path.write_text(
                "id\n"
                "780999000001\n"
                "780999000002\n",
                encoding="utf-8",
            )

            registry = IdRegistry(
                categories_json=categories_json,
                info_products_dir=info_products_dir,
            )
            registry.ensure_initialized()

            with legacy_path.open("r", newline="", encoding="utf-8") as csv_file:
                rows = list(csv.reader(csv_file))

        tracking_index = INVENTORY_HEADERS.index(TRACK_INVENTORY_HEADER)
        self.assertEqual(rows[0], list(INVENTORY_HEADERS))
        self.assertEqual(len(rows[0]), 37)
        self.assertEqual(rows[1][0], "780999000001")
        self.assertEqual(rows[1][1], "3")
        self.assertEqual(rows[1][2], "7809990000013")
        self.assertEqual(rows[1][tracking_index], "1")
        self.assertEqual(rows[2][0], "780999000002")
        self.assertEqual(rows[2][1], "0")
        self.assertEqual(rows[2][2], "7809990000020")
        self.assertEqual(rows[2][tracking_index], "1")

    def test_migrate_full_schema_without_tracking_column_sets_default_tracking(self) -> None:
        """Si falta columna de tracking, debe insertarse con valor 1 en todas las filas."""
        with tempfile.TemporaryDirectory() as temp_dir:
            base_path = Path(temp_dir)
            categories_json = base_path / "utilities" / "categories.json"
            info_products_dir = base_path / "utilities" / "info_products"
            info_products_dir.mkdir(parents=True, exist_ok=True)
            self._write_categories_json(categories_json)

            csv_path = info_products_dir / "punos.csv"
            with csv_path.open("w", newline="", encoding="utf-8") as csv_file:
                writer = csv.writer(csv_file)
                writer.writerow(LEGACY_INVENTORY_HEADERS)
                row = [""] * len(LEGACY_INVENTORY_HEADERS)
                row[0] = "780999000001"
                row[1] = "3"
                row[2] = "7809990000013"
                writer.writerow(row)

            registry = IdRegistry(
                categories_json=categories_json,
                info_products_dir=info_products_dir,
            )
            registry.ensure_initialized()

            with csv_path.open("r", newline="", encoding="utf-8") as csv_file:
                rows = list(csv.reader(csv_file))

        tracking_index = INVENTORY_HEADERS.index(TRACK_INVENTORY_HEADER)
        self.assertEqual(rows[0], list(INVENTORY_HEADERS))
        self.assertEqual(rows[1][0], "780999000001")
        self.assertEqual(rows[1][1], "3")
        self.assertEqual(rows[1][tracking_index], "1")

    def test_ensure_initialized_removes_id_column_case_insensitive(self) -> None:
        """Debe remover columna ID/Id/id y mantener datos del resto de columnas."""
        with tempfile.TemporaryDirectory() as temp_dir:
            base_path = Path(temp_dir)
            categories_json = base_path / "utilities" / "categories.json"
            info_products_dir = base_path / "utilities" / "info_products"
            info_products_dir.mkdir(parents=True, exist_ok=True)
            self._write_categories_json(categories_json)

            csv_path = info_products_dir / "punos.csv"
            with csv_path.open("w", newline="", encoding="utf-8") as csv_file:
                writer = csv.writer(csv_file)
                writer.writerow(["Id", *INVENTORY_HEADERS])
                first_row = ["11", *[""] * len(INVENTORY_HEADERS)]
                first_row[1 + INVENTORY_HEADERS.index("Base EAN13")] = "780999000001"
                first_row[1 + INVENTORY_HEADERS.index("Referencia interna")] = "PUN-001"
                writer.writerow(first_row)
                second_row = ["12", *[""] * len(INVENTORY_HEADERS)]
                second_row[1 + INVENTORY_HEADERS.index("Base EAN13")] = "780999000002"
                second_row[1 + INVENTORY_HEADERS.index("Nombre Base")] = "Punos Test"
                writer.writerow(second_row)

            registry = IdRegistry(
                categories_json=categories_json,
                info_products_dir=info_products_dir,
            )
            registry.ensure_initialized()

            with csv_path.open("r", newline="", encoding="utf-8") as csv_file:
                rows = list(csv.reader(csv_file))

        self.assertEqual(rows[0], list(INVENTORY_HEADERS))
        self.assertNotIn("ID", rows[0])
        self.assertEqual(rows[1][INVENTORY_HEADERS.index("Base EAN13")], "780999000001")
        self.assertEqual(rows[1][INVENTORY_HEADERS.index("Referencia interna")], "PUN-001")
        self.assertEqual(rows[2][INVENTORY_HEADERS.index("Base EAN13")], "780999000002")
        self.assertEqual(rows[2][INVENTORY_HEADERS.index("Nombre Base")], "Punos Test")

    def test_get_next_id_uses_last_base_ean13_after_migration(self) -> None:
        """Debe leer Base EAN13 migrado y continuar el correlativo correctamente."""
        with tempfile.TemporaryDirectory() as temp_dir:
            base_path = Path(temp_dir)
            categories_json = base_path / "utilities" / "categories.json"
            info_products_dir = base_path / "utilities" / "info_products"
            info_products_dir.mkdir(parents=True, exist_ok=True)
            self._write_categories_json(categories_json)

            legacy_path = info_products_dir / "punos.csv"
            legacy_path.write_text(
                "id\n"
                "780999000001\n"
                "780999000002\n",
                encoding="utf-8",
            )

            registry = IdRegistry(
                categories_json=categories_json,
                info_products_dir=info_products_dir,
            )
            registry.ensure_initialized()
            next_id = registry.get_next_id("punos")

        self.assertEqual(next_id, "780999000003")

    def test_ensure_initialized_creates_csvs_with_new_inventory_header(self) -> None:
        """Si no existe estructura, debe crear CSVs con header nuevo."""
        with tempfile.TemporaryDirectory() as temp_dir:
            base_path = Path(temp_dir)
            categories_json = base_path / "utilities" / "categories.json"
            info_products_dir = base_path / "utilities" / "info_products"

            registry = IdRegistry(
                categories_json=categories_json,
                info_products_dir=info_products_dir,
            )
            registry.ensure_initialized()
            categories = registry.list_categories()

            for category in categories:
                csv_path = info_products_dir / f"{category.slug}.csv"
                self.assertTrue(csv_path.exists())
                with csv_path.open("r", newline="", encoding="utf-8") as csv_file:
                    header = next(csv.reader(csv_file))
                self.assertEqual(header, list(INVENTORY_HEADERS))

    def test_create_category_updates_categories_inventory_and_mapping(self) -> None:
        """Debe crear categoria utilizable y actualizar inventario_categorias.csv."""
        with tempfile.TemporaryDirectory() as temp_dir:
            base_path = Path(temp_dir)
            categories_json = base_path / "utilities" / "categories.json"
            info_products_dir = base_path / "utilities" / "info_products"
            inventory_categories_csv = base_path / "utilities" / "inventario_categorias.csv"
            info_products_dir.mkdir(parents=True, exist_ok=True)
            self._write_categories_json(categories_json)
            inventory_categories_csv.write_text(
                "Producto,Categoría,Subcategoría\n"
                "Punos,Repuestos,Manubrio\n",
                encoding="utf-8",
            )

            registry = IdRegistry(
                categories_json=categories_json,
                info_products_dir=info_products_dir,
                inventory_categories_csv=inventory_categories_csv,
            )
            registry.create_category("candado", "Candado")

            categories_data = json.loads(categories_json.read_text(encoding="utf-8"))
            created = [
                item
                for item in categories_data.get("categories", [])
                if str(item.get("slug", "")).strip() == "candado"
            ]
            self.assertEqual(len(created), 1)

            created_csv_path = info_products_dir / "candado.csv"
            self.assertTrue(created_csv_path.exists())
            with created_csv_path.open("r", newline="", encoding="utf-8") as csv_file:
                header = next(csv.reader(csv_file))
            self.assertEqual(header, list(INVENTORY_HEADERS))

            with inventory_categories_csv.open("r", newline="", encoding="utf-8") as csv_file:
                rows = list(csv.DictReader(csv_file))
            created_mapping = [
                row
                for row in rows
                if (row.get("Producto") or "").strip() == "Candado"
            ]
            self.assertEqual(len(created_mapping), 1)
            self.assertEqual(
                (created_mapping[0].get("Categoría") or "").strip(),
                "Sin clasificar",
            )
            self.assertEqual(
                (created_mapping[0].get("Subcategoría") or "").strip(),
                "Candado",
            )

    @staticmethod
    def _write_categories_json(path: Path) -> None:
        data = {
            "next_code": 1,
            "categories": [
                {
                    "slug": "punos",
                    "display_name": "Punos",
                    "code": 0,
                }
            ],
        }
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    unittest.main()
