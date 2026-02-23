"""Pagina de ingreso de productos para importacion."""

from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor
from PyQt6.QtWidgets import (
    QAbstractSpinBox,
    QCheckBox,
    QComboBox,
    QDoubleSpinBox,
    QFrame,
    QGridLayout,
    QGraphicsDropShadowEffect,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QSizePolicy,
    QSpinBox,
    QSpacerItem,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from cliente.frontend.details_dialog import ProductDetailsDialog
from cliente.frontend.dialogs import show_error, show_info
from cliente.frontend.widgets.checkable_combo import CheckableComboBox
from shared.errors import ServiceError, ValidationError
from shared.protocol import ImportProductDraft
from shared.tags import AVAILABLE_TAGS, normalize_selected_tags

if TYPE_CHECKING:
    from cliente.backend.controller import AppController


class ImportProductPage(QWidget):
    """Pagina embebible para capturar productos antes de la importacion."""

    def __init__(
        self,
        controller: AppController,
        on_back: Callable[[], None],
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._controller = controller
        self._on_back = on_back
        self.setObjectName("importPage")

        self._build_ui()
        self._apply_styles()

    def _build_ui(self) -> None:
        """Construye la interfaz de la pagina."""
        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(24, 24, 24, 24)
        root_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        card = QFrame(self)
        card.setObjectName("importCard")
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(24, 24, 24, 24)
        card_layout.setSpacing(18)

        title_label = QLabel("Crear archivo de importación", card)
        title_label.setObjectName("dialogTitle")
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        title_separator = QFrame(card)
        title_separator.setObjectName("titleSeparator")
        title_separator.setFixedHeight(1)

        form_columns_layout = QHBoxLayout()
        form_columns_layout.setContentsMargins(0, 0, 0, 0)
        form_columns_layout.setSpacing(18)

        left_column_widget = QWidget(card)
        left_form_layout = QGridLayout(left_column_widget)
        left_form_layout.setContentsMargins(0, 0, 0, 0)
        left_form_layout.setHorizontalSpacing(20)
        left_form_layout.setVerticalSpacing(12)
        left_form_layout.setColumnMinimumWidth(0, 0)
        left_form_layout.setColumnStretch(1, 1)

        right_column_widget = QWidget(card)
        right_form_layout = QGridLayout(right_column_widget)
        right_form_layout.setContentsMargins(0, 0, 0, 0)
        right_form_layout.setHorizontalSpacing(14)
        right_form_layout.setVerticalSpacing(12)
        right_form_layout.setColumnMinimumWidth(0, 145)
        right_form_layout.setColumnStretch(1, 1)

        self._id_externo_badge = QFrame(card)
        self._id_externo_badge.setObjectName("idBadge")
        id_badge_layout = QHBoxLayout(self._id_externo_badge)
        id_badge_layout.setContentsMargins(14, 10, 14, 10)

        self._id_externo_value_label = QLabel("-", self._id_externo_badge)
        self._id_externo_value_label.setObjectName("idBadgeValue")
        self._id_externo_value_label.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse
        )
        id_badge_layout.addWidget(self._id_externo_value_label)

        badge_shadow = QGraphicsDropShadowEffect(self._id_externo_badge)
        badge_shadow.setBlurRadius(16)
        badge_shadow.setOffset(0, 3)
        badge_shadow.setColor(QColor(0, 0, 0, 28))
        self._id_externo_badge.setGraphicsEffect(badge_shadow)

        self._referencia_interna_input = QLineEdit(card)
        self._referencia_interna_input.setObjectName("referenciaInternaInput")
        self._referencia_interna_input.setReadOnly(True)
        self._referencia_interna_input.setPlaceholderText("Se genera automaticamente")
        self._referencia_interna_input.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Fixed,
        )

        self._producto_input = QComboBox(card)
        self._producto_input.addItem("Sin categorias", "")
        self._producto_input.currentIndexChanged.connect(self._on_product_changed)
        self._producto_input.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Fixed,
        )

        self._descripcion_web_input = QTextEdit(card)
        self._descripcion_web_input.setPlaceholderText(
            "Escribe la descripción HTML/para web…"
        )
        self._descripcion_web_input.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Fixed,
        )
        self._descripcion_web_input.setFixedHeight(90)

        self._descripcion_seo_input = QTextEdit(card)
        self._descripcion_seo_input.setPlaceholderText(
            "Escribe la descripción corta SEO…"
        )
        self._descripcion_seo_input.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Fixed,
        )
        self._descripcion_seo_input.setFixedHeight(90)

        self._marca_input = QLineEdit(card)
        self._marca_input.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Fixed,
        )

        self._modelo_input = QLineEdit(card)
        self._modelo_input.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Fixed,
        )

        self._cantidad_inicial_input = QSpinBox(card)
        self._cantidad_inicial_input.setRange(0, 1_000_000)
        self._cantidad_inicial_input.setButtonSymbols(
            QAbstractSpinBox.ButtonSymbols.NoButtons
        )

        self._atributo_input = QComboBox(card)
        self._atributo_input.addItems(["No tiene", "Color", "Diseño"])

        self._valores_atributo_input = QLineEdit(card)
        self._valores_atributo_input.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Fixed,
        )

        self._marca_input.textChanged.connect(self._on_reference_source_changed)
        self._modelo_input.textChanged.connect(self._on_reference_source_changed)
        self._valores_atributo_input.textChanged.connect(self._on_reference_source_changed)

        self._precio_costo_input = QDoubleSpinBox(card)
        self._precio_costo_input.setRange(0.0, 1_000_000_000.0)
        self._precio_costo_input.setDecimals(2)
        self._precio_costo_input.setSingleStep(0.5)
        self._precio_costo_input.setButtonSymbols(
            QAbstractSpinBox.ButtonSymbols.NoButtons
        )

        self._numero_variantes_input = QSpinBox(card)
        self._numero_variantes_input.setObjectName("numeroVariantesInput")
        self._numero_variantes_input.setRange(1, 10_000)
        self._numero_variantes_input.setValue(1)
        self._numero_variantes_input.setButtonSymbols(
            QAbstractSpinBox.ButtonSymbols.NoButtons
        )

        self._etiquetas_input = CheckableComboBox(card)
        self._etiquetas_input.set_items(list(AVAILABLE_TAGS))
        self._etiquetas_input.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Fixed,
        )

        self._esta_publicado_input = QCheckBox(card)
        self._esta_publicado_input.setChecked(True)

        self._rastrear_inventario_input = QCheckBox(card)
        self._rastrear_inventario_input.setChecked(True)

        self._disponible_pdv_input = QCheckBox(card)
        self._disponible_pdv_input.setChecked(True)

        self._alto_envio_input = QDoubleSpinBox(card)
        self._alto_envio_input.setRange(0.0, 100_000.0)
        self._alto_envio_input.setDecimals(2)
        self._alto_envio_input.setSingleStep(0.5)
        self._alto_envio_input.setButtonSymbols(
            QAbstractSpinBox.ButtonSymbols.NoButtons
        )

        self._largo_envio_input = QDoubleSpinBox(card)
        self._largo_envio_input.setRange(0.0, 100_000.0)
        self._largo_envio_input.setDecimals(2)
        self._largo_envio_input.setSingleStep(0.5)
        self._largo_envio_input.setButtonSymbols(
            QAbstractSpinBox.ButtonSymbols.NoButtons
        )

        self._ancho_envio_input = QDoubleSpinBox(card)
        self._ancho_envio_input.setRange(0.0, 100_000.0)
        self._ancho_envio_input.setDecimals(2)
        self._ancho_envio_input.setSingleStep(0.5)
        self._ancho_envio_input.setButtonSymbols(
            QAbstractSpinBox.ButtonSymbols.NoButtons
        )

        self._peso_completo_input = QDoubleSpinBox(card)
        self._peso_completo_input.setRange(0.0, 100_000.0)
        self._peso_completo_input.setDecimals(2)
        self._peso_completo_input.setSingleStep(0.5)
        self._peso_completo_input.setButtonSymbols(
            QAbstractSpinBox.ButtonSymbols.NoButtons
        )

        self._dimensiones_producto_input = QLineEdit(card)
        self._dimensiones_producto_input.setPlaceholderText("Ej: 15 x 8 x 3")

        self._unidad_medida_input = QComboBox(card)
        self._unidad_medida_input.addItems(["", "cm", "mm", "in", "g", "kg"])

        self._venta_sin_iva_input = QDoubleSpinBox(card)
        self._venta_sin_iva_input.setRange(0.0, 1_000_000_000.0)
        self._venta_sin_iva_input.setDecimals(2)
        self._venta_sin_iva_input.setSingleStep(0.5)
        self._venta_sin_iva_input.setButtonSymbols(
            QAbstractSpinBox.ButtonSymbols.NoButtons
        )

        row_left = 0
        row_left = self._add_form_row(
            left_form_layout,
            row_left,
            "ID Externo",
            self._id_externo_badge,
        )
        row_left = self._add_form_row(
            left_form_layout,
            row_left,
            "Referencia interna",
            self._referencia_interna_input,
        )
        row_left = self._add_spacer_row(left_form_layout, row_left, 6)
        row_left = self._add_form_row(
            left_form_layout,
            row_left,
            "Producto",
            self._producto_input,
        )
        row_left = self._add_form_row(
            left_form_layout,
            row_left,
            "Modelo",
            self._modelo_input,
        )
        row_left = self._add_form_row(
            left_form_layout,
            row_left,
            "Marca",
            self._marca_input,
        )
        row_left = self._add_form_row(
            left_form_layout,
            row_left,
            "Cantidad inicial",
            self._cantidad_inicial_input,
        )
        row_left = self._add_form_row(
            left_form_layout,
            row_left,
            "Atributo",
            self._atributo_input,
        )
        row_left = self._add_form_row(
            left_form_layout,
            row_left,
            "Valores de Atributo",
            self._valores_atributo_input,
        )
        row_left = self._add_form_row(
            left_form_layout,
            row_left,
            "Precio de Costo",
            self._precio_costo_input,
        )
        row_left = self._add_form_row(
            left_form_layout,
            row_left,
            "Numero de variantes",
            self._numero_variantes_input,
        )
        row_left = self._add_form_row(
            left_form_layout,
            row_left,
            "Etiquetas",
            self._etiquetas_input,
        )
        row_left = self._add_form_row(
            left_form_layout,
            row_left,
            "Esta Publicado",
            self._esta_publicado_input,
        )
        row_left = self._add_form_row(
            left_form_layout,
            row_left,
            "Rastrear inventario",
            self._rastrear_inventario_input,
        )
        self._add_form_row(
            left_form_layout,
            row_left,
            "Disponible en Punto de venta",
            self._disponible_pdv_input,
        )
        left_form_layout.setRowStretch(row_left + 1, 1)

        row_right = 0
        row_right = self._add_form_row(
            right_form_layout,
            row_right,
            "Alto Envio",
            self._alto_envio_input,
            label_min_width=145,
        )
        row_right = self._add_form_row(
            right_form_layout,
            row_right,
            "Largo Envio",
            self._largo_envio_input,
            label_min_width=145,
        )
        row_right = self._add_form_row(
            right_form_layout,
            row_right,
            "Ancho Envio",
            self._ancho_envio_input,
            label_min_width=145,
        )
        row_right = self._add_form_row(
            right_form_layout,
            row_right,
            "Peso Completo",
            self._peso_completo_input,
            label_min_width=145,
        )
        row_right = self._add_form_row(
            right_form_layout,
            row_right,
            "Dimensiones del producto",
            self._dimensiones_producto_input,
            label_min_width=145,
            align_top=True,
        )
        row_right = self._add_form_row(
            right_form_layout,
            row_right,
            "Unidad de Medida (Dimensiones)",
            self._unidad_medida_input,
            label_min_width=145,
            align_top=True,
        )
        row_right = self._add_form_row(
            right_form_layout,
            row_right,
            "Venta sin IVA",
            self._venta_sin_iva_input,
            label_min_width=145,
        )
        row_right = self._add_spacer_row(right_form_layout, row_right, 8)
        row_right = self._add_form_row(
            right_form_layout,
            row_right,
            "Descripción para el sitio web",
            self._descripcion_web_input,
            label_min_width=145,
            align_top=True,
        )
        self._add_form_row(
            right_form_layout,
            row_right,
            "Descripción SEO",
            self._descripcion_seo_input,
            label_min_width=145,
            align_top=True,
        )
        right_form_layout.setRowStretch(row_right + 1, 1)

        column_separator = QFrame(card)
        column_separator.setObjectName("columnSeparator")
        column_separator.setFixedWidth(1)

        form_columns_layout.addWidget(left_column_widget)
        form_columns_layout.addWidget(column_separator)
        form_columns_layout.addWidget(right_column_widget)
        form_columns_layout.setStretch(0, 1)
        form_columns_layout.setStretch(2, 1)

        buttons_layout = QHBoxLayout()
        buttons_layout.setSpacing(10)

        self._next_button = QPushButton("Añadir Producto", card)
        self._save_button = QPushButton("Guardar", card)
        self._details_button = QPushButton("Obtener detalles", card)
        back_button = QPushButton("Regresar", card)
        back_button.setObjectName("backButton")

        self._next_button.clicked.connect(self._on_next_clicked)
        self._save_button.clicked.connect(self._on_save_clicked)
        self._details_button.clicked.connect(self._on_details_clicked)
        back_button.clicked.connect(self._on_back_clicked)

        buttons_layout.addWidget(self._next_button)
        buttons_layout.addWidget(self._save_button)
        buttons_layout.addWidget(self._details_button)
        buttons_layout.addWidget(back_button)

        card_layout.addWidget(title_label)
        card_layout.addWidget(title_separator)
        card_layout.addLayout(form_columns_layout)
        card_layout.addSpacing(8)
        card_layout.addLayout(buttons_layout)

        shadow = QGraphicsDropShadowEffect(card)
        shadow.setBlurRadius(38)
        shadow.setOffset(0, 8)
        shadow.setColor(QColor(0, 0, 0, 38))
        card.setGraphicsEffect(shadow)

        root_layout.addWidget(card)
        self._marca_input.setFocus()
        self._connect_form_state_signals()
        self._refresh_internal_reference()
        self._update_form_state()

    def _apply_styles(self) -> None:
        """Aplica estilos para mantener consistencia con la app."""
        self.setStyleSheet(
            """
            QWidget#importPage {
                background-color: #eef1f4;
            }
            QFrame#importCard {
                background-color: #ffffff;
                border-radius: 18px;
            }
            QLabel#dialogTitle {
                color: #20232a;
                font-family: "Segoe UI";
                font-size: 18px;
                font-weight: 700;
            }
            QFrame#titleSeparator,
            QFrame#columnSeparator {
                background-color: #dbe2ea;
            }
            QLabel#formLabel {
                color: #334155;
                font-family: "Segoe UI";
                font-size: 14px;
                font-weight: 600;
            }
            QFrame#idBadge {
                background-color: #f8fafc;
                border: 1px solid #d1d5db;
                border-radius: 10px;
                min-height: 42px;
            }
            QLabel#idBadgeValue {
                color: #1e40af;
                font-family: "Segoe UI";
                font-size: 15px;
                font-weight: 700;
            }
            QLineEdit, QTextEdit, QSpinBox, QDoubleSpinBox, QComboBox {
                background-color: #f8fafc;
                border: 1px solid #d1d5db;
                border-radius: 8px;
                color: #111827;
                font-family: "Segoe UI";
                font-size: 14px;
                padding: 10px;
            }
            QLineEdit:focus, QTextEdit:focus, QSpinBox:focus,
            QDoubleSpinBox:focus, QComboBox:focus {
                border: 1px solid #2563eb;
                background-color: #ffffff;
            }
            QLineEdit#referenciaInternaInput[skuDuplicate="true"] {
                border: 1px solid #dc2626;
                background-color: #fef2f2;
                color: #991b1b;
            }
            QLineEdit#referenciaInternaInput[skuDuplicate="true"]:disabled {
                border: 1px solid #dc2626;
                background-color: #fee2e2;
                color: #991b1b;
            }
            QSpinBox#numeroVariantesInput[nombreBaseDuplicate="true"] {
                border: 1px solid #eab308;
                background-color: #fef9c3;
                color: #854d0e;
            }
            QSpinBox#numeroVariantesInput[nombreBaseDuplicate="true"]:disabled {
                border: 1px solid #eab308;
                background-color: #fef3c7;
                color: #854d0e;
            }
            QPushButton {
                background-color: #C80202;
                border: none;
                border-radius: 10px;
                color: #ffffff;
                font-family: "Segoe UI";
                font-size: 13px;
                font-weight: 600;
                min-height: 36px;
                padding: 6px 10px;
            }
            QPushButton:hover {
                background-color: #A30202;
            }
            QPushButton:pressed {
                background-color: #820101;
            }
            QPushButton:disabled {
                background-color: #d5a3a3;
                color: #f5e8e8;
            }
            QPushButton#backButton {
                background-color: #e5e7eb;
                color: #1f2937;
            }
            QPushButton#backButton:hover {
                background-color: #d1d5db;
            }
            QPushButton#backButton:pressed {
                background-color: #b9c0c9;
            }
            QPushButton#backButton:disabled {
                background-color: #e5e7eb;
                color: #9ca3af;
            }
            """
        )

    def _connect_form_state_signals(self) -> None:
        """Conecta eventos de formulario para refrescar estado de botones."""
        self._producto_input.currentIndexChanged.connect(self._update_form_state)
        self._referencia_interna_input.textChanged.connect(self._update_form_state)
        self._marca_input.textChanged.connect(self._update_form_state)
        self._modelo_input.textChanged.connect(self._update_form_state)
        self._cantidad_inicial_input.valueChanged.connect(self._update_form_state)
        self._atributo_input.currentIndexChanged.connect(self._update_form_state)
        self._valores_atributo_input.textChanged.connect(self._update_form_state)
        self._precio_costo_input.valueChanged.connect(self._update_form_state)
        self._numero_variantes_input.valueChanged.connect(self._update_form_state)
        self._alto_envio_input.valueChanged.connect(self._update_form_state)
        self._largo_envio_input.valueChanged.connect(self._update_form_state)
        self._ancho_envio_input.valueChanged.connect(self._update_form_state)
        self._peso_completo_input.valueChanged.connect(self._update_form_state)
        self._dimensiones_producto_input.textChanged.connect(self._update_form_state)
        self._unidad_medida_input.currentIndexChanged.connect(self._update_form_state)
        self._venta_sin_iva_input.valueChanged.connect(self._update_form_state)
        self._descripcion_web_input.textChanged.connect(self._update_form_state)
        self._descripcion_seo_input.textChanged.connect(self._update_form_state)
        self._etiquetas_input.checked_items_changed.connect(self._update_form_state)

    def _is_required_data_complete(self, data: ImportProductDraft) -> bool:
        """Valida campos obligatorios para habilitar acciones de formulario."""
        if not data.producto_slug.strip():
            return False
        if not data.id_externo.strip():
            return False
        if not data.referencia_interna.strip():
            return False
        if not data.marca.strip():
            return False
        if not data.modelo.strip():
            return False
        if data.precio_costo <= 0:
            return False
        if data.venta_sin_iva <= 0:
            return False
        if data.numero_variantes < 1:
            return False
        return True

    def _is_duplicate_sku(self, data: ImportProductDraft) -> bool:
        """Indica si la referencia interna ya existe para la categoria seleccionada."""
        slug = data.producto_slug.strip()
        sku = data.referencia_interna.strip()
        if not slug or not sku:
            return False

        try:
            return self._controller.is_duplicate_sku(slug, sku)
        except (ValidationError, ServiceError):
            return False

    @staticmethod
    def _build_nombre_base(data: ImportProductDraft) -> str:
        """Construye nombre base combinando producto, marca y modelo."""
        parts = [data.producto.strip(), data.marca.strip(), data.modelo.strip()]
        return " ".join(part for part in parts if part)

    def _is_duplicate_nombre_base(self, data: ImportProductDraft) -> bool:
        """Indica si el Nombre Base ya existe para la categoria seleccionada."""
        slug = data.producto_slug.strip()
        nombre_base = self._build_nombre_base(data)
        if not slug or not nombre_base:
            return False

        try:
            return self._controller.is_duplicate_name(slug, nombre_base)
        except (ValidationError, ServiceError):
            return False

    def _apply_nombre_base_warning(self, has_warning: bool) -> None:
        """Aplica estilo de advertencia visual para # variantes."""
        property_value = "true" if has_warning else "false"
        self._numero_variantes_input.setProperty("nombreBaseDuplicate", property_value)
        self._numero_variantes_input.style().unpolish(self._numero_variantes_input)
        self._numero_variantes_input.style().polish(self._numero_variantes_input)
        self._numero_variantes_input.update()

    def _set_non_sku_inputs_enabled(self, enabled: bool) -> None:
        """Habilita o deshabilita campos que no participan en la construccion del SKU."""
        non_sku_inputs: tuple[QWidget, ...] = (
            self._referencia_interna_input,
            self._descripcion_web_input,
            self._descripcion_seo_input,
            self._cantidad_inicial_input,
            self._atributo_input,
            self._precio_costo_input,
            self._numero_variantes_input,
            self._etiquetas_input,
            self._esta_publicado_input,
            self._rastrear_inventario_input,
            self._disponible_pdv_input,
            self._alto_envio_input,
            self._largo_envio_input,
            self._ancho_envio_input,
            self._peso_completo_input,
            self._dimensiones_producto_input,
            self._unidad_medida_input,
            self._venta_sin_iva_input,
        )
        for widget in non_sku_inputs:
            widget.setEnabled(enabled)

    def _apply_duplicate_sku_state(self, is_duplicate: bool) -> None:
        """Aplica estilo y bloqueo cuando existe SKU duplicado."""
        property_value = "true" if is_duplicate else "false"
        self._referencia_interna_input.setProperty("skuDuplicate", property_value)
        self._referencia_interna_input.style().unpolish(self._referencia_interna_input)
        self._referencia_interna_input.style().polish(self._referencia_interna_input)
        self._referencia_interna_input.update()

        self._set_non_sku_inputs_enabled(not is_duplicate)

    def _update_form_state(self, *_args: object) -> None:
        """Habilita/deshabilita campos y botones segun estado del formulario."""
        data = self._collect_data()

        has_nombre_base_warning = self._is_duplicate_nombre_base(data)
        self._apply_nombre_base_warning(has_nombre_base_warning)

        is_duplicate = self._is_duplicate_sku(data)
        self._apply_duplicate_sku_state(is_duplicate)
        if is_duplicate:
            self._next_button.setEnabled(False)
            self._save_button.setEnabled(False)
            return

        is_valid = self._is_required_data_complete(data)
        has_pending = self._has_pending_data(data)

        self._next_button.setEnabled(is_valid)
        self._save_button.setEnabled(is_valid or not has_pending)

    def _on_next_clicked(self) -> None:
        """Procesa ingreso del producto actual y limpia el formulario."""
        data = self._collect_data()
        try:
            self._controller.on_import_next(data)
        except (ValidationError, ServiceError) as exc:
            show_error(self, "Error de validacion", str(exc))
            return

        self._reset_form()

    def _on_save_clicked(self) -> None:
        """Ejecuta accion de guardado placeholder y vuelve al menu."""
        data = self._collect_data()
        if self._has_pending_data(data):
            try:
                self._controller.on_import_next(data)
            except (ValidationError, ServiceError) as exc:
                show_error(self, "Error de guardado", str(exc))
                return

        try:
            final_path = self._controller.on_import_save()
        except (ValidationError, ServiceError) as exc:
            show_error(self, "Error de guardado", str(exc))
            return

        show_info(self, "Archivo guardado", f"Archivo generado en:\n{final_path}")
        self._on_back()

    def _on_details_clicked(self) -> None:
        """Abre dialogo de detalles con nombre comercial y observaciones."""
        data = self._collect_data()
        try:
            nombre_comercial = self._controller.build_nombre_comercial_preview(data)
        except (ValidationError, ServiceError):
            nombre_comercial = ""

        dialog = ProductDetailsDialog(nombre_comercial=nombre_comercial, parent=self)
        dialog.exec()

    def _on_back_clicked(self) -> None:
        """Regresa al menu principal."""
        self._controller.on_import_back()
        self._on_back()

    def refresh_product_categories(self) -> None:
        """Recarga categorias en el combo y recalcula ID externo."""
        categories = self._controller.list_product_categories()
        previous_slug = self._selected_product_slug()

        self._producto_input.blockSignals(True)
        self._producto_input.clear()

        for slug, display_name in categories:
            self._producto_input.addItem(display_name, slug)

        if not categories:
            self._producto_input.addItem("Sin categorias", "")
            self._producto_input.setCurrentIndex(0)
        else:
            previous_index = self._find_category_index(previous_slug)
            self._producto_input.setCurrentIndex(previous_index if previous_index >= 0 else 0)

        self._producto_input.blockSignals(False)
        self._preload_selected_category_index()
        self._refresh_external_id()
        self._refresh_internal_reference()
        self._update_form_state()

    def _collect_data(self) -> ImportProductDraft:
        """Recolecta y retorna los datos del formulario en un DTO."""
        selected_slug = self._selected_product_slug()
        id_externo = self._id_externo_value_label.text().strip()
        if id_externo == "-":
            id_externo = ""

        return ImportProductDraft(
            id_externo=id_externo,
            referencia_interna=self._referencia_interna_input.text().strip(),
            producto=self._producto_input.currentText().strip(),
            marca=self._marca_input.text().strip(),
            descripcion_sitio_web=self._descripcion_web_input.toPlainText().strip(),
            descripcion_seo=self._descripcion_seo_input.toPlainText().strip(),
            modelo=self._modelo_input.text().strip(),
            cantidad_inicial=self._cantidad_inicial_input.value(),
            atributo=self._atributo_input.currentText(),
            valores_atributo=self._valores_atributo_input.text().strip(),
            precio_costo=float(self._precio_costo_input.value()),
            venta_sin_iva=float(self._venta_sin_iva_input.value()),
            largo_envio=float(self._largo_envio_input.value()),
            ancho_envio=float(self._ancho_envio_input.value()),
            alto_envio=float(self._alto_envio_input.value()),
            peso_completo=float(self._peso_completo_input.value()),
            dimensiones_producto=self._dimensiones_producto_input.text().strip(),
            unidad_medida_dimensiones=self._unidad_medida_input.currentText().strip(),
            numero_variantes=self._numero_variantes_input.value(),
            esta_publicado=self._esta_publicado_input.isChecked(),
            rastrear_inventario=self._rastrear_inventario_input.isChecked(),
            disponible_punto_venta=self._disponible_pdv_input.isChecked(),
            producto_slug=selected_slug,
            etiquetas=self._selected_tags_csv(),
        )

    def _reset_form(self) -> None:
        """Limpia campos de ingreso para capturar un nuevo producto."""
        self._referencia_interna_input.clear()
        self._descripcion_web_input.clear()
        self._descripcion_seo_input.clear()
        self._marca_input.clear()
        self._modelo_input.clear()
        self._cantidad_inicial_input.setValue(0)
        self._atributo_input.setCurrentIndex(0)
        self._valores_atributo_input.clear()
        self._precio_costo_input.setValue(0.0)
        self._numero_variantes_input.setValue(1)
        self._alto_envio_input.setValue(0.0)
        self._largo_envio_input.setValue(0.0)
        self._ancho_envio_input.setValue(0.0)
        self._peso_completo_input.setValue(0.0)
        self._dimensiones_producto_input.clear()
        self._unidad_medida_input.setCurrentIndex(0)
        self._venta_sin_iva_input.setValue(0.0)
        self._etiquetas_input.set_checked_items([])

        self._esta_publicado_input.setChecked(True)
        self._rastrear_inventario_input.setChecked(True)
        self._disponible_pdv_input.setChecked(True)
        self._refresh_external_id()
        self._refresh_internal_reference()
        self._marca_input.setFocus()
        self._update_form_state()

    def _has_pending_data(self, data: ImportProductDraft) -> bool:
        """Indica si hay datos no enviados pendientes de persistencia."""
        text_fields = (
            data.descripcion_sitio_web,
            data.descripcion_seo,
            data.marca,
            data.modelo,
            data.valores_atributo,
            data.dimensiones_producto,
        )
        if any(field.strip() for field in text_fields):
            return True

        if data.cantidad_inicial != 0:
            return True
        if data.precio_costo != 0.0:
            return True
        if data.venta_sin_iva != 0.0:
            return True
        if data.numero_variantes != 1:
            return True
        if data.etiquetas.strip():
            return True
        if data.alto_envio != 0.0:
            return True
        if data.largo_envio != 0.0:
            return True
        if data.ancho_envio != 0.0:
            return True
        if data.peso_completo != 0.0:
            return True
        default_unidad = self._unidad_medida_input.itemText(0).strip()
        if data.unidad_medida_dimensiones != default_unidad:
            return True

        return False

    def _selected_tags_csv(self) -> str:
        """Retorna etiquetas seleccionadas en formato CSV normalizado."""
        return normalize_selected_tags(self._etiquetas_input.checked_items())

    def _add_form_row(
        self,
        layout: QGridLayout,
        row: int,
        label_text: str,
        field: QWidget,
        align_top: bool = False,
        label_min_width: int = 0,
    ) -> int:
        """Agrega una fila al grid y retorna el siguiente indice de fila."""
        label = self._build_form_label(label_text)
        if label_min_width > 0:
            label.setMinimumWidth(label_min_width)

        label_alignment = Qt.AlignmentFlag.AlignLeft
        if align_top:
            label_alignment |= Qt.AlignmentFlag.AlignTop
        else:
            label_alignment |= Qt.AlignmentFlag.AlignVCenter

        layout.addWidget(label, row, 0, alignment=label_alignment)
        layout.addWidget(field, row, 1)
        return row + 1

    @staticmethod
    def _add_spacer_row(layout: QGridLayout, row: int, height: int) -> int:
        """Agrega una fila espaciadora que ocupa ambas columnas."""
        spacer = QSpacerItem(
            0,
            height,
            QSizePolicy.Policy.Minimum,
            QSizePolicy.Policy.Fixed,
        )
        layout.addItem(spacer, row, 0, 1, 2)
        return row + 1

    @staticmethod
    def _build_form_label(text: str) -> QLabel:
        """Crea labels de formulario con estilo consistente."""
        label = QLabel(text)
        label.setObjectName("formLabel")
        return label

    def _on_product_changed(self, _index: int) -> None:
        """Actualiza ID externo sugerido al cambiar categoria de producto."""
        self._preload_selected_category_index()
        self._refresh_external_id()
        self._refresh_internal_reference()

    def _preload_selected_category_index(self) -> None:
        """Precarga cache de duplicados para el slug seleccionado."""
        slug = self._selected_product_slug()
        if not slug:
            return

        try:
            self._controller.load_category_index(slug)
        except (ValidationError, ServiceError):
            return

    def _on_reference_source_changed(self, _value: str) -> None:
        """Recalcula referencia interna cuando cambian sus campos fuente."""
        self._refresh_internal_reference()

    def _refresh_external_id(self) -> None:
        """Calcula y muestra el siguiente ID para la categoria seleccionada."""
        slug = self._selected_product_slug()
        if not slug:
            self._id_externo_value_label.setText("-")
            self._update_form_state()
            return

        try:
            next_id = self._controller.get_next_id_for(slug)
        except (ValidationError, ServiceError) as exc:
            show_error(self, "Error de importacion", str(exc))
            self._id_externo_value_label.setText("-")
            self._update_form_state()
            return

        self._id_externo_value_label.setText(next_id)
        self._update_form_state()

    def _refresh_internal_reference(self) -> None:
        """Construye referencia interna en formato TIP-MAR-MOD-A."""
        referencia_interna = self._controller.build_internal_reference(
            producto_slug=self._selected_product_slug(),
            marca=self._marca_input.text(),
            modelo=self._modelo_input.text(),
            valores_atributo=self._valores_atributo_input.text(),
        )
        self._referencia_interna_input.setText(referencia_interna)
        self._update_form_state()

    def _selected_product_slug(self) -> str:
        """Retorna slug seleccionado actualmente en el combo de productos."""
        selected_data = self._producto_input.currentData()
        if selected_data is None:
            return ""
        return str(selected_data).strip()

    def _find_category_index(self, slug: str) -> int:
        """Busca indice de una categoria por slug en el combo."""
        if not slug:
            return -1

        for index in range(self._producto_input.count()):
            if str(self._producto_input.itemData(index) or "").strip() == slug:
                return index
        return -1

