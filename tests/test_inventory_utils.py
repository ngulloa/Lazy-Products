"""Tests para utilidades de inventario."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from servidor.services.inventory_utils import (
    build_barcode,
    build_nombre_base,
    build_nombre_comercial,
    compute_volumen,
    ean13_check_digit,
    format_clp,
    get_category_for_producto,
    load_category_mapping,
)


class InventoryUtilsTests(unittest.TestCase):
    """Valida funciones utilitarias de inventario."""

    def test_ean13_check_digit(self) -> None:
        """Debe calcular correctamente el digito verificador de EAN-13."""
        self.assertEqual(ean13_check_digit("780999000001"), "3")

    def test_build_barcode(self) -> None:
        """Debe construir EAN-13 completo."""
        self.assertEqual(build_barcode("780999000001"), "7809990000013")

    def test_format_clp(self) -> None:
        """Debe formatear CLP sin decimales."""
        self.assertEqual(format_clp(4990), "$4,990")

    def test_nombre_base_y_comercial_con_dimensiones(self) -> None:
        """Debe construir nombre base y comercial con dimensiones + unidad."""
        nombre_base = build_nombre_base("Puños", "Velo", "Ergo")
        nombre_comercial = build_nombre_comercial(nombre_base, "Negro", "130", "mm")

        self.assertEqual(nombre_base, "Puños Velo Ergo")
        self.assertEqual(nombre_comercial, "Puños Velo Ergo Negro 130mm")

    def test_nombre_comercial_sin_dimensiones(self) -> None:
        """No debe agregar bloque de dimensiones cuando falte dimension o unidad."""
        nombre_base = build_nombre_base("Puños", "Velo", "Ergo")

        sin_dimension = build_nombre_comercial(nombre_base, "Negro", "", "mm")
        sin_unidad = build_nombre_comercial(nombre_base, "Negro", "130", "")

        self.assertEqual(sin_dimension, "Puños Velo Ergo Negro")
        self.assertEqual(sin_unidad, "Puños Velo Ergo Negro")

    def test_compute_volumen(self) -> None:
        """Debe multiplicar largo, ancho y alto."""
        self.assertEqual(compute_volumen(150, 80, 40), 480000)

    def test_load_category_mapping_y_lookup(self) -> None:
        """Debe cargar mapeo desde CSV temporal y resolver categoria por producto."""
        csv_content = (
            "Producto,Categoría,Subcategoría\n"
            "Puños,Repuestos,Manubrio\n"
            "Tricota,Indumentaria,Tricotas\n"
        )

        with tempfile.TemporaryDirectory() as temp_dir:
            csv_path = Path(temp_dir) / "categorias.csv"
            csv_path.write_text(csv_content, encoding="utf-8")

            mapping = load_category_mapping(csv_path)
            categoria, subcategoria = get_category_for_producto(mapping, "Puños")

        self.assertEqual(categoria, "Repuestos")
        self.assertEqual(subcategoria, "Manubrio")


if __name__ == "__main__":
    unittest.main()
