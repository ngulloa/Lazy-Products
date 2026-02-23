"""Tests de consultas de inventario en IdRegistry."""

from __future__ import annotations

import csv
import json
import tempfile
import unittest
from pathlib import Path

from cliente.backend.id_registry import INVENTORY_HEADERS, IdRegistry


class IdRegistryQueriesTests(unittest.TestCase):
    """Valida consultas por SKU y Nombre Base en CSV por categoria."""

    def test_sku_exists_returns_true_and_false(self) -> None:
        """Debe encontrar SKU existente y retornar False para no existente."""
        with tempfile.TemporaryDirectory() as temp_dir:
            registry = self._build_registry_with_sample_csv(Path(temp_dir))

            self.assertTrue(registry.sku_exists("punos", "PUN-BIK-ERG-N"))
            self.assertFalse(registry.sku_exists("punos", "SKU-NO-EXISTE"))
            self.assertFalse(registry.sku_exists("punos", ""))

    def test_nombre_base_exists_returns_true_and_false(self) -> None:
        """Debe encontrar Nombre Base existente y retornar False para no existente."""
        with tempfile.TemporaryDirectory() as temp_dir:
            registry = self._build_registry_with_sample_csv(Path(temp_dir))

            self.assertTrue(registry.nombre_base_exists("punos", "Punos Bikeboy Ergonomico"))
            self.assertFalse(registry.nombre_base_exists("punos", "Nombre Base Inexistente"))
            self.assertFalse(registry.nombre_base_exists("punos", ""))

    def test_queries_consider_legacy_and_canonical_slug_files(self) -> None:
        """Debe consultar datos en CSV canonico y legacy de una misma categoria."""
        with tempfile.TemporaryDirectory() as temp_dir:
            registry, _, _ = self._build_registry_with_slug_pair(
                base_path=Path(temp_dir),
                canonical_rows=[
                    self._build_row(
                        base_ean13="780999004001",
                        sku="NEU-CAN-001",
                        nombre_base="Neumatico Canonico",
                    )
                ],
                legacy_rows=[
                    self._build_row(
                        base_ean13="780999004002",
                        sku="NEU-LEG-001",
                        nombre_base="Neumatico Legacy",
                    )
                ],
            )

            self.assertTrue(registry.sku_exists("neumaticos", "NEU-CAN-001"))
            self.assertTrue(registry.sku_exists("neumaticos", "NEU-LEG-001"))
            self.assertTrue(registry.nombre_base_exists("neumaticos", "Neumatico Canonico"))
            self.assertTrue(registry.nombre_base_exists("neumaticos", "Neumatico Legacy"))

    def test_get_next_id_considers_largest_last_id_in_legacy_and_canonical(self) -> None:
        """Debe calcular next_id tomando el mayor correlativo entre canonico y legacy."""
        with tempfile.TemporaryDirectory() as temp_dir:
            registry, _, _ = self._build_registry_with_slug_pair(
                base_path=Path(temp_dir),
                canonical_rows=[
                    self._build_row(
                        base_ean13="780999004010",
                        sku="",
                        nombre_base="",
                    )
                ],
                legacy_rows=[
                    self._build_row(
                        base_ean13="780999004099",
                        sku="",
                        nombre_base="",
                    )
                ],
            )

            next_id = registry.get_next_id("neumaticos")

        self.assertEqual(next_id, "780999004100")

    def test_register_id_with_legacy_slug_writes_only_to_canonical_file(self) -> None:
        """Debe persistir en CSV canonico aunque el slug recibido sea legacy."""
        with tempfile.TemporaryDirectory() as temp_dir:
            registry, canonical_path, legacy_path = self._build_registry_with_slug_pair(
                base_path=Path(temp_dir),
                canonical_rows=[
                    self._build_row(
                        base_ean13="780999004001",
                        sku="",
                        nombre_base="",
                    )
                ],
                legacy_rows=[
                    self._build_row(
                        base_ean13="780999004002",
                        sku="",
                        nombre_base="",
                    )
                ],
            )

            registry.register_id("neumaticos", "780999004200")

            canonical_ids = self._read_base_ean13_values(canonical_path)
            legacy_ids = self._read_base_ean13_values(legacy_path)

        self.assertIn("780999004200", canonical_ids)
        self.assertNotIn("780999004200", legacy_ids)

    def _build_registry_with_sample_csv(self, base_path: Path) -> IdRegistry:
        categories_json = base_path / "utilities" / "categories.json"
        info_products_dir = base_path / "utilities" / "info_products"
        info_products_dir.mkdir(parents=True, exist_ok=True)
        self._write_categories_json(categories_json)

        csv_path = info_products_dir / "punos.csv"
        with csv_path.open("w", newline="", encoding="utf-8") as csv_file:
            writer = csv.writer(csv_file)
            writer.writerow(INVENTORY_HEADERS)
            writer.writerow(
                self._build_row(
                    base_ean13="780999000001",
                    sku="PUN-BIK-ERG-N",
                    nombre_base="Punos Bikeboy Ergonomico",
                )
            )
            writer.writerow(
                self._build_row(
                    base_ean13="780999000002",
                    sku="",
                    nombre_base="",
                )
            )

        return IdRegistry(
            categories_json=categories_json,
            info_products_dir=info_products_dir,
        )

    def _build_registry_with_slug_pair(
        self,
        base_path: Path,
        canonical_rows: list[list[str]],
        legacy_rows: list[list[str]],
    ) -> tuple[IdRegistry, Path, Path]:
        categories_json = base_path / "utilities" / "categories.json"
        info_products_dir = base_path / "utilities" / "info_products"
        info_products_dir.mkdir(parents=True, exist_ok=True)
        self._write_categories_json(categories_json, slug="neumatico", code=4)

        canonical_path = info_products_dir / "neumatico.csv"
        legacy_path = info_products_dir / "neumaticos.csv"
        self._write_inventory_csv(canonical_path, canonical_rows)
        self._write_inventory_csv(legacy_path, legacy_rows)

        registry = IdRegistry(
            categories_json=categories_json,
            info_products_dir=info_products_dir,
        )
        return registry, canonical_path, legacy_path

    @staticmethod
    def _write_inventory_csv(path: Path, rows: list[list[str]]) -> None:
        with path.open("w", newline="", encoding="utf-8") as csv_file:
            writer = csv.writer(csv_file)
            writer.writerow(INVENTORY_HEADERS)
            writer.writerows(rows)

    @staticmethod
    def _build_row(
        base_ean13: str,
        sku: str,
        nombre_base: str,
    ) -> list[str]:
        row = {header: "" for header in INVENTORY_HEADERS}
        row["Base EAN13"] = base_ean13
        row["Referencia interna"] = sku
        row["Nombre Base"] = nombre_base
        return [row[header] for header in INVENTORY_HEADERS]

    @staticmethod
    def _read_base_ean13_values(path: Path) -> list[str]:
        values: list[str] = []
        with path.open("r", newline="", encoding="utf-8") as csv_file:
            reader = csv.DictReader(csv_file)
            for row in reader:
                values.append((row.get("Base EAN13") or "").strip())
        return values

    @staticmethod
    def _write_categories_json(path: Path, slug: str = "punos", code: int = 0) -> None:
        data = {
            "next_code": code + 1,
            "categories": [
                {
                    "slug": slug,
                    "display_name": slug.capitalize(),
                    "code": code,
                }
            ],
        }
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    unittest.main()
