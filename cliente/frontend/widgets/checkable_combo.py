"""ComboBox checkeable para seleccion multiple."""

from __future__ import annotations

from PyQt6.QtCore import QEvent, Qt, pyqtSignal
from PyQt6.QtGui import QStandardItem, QStandardItemModel
from PyQt6.QtWidgets import QComboBox, QWidget


class CheckableComboBox(QComboBox):
    """ComboBox con items checkeables y texto resumen fijo."""

    checked_items_changed = pyqtSignal()
    _EMPTY_SUMMARY = "Etiquetas"

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._model = QStandardItemModel(self)
        self.setModel(self._model)
        self.setEditable(True)
        self.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
        self.lineEdit().setReadOnly(True)
        self.lineEdit().setPlaceholderText(self._EMPTY_SUMMARY)
        self.lineEdit().setCursorPosition(0)
        self.setCurrentIndex(-1)
        self.view().viewport().installEventFilter(self)
        self.view().installEventFilter(self)
        self._model.dataChanged.connect(self._on_model_data_changed)
        self._update_summary_text()

    def set_items(self, items: list[str]) -> None:
        """Define los elementos disponibles, todos inicialmente desmarcados."""
        self._model.clear()
        for label in items:
            text = label.strip()
            if not text:
                continue
            item = QStandardItem(text)
            item.setEditable(False)
            item.setFlags(
                Qt.ItemFlag.ItemIsEnabled
                | Qt.ItemFlag.ItemIsSelectable
                | Qt.ItemFlag.ItemIsUserCheckable
            )
            item.setData(Qt.CheckState.Unchecked, Qt.ItemDataRole.CheckStateRole)
            self._model.appendRow(item)

        self._update_summary_text()
        self.checked_items_changed.emit()

    def checked_items(self) -> list[str]:
        """Retorna lista de elementos marcados en orden visual."""
        selected: list[str] = []
        for row in range(self._model.rowCount()):
            item = self._model.item(row)
            if item is None:
                continue
            if item.checkState() == Qt.CheckState.Checked:
                selected.append(item.text().strip())
        return selected

    def set_checked_items(self, items: list[str]) -> None:
        """Marca los elementos indicados y desmarca el resto."""
        desired = {value.strip() for value in items if value.strip()}
        for row in range(self._model.rowCount()):
            item = self._model.item(row)
            if item is None:
                continue
            check_state = (
                Qt.CheckState.Checked if item.text().strip() in desired else Qt.CheckState.Unchecked
            )
            item.setCheckState(check_state)

        self._update_summary_text()
        self.checked_items_changed.emit()

    def eventFilter(self, watched: object, event: QEvent) -> bool:
        """Permite checkear multiples items sin perder el resumen del combo."""
        if watched is self.view().viewport() and event.type() == QEvent.Type.MouseButtonRelease:
            index = self.view().indexAt(event.pos())
            if index.isValid():
                self._toggle_item(index.row())
                return True

        if watched is self.view() and event.type() == QEvent.Type.KeyPress:
            if event.key() in (Qt.Key.Key_Space, Qt.Key.Key_Return, Qt.Key.Key_Enter):
                index = self.view().currentIndex()
                if index.isValid():
                    self._toggle_item(index.row())
                    return True

        return super().eventFilter(watched, event)

    def _toggle_item(self, row: int) -> None:
        """Alterna estado checkeado de un item."""
        item = self._model.item(row)
        if item is None:
            return
        next_state = (
            Qt.CheckState.Unchecked
            if item.checkState() == Qt.CheckState.Checked
            else Qt.CheckState.Checked
        )
        item.setCheckState(next_state)
        self._update_summary_text()
        self.checked_items_changed.emit()

    def _on_model_data_changed(self, *_args: object) -> None:
        """Sincroniza resumen cuando hay cambios directos en el modelo."""
        self._update_summary_text()

    def _update_summary_text(self) -> None:
        """Actualiza texto mostrado en el combo sin cambiar seleccion visible."""
        selected = self.checked_items()
        summary = self._build_summary_text(selected)
        self.setCurrentIndex(-1)
        self.lineEdit().setText(summary)
        self.lineEdit().setCursorPosition(0)
        tooltip = ", ".join(selected) if selected else self._EMPTY_SUMMARY
        self.setToolTip(tooltip)

    def _build_summary_text(self, selected: list[str]) -> str:
        """Construye resumen compacto de etiquetas seleccionadas."""
        if not selected:
            return self._EMPTY_SUMMARY

        preview = ", ".join(selected)
        if len(preview) <= 28 and len(selected) <= 3:
            return preview
        return f"Etiquetas ({len(selected)})"
