import sys
import numpy as np
import pyqtgraph as pg
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
    QApplication, QMainWindow, QPushButton, QTextEdit, QFrame, QListWidget, QListWidgetItem
)
from PyQt6.QtCore import Qt



# Local Imports
try:
    from modeling_engines.base_modeling_dashboard import BaseModelingDashboard
except (ImportError, ModuleNotFoundError):
    from base_modeling_dashboard import BaseModelingDashboard

from processors.factory import get_processor
from utils.app_logger import logger

class KAnalysisDashboard(BaseModelingDashboard):
    """
    K-Analysis Dashboard for EA Voltage Series.
    Finds the power-law dependence (k) of the EA peak vs Electric Field.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        # Capture the window reference before we are reparented by a layout
        self.parent_window = getattr(parent, 'parent_window', None)

        self.x_data = None
        self.y_data = None
        self.metadata = {}
        self.traces = [] # Loaded from EAProcessor
        
        self.current_view = "spectrum" # or "k-plot"
        self.region = None
        
        self.build_ui()

    def build_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        
        # --- Left Side: Plotting Area ---
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        
        self.plot = pg.PlotWidget(title="EA Voltage Series")
        self.plot.showGrid(x=True, y=True)
        self.plot.addLegend()
        
        self.results_log = QTextEdit()
        self.results_log.setReadOnly(True)
        self.results_log.setMaximumHeight(120)
        
        left_layout.addWidget(self.plot, stretch=4)
        left_layout.addWidget(self.results_log, stretch=1)
        
        # --- Right Side: Controls ---
        right_panel = QFrame()
        right_panel.setFixedWidth(240)
        right_panel.setFrameShape(QFrame.Shape.StyledPanel)
        controls = QVBoxLayout(right_panel)
        controls.setAlignment(Qt.AlignmentFlag.AlignTop)
        
        controls.addWidget(QLabel("<b>K-ANALYSIS TOOLS</b>"))
        controls.addSpacing(10)
        
        self.btn_toggle_view = QPushButton("📊 Switch to Log-Log Plot")
        self.btn_toggle_view.clicked.connect(self.toggle_view)
        controls.addWidget(self.btn_toggle_view)
        
        self.btn_range = QPushButton("🎯 Select Peak Range")
        self.btn_range.setCheckable(True)
        self.btn_range.clicked.connect(self.toggle_range_selector)
        controls.addWidget(self.btn_range)
        
        controls.addStretch()
        
        layout.addWidget(left_panel, stretch=4)
        layout.addWidget(right_panel, stretch=1)

    def set_active_data(self, x_data, y_data, metadata_dict):
        """Re-loads the whole series using the EAProcessor logic."""
        self.x_data = x_data
        self.metadata = metadata_dict
        
        # Use the EAProcessor to load the full series correctly
        processor = get_processor("EA Voltage Series", self.parent_window)
        self.traces = processor._load_traces(metadata_dict)
        
        self.update_view()

    def update_view(self):
        self.plot.clear()
        if not self.traces: return
        
        processor = get_processor(self.metadata.get("core", {}).get("technique"), self.parent_window)
        settings = self.metadata.get("analysis_settings", {})

        if self.current_view == "spectrum":
            self.plot.setTitle("EA Voltage Series Spectrum")
            self.plot.setLabel('left', 'EA Signal', units='mOD')
            self.plot.setLogMode(x=False, y=False)
            
            # Plot all traces in the series
            for i, raw_trace in enumerate(self.traces):
                x, y = processor._process_trace(raw_trace['wavelengths'], raw_trace['ea'], settings, i)
                color = pg.intColor(i, len(self.traces))
                self.plot.plot(x, y, pen=color, name=raw_trace['label'])
        else:
            self.plot.setTitle("Peak Amplitude vs Electric Field")
            self.plot.setLabel('left', 'Peak Amplitude', units='mOD')
            self.plot.setLabel('bottom', 'Voltage', units='V')
            self.plot.setLogMode(x=True, y=True)
            self.perform_k_analysis()

    def toggle_view(self):
        if self.current_view == "spectrum":
            self.current_view = "k-plot"
            self.btn_toggle_view.setText("📈 Switch to Spectrum")
        else:
            self.current_view = "spectrum"
            self.btn_toggle_view.setText("📊 Switch to Log-Log Plot")
        self.update_view()

    def toggle_range_selector(self, checked):
        if checked:
            if self.current_view != "spectrum":
                self.toggle_view()
            
            # Add a draggable region
            self.region = pg.LinearRegionItem()
            self.region.setZValue(10)
            self.plot.addItem(self.region)
            self.region.sigRegionChangeFinished.connect(self.perform_k_analysis)
        else:
            if self.region:
                self.plot.removeItem(self.region)
                self.region = None

    def perform_k_analysis(self):
        if not self.region or not self.traces: return
        
        min_x, max_x = self.region.getRegion()
        processor = get_processor(self.metadata.get("core", {}).get("technique"), self.parent_window)
        settings = self.metadata.get("analysis_settings", {})
        
        voltages = []
        peaks = []
        
        for i, raw_trace in enumerate(self.traces):
            x, y = processor._process_trace(raw_trace['wavelengths'], raw_trace['ea'], settings, i)
            
            mask = (x >= min_x) & (x <= max_x)
            if np.any(mask):
                voltages.append(raw_trace.get('value', 0))
                # Find the maximum absolute peak in the range
                peaks.append(np.max(np.abs(y[mask])))
        
        v_arr = np.array(voltages)
        p_arr = np.array(peaks)
        
        # Filter out zeros for log-log fit
        mask = (v_arr > 0) & (p_arr > 0)
        if np.sum(mask) < 2: return
        
        log_v = np.log10(v_arr[mask])
        log_p = np.log10(p_arr[mask])
        
        # Linear Fit: log(P) = k * log(V) + C
        k, intercept = np.polyfit(log_v, log_p, 1)
        
        self.results_log.append(f"<b>Selected Range:</b> {min_x:.1f} - {max_x:.1f} nm")
        self.results_log.append(f"<b>Calculated k-factor:</b> {k:.3f}")
        self.results_log.append("-" * 20)

        if self.current_view == "k-plot":
            self.plot.clear()
            self.plot.plot(v_arr[mask], p_arr[mask], pen=None, symbol='o', symbolBrush='y', name="Data")
            # Plot Fit Line
            fit_v = np.linspace(min(v_arr[mask]), max(v_arr[mask]), 100)
            fit_p = 10**(k * np.log10(fit_v) + intercept)
            self.plot.plot(fit_v, fit_p, pen=pg.mkPen('r', width=2), name=f"Fit (k={k:.2f})")

    def shutdown(self):
        self.plot.clear()
        logger.info("KAnalysisDashboard shutting down.")

    def apply_theme(self, is_dark: bool):
        self.plot.setBackground('k' if is_dark else 'w')

if __name__ == "__main__":
    app = QApplication(sys.argv)
    win = QMainWindow()
    win.resize(1000, 600)
    dash = KAnalysisDashboard()
    win.setCentralWidget(dash)
    # Mocking metadata is complex here due to Processor dependencies, 
    # usually tested within the main app environment.
    win.show()
    sys.exit(app.exec())