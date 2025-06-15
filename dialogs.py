# dialogs.py

from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QTabWidget, QWidget,
    QTableWidget, QTableWidgetItem, QHeaderView, QLineEdit,
    QPushButton, QSizePolicy, QLabel
)
from PyQt5.QtCore import Qt
import pyqtgraph as pg
from utils import format_time

class SimilarityTableDialog(QDialog):
    def __init__(self, parent, ref_idx: int, results: dict[int, float], playlist: list[dict]):
        super().__init__(parent)
        self.playlist = playlist
        self.ref_idx = ref_idx

        self.setWindowTitle("Сходство треков")
        self.resize(800, 600)

        lo = QVBoxLayout(self)

        # Эталон
        lbl = QLabel(f"Эталон: «{playlist[ref_idx]['title']}»", self)
        lbl.setAlignment(Qt.AlignCenter)
        lbl.setStyleSheet("font-weight: bold; font-size: 16px;")
        lo.addWidget(lbl)

        # Поиск
        self.search = QLineEdit(self)
        self.search.setPlaceholderText("Поиск по названию...")
        lo.addWidget(self.search)

        # Подготовка данных
        self.sorted_items = sorted(results.items(), key=lambda x: -x[1])

        # Таблица: Трек, Длительность, Сходство
        self.table = QTableWidget(len(self.sorted_items), 3, self)
        self.table.setHorizontalHeaderLabels(["Трек", "Длительность", "Сходство"])
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setAlternatingRowColors(True)
        self.table.setSortingEnabled(False)
        self.table.verticalHeader().setDefaultSectionSize(30)
        self.table.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        hdr = self.table.horizontalHeader()
        hdr.setSectionResizeMode(QHeaderView.Stretch)

        # Заполнение
        for row, (idx, score) in enumerate(self.sorted_items):
            tr = playlist[idx]
            title = tr["title"]
            dur_ms = int(tr["duration"] * 1000)
            perc = f"{score*100:.1f}%"

            item_t = QTableWidgetItem(title)
            item_t.setData(Qt.UserRole, idx)
            item_d = QTableWidgetItem(format_time(dur_ms))
            item_s = QTableWidgetItem(perc)
            item_s.setToolTip(f"{score:.4f}")

            self.table.setItem(row, 0, item_t)
            self.table.setItem(row, 1, item_d)
            self.table.setItem(row, 2, item_s)

        self.table.setSortingEnabled(True)
        self.table.sortItems(2, Qt.DescendingOrder)
        
        lo.addWidget(self.table)

        # Закрыть
        btn = QPushButton("Закрыть", self)
        btn.clicked.connect(self.accept)
        lo.addWidget(btn)

        # Сигналы
        self.search.textChanged.connect(self._filter_rows)
        self.table.itemDoubleClicked.connect(self._on_double_click)

    def _filter_rows(self, text: str):
        text = text.lower().strip()
        for row, (idx, _) in enumerate(self.sorted_items):
            title = self.playlist[idx]["title"].lower()
            self.table.setRowHidden(row, text not in title)

    def _on_double_click(self, item: QTableWidgetItem):
        idx = self.table.item(item.row(), 0).data(Qt.UserRole)
        self.parent().playlistWidget.setCurrentRow(idx)
        self.parent().update_ui_for_current_track()
        self.accept()