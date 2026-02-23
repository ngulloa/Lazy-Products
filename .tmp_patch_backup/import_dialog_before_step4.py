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

from cliente.frontend.dialogs import show_error, show_info
from shared.errors import ServiceError, ValidationError
from shared.protocol import ImportProductDraft

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
        card_layout.setContentsMargins(32, 32, 32, 32)
        card_layout.setSpacing(18)

        title_label = QLabel("Crear archivo de importación", card)
        title_label.setObjectName("dialogTitle")
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        form_layout = QGridLayout()
        form_layout.setContentsMargins(0, 0, 0, 0)
        form_layout.setHorizontalSpacing(20)
        form_layout.setVerticalSpacing(12)
        form_layout.setColumnMinimumWidth(0, 210)
        form_layout.setColumnStretch(1, 1)

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

        self._producto_input = QComboBox(card)
        self._producto_input.addItem("Sin categorias", "")
        self._producto_input.currentIndexChanged.connect(self._on_product_changed)

        self._descripcion_web_input = QTextEdit(card)
        self._descripcion_web_input.setFixedHeight(84)
        self._descripcion_web_input.setPlaceholderText(
            "Escribe la descripción HTML/para web…"
        )

        self._descripcion_seo_input = QTextEdit(card)
        self._descripcion_seo_input.setFixedHeight(70)
        self._descripcion_seo_input.setPlaceholderText(
            "Escribe la descripción corta SEO…"
        )

        self._modelo_input = QLineEdit(card)

        self._cantidad_inicial_input = QSpinBox(card)
        self._cantidad_inicial_input.setRange(0, 1_000_000)
        self._cantidad_inicial_input.setButtonSymbols(
            QAbstractSpinBox.ButtonSymbols.NoButtons
        )

        self._atributo_input = QComboBox(card)
        self._atributo_input.addItems(["Color", "Diseño"])

        self._valores_atributo_input = QLineEdit(card)

        self._precio_costo_input = QDoubleSpinBox(card)
        self._precio_costo_input.setRange(0.0, 1_000_000_000.0)
        self._precio_costo_input.setDecimals(2)
        self._precio_costo_input.setSingleStep(0.5)
        self._precio_costo_input.setButtonSymbols(
            QAbstractSpinBox.ButtonSymbols.NoButtons
        )

        self._numero_variantes_input = QSpinBox(card)
        self._numero_variantes_input.setRange(1, 10_000)
        self._numero_variantes_input.setValue(1)
        self._numero_variantes_input.setButtonSymbols(
            QAbstractSpinBox.ButtonSymbols.NoButtons
        )

        self._esta_publicado_input = QCheckBox(card)
        self._esta_publicado_input.setChecked(True)

        self._rastrear_inventario_input = QCheckBox(card)
        self._rastrear_inventario_input.setChecked(True)

        self._disponible_pdv_input = QCheckBox(card)
        self._disponible_pdv_input.setChecked(True)

        row = 0
        row = self._add_form_row(form_layout, row, "ID Externo", self._id_externo_badge)
        row = self._add_form_row(
            form_layout,
            row,
            "Referencia interna",
            self._referencia_interna_input,
        )
        row = self._add_form_row(form_layout, row, "Producto", self._producto_input)
        row = self._add_form_row(
            form_layout,
            row,
            "Descripcion para el sitio web",
            self._descripcion_web_input,
            align_top=True,
        )
        row = self._add_spacer_row(form_layout, row, 12)
        row = self._add_form_row(
            form_layout,
            row,
            "Descripcion SEO",
            self._descripcion_seo_input,
            align_top=True,
        )
        row = self._add_form_row(form_layout, row, "Modelo", self._modelo_input)
        row = self._add_form_row(
            form_layout,
            row,
            "Cantidad inicial",
            self._cantidad_inicial_input,
        )
        row = self._add_form_row(form_layout, row, "Atributo", self._atributo_input)
        row = self._add_form_row(
            form_layout,
            row,
            "Valores de Atributo",
            self._valores_atributo_input,
        )
        row = self._add_form_row(
            form_layout,
            row,
            "Precio de Costo",
            self._precio_costo_input,
        )
        row = self._add_form_row(
            form_layout,
            row,
            "Numero de variantes",
            self._numero_variantes_input,
        )
        row = self._add_form_row(
            form_layout,
            row,
            "Esta Publicado",
            self._esta_publicado_input,
        )
        row = self._add_form_row(
            form_layout,
            row,
            "Rastrear inventario",
            self._rastrear_inventario_input,
        )
        self._add_form_row(
            form_layout,
            row,
            "Disponible en Punto de venta",
            self._disponible_pdv_input,
        )

        buttons_layout = QHBoxLayout()
        buttons_layout.setSpacing(10)

        next_button = QPushButton("Siguiente", card)
        save_button = QPushButton("Guardar", card)
        back_button = QPushButton("Regresar", card)
        back_button.setObjectName("backButton")

        next_button.clicked.connect(self._on_next_clicked)
        save_button.clicked.connect(self._on_save_clicked)
        back_button.clicked.connect(self._on_back_clicked)

        buttons_layout.addWidget(next_button)
        buttons_layout.addWidget(save_button)
        buttons_layout.addWidget(back_button)

        card_layout.addWidget(title_label)
        card_layout.addLayout(form_layout)
        card_layout.addSpacing(8)
        card_layout.addLayout(buttons_layout)

        shadow = QGraphicsDropShadowEffect(card)
        shadow.setBlurRadius(38)
        shadow.setOffset(0, 8)
        shadow.setColor(QColor(0, 0, 0, 38))
        card.setGraphicsEffect(shadow)

        root_layout.addWidget(card)
        self._referencia_interna_input.setFocus()

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
                font-size: 24px;
                font-weight: 700;
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
            QPushButton {
                background-color: #2563eb;
                border: none;
                border-radius: 10px;
                color: #ffffff;
                font-family: "Segoe UI";
                font-size: 14px;
                font-weight: 600;
                min-height: 44px;
                padding: 8px 12px;
            }
            QPushButton:hover {
                background-color: #1d4ed8;
            }
            QPushButton:pressed {
                background-color: #1e40af;
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
            """
        )

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
        self._refresh_external_id()

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
            descripcion_sitio_web=self._descripcion_web_input.toPlainText().strip(),
            descripcion_seo=self._descripcion_seo_input.toPlainText().strip(),
            modelo=self._modelo_input.text().strip(),
            cantidad_inicial=self._cantidad_inicial_input.value(),
            atributo=self._atributo_input.currentText(),
            valores_atributo=self._valores_atributo_input.text().strip(),
            precio_costo=float(self._precio_costo_input.value()),
            numero_variantes=self._numero_variantes_input.value(),
            esta_publicado=self._esta_publicado_input.isChecked(),
            rastrear_inventario=self._rastrear_inventario_input.isChecked(),
            disponible_punto_venta=self._disponible_pdv_input.isChecked(),
            producto_slug=selected_slug,
        )

    def _reset_form(self) -> None:
        """Limpia campos de ingreso para capturar un nuevo producto."""
        self._referencia_interna_input.clear()
        self._descripcion_web_input.clear()
        self._descripcion_seo_input.clear()
        self._modelo_input.clear()
        self._cantidad_inicial_input.setValue(0)
        self._atributo_input.setCurrentIndex(0)
        self._valores_atributo_input.clear()
        self._precio_costo_input.setValue(0.0)
        self._numero_variantes_input.setValue(1)

        self._esta_publicado_input.setChecked(True)
        self._rastrear_inventario_input.setChecked(True)
        self._disponible_pdv_input.setChecked(True)
        self._refresh_external_id()
        self._referencia_interna_input.setFocus()

    @staticmethod
    def _has_pending_data(data: ImportProductDraft) -> bool:
        """Indica si hay datos no enviados pendientes de persistencia."""
        text_fields = (
            data.referencia_interna,
            data.descripcion_sitio_web,
            data.descripcion_seo,
            data.modelo,
            data.valores_atributo,
        )
        if any(field.strip() for field in text_fields):
            return True

        if data.cantidad_inicial != 0:
            return True
        if data.precio_costo != 0.0:
            return True
        if data.numero_variantes != 1:
            return True

        return False

    def _add_form_row(
        self,
        layout: QGridLayout,
        row: int,
        label_text: str,
        field: QWidget,
        align_top: bool = False,
    ) -> int:
        """Agrega una fila al grid y retorna el siguiente indice de fila."""
        label = self._build_form_label(label_text)
        label.setMinimumWidth(210)

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
        self._refresh_external_id()

    def _refresh_external_id(self) -> None:
        """Calcula y muestra el siguiente ID para la categoria seleccionada."""
        slug = self._selected_product_slug()
        if not slug:
            self._id_externo_value_label.setText("-")
            return

        try:
            next_id = self._controller.get_next_id_for(slug)
        except (ValidationError, ServiceError) as exc:
            show_error(self, "Error de importacion", str(exc))
            self._id_externo_value_label.setText("-")
            return

        self._id_externo_value_label.setText(next_id)

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
