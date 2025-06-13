from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QTableWidget, QTableWidgetItem, QPushButton, QMessageBox
)
import pyqtgraph as pg


class SimilarityTableDialog(QDialog):
    """
    Диалог для отображения результатов сходства в виде таблицы.
    results: dict[int, float] — {индекс_в_playlist: степень_сходства}
    playlist: list[dict] — список треков с ключом 'title'
    """
    def __init__(self, parent, results: dict, playlist: list[dict]):
        super().__init__(parent)
        self.setWindowTitle("Похожесть треков")
        self.resize(400, 300)

        # Сортируем по убыванию сходства
        sorted_items = sorted(results.items(), key=lambda x: -x[1])

        layout = QVBoxLayout(self)

        table = QTableWidget(len(sorted_items), 2, self)
        table.setHorizontalHeaderLabels(["Трек", "Сходство"])
        table.setEditTriggers(table.NoEditTriggers)

        for row, (idx, score) in enumerate(sorted_items):
            title = playlist[idx]['title']
            perc = f"{score * 100:.1f}%"
            table.setItem(row, 0, QTableWidgetItem(title))
            table.setItem(row, 1, QTableWidgetItem(perc))

        table.resizeColumnsToContents()
        layout.addWidget(table)

        close_btn = QPushButton("Закрыть")
        close_btn.clicked.connect(self.accept)
        layout.addWidget(close_btn)


class SimilarityGraphDialog(QDialog):
    """
    Диалог для отображения результатов сходства в виде гистограммы (BarGraphItem).
    results: dict[int, float] — {индекс_в_playlist: степень_сходства}
    playlist: list[dict]
    """
    def __init__(self, parent, results: dict, playlist: list[dict]):
        super().__init__(parent)
        self.setWindowTitle("График сходства треков")
        self.resize(600, 400)

        layout = QVBoxLayout(self)

        sorted_items = sorted(results.items(), key=lambda x: -x[1])
        xs = list(range(len(sorted_items)))
        ys = [score * 100 for _, score in sorted_items]

        plot_widget = pg.PlotWidget()
        bars = pg.BarGraphItem(x=xs, height=ys, width=0.6, brush=pg.mkBrush('#3daee9'))
        plot_widget.addItem(bars)

        # Подписи оси X
        xticks = [(i, playlist[idx]['title']) for i, (idx, _) in enumerate(sorted_items)]
        plot_widget.getAxis('bottom').setTicks([xticks])
        plot_widget.getAxis('bottom').setStyle(tickTextAngle=45)

        plot_widget.setLabel('left', 'Сходство, %')
        plot_widget.setLabel('bottom', 'Трек')

        layout.addWidget(plot_widget)

        close_btn = QPushButton("Закрыть")
        close_btn.clicked.connect(self.accept)
        layout.addWidget(close_btn)
