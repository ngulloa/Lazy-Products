"""Registro local de categorias e IDs para importacion."""

from __future__ import annotations

import csv
import json
import logging
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from parametros import CATEGORIES_JSON, IDS_DIR
from shared.errors import ServiceError, ValidationError

LOGGER = logging.getLogger(__name__)


@dataclass(slots=True)
class Category:
    """Representa una categoria con slug, nombre visible y codigo interno."""

    slug: str
    display_name: str
    code: int


class IdRegistry:
    """Administra categorias persistentes y correlativos de IDs por categoria."""

    _DEFAULT_CATEGORIES: tuple[Category, ...] = (
        Category(slug="punos", display_name="Puños", code=0),
        Category(slug="sillin", display_name="Sillín", code=1),
        Category(slug="luces", display_name="Luces", code=2),
        Category(slug="camaras", display_name="Cámaras", code=3),
        Category(slug="neumatico", display_name="Neumático", code=4),
        Category(slug="pedales", display_name="Pedales", code=5),
        Category(slug="caramagiola", display_name="Caramagiola", code=6),
        Category(slug="porta-caramagiola", display_name="Porta-caramagiola", code=7),
        Category(slug="cascos", display_name="Cascos", code=8),
        Category(slug="cadenas", display_name="Cadenas", code=9),
        Category(slug="manillas-de-freno", display_name="Manillas de freno", code=10),
        Category(slug="manillas-de-cambio", display_name="Manillas de cambio", code=11),
        Category(slug="tricota", display_name="Tricota", code=12),
    )

    def __init__(
        self,
        categories_json: Path = CATEGORIES_JSON,
        ids_dir: Path = IDS_DIR,
    ) -> None:
        self._categories_json = categories_json
        self._ids_dir = ids_dir

    def ensure_initialized(self) -> None:
        """Crea utilitarios base si no existen y asegura headers de CSV."""
        self._categories_json.parent.mkdir(parents=True, exist_ok=True)
        self._ids_dir.mkdir(parents=True, exist_ok=True)

        if not self._categories_json.exists():
            data = {
                "next_code": 13,
                "categories": [asdict(category) for category in self._DEFAULT_CATEGORIES],
            }
            self._write_categories_data(data)
            LOGGER.info("categories.json inicializado en: %s", self._categories_json)

        data = self._read_categories_data()
        categories = self._parse_categories(data.get("categories", []))
        for category in categories:
            self._ensure_category_csv(category.slug)

        LOGGER.info("Utilities inicializado: %s", self._categories_json.parent)

    def list_categories(self) -> list[Category]:
        """Retorna categorias registradas."""
        self.ensure_initialized()
        data = self._read_categories_data()
        categories = self._parse_categories(data.get("categories", []))
        categories.sort(key=lambda category: category.code)
        return categories

    def get_next_id(self, slug: str) -> str:
        """Calcula el siguiente ID para una categoria sin persistirlo."""
        category = self._get_category(slug)
        csv_path = self._category_csv_path(category.slug)
        self._ensure_category_csv(category.slug)

        last_id = self._read_last_registered_id(csv_path)
        prefix = f"780999{category.code:02d}"
        if last_id is None:
            correlativo = 0
        else:
            correlativo = self._extract_correlative(last_id, prefix) + 1

        return f"{prefix}{correlativo:04d}"

    def register_id(self, slug: str, used_id: str) -> None:
        """Registra un ID usado en el CSV de la categoria indicada."""
        category = self._get_category(slug)
        used_id_clean = used_id.strip()
        if not used_id_clean:
            raise ValidationError("used_id no puede estar vacio.")

        csv_path = self._category_csv_path(category.slug)
        self._ensure_category_csv(category.slug)
        with csv_path.open("a", newline="", encoding="utf-8") as csv_file:
            writer = csv.writer(csv_file)
            writer.writerow([used_id_clean])

    def create_category(self, slug: str, display_name: str) -> None:
        """Crea una nueva categoria con codigo correlativo y su CSV de IDs."""
        self.ensure_initialized()

        normalized_slug = self._normalize_slug(slug)
        if not normalized_slug:
            raise ValidationError("slug no puede estar vacio.")

        display_name_clean = display_name.strip()
        if not display_name_clean:
            raise ValidationError("display_name no puede estar vacio.")

        data = self._read_categories_data()
        categories = self._parse_categories(data.get("categories", []))
        if any(category.slug == normalized_slug for category in categories):
            raise ValidationError(f"La categoria ya existe: {normalized_slug}")

        next_code = self._parse_next_code(data.get("next_code"))
        categories.append(
            Category(slug=normalized_slug, display_name=display_name_clean, code=next_code)
        )

        updated_data = {
            "next_code": next_code + 1,
            "categories": [asdict(category) for category in categories],
        }
        self._write_categories_data(updated_data)
        self._ensure_category_csv(normalized_slug)

        LOGGER.info("Categoria creada: %s (%s)", normalized_slug, display_name_clean)

    def _get_category(self, slug: str) -> Category:
        """Retorna una categoria existente o levanta ValidationError."""
        normalized_slug = self._normalize_slug(slug)
        categories = self.list_categories()
        for category in categories:
            if category.slug == normalized_slug:
                return category

        raise ValidationError(f"Categoria no encontrada: {normalized_slug}")

    def _ensure_category_csv(self, slug: str) -> None:
        """Crea el CSV de IDs para una categoria si no existe."""
        csv_path = self._category_csv_path(slug)
        if csv_path.exists():
            return

        with csv_path.open("w", newline="", encoding="utf-8") as csv_file:
            writer = csv.writer(csv_file)
            writer.writerow(["id"])

    def _read_last_registered_id(self, csv_path: Path) -> str | None:
        """Obtiene el ultimo id registrado en el CSV de categoria."""
        last_id: str | None = None
        with csv_path.open("r", newline="", encoding="utf-8") as csv_file:
            reader = csv.DictReader(csv_file)
            for row in reader:
                value = (row.get("id") or "").strip()
                if value:
                    last_id = value

        return last_id

    def _extract_correlative(self, used_id: str, prefix: str) -> int:
        """Extrae correlativo de un ID registrado y valida formato base."""
        if not used_id.startswith(prefix):
            raise ServiceError(f"ID registrado invalido para categoria: {used_id}")

        numeric_tail = used_id[len(prefix) :]
        if len(numeric_tail) != 4 or not numeric_tail.isdigit():
            raise ServiceError(f"Formato de ID invalido en registro: {used_id}")

        return int(numeric_tail)

    def _read_categories_data(self) -> dict[str, Any]:
        """Lee el archivo categories.json."""
        try:
            raw_text = self._categories_json.read_text(encoding="utf-8")
        except OSError as exc:
            raise ServiceError("No fue posible leer categories.json.") from exc

        try:
            data = json.loads(raw_text)
        except json.JSONDecodeError as exc:
            raise ServiceError("categories.json tiene formato invalido.") from exc

        if not isinstance(data, dict):
            raise ServiceError("categories.json debe ser un objeto JSON.")
        return data

    def _write_categories_data(self, data: dict[str, Any]) -> None:
        """Escribe categories.json de manera segura (temp + replace)."""
        temp_path = self._categories_json.with_name(f"{self._categories_json.name}.tmp")
        try:
            serialized = json.dumps(data, ensure_ascii=False, indent=2)
            temp_path.write_text(serialized + "\n", encoding="utf-8")
            temp_path.replace(self._categories_json)
        except OSError as exc:
            raise ServiceError("No fue posible persistir categories.json.") from exc
        finally:
            if temp_path.exists():
                temp_path.unlink(missing_ok=True)

    @staticmethod
    def _parse_categories(raw_categories: Any) -> list[Category]:
        """Parsea categorias desde JSON a dataclasses tipadas."""
        if not isinstance(raw_categories, list):
            raise ServiceError("categories debe ser una lista en categories.json.")

        parsed: list[Category] = []
        for item in raw_categories:
            if not isinstance(item, dict):
                raise ServiceError("Cada categoria debe ser un objeto JSON.")
            try:
                category = Category(
                    slug=str(item["slug"]).strip(),
                    display_name=str(item["display_name"]).strip(),
                    code=int(item["code"]),
                )
            except (KeyError, TypeError, ValueError) as exc:
                raise ServiceError("Categoria invalida en categories.json.") from exc

            if not category.slug or not category.display_name:
                raise ServiceError("slug y display_name no pueden estar vacios.")
            parsed.append(category)

        return parsed

    @staticmethod
    def _parse_next_code(raw_next_code: Any) -> int:
        """Valida y retorna next_code como entero no negativo."""
        try:
            next_code = int(raw_next_code)
        except (TypeError, ValueError) as exc:
            raise ServiceError("next_code invalido en categories.json.") from exc

        if next_code < 0:
            raise ServiceError("next_code no puede ser negativo.")
        return next_code

    def _category_csv_path(self, slug: str) -> Path:
        """Retorna ruta CSV asociada al slug."""
        return self._ids_dir / f"{slug}.csv"

    @staticmethod
    def _normalize_slug(slug: str) -> str:
        """Normaliza slug para uso interno."""
        return slug.strip().lower()
