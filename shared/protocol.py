"""DTOs del protocolo cliente-servidor."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class CreateImportTemplateRequest:
    """Solicitud para crear plantilla de importacion."""

    output_dir: str
    filename: str


@dataclass(slots=True)
class CreateImportTemplateResponse:
    """Respuesta de creacion de plantilla de importacion."""

    created_path: str


@dataclass(slots=True)
class ImportProductDraft:
    """DTO para capturar datos del dialogo de importacion de productos."""

    id_externo: str
    referencia_interna: str
    producto: str
    marca: str
    descripcion_sitio_web: str
    descripcion_seo: str
    modelo: str
    cantidad_inicial: int
    atributo: str
    valores_atributo: str
    precio_costo: float
    venta_sin_iva: float
    largo_envio: float
    ancho_envio: float
    alto_envio: float
    peso_completo: float
    dimensiones_producto: str
    unidad_medida_dimensiones: str
    numero_variantes: int
    esta_publicado: bool
    rastrear_inventario: bool
    disponible_punto_venta: bool
    producto_slug: str = ""
    etiquetas: str = ""


@dataclass(slots=True)
class StartImportSessionRequest:
    """Solicitud para iniciar una sesion de archivo de importacion."""

    output_dir: str
    filename_stem: str


@dataclass(slots=True)
class StartImportSessionResponse:
    """Respuesta con la ruta del archivo en progreso."""

    inprogress_path: str


@dataclass(slots=True)
class AppendImportRowRequest:
    """Solicitud para agregar una fila de producto al CSV en progreso."""

    file_path: str
    product: ImportProductDraft


@dataclass(slots=True)
class AppendImportRowResponse:
    """Respuesta de agregado de fila en importacion."""

    file_path: str


@dataclass(slots=True)
class FinalizeImportSessionRequest:
    """Solicitud para finalizar la sesion de importacion."""

    file_path: str


@dataclass(slots=True)
class FinalizeImportSessionResponse:
    """Respuesta con ruta final del archivo de importacion."""

    final_path: str
