import os
import sys
import re

import pandas as pd

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

try:
    from modeling_engines.base_modeling_dashboard import BaseModelingDashboard
except (ImportError, ModuleNotFoundError):
    from base_modeling_dashboard import BaseModelingDashboard

try:
    from modeling_engines.k_analysis.k_analysis_controller import KAnalysisAppController
except (ImportError, ModuleNotFoundError):
    from k_analysis_controller import KAnalysisAppController


class KAnalysisDashboard(BaseModelingDashboard):
    """
    K-Analysis Dashboard for EA Voltage Series.
    Finds the power-law dependence (k) of the EA peak vs Electric Field.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent_window = getattr(parent, 'parent_window', None)

        self._is_dark = True
        self.x_data = None
        self.y_data = None
        self.metadata = {}
        self.traces = []

        self.current_view = "spectrum"
        self.regions = []
        self.k_results = []

        self._selection_mode_active = False
        self._first_click_x = None
        self._temp_region = None

        self.controller = KAnalysisAppController(self)
        self.build_ui()

    def build_ui(self):
        self.controller.initialize()

    def set_active_data(self, x_data, y_data, metadata_dict):
        self.controller.set_active_data(x_data, y_data, metadata_dict)

    def update_view(self):
        self.controller.update_view()

    def toggle_view(self):
        self.controller.toggle_view()

    def add_new_range(self):
        self.controller.add_new_range()

    def _connect_plot_mouse_events(self, connect: bool):
        self.controller._connect_plot_mouse_events(connect)

    def _set_region_pen(self, region, pen):
        self.controller._set_region_pen(region, pen)

    def _save_ranges_to_session(self):
        self.controller._save_ranges_to_session()

    def fit_gaussian(self, x_slice, y_slice):
        return self.controller.fit_gaussian(x_slice, y_slice)

    def _handle_plot_click(self, event):
        self.controller._handle_plot_click(event)

    def _handle_plot_mouse_move(self, pos):
        self.controller._handle_plot_mouse_move(pos)

    def _finalize_temp_region(self):
        self.controller._finalize_temp_region()

    def _create_and_add_region(self, x_start, x_end):
        self.controller._create_and_add_region(x_start, x_end)

    def _cancel_selection_mode(self):
        self.controller._cancel_selection_mode()

    def _set_ui_selection_mode(self, active: bool):
        self.controller._set_ui_selection_mode(active)

    def remove_selected_range(self):
        self.controller.remove_selected_range()

    def clear_all_regions(self, save_to_session=True):
        self.controller.clear_all_regions(save_to_session=save_to_session)

    def _update_region_label(self, region_item):
        self.controller._update_region_label(region_item)

    def on_range_selected_from_list(self, row):
        self.controller.on_range_selected_from_list(row)

    def perform_k_analysis(self, region_item=None):
        return self.controller.perform_k_analysis(region_item)

    def shutdown(self):
        self.controller.shutdown()

    def apply_theme(self, is_dark: bool):
        self.controller.apply_theme(is_dark)


if __name__ == "__main__":
    from PyQt6.QtWidgets import QApplication, QMainWindow

    app = QApplication(sys.argv)
    win = QMainWindow()
    win.resize(1000, 600)
    dash = KAnalysisDashboard()
    win.setCentralWidget(dash)

    # filepath = "Data/AFRL Compiled EA Data/(R)-((3-Br)MBA)_2 PbI_4 EA_series_data_16K.csv"
    filepath = "Data/AFRL Compiled EA Data/(R)-((3-Cl)MBA)_2 PbI_4 EA_series_data_16K.csv"
    # filepath = "Data/AFRL Compiled EA Data/(R)-((3-I)MBA)_2 PbI_4 EA_series_data_16K.csv"
    # filepath = "Data/AFRL Compiled EA Data/(R)-((3-CF_3)MBA)_2 PbI_4 EA_series_data_16K.csv"
    df = pd.read_csv(filepath)

    x = df["Energy (eV)"].values
    absorption = df["Absorption (OD)"].values

    real_traces = []
    for col in df.columns:
        if col.startswith("EA"):
            match = re.search(r"(\d+)", col)
            voltage_value = float(match.group(1)) if match else 0.0
            label = col.replace("EA ", "").replace(" (mOD)", "")

            real_traces.append({
                "wavelengths": x,
                "ea": df[col].values,
                "label": label,
                "value": voltage_value
            })

    dash.traces = real_traces
    dash.metadata = {"core": {"technique": "EA Voltage Series"}, "analysis_settings": {}}
    dash.x_data = x
    dash.y_data = absorption

    dash.update_view()

    win.show()
    sys.exit(app.exec())