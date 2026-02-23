"""Tests para normalizacion y parseo de etiquetas."""

from __future__ import annotations

import unittest

from shared.tags import normalize_selected_tags, parse_tags_csv


class TagsTests(unittest.TestCase):
    """Valida utilidades de etiquetas compartidas."""

    def test_normalize_selected_tags_empty(self) -> None:
        """Debe retornar string vacio cuando no hay etiquetas validas."""
        self.assertEqual(normalize_selected_tags([]), "")

    def test_normalize_selected_tags_with_duplicates_and_spaces(self) -> None:
        """Debe limpiar espacios y remover duplicados preservando orden."""
        tags = [" MTB ", "Ruta", "MTB", "", "  ", "Ruta ", "Enduro"]
        self.assertEqual(normalize_selected_tags(tags), "MTB, Ruta, Enduro")

    def test_parse_tags_csv_with_space_separator(self) -> None:
        """Debe parsear etiquetas separadas por coma y espacio."""
        self.assertEqual(parse_tags_csv("MTB, Ruta"), ["MTB", "Ruta"])

    def test_parse_tags_csv_empty(self) -> None:
        """Debe retornar lista vacia cuando la cadena es vacia."""
        self.assertEqual(parse_tags_csv(""), [])


if __name__ == "__main__":
    unittest.main()
