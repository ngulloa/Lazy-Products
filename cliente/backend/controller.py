"""Controlador principal del cliente."""

from __future__ import annotations

import logging
import re
from collections.abc import Callable
from pathlib import Path
from typing import TYPE_CHECKING

from parametros import DEFAULT_IMPORT_FILENAME_STEM, OUTPUT_DIR
from servidor.services.inventory_utils import build_nombre_base, build_nombre_comercial
from shared.errors import ValidationError
from shared.protocol import (
    AppendImportRowRequest,
    FinalizeImportSessionRequest,
    ImportProductDraft,
    StartImportSessionRequest,
)

from .gateway import ServerGateway
from .id_registry import IdRegistry
from .product_names import (
    build_internal_reference as build_product_internal_reference,
    slug_to_display_name,
)
from .validators import validate_output_dir

if TYPE_CHECKING:
    from PyQt6.QtWidgets import QApplication

LOGGER = logging.getLogger(__name__)


class AppController:
    """Coordina acciones de UI y servicios de negocio."""

    _SLUG_PATTERN = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")

    def __init__(
        self,
        gateway: ServerGateway,
        id_registry: IdRegistry | None = None,
    ) -> None:
        self._gateway = gateway
        self._id_registry = id_registry or IdRegistry()
        self._id_registry.ensure_initialized()
        self._import_session_path: str | None = None
        self._duplicate_index_cache: dict[str, tuple[set[str], set[str]]] = {}

    def on_create_import_file(self) -> None:
        """Registra la accion para abrir la pantalla de importacion."""
        LOGGER.info("Accion ejecutada: abrir pantalla de importacion")

    def on_open_create_product(self) -> None:
        """Registra la accion para abrir dialogo de creacion de producto."""
        LOGGER.info("Accion ejecutada: abrir dialogo crear producto")

    def on_create_product(self, slug: str) -> None:
        """Valida slug y crea una categoria lista para uso en importacion."""
        normalized_slug = slug.strip()
        if not normalized_slug:
            raise ValidationError("El nombre no puede estar vacio.")

        if normalized_slug != normalized_slug.lower():
            raise ValidationError("Slug invalido. Debe estar en minusculas.")

        if not self._SLUG_PATTERN.fullmatch(normalized_slug):
            raise ValidationError(
                "Slug invalido. Usa solo minusculas, numeros y guiones, sin espacios."
            )

        display_name = slug_to_display_name(normalized_slug)
        self._id_registry.create_category(normalized_slug, display_name)
        self._duplicate_index_cache.pop(normalized_slug, None)
        LOGGER.info(
            "Categoria creada desde UI: slug=%s, display_name=%s",
            normalized_slug,
            display_name,
        )

    def list_product_categories(self) -> list[tuple[str, str]]:
        """Lista categorias disponibles como pares (slug, display_name)."""
        categories = self._id_registry.list_categories()
        return [(category.slug, category.display_name) for category in categories]

    def get_next_id_for(self, slug: str) -> str:
        """Retorna el siguiente ID externo disponible para un slug."""
        return self._id_registry.get_next_id(slug)

    def load_category_index(self, slug: str) -> tuple[set[str], set[str]]:
        """Carga/retorna cache de duplicados (SKU y Nombre Base) para un slug."""
        slug_key = self._normalize_slug_key(slug)
        if not slug_key:
            return set(), set()

        cached = self._duplicate_index_cache.get(slug_key)
        if cached is not None:
            return cached

        duplicate_index = self._id_registry.load_duplicate_index(slug_key)
        self._duplicate_index_cache[slug_key] = duplicate_index
        return duplicate_index

    def is_duplicate_sku(self, slug: str, sku: str) -> bool:
        """Indica si SKU ya existe en la categoria, usando cache en memoria."""
        sku_clean = sku.strip()
        if not sku_clean:
            return False

        sku_values, _ = self.load_category_index(slug)
        return sku_clean in sku_values

    def is_duplicate_name(self, slug: str, name: str) -> bool:
        """Indica si Nombre Base ya existe en la categoria, usando cache en memoria."""
        name_clean = name.strip()
        if not name_clean:
            return False

        _, name_values = self.load_category_index(slug)
        return name_clean in name_values

    def sku_exists(self, slug: str, sku: str) -> bool:
        """Retorna True si el SKU ya existe para la categoria indicada."""
        return self.is_duplicate_sku(slug, sku)

    def nombre_base_exists(self, slug: str, nombre_base: str) -> bool:
        """Retorna True si el Nombre Base ya existe para la categoria indicada."""
        return self.is_duplicate_name(slug, nombre_base)

    @staticmethod
    def build_internal_reference(
        producto_slug: str,
        marca: str,
        modelo: str,
        valores_atributo: str,
    ) -> str:
        """Construye la referencia interna del producto para la UI."""
        return build_product_internal_reference(
            producto_slug=producto_slug,
            marca=marca,
            modelo=modelo,
            valores_atributo=valores_atributo,
        )

    @staticmethod
    def build_nombre_comercial_preview(data: ImportProductDraft) -> str:
        """Construye preview de nombre comercial en base al draft actual."""
        nombre_base = build_nombre_base(data.producto, data.marca, data.modelo)
        return build_nombre_comercial(
            nombre_base=nombre_base,
            valores_atributo=data.valores_atributo,
            dimensiones_producto=data.dimensiones_producto,
            unidad=data.unidad_medida_dimensiones,
        )

    def start_import_session_if_needed(self) -> str:
        """Inicia una sesion CSV en progreso si no hay una activa."""
        if self._import_session_path is not None:
            return self._import_session_path

        request = StartImportSessionRequest(
            output_dir=str(OUTPUT_DIR),
            filename_stem=DEFAULT_IMPORT_FILENAME_STEM,
        )

        validate_output_dir(Path(request.output_dir))
        response = self._gateway.start_import_session(request)
        self._import_session_path = response.inprogress_path

        LOGGER.info("Sesion de importacion activa: %s", self._import_session_path)
        return self._import_session_path

    def on_import_next(self, data: ImportProductDraft) -> None:
        """Valida y agrega una fila de producto al CSV en progreso."""
        self._validate_required_fields(data)
        file_path = self.start_import_session_if_needed()

        response = self._gateway.append_import_row(
            AppendImportRowRequest(file_path=file_path, product=data)
        )
        self._update_duplicate_index_after_append(data)
        LOGGER.info("Se agrego una fila al CSV de importacion: %s", response.file_path)

    def on_import_save(self) -> str:
        """Finaliza el archivo de importacion y limpia la sesion activa."""
        file_path = self.start_import_session_if_needed()

        response = self._gateway.finalize_import_session(
            FinalizeImportSessionRequest(file_path=file_path)
        )
        self._import_session_path = None

        LOGGER.info("Archivo de importacion finalizado: %s", response.final_path)
        return response.final_path

    def on_import_back(self) -> None:
        """Registra regreso al menu principal sin cerrar la sesion activa."""
        LOGGER.info("Regresar desde importacion. Sesion activa: %s", self._import_session_path)

    def on_view_products(self) -> None:
        """Placeholder para visualizar productos."""
        LOGGER.info("Accion ejecutada: visualizar productos (placeholder)")

    def on_search_products(self) -> None:
        """Placeholder para buscar productos."""
        LOGGER.info("Accion ejecutada: buscar productos (placeholder)")

    def on_exit(
        self,
        app: QApplication | Callable[[], None] | None,
    ) -> None:
        """Cierra la aplicacion."""
        LOGGER.info("Accion ejecutada: salir")

        if callable(app):
            app()
            return

        if app is not None:
            app.quit()

    @staticmethod
    def _validate_required_fields(data: ImportProductDraft) -> None:
        """Valida los campos minimos requeridos para continuar."""
        missing_fields: list[str] = []

        if not data.id_externo.strip():
            missing_fields.append("ID Externo")
        if not data.referencia_interna.strip():
            missing_fields.append("Referencia interna")
        if not data.producto.strip():
            missing_fields.append("Producto")
        if not data.producto_slug.strip():
            missing_fields.append("Categoria de producto")
        if not data.marca.strip():
            missing_fields.append("Marca")
        if not data.modelo.strip():
            missing_fields.append("Modelo")
        if data.precio_costo <= 0:
            missing_fields.append("Precio de Costo (debe ser mayor a 0)")
        if data.venta_sin_iva <= 0:
            missing_fields.append("Venta sin IVA (debe ser mayor a 0)")

        if missing_fields:
            message = "Completa los campos obligatorios: " + ", ".join(missing_fields)
            raise ValidationError(message)

    @staticmethod
    def _normalize_slug_key(slug: str) -> str:
        """Normaliza slug para uso como key de cache."""
        return slug.strip().lower()

    def _update_duplicate_index_after_append(self, data: ImportProductDraft) -> None:
        """Actualiza cache de duplicados en memoria tras append exitoso."""
        slug_key = self._normalize_slug_key(data.producto_slug)
        if not slug_key:
            return

        cached = self._duplicate_index_cache.get(slug_key)
        if cached is None:
            return

        sku_values, name_values = cached
        sku = data.referencia_interna.strip()
        if sku:
            sku_values.add(sku)

        nombre_base = build_nombre_base(data.producto, data.marca, data.modelo).strip()
        if nombre_base:
            name_values.add(nombre_base)
