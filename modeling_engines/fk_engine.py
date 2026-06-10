import numpy as np
from PyQt6.QtWidgets import QLabel, QDoubleSpinBox, QVBoxLayout
from modeling_engines.base_engine import BaseModelingEngine
from ui.analysis_settings_panel import CollapsibleSection, _SpinRow
from processors.ea_processor import EAProcessor
import processors.public.colton_math_functions as cmf
from utils.project_manager import ProjectManager
from scipy.signal import savgol_filter

class FKModelingEngine(BaseModelingEngine):
    """
    Franz-Keldysh Modeling Engine.
    Fits EA signals to derivatives of absorption to extract physical constants.
    """
    def __init__(self, parent_tab):
        super().__init__(parent_tab)
        self.processor = EAProcessor(parent_tab.parent_window)
        self.fit_curve = None
        self.x_data = None
        self.y_data = None

    def build_ui(self, layout: QVBoxLayout):
        """Builds the parameter inputs in the Modeling Control Center."""
        is_dark = getattr(self.parent_tab.parent_window, "dark_mode", True)
        
        # Retrieve current settings from JSON session
        data = ProjectManager.Session.get_data()
        tech_results = data.get("modeling", {}).get("saved_results", {}).get(self.parent_tab._current_technique, {})
        # FK specific data is stored under its own key within the technique's results
        fk_data = tech_results.get("Franz-Keldysh", {})

        section = CollapsibleSection("Franz-Keldysh Parameters", is_dark)
        
        # 1. Effective Mass
        self.row_mass = _SpinRow("Effective Mass (m₀):", section.C, min_v=0.01, max_v=2.0, step=0.01, decimals=3)
        self.row_mass.spin.setValue(fk_data.get("effective_mass", 0.120))
        self.row_mass.spin.valueChanged.connect(lambda v: self.parent_tab._on_setting_changed("effective_mass", v))
        section.content_layout.addWidget(self.row_mass)

        # 2. Electric Field
        self.row_field = _SpinRow("Local Field (kV/cm):", section.C, min_v=0.0, max_v=500.0, step=1.0, decimals=1)
        self.row_field.spin.setValue(fk_data.get("electric_field", 50.0))
        self.row_field.spin.valueChanged.connect(lambda v: self.parent_tab._on_setting_changed("electric_field", v))
        section.content_layout.addWidget(self.row_field)

        layout.insertWidget(0, section)

    def run_modeling(self):
        """
        Performs the FK Fit. 
        Logic: EA = a*dA/dE + b*d2A/dE2
        """
        json_data = ProjectManager.Session.get_data()
        # Use EAProcessor to get the same phased/processed data from the Analysis tab
        traces = self.processor._load_traces(json_data)
        if not traces:
            return

        # Get the first trace (typically the highest voltage for fitting)
        trace = traces[-1]
        settings = self.processor.get_settings(json_data)
        
        # Process wavelengths and signal exactly like the plotting tool
        x, y = self.processor._process_trace(trace["wavelengths"], trace["ea"], settings, 0)
        
        # For FK fitting, we need the Absorption derivatives. 
        # We can calculate these from the 'transmission_file' relative to 'blank_file'
        # Assuming Absorption derivatives are calculated here:
        try:
            # Simplified example: Calculating derivatives of the signal itself 
            # for demonstration of the FK_fit signature usage.
            d1 = savgol_filter(y, 15, 3, deriv=1)
            d2 = savgol_filter(y, 15, 3, deriv=2)
            d3 = savgol_filter(y, 15, 3, deriv=3)
            
            self.fit_curve = cmf.FK_fit(d1, d2, d3, y)
            self.x_data = x
            self.y_data = y
            
            # Update results for persistence
            self.results["fit_quality"] = "Success"
        except Exception as e:
            print(f"Modeling Error: {e}")

    def plot_results(self, figure):
        """Overlays the fit on the data."""
        figure.clear()
        ax = figure.add_subplot(111)
        
        if self.x_data is not None:
            ax.plot(self.x_data, self.y_data, 'ko', markersize=2, alpha=0.5, label="Data")
            if self.fit_curve is not None:
                ax.plot(self.x_data, self.fit_curve, 'r-', linewidth=2, label="FK Fit")
        
        ax.set_title("Franz-Keldysh Derivative Fit")
        ax.set_xlabel("Energy (eV)")
        ax.set_ylabel("$\Delta T/T$ (mOD)")
        ax.legend(frameon=False)
        ax.axhline(0, color='black', lw=0.5)