"""Tests para ImportBuilderService."""

from __future__ import annotations

import csv
import tempfile
import unittest
from unittest import mock
from pathlib import Path

from cliente.backend.id_registry import IdRegistry
from servidor.services.import_builder import ImportBuilderService
from shared.csv_schema import IMPORT_HEADERS, INFO_PRODUCTS_HEADERS
from shared.errors import ServiceError
from shared.protocol import ImportProductDraft


class ImportBuilderServiceTests(unittest.TestCase):
    """Valida comportamiento de construccion de CSV de importacion."""

    EXPECTED_IMPORT_HEADERS = list(IMPORT_HEADERS)
    EXPECTED_CATEGORY_HEADERS = list(INFO_PRODUCTS_HEADERS)

    def setUp(self) -> None:
        self.service = ImportBuilderService()

    def test_create_template_creates_file_and_directory(self) -> None:
        """Debe crear directorio y archivo de salida si no existen."""
        with tempfile.TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir) / "output"
            created_path = self.service.create_template(
                output_dir=output_dir,
                filename="import_template.csv",
            )

            self.assertTrue(output_dir.exists())
            self.assertTrue(created_path.exists())
            self.assertEqual(created_path.name, "import_template.csv")

    def test_create_template_writes_expected_header(self) -> None:
        """Debe escribir el header minimo sku,nombre,cantidad."""
        with tempfile.TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir) / "output"
            created_path = self.service.create_template(
                output_dir=output_dir,
                filename="template.csv",
            )

            with created_path.open("r", newline="", encoding="utf-8") as csv_file:
                reader = csv.reader(csv_file)
                header = next(reader)

            self.assertEqual(header, ["sku", "nombre", "cantidad"])

    def test_start_import_session_writes_expected_headers(self) -> None:
        """Debe escribir el header completo de 38 columnas en sesion de importacion."""
        with tempfile.TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir) / "output"
            file_path = self.service.start_import_session(
                output_dir=output_dir,
                filename_stem="inventario",
            )

            with file_path.open("r", newline="", encoding="utf-8") as csv_file:
                reader = csv.reader(csv_file)
                header = next(reader)

            self.assertEqual(header, self.EXPECTED_IMPORT_HEADERS)
            self.assertEqual(len(header), 38)

    def test_append_product_writes_row_with_expected_columns_count(self) -> None:
        """Cada append debe generar exactamente 38 columnas en archivo de sesion."""
        with tempfile.TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir) / "output"
            categories_path = self._create_categories_csv(Path(temp_dir))
            category_inventory_dir = Path(temp_dir) / "info_products"
            service = ImportBuilderService(
                categories_csv_path=categories_path,
                category_inventory_dir=category_inventory_dir,
            )

            file_path = service.start_import_session(
                output_dir=output_dir,
                filename_stem="inventario",
            )
            service.append_product(file_path, self._build_draft())

            with file_path.open("r", newline="", encoding="utf-8") as csv_file:
                rows = list(csv.reader(csv_file))

            self.assertEqual(len(rows), 2)
            self.assertEqual(len(rows[1]), 38)

    def test_append_product_writes_session_and_category_inventory(self) -> None:
        """Debe persistir una fila completa en sesion y en inventario por categoria."""
        with tempfile.TemporaryDirectory() as temp_dir:
            base_path = Path(temp_dir)
            output_dir = base_path / "output"
            category_inventory_dir = base_path / "info_products"
            categories_path = self._create_categories_csv(base_path)

            service = ImportBuilderService(
                categories_csv_path=categories_path,
                category_inventory_dir=category_inventory_dir,
            )
            file_path = service.start_import_session(
                output_dir=output_dir,
                filename_stem="inventario",
            )

            draft = self._build_draft()
            service.append_product(file_path, draft)

            category_path = category_inventory_dir / "punos.csv"
            self.assertTrue(category_path.exists())

            with file_path.open("r", newline="", encoding="utf-8") as csv_file:
                session_rows = list(csv.reader(csv_file))

            with category_path.open("r", newline="", encoding="utf-8") as csv_file:
                category_rows = list(csv.reader(csv_file))

            self.assertEqual(len(session_rows), 2)
            self.assertEqual(len(category_rows), 2)
            self.assertEqual(session_rows[0], self.EXPECTED_IMPORT_HEADERS)
            self.assertEqual(category_rows[0], self.EXPECTED_CATEGORY_HEADERS)

            session_row = session_rows[1]
            category_row = category_rows[1]

            self.assertEqual(session_row[0], "1")
            self.assertEqual(category_row[0], "780999000001")
            self.assertEqual(session_row[3], "7809990000013")
            self.assertEqual(category_row[2], "7809990000013")
            self.assertEqual(session_row[26], "PuÃ±os Bikeboy ErgonÃ³mico/Lock-on")
            self.assertEqual(category_row[25], "PuÃ±os Bikeboy ErgonÃ³mico/Lock-on")
            self.assertEqual(session_row[27], "PuÃ±os Bikeboy ErgonÃ³mico/Lock-on Negro 130mm")
            self.assertEqual(category_row[26], "PuÃ±os Bikeboy ErgonÃ³mico/Lock-on Negro 130mm")
            self.assertEqual(session_row[28], "Repuestos")
            self.assertEqual(category_row[27], "Repuestos")
            self.assertEqual(session_row[29], "Manubrio")
            self.assertEqual(category_row[28], "Manubrio")
            self.assertEqual(session_row[32], "Repuestos / Manubrio")
            self.assertEqual(category_row[31], "Repuestos / Manubrio")
            self.assertEqual(session_row[33], "1")
            self.assertEqual(category_row[32], "1")
            self.assertEqual(session_row[34], "1")
            self.assertEqual(category_row[33], "1")
            self.assertEqual(session_row[37], "TRUE")
            self.assertEqual(category_row[36], "TRUE")

    def test_append_product_persists_tags_with_comma_as_single_field(self) -> None:
        """Debe persistir Etiquetas como un campo CSV unico aunque contenga coma."""
        with tempfile.TemporaryDirectory() as temp_dir:
            base_path = Path(temp_dir)
            output_dir = base_path / "output"
            category_inventory_dir = base_path / "info_products"
            categories_path = self._create_categories_csv(base_path)
            service = ImportBuilderService(
                categories_csv_path=categories_path,
                category_inventory_dir=category_inventory_dir,
            )
            file_path = service.start_import_session(
                output_dir=output_dir,
                filename_stem="inventario",
            )

            service.append_product(
                file_path,
                self._build_draft(etiquetas="MTB, Ruta"),
            )

            category_path = category_inventory_dir / "punos.csv"

            with file_path.open("r", newline="", encoding="utf-8") as csv_file:
                session_rows = list(csv.DictReader(csv_file))
            with category_path.open("r", newline="", encoding="utf-8") as csv_file:
                category_rows = list(csv.DictReader(csv_file))

            self.assertEqual(session_rows[0]["Etiquetas"], "MTB, Ruta")
            self.assertEqual(category_rows[0]["Etiquetas"], "MTB, Ruta")

    def test_append_product_adds_exactly_one_row_to_both_files(self) -> None:
        """Debe agregar exactamente una fila en sesion y categoria por cada append."""
        with tempfile.TemporaryDirectory() as temp_dir:
            base_path = Path(temp_dir)
            output_dir = base_path / "output"
            category_inventory_dir = base_path / "info_products"
            categories_path = self._create_categories_csv(base_path)
            service = ImportBuilderService(
                categories_csv_path=categories_path,
                category_inventory_dir=category_inventory_dir,
            )

            file_path = service.start_import_session(
                output_dir=output_dir,
                filename_stem="inventario",
            )
            category_path = category_inventory_dir / "punos.csv"
            category_path.parent.mkdir(parents=True, exist_ok=True)
            with category_path.open("w", newline="", encoding="utf-8") as csv_file:
                writer = csv.writer(csv_file)
                writer.writerow(self.EXPECTED_CATEGORY_HEADERS)

            with file_path.open("r", newline="", encoding="utf-8") as csv_file:
                session_rows_before = list(csv.reader(csv_file))
            with category_path.open("r", newline="", encoding="utf-8") as csv_file:
                category_rows_before = list(csv.reader(csv_file))

            service.append_product(file_path, self._build_draft())

            with file_path.open("r", newline="", encoding="utf-8") as csv_file:
                session_rows_after = list(csv.reader(csv_file))
            with category_path.open("r", newline="", encoding="utf-8") as csv_file:
                category_rows_after = list(csv.reader(csv_file))

            self.assertEqual(len(session_rows_after), len(session_rows_before) + 1)
            self.assertEqual(len(category_rows_after), len(category_rows_before) + 1)

    def test_append_product_rolls_back_session_when_category_write_fails(self) -> None:
        """Debe revertir sesion si falla escritura de categoria."""
        with tempfile.TemporaryDirectory() as temp_dir:
            base_path = Path(temp_dir)
            output_dir = base_path / "output"
            category_inventory_dir = base_path / "info_products"
            categories_path = self._create_categories_csv(base_path)
            service = ImportBuilderService(
                categories_csv_path=categories_path,
                category_inventory_dir=category_inventory_dir,
            )

            file_path = service.start_import_session(
                output_dir=output_dir,
                filename_stem="inventario",
            )
            draft = self._build_draft()
            category_path = category_inventory_dir / "punos.csv"

            original_write_row = service._write_row
            call_count = 0

            def fail_on_second_write(csv_file: object, row: list[str]) -> None:
                nonlocal call_count
                call_count += 1
                if call_count == 2:
                    raise OSError("Fallo forzado en segunda escritura")
                original_write_row(csv_file, row)

            with mock.patch.object(service, "_write_row", side_effect=fail_on_second_write):
                with self.assertRaises(ServiceError):
                    service.append_product(file_path, draft)

            with file_path.open("r", newline="", encoding="utf-8") as csv_file:
                session_rows = list(csv.reader(csv_file))
            with category_path.open("r", newline="", encoding="utf-8") as csv_file:
                category_rows = list(csv.reader(csv_file))

            self.assertEqual(len(session_rows), 1)
            self.assertEqual(len(category_rows), 1)
            self.assertEqual(session_rows[0], self.EXPECTED_IMPORT_HEADERS)
            self.assertEqual(category_rows[0], self.EXPECTED_CATEGORY_HEADERS)

    def test_finalize_import_session_renames_inprogress_file(self) -> None:
        """Debe renombrar un .inprogress.csv a .csv al finalizar la sesion."""
        with tempfile.TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir) / "output"
            inprogress_path = self.service.start_import_session(
                output_dir=output_dir,
                filename_stem="inventario",
            )
            expected_final_path = inprogress_path.with_name(
                inprogress_path.name.replace(".inprogress.csv", ".csv")
            )

            final_path = self.service.finalize_import_session(inprogress_path)

            self.assertEqual(final_path, expected_final_path)
            self.assertTrue(final_path.exists())
            self.assertFalse(inprogress_path.exists())

    def test_finalize_import_session_resolves_collision_without_overwrite(self) -> None:
        """Debe generar un nombre alternativo cuando el .csv final ya existe."""
        with tempfile.TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir) / "output"
            inprogress_path = self.service.start_import_session(
                output_dir=output_dir,
                filename_stem="inventario",
            )
            original_final_path = inprogress_path.with_name(
                inprogress_path.name.replace(".inprogress.csv", ".csv")
            )
            original_final_path.parent.mkdir(parents=True, exist_ok=True)
            original_final_path.write_text("contenido previo", encoding="utf-8")

            final_path = self.service.finalize_import_session(inprogress_path)
            expected_collision_path = original_final_path.with_name(
                f"{original_final_path.stem}_1.csv"
            )

            self.assertEqual(final_path, expected_collision_path)
            self.assertTrue(final_path.exists())
            self.assertFalse(inprogress_path.exists())
            self.assertEqual(
                original_final_path.read_text(encoding="utf-8"),
                "contenido previo",
            )

    def test_finalize_import_session_requires_inprogress_suffix(self) -> None:
        """Debe fallar cuando el archivo no termina en .inprogress.csv."""
        with tempfile.TemporaryDirectory() as temp_dir:
            invalid_path = Path(temp_dir) / "import_productos_20260101_120000.csv"
            invalid_path.write_text("ID,Producto\n", encoding="utf-8")

            with self.assertRaises(ServiceError):
                self.service.finalize_import_session(invalid_path)

    def test_create_category_then_append_product_works_immediately(self) -> None:
        """Tras crear categoria, append debe funcionar sin fallo de mapeo."""
        with tempfile.TemporaryDirectory() as temp_dir:
            base_path = Path(temp_dir)
            output_dir = base_path / "output"
            utilities_dir = base_path / "utilities"
            categories_json = utilities_dir / "categories.json"
            inventory_categories_csv = utilities_dir / "inventario_categorias.csv"
            info_products_dir = utilities_dir / "info_products"

            self._write_categories_json(categories_json)
            categories_path = self._create_categories_csv(utilities_dir)

            registry = IdRegistry(
                categories_json=categories_json,
                info_products_dir=info_products_dir,
                inventory_categories_csv=inventory_categories_csv,
            )
            service = ImportBuilderService(
                categories_csv_path=categories_path,
                category_inventory_dir=info_products_dir,
            )
            file_path = service.start_import_session(
                output_dir=output_dir,
                filename_stem="inventario",
            )

            # Carga inicial de mapeo para verificar que append posterior no use cache stale.
            service.append_product(file_path, self._build_draft())

            registry.create_category("candado", "Candado")

            with inventory_categories_csv.open("r", newline="", encoding="utf-8") as csv_file:
                mapping_rows = list(csv.DictReader(csv_file))
            self.assertTrue(
                any((row.get("Producto") or "").strip() == "Candado" for row in mapping_rows)
            )

            draft = self._build_draft(
                id_externo="780999013001",
                referencia_interna="CAN-SEG-001",
                producto="Candado",
                producto_slug="candado",
            )
            service.append_product(file_path, draft)

            category_path = info_products_dir / "candado.csv"
            self.assertTrue(category_path.exists())
            with category_path.open("r", newline="", encoding="utf-8") as csv_file:
                rows = list(csv.reader(csv_file))
            self.assertEqual(len(rows), 2)
            self.assertEqual(rows[0], self.EXPECTED_CATEGORY_HEADERS)
            self.assertEqual(
                rows[1][self.EXPECTED_CATEGORY_HEADERS.index("Base EAN13")],
                "780999013001",
            )

    @staticmethod
    def _create_categories_csv(base_path: Path) -> Path:
        csv_path = base_path / "inventario_categorias.csv"
        csv_path.write_text(
            "Producto,Categoría,Subcategoría\n"
            "Puños,Repuestos,Manubrio\n",
            encoding="utf-8",
        )
        return csv_path

    @staticmethod
    def _write_categories_json(path: Path) -> None:
        data = (
            '{\n'
            '  "next_code": 1,\n'
            '  "categories": [\n'
            '    {\n'
            '      "slug": "punos",\n'
            '      "display_name": "Punos",\n'
            '      "code": 0\n'
            "    }\n"
            "  ]\n"
            "}\n"
        )
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(data, encoding="utf-8")

    @staticmethod
    def _build_draft(
        *,
        id_externo: str = "780999000001",
        referencia_interna: str = "PUN-BIK-ERG-N",
        producto: str = "PuÃ±os",
        producto_slug: str = "punos",
        etiquetas: str = "",
    ) -> ImportProductDraft:
        return ImportProductDraft(
            id_externo=id_externo,
            referencia_interna=referencia_interna,
            producto=producto,
            marca="Bikeboy",
            descripcion_sitio_web="Descripcion web",
            descripcion_seo="Descripcion seo",
            modelo="ErgonÃ³mico/Lock-on",
            cantidad_inicial=4,
            atributo="Color",
            valores_atributo="Negro",
            precio_costo=3838.0,
            venta_sin_iva=4193.0,
            largo_envio=150.0,
            ancho_envio=80.0,
            alto_envio=40.0,
            peso_completo=160.0,
            dimensiones_producto="130",
            unidad_medida_dimensiones="mm",
            numero_variantes=1,
            esta_publicado=True,
            rastrear_inventario=True,
            disponible_punto_venta=True,
            producto_slug=producto_slug,
            etiquetas=etiquetas,
        )


if __name__ == "__main__":
    unittest.main()

