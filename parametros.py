"""Parametros globales del proyecto."""

from __future__ import annotations

import logging
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
INPUT_DIR = DATA_DIR / "input"
OUTPUT_DIR = DATA_DIR / "output"
UTILITIES_DIR = DATA_DIR / "utilities"
INFO_PRODUCTS_DIR = UTILITIES_DIR / "info_products"
CATEGORIES_JSON = UTILITIES_DIR / "categories.json"
INVENTORY_CATEGORIES_CSV = UTILITIES_DIR / "inventario_categorias.csv"
DEFAULT_TEMPLATE_FILENAME = "import_template.csv"
DEFAULT_IMPORT_FILENAME_STEM = "import_productos"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
