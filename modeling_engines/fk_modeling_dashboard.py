import sys
import numpy as np
import pyqtgraph as pg
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
    QApplication, QMainWindow, QPushButton, QTextEdit, QFrame, QCheckBox
)
from PyQt6.QtCore import Qt

# Local Imports
try:
    from modeling_engines.base_modeling_dashboard import BaseModelingDashboard
except (ImportError, ModuleNotFoundError):
    from base_modeling_dashboard import BaseModelingDashboard

from processors.public.colton_math_functions import FK_fit
from utils.app_logger import logger

class FKModelingDashboard(BaseModelingDashboard):
    """
    Franz-Keldysh Analysis Dashboard.
    Fits Electro-Absorption (EA) data to a linear combination of 
    Absorption derivatives (d1, d2, d3).
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.x_data = None
        self.y_data = None
        self.metadata = {}
        
        self.build_ui()

    def build_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        
        # --- Left Side: Visualization ---
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        
        self.plot = pg.PlotWidget(title="Franz-Keldysh Derivative Fit")
        self.plot.setLabel('left', 'EA Signal', units='a.u.')
        self.plot.setLabel('bottom', 'Energy', units='eV')
        self.plot.addLegend()
        self.plot.showGrid(x=True, y=True)
        
        self.region = pg.LinearRegionItem()
        self.region.setZValue(10)
        self.plot.addItem(self.region)
        
        self.results_log = QTextEdit()
        self.results_log.setReadOnly(True)
        self.results_log.setPlaceholderText("Fit coefficients will appear here...")
        self.results_log.setMaximumHeight(150)
        
        left_layout.addWidget(self.plot, stretch=3)
        left_layout.addWidget(self.results_log, stretch=1)
        
        # --- Right Side: Controls ---
        right_panel = QFrame()
        right_panel.setFixedWidth(240)
        right_panel.setFrameShape(QFrame.Shape.StyledPanel)
        controls = QVBoxLayout(right_panel)
        controls.setAlignment(Qt.AlignmentFlag.AlignTop)
        
        controls.addWidget(QLabel("<b>FK ANALYSIS CONTROLS</b>"))
        controls.addSpacing(10)
        
        self.btn_fit = QPushButton("🚀 Run Derivative Fit")
        self.btn_fit.setMinimumHeight(40)
        self.btn_fit.clicked.connect(self.execute_fk_analysis)
        controls.addWidget(self.btn_fit)
        
        self.chk_show_full_fit = QCheckBox("Show Fit Across Entire Range")
        self.chk_show_full_fit.setChecked(False)
        self.chk_show_full_fit.toggled.connect(self.execute_fk_analysis)
        controls.addWidget(self.chk_show_full_fit)
        
        controls.addStretch()
        
        layout.addWidget(left_panel, stretch=4)
        layout.addWidget(right_panel, stretch=1)

    def set_active_data(self, x_data, y_data, metadata_dict):
        self.x_data = x_data
        self.y_data = y_data
        self.metadata = metadata_dict
        self.update_view()
        if self.x_data is not None and len(self.x_data) > 0:
            min_x, max_x = np.min(self.x_data), np.max(self.x_data)
            self.region.setRegion([min_x, max_x])

    def update_view(self):
        if self.x_data is None: return
        self.plot.clear()
        self.plot.plot(self.x_data, self.y_data, pen='w', name="Experimental EA")
        self.plot.addItem(self.region)

    def execute_fk_analysis(self):
        """Performs the FK fit using derivatives of the absorption."""
        if self.x_data is None or self.y_data is None:
            logger.warning("FK Dashboard: No data loaded to fit.")
            return

        min_x, max_x = self.region.getRegion()
        mask = (self.x_data >= min_x) & (self.x_data <= max_x)
        
        if not np.any(mask):
            self.results_log.append("No data in the selected region.")
            return

        # Calculate derivatives over full dataset to avoid edge effects
        d1 = np.gradient(self.y_data)
        d2 = np.gradient(d1)
        
        d1_fit = d1[mask]
        d2_fit = d2[mask]
        y_fit = self.y_data[mask]
        x_fit = self.x_data[mask]

        from scipy.optimize import minimize
        def objective(guess):
            a, b = guess
            fit = a * d1_fit + b * d2_fit
            return np.sum((fit - y_fit) ** 2)

        initial_guess = [0.01, 0.01]
        result = minimize(objective, initial_guess)
        
        if not result.success:
            self.results_log.append(f"FK Fit failed: {result.message}")
            return

        a, b = result.x
        
        if self.chk_show_full_fit.isChecked():
            x_plot = self.x_data
            fit_curve = a * d1 + b * d2
        else:
            x_plot = x_fit
            fit_curve = a * d1_fit + b * d2_fit
        
        if hasattr(self, 'fit_plot_item') and self.fit_plot_item in self.plot.listDataItems():
            self.plot.removeItem(self.fit_plot_item)
            
        self.fit_plot_item = self.plot.plot(x_plot, fit_curve, pen=pg.mkPen('y', width=2), name="FK Fit Result")
        self.results_log.append("-------------------------")
        self.results_log.append(f"FK Fit executed successfully.")
        self.results_log.append(f"Fitted range: {min_x:.3f} eV to {max_x:.3f} eV")
        self.results_log.append(f"Coefficients:\n 1st Deriv: {a:.4e}\n 2nd Deriv: {b:.4e}")

    def shutdown(self):
        self.plot.clear()
        logger.info("FKModelingDashboard shutdown.")

    def apply_theme(self, is_dark: bool):
        bg = 'k' if is_dark else 'w'
        self.plot.setBackground(bg)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    win = QMainWindow()
    win.resize(1100, 700)
    dash = FKModelingDashboard()
    win.setCentralWidget(dash)
    
    # Mock EA data for standalone testing
    x = np.linspace(1.5, 2.5, 500)
    y = np.sin(x*20) * np.exp(-(x-2)**2 / 0.1)
    dash.set_active_data(x, y, {"core": {"technique": "EA Voltage Series"}})
    
    win.show()
    sys.exit(app.exec())