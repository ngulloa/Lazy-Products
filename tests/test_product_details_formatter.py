"""Tests for product details clipboard formatter."""

from __future__ import annotations

import unittest

from cliente.backend.product_details_formatter import (
    format_product_details_clipboard_text,
    normalize_weight_to_grams,
)
from shared.protocol import ImportProductDraft


class ProductDetailsFormatterTests(unittest.TestCase):
    """Validates clipboard text formatting for product details dialog."""

    def test_normalize_weight_kg_string(self) -> None:
        """Converts kg text input to grams."""
        self.assertEqual(normalize_weight_to_grams("0.12 kg"), "120 g")

    def test_normalize_weight_float_value(self) -> None:
        """Treats numeric inputs as grams."""
        self.assertEqual(normalize_weight_to_grams(160.0), "160 g")

    def test_dimensions_neumaticos_adds_inches(self) -> None:
        """Adds inch quotes for pure numeric tire dimensions."""
        draft = self._build_draft(
            producto="Neum\u00e1ticos",
            dimensiones_producto="29",
        )

        text = format_product_details_clipboard_text(
            draft=draft,
            nombre_comercial="Neumatico Test",
            observaciones_raw="",
        )

        self.assertIn('Dimensiones Producto: 29"', text)

    def test_does_not_include_variant_lines_when_single_variant(self) -> None:
        """Skips variant details when numero_variantes is 1."""
        draft = self._build_draft(
            numero_variantes=1,
            atributo="Color",
            valores_atributo="Negro",
        )

        text = format_product_details_clipboard_text(
            draft=draft,
            nombre_comercial="Producto Test",
            observaciones_raw="Observacion",
        )

        self.assertNotIn("\nAtributo:", text)
        self.assertNotIn("\nValores Atributo:", text)

    def test_appends_tags_inside_observaciones_line(self) -> None:
        """Appends tags text at the end of Observaciones line."""
        draft = self._build_draft(etiquetas="MTB, Ruta")

        text = format_product_details_clipboard_text(
            draft=draft,
            nombre_comercial="Producto Test",
            observaciones_raw="Incluye usb",
        )

        self.assertIn(
            "Observaciones: Incluye USB Etiquetas: MTB, Ruta.",
            text,
        )

    def test_omits_marca_and_modelo_when_empty(self) -> None:
        """Omits optional Marca and Modelo lines when values are empty."""
        draft = self._build_draft(marca="", modelo="")

        text = format_product_details_clipboard_text(
            draft=draft,
            nombre_comercial="Producto Test",
            observaciones_raw="",
        )

        self.assertNotIn("\nMarca:", text)
        self.assertNotIn("\nModelo:", text)

    @staticmethod
    def _build_draft(
        *,
        producto: str = "Luces",
        marca: str = "MarcaX",
        modelo: str = "ModeloY",
        atributo: str = "No tiene",
        valores_atributo: str = "",
        dimensiones_producto: str = "12",
        peso_completo: float = 160.0,
        numero_variantes: int = 1,
        etiquetas: str = "",
        material: str = "",
    ) -> ImportProductDraft:
        return ImportProductDraft(
            id_externo="780999000001",
            referencia_interna="REF-001",
            producto=producto,
            marca=marca,
            descripcion_sitio_web="",
            descripcion_seo="",
            modelo=modelo,
            cantidad_inicial=1,
            atributo=atributo,
            valores_atributo=valores_atributo,
            precio_costo=1000.0,
            venta_sin_iva=1200.0,
            largo_envio=10.0,
            ancho_envio=10.0,
            alto_envio=10.0,
            peso_completo=peso_completo,
            dimensiones_producto=dimensiones_producto,
            unidad_medida_dimensiones="mm",
            numero_variantes=numero_variantes,
            esta_publicado=True,
            rastrear_inventario=True,
            disponible_punto_venta=True,
            producto_slug="test-producto",
            etiquetas=etiquetas,
            material=material,
        )


if __name__ == "__main__":
    unittest.main()
