from __future__ import annotations

import pyqtgraph as pg
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QCheckBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)


class KAnalysisUiWidget(QWidget):
    """Container widget that hosts the plotting surface and controls."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)

        left_panel = QWidget(self)
        left_layout = QVBoxLayout(left_panel)

        self.plot = pg.PlotWidget(title="EA Voltage Series")
        self.plot.showGrid(x=True, y=True)
        self.plot.setMouseTracking(True)
        self.plot.addLegend()

        self.results_log = QTextEdit(self)
        self.results_log.setReadOnly(True)
        self.results_log.setMaximumHeight(120)

        left_layout.addWidget(self.plot, stretch=4)
        left_layout.addWidget(self.results_log, stretch=1)

        right_panel = QFrame(self)
        right_panel.setFixedWidth(240)
        right_panel.setFrameShape(QFrame.Shape.StyledPanel)
        controls = QVBoxLayout(right_panel)
        controls.setAlignment(Qt.AlignmentFlag.AlignTop)

        controls.addWidget(QLabel("<b>K-ANALYSIS TOOLS</b>"))
        controls.addSpacing(10)

        self.btn_add_range = QPushButton("➕ Add Peak Range", self)
        controls.addWidget(self.btn_add_range)

        self.btn_remove_range = QPushButton("➖ Remove Selected Range", self)
        self.btn_remove_range.setEnabled(False)
        controls.addWidget(self.btn_remove_range)

        controls.addWidget(QLabel("<b>Active Ranges:</b>"))
        self.range_list_widget = QListWidget(self)
        controls.addWidget(self.range_list_widget)

        self.btn_toggle_view = QPushButton("📊 Switch to Log-Log Plot", self)
        controls.addWidget(self.btn_toggle_view)

        self.chk_show_fits = QCheckBox("Show Gaussian Fits", self)
        self.chk_show_fits.setChecked(True)
        controls.addWidget(self.chk_show_fits)

        controls.addStretch()

        layout.addWidget(left_panel, stretch=4)
        layout.addWidget(right_panel, stretch=1)


def build_k_analysis_ui(parent=None) -> KAnalysisUiWidget:
    """Create the reusable UI container used by the dashboard."""
    return KAnalysisUiWidget(parent)
