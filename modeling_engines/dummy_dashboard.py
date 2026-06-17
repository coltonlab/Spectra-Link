import sys
import numpy as np
import pyqtgraph as pg
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, 
    QSlider, QTextEdit, QLabel, QApplication, QMainWindow
)
from PyQt6.QtCore import Qt

# Support both standalone execution and package import
try:
    from modeling_engines.base_modeling_dashboard import BaseModelingDashboard
except (ImportError, ModuleNotFoundError):
    # Fallback for when running the script directly from within the modeling_engines folder
    from base_modeling_dashboard import BaseModelingDashboard

class DummyDashboard(BaseModelingDashboard):
    """
    A reference implementation of a modeling dashboard used for testing 
    the pluggable architecture.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.x_data = None
        self.y_data = None
        self.metadata = None
        
        self.build_ui()

    def build_ui(self):
        """Constructs the split-pane layout with plots and controls."""
        main_layout = QHBoxLayout(self)
        
        # --- Left Column: Plots & Text ---
        left_col = QVBoxLayout()
        
        self.top_plot = pg.PlotWidget(title="Raw Experimental Data")
        self.top_plot.setLabel('left', 'Intensity', units='a.u.')
        self.top_plot.showGrid(x=True, y=True)
        
        self.bottom_plot = pg.PlotWidget(title="Simulated Fit Result")
        self.bottom_plot.setLabel('left', 'Amplitude', units='a.u.')
        self.bottom_plot.showGrid(x=True, y=True)
        
        self.results_box = QTextEdit()
        self.results_box.setReadOnly(True)
        self.results_box.setPlaceholderText("Fit parameters will appear here...")
        self.results_box.setMaximumHeight(100)
        
        left_col.addWidget(self.top_plot, stretch=2)
        left_col.addWidget(self.bottom_plot, stretch=2)
        left_col.addWidget(self.results_box, stretch=1)
        
        # --- Right Column: Controls ---
        right_col = QVBoxLayout()
        right_col.setAlignment(Qt.AlignmentFlag.AlignTop)
        
        right_col.addWidget(QLabel("<b>Model Controls</b>"))
        
        self.scale_slider = QSlider(Qt.Orientation.Horizontal)
        self.scale_slider.setRange(1, 200)
        self.scale_slider.setValue(100)
        self.scale_slider.valueChanged.connect(self._on_parameter_changed)
        
        self.lbl_slider = QLabel("Scaling Factor: 1.0")
        
        self.btn_run = QPushButton("Execute Fit")
        self.btn_run.clicked.connect(self._simulate_fit)
        
        right_col.addWidget(self.lbl_slider)
        right_col.addWidget(self.scale_slider)
        right_col.addWidget(self.btn_run)
        right_col.addStretch() # Push items to the top
        
        # Combine columns
        main_layout.addLayout(left_col, stretch=4)
        main_layout.addLayout(right_col, stretch=1)

    def set_active_data(self, x_data: np.ndarray, y_data: np.ndarray, metadata_dict: dict):
        """Update the dashboard with new spectroscopic data."""
        self.x_data = x_data
        self.y_data = y_data
        self.metadata = metadata_dict
        
        # Update top plot immediately
        self.top_plot.clear()
        self.top_plot.plot(self.x_data, self.y_data, pen='y')
        
        # Reset bottom plot and results
        self._simulate_fit()

    def _on_parameter_changed(self, value):
        factor = value / 100.0
        self.lbl_slider.setText(f"Scaling Factor: {factor:.2f}")
        self._simulate_fit()

    def _simulate_fit(self):
        """Simulate a mathematical model by scaling the Y data."""
        if self.x_data is None or self.y_data is None:
            return
            
        factor = self.scale_slider.value() / 100.0
        fit_y = self.y_data * factor
        
        self.bottom_plot.clear()
        self.bottom_plot.plot(self.x_data, fit_y, pen=pg.mkPen('c', width=2))
        
        # Update text output
        results = (
            f"Model: Linear Scaling\n"
            f"Technique: {self.metadata.get('core', {}).get('technique', 'Unknown')}\n"
            f"Global Scale: {factor:.4f}\n"
            f"Peak Y: {np.max(fit_y):.4e}"
        )
        self.results_box.setText(results)

    def shutdown(self):
        """Clean up pyqtgraph instances to prevent memory leaks."""
        self.top_plot.clear()
        self.bottom_plot.clear()
        self.x_data = None
        self.y_data = None
        print("DummyDashboard cleaned up.")

    def apply_theme(self, is_dark: bool):
        """Handle internal theme changes for pyqtgraph."""
        bg_color = 'k' if is_dark else 'w'
        self.top_plot.setBackground(bg_color)
        self.bottom_plot.setBackground(bg_color)

if __name__ == "__main__":
    # --- Rapid Testing Block ---
    app = QApplication(sys.argv)
    
    # Create a generic host window
    window = QMainWindow()
    window.setWindowTitle("Spectra-Link | Modeling Plugin Test Stand")
    window.resize(1000, 600)
    
    dashboard = DummyDashboard()
    window.setCentralWidget(dashboard)
    
    # Generate fake experimental data (e.g., a noisy sine wave)
    x = np.linspace(400, 800, 500)
    noise = np.random.normal(0, 0.05, 500)
    y = np.sin(x / 50.0) + noise
    
    mock_metadata = {
        "core": {"technique": "Mock Spectroscopy"},
        "params": {"temperature": 300}
    }
    
    # Handshake call
    dashboard.set_active_data(x, y, mock_metadata)
    dashboard.apply_theme(is_dark=True) # Test dark mode
    
    window.show()
    sys.exit(app.exec())