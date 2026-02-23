"""Gateway de comunicacion cliente-servidor."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Protocol

from servidor.services.import_builder import ImportBuilderService
from shared.errors import ServiceError
from shared.protocol import (
    AppendImportRowRequest,
    AppendImportRowResponse,
    CreateImportTemplateRequest,
    CreateImportTemplateResponse,
    FinalizeImportSessionRequest,
    FinalizeImportSessionResponse,
    StartImportSessionRequest,
    StartImportSessionResponse,
)

LOGGER = logging.getLogger(__name__)


class ServerGateway(Protocol):
    """Interfaz de acceso del cliente a servicios del servidor."""

    def create_import_template(
        self,
        request: CreateImportTemplateRequest,
    ) -> CreateImportTemplateResponse:
        """Legacy: solicita creacion de plantilla de importacion."""

    def start_import_session(
        self,
        request: StartImportSessionRequest,
    ) -> StartImportSessionResponse:
        """Solicita inicio de sesion de importacion."""

    def append_import_row(
        self,
        request: AppendImportRowRequest,
    ) -> AppendImportRowResponse:
        """Solicita agregado de una fila al CSV de importacion."""

    def finalize_import_session(
        self,
        request: FinalizeImportSessionRequest,
    ) -> FinalizeImportSessionResponse:
        """Solicita finalizacion de la sesion de importacion."""


class LocalServerGateway:
    """Implementacion local del gateway usando servicios en memoria."""

    def __init__(
        self,
        import_builder_service: ImportBuilderService | None = None,
    ) -> None:
        self._import_builder_service = import_builder_service or ImportBuilderService()

    def create_import_template(
        self,
        request: CreateImportTemplateRequest,
    ) -> CreateImportTemplateResponse:
        """Legacy: mantiene compatibilidad para crear plantilla de importacion."""
        LOGGER.debug(
            "create_import_template() se mantiene por compatibilidad; "
            "el flujo actual usa sesiones start/append/finalize."
        )
        try:
            created_path = self._import_builder_service.create_template(
                output_dir=Path(request.output_dir),
                filename=request.filename,
            )
        except ServiceError:
            raise
        except Exception as exc:
            LOGGER.exception("Fallo inesperado al crear plantilla de importacion.")
            raise ServiceError("No fue posible crear la plantilla de importacion.") from exc

        return CreateImportTemplateResponse(created_path=str(created_path))

    def start_import_session(
        self,
        request: StartImportSessionRequest,
    ) -> StartImportSessionResponse:
        """Inicia una sesion de importacion delegando en el servicio."""
        try:
            inprogress_path = self._import_builder_service.start_import_session(
                output_dir=Path(request.output_dir),
                filename_stem=request.filename_stem,
            )
        except ServiceError:
            raise
        except Exception as exc:
            LOGGER.exception("Fallo inesperado al iniciar sesion de importacion.")
            raise ServiceError("No fue posible iniciar la sesion de importacion.") from exc

        return StartImportSessionResponse(inprogress_path=str(inprogress_path))

    def append_import_row(
        self,
        request: AppendImportRowRequest,
    ) -> AppendImportRowResponse:
        """Agrega una fila al archivo en progreso."""
        try:
            self._import_builder_service.append_product(
                file_path=Path(request.file_path),
                product=request.product,
            )
        except ServiceError:
            raise
        except Exception as exc:
            LOGGER.exception("Fallo inesperado al agregar fila de importacion.")
            raise ServiceError("No fue posible agregar la fila al archivo de importacion.") from exc

        return AppendImportRowResponse(file_path=request.file_path)

    def finalize_import_session(
        self,
        request: FinalizeImportSessionRequest,
    ) -> FinalizeImportSessionResponse:
        """Finaliza la sesion y retorna el archivo definitivo."""
        try:
            final_path = self._import_builder_service.finalize_import_session(
                file_path=Path(request.file_path),
            )
        except ServiceError:
            raise
        except Exception as exc:
            LOGGER.exception("Fallo inesperado al finalizar sesion de importacion.")
            raise ServiceError("No fue posible finalizar la sesion de importacion.") from exc

        return FinalizeImportSessionResponse(final_path=str(final_path))
