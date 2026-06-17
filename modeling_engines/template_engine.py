import sys
import numpy as np
import pyqtgraph as pg
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QApplication, QMainWindow, QSplitter
from PyQt6.QtCore import Qt

# Ensure we can import the base class regardless of how the script is run
try:
    from modeling_engines.base_modeling_dashboard import BaseModelingDashboard
except (ImportError, ModuleNotFoundError):
    from base_modeling_dashboard import BaseModelingDashboard

class NewTechniqueDashboard(BaseModelingDashboard):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.x_data = None
        self.y_data = None
        self.metadata = {}
        
        self.build_ui()

    def build_ui(self):
        """Standard layout: Plots on left, Controls on right."""
        main_layout = QHBoxLayout(self)
        
        # Left Side: Plotting Area
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        self.plot = pg.PlotWidget(title="Analysis Result")
        self.plot.showGrid(x=True, y=True)
        left_layout.addWidget(self.plot)
        
        # Right Side: Control Panel
        right_widget = QWidget()
        right_widget.setFixedWidth(250)
        self.controls_layout = QVBoxLayout(right_widget)
        self.controls_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.controls_layout.addWidget(QLabel("<b>Parameters</b>"))
        
        # Add your sliders/inputs here...
        
        self.controls_layout.addStretch()
        
        main_layout.addWidget(left_widget, stretch=4)
        main_layout.addWidget(right_widget, stretch=1)

    def set_active_data(self, x_data, y_data, metadata_dict):
        """Handshake method to receive data from the main app."""
        self.x_data = x_data
        self.y_data = y_data
        self.metadata = metadata_dict
        
        self.update_plot()

    def update_plot(self):
        """Perform math and update the UI."""
        if self.x_data is None: return
        self.plot.clear()
        self.plot.plot(self.x_data, self.y_data, pen='c')

    def shutdown(self):
        """Cleanup logic called by the main app."""
        self.plot.clear()
        logger.info("NewTechniqueDashboard shutting down.")

    def apply_theme(self, is_dark: bool):
        bg = 'k' if is_dark else 'w'
        self.plot.setBackground(bg)

# --- Standalone Test Stand ---
if __name__ == "__main__":
    app = QApplication(sys.argv)
    win = QMainWindow()
    win.resize(1000, 600)
    
    dash = NewTechniqueDashboard()
    win.setCentralWidget(dash)
    
    # Mock Data
    x = np.linspace(0, 10, 100)
    y = np.sin(x)
    dash.set_active_data(x, y, {"core": {"technique": "Testing"}})
    
    win.show()
    sys.exit(app.exec())
