"""Tests de cache de duplicados en AppController."""

from __future__ import annotations

import csv
import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from cliente.backend.controller import AppController
from cliente.backend.gateway import LocalServerGateway
from cliente.backend.id_registry import IdRegistry
from servidor.services.import_builder import ImportBuilderService
from shared.csv_schema import INFO_PRODUCTS_HEADERS
from shared.protocol import ImportProductDraft, StartImportSessionRequest


class AppControllerCacheTests(unittest.TestCase):
    """Valida cache por categoria para chequeos de duplicados."""

    def test_load_category_index_uses_cache_per_slug(self) -> None:
        """Debe leer CSV una sola vez al consultar repetidamente el mismo slug."""
        with tempfile.TemporaryDirectory() as temp_dir:
            base_path = Path(temp_dir)
            controller, registry, _ = self._build_controller(base_path)
            self._write_info_products_csv(
                base_path / "utilities" / "info_products" / "punos.csv",
                rows=[
                    self._build_info_row(
                        base_ean13="780999000001",
                        sku="PUN-001",
                        nombre_base="Punos Marca Modelo",
                    )
                ],
            )

            with mock.patch.object(
                registry,
                "load_duplicate_index",
                wraps=registry.load_duplicate_index,
            ) as spy:
                controller.load_category_index("punos")
                controller.load_category_index("punos")
                self.assertEqual(spy.call_count, 1)

            self.assertTrue(controller.is_duplicate_sku("punos", "PUN-001"))
            self.assertTrue(controller.is_duplicate_name("punos", "Punos Marca Modelo"))
            self.assertFalse(controller.is_duplicate_sku("punos", "SKU-NO-EXISTE"))

    def test_on_import_next_updates_duplicate_cache_without_reloading(self) -> None:
        """Tras append exitoso, cache en memoria debe reflejar SKU y Nombre Base nuevos."""
        with tempfile.TemporaryDirectory() as temp_dir:
            base_path = Path(temp_dir)
            controller, registry, gateway = self._build_controller(base_path)

            controller.load_category_index("punos")
            self.assertFalse(controller.is_duplicate_sku("punos", "PUN-NEW-001"))
            self.assertFalse(controller.is_duplicate_name("punos", "Punos Marca Modelo"))

            start_response = gateway.start_import_session(
                StartImportSessionRequest(
                    output_dir=str(base_path / "output"),
                    filename_stem="inventario",
                )
            )
            controller._import_session_path = start_response.inprogress_path  # noqa: SLF001

            controller.on_import_next(
                self._build_draft(
                    id_externo="780999000123",
                    referencia_interna="PUN-NEW-001",
                    producto="Punos",
                    marca="Marca",
                    modelo="Modelo",
                    producto_slug="punos",
                )
            )

            with mock.patch.object(
                registry,
                "load_duplicate_index",
                side_effect=AssertionError("No deberia recargar desde disco"),
            ):
                self.assertTrue(controller.is_duplicate_sku("punos", "PUN-NEW-001"))
                self.assertTrue(controller.is_duplicate_name("punos", "Punos Marca Modelo"))

    def _build_controller(
        self,
        base_path: Path,
    ) -> tuple[AppController, IdRegistry, LocalServerGateway]:
        utilities_dir = base_path / "utilities"
        categories_json = utilities_dir / "categories.json"
        info_products_dir = utilities_dir / "info_products"
        inventory_categories_csv = utilities_dir / "inventario_categorias.csv"
        self._write_categories_json(categories_json)
        self._write_inventory_categories_csv(inventory_categories_csv)
        self._write_info_products_csv(info_products_dir / "punos.csv", rows=[])

        id_registry = IdRegistry(
            categories_json=categories_json,
            info_products_dir=info_products_dir,
            inventory_categories_csv=inventory_categories_csv,
        )
        gateway = LocalServerGateway(
            import_builder_service=ImportBuilderService(
                categories_csv_path=inventory_categories_csv,
                category_inventory_dir=info_products_dir,
            )
        )
        controller = AppController(gateway=gateway, id_registry=id_registry)
        return controller, id_registry, gateway

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

    @staticmethod
    def _write_inventory_categories_csv(path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            "Producto,Categoría,Subcategoría\n"
            "Punos,Repuestos,Manubrio\n",
            encoding="utf-8",
        )

    @staticmethod
    def _write_info_products_csv(path: Path, rows: list[list[str]]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", newline="", encoding="utf-8") as csv_file:
            writer = csv.writer(csv_file)
            writer.writerow(INFO_PRODUCTS_HEADERS)
            writer.writerows(rows)

    @staticmethod
    def _build_info_row(
        base_ean13: str,
        sku: str,
        nombre_base: str,
    ) -> list[str]:
        row = {header: "" for header in INFO_PRODUCTS_HEADERS}
        row["Base EAN13"] = base_ean13
        row["Referencia interna"] = sku
        row["Nombre Base"] = nombre_base
        return [row[header] for header in INFO_PRODUCTS_HEADERS]

    @staticmethod
    def _build_draft(
        id_externo: str,
        referencia_interna: str,
        producto: str,
        marca: str,
        modelo: str,
        producto_slug: str,
    ) -> ImportProductDraft:
        return ImportProductDraft(
            id_externo=id_externo,
            referencia_interna=referencia_interna,
            producto=producto,
            marca=marca,
            descripcion_sitio_web="Descripcion web",
            descripcion_seo="Descripcion seo",
            modelo=modelo,
            cantidad_inicial=1,
            atributo="Color",
            valores_atributo="Negro",
            precio_costo=1000.0,
            venta_sin_iva=1500.0,
            largo_envio=10.0,
            ancho_envio=10.0,
            alto_envio=10.0,
            peso_completo=100.0,
            dimensiones_producto="130",
            unidad_medida_dimensiones="mm",
            numero_variantes=1,
            esta_publicado=True,
            rastrear_inventario=True,
            disponible_punto_venta=True,
            producto_slug=producto_slug,
        )


if __name__ == "__main__":
    unittest.main()
