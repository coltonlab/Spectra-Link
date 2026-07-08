import os
import sys
import numpy as np
import pandas as pd
import re
import pyqtgraph as pg
from PyQt6.QtWidgets import QWidget, QHBoxLayout, QApplication, QMainWindow
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QColor

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

# Local Imports
try:
    from modeling_engines.base_modeling_dashboard import BaseModelingDashboard
except (ImportError, ModuleNotFoundError):
    from base_modeling_dashboard import BaseModelingDashboard

try:
    from processors.factory import get_processor
    from utils.app_logger import logger
except (ImportError, ModuleNotFoundError):
    from processors.factory import get_processor
    from utils.app_logger import logger

try:
    from modeling_engines.k_analysis.k_analysis_ui import build_k_analysis_ui
    from modeling_engines.k_analysis.k_analysis_analysis import fit_gaussian as gaussian_fit, perform_k_analysis as run_k_analysis
except (ImportError, ModuleNotFoundError):
    from k_analysis_ui import build_k_analysis_ui
    from k_analysis_analysis import fit_gaussian as gaussian_fit, perform_k_analysis as run_k_analysis

class KAnalysisDashboard(BaseModelingDashboard):
    """
    K-Analysis Dashboard for EA Voltage Series.
    Finds the power-law dependence (k) of the EA peak vs Electric Field.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        # Capture the window reference before we are reparented by a layout
        self.parent_window = getattr(parent, 'parent_window', None)

        self._is_dark = True
        self.x_data = None
        self.y_data = None
        self.metadata = {}
        self.traces = [] # Loaded from EAProcessor
        
        self.current_view = "spectrum" # or "k-plot"
        self.regions = [] # List of pg.LinearRegionItem
        self.k_results = [] # Stores results for each region
        
        # State for interactive region selection
        self._selection_mode_active = False
        self._first_click_x = None
        self._temp_region = None # Temporary region for visual feedback
        
        self.build_ui()

    def build_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)

        self.ui = build_k_analysis_ui(self)
        layout.addWidget(self.ui)

        self.plot = self.ui.plot
        self.results_log = self.ui.results_log
        self.btn_add_range = self.ui.btn_add_range
        self.btn_remove_range = self.ui.btn_remove_range
        self.range_list_widget = self.ui.range_list_widget
        self.btn_toggle_view = self.ui.btn_toggle_view
        self.chk_show_fits = self.ui.chk_show_fits

        self.btn_add_range.clicked.connect(self.add_new_range)
        self.btn_remove_range.clicked.connect(self.remove_selected_range)
        self.range_list_widget.currentRowChanged.connect(self.on_range_selected_from_list)
        self.btn_toggle_view.clicked.connect(self.toggle_view)
        self.chk_show_fits.stateChanged.connect(self.update_view)

    def set_active_data(self, x_data, y_data, metadata_dict):
        """Re-loads the whole series using the EAProcessor logic."""
        self._is_loading = True
        try:
            self.x_data = x_data
            self.metadata = metadata_dict
            
            # Clear existing regions and results when new data is loaded without saving empty
            self.clear_all_regions(save_to_session=False)
            self.k_results = []
            
            # Use the EAProcessor to load the full series correctly
            processor = get_processor("EA Voltage Series", self.parent_window)
            self.traces = processor._load_traces(metadata_dict)
            
            self.update_view()
            
            # Load saved ranges from metadata
            saved_ranges = self.metadata.get("analysis_settings", {}).get("k_analysis_ranges", [])
            for r in saved_ranges:
                if len(r) == 2:
                    self._create_and_add_region(r[0], r[1])
        finally:
            self._is_loading = False
            self._save_ranges_to_session()

    def update_view(self):
        if not self.traces: return
        
        # Clear previous curves/plots but keep the interactive LinearRegionItems
        for item in self.plot.getPlotItem().items[:]:
            if not isinstance(item, pg.LinearRegionItem):
                self.plot.removeItem(item)

        processor = get_processor(self.metadata.get("core", {}).get("technique"), self.parent_window)
        settings = self.metadata.get("analysis_settings", {})

        fg_color = '#ffffff' if getattr(self, '_is_dark', True) else '#333333'
        if self.current_view == "spectrum":
            self.plot.setTitle("EA Voltage Series Spectrum", color=fg_color)
            self.plot.setLabel('left', 'EA Signal', units='mOD', color=fg_color)
            self.plot.setLabel('bottom', 'Energy', units='eV', color=fg_color)
            self.plot.setLogMode(x=False, y=False)
            self.plot.showGrid(x=True, y=True)
            
            # Ensure regions are visible in spectrum view
            for region in self.regions:
                if region not in self.plot.getPlotItem().items:
                    self.plot.addItem(region)
                region.show()
            if self._temp_region:
                if self._temp_region not in self.plot.getPlotItem().items:
                    self.plot.addItem(self._temp_region)
                self._temp_region.show()
            self._connect_plot_mouse_events(True)

            # Plot all traces in the series
            for i, raw_trace in enumerate(self.traces):
                x, y = processor._process_trace(raw_trace['wavelengths'], raw_trace['ea'], settings, i)
                color = pg.intColor(i, len(self.traces))
                self.plot.plot(x, y, pen=pg.mkPen(color, width=2), name=raw_trace['label'])
                
                # Plot Gaussian fits if toggled on
                if self.chk_show_fits.isChecked():
                    for region in self.regions:
                        min_x, max_x = region.getRegion()
                        mask = (x >= min_x) & (x <= max_x)
                        if np.sum(mask) >= 4:
                            x_slice = x[mask]
                            y_slice = y[mask]
                            popt = self.fit_gaussian(x_slice, y_slice)
                            if popt is not None:
                                x_smooth = np.linspace(min_x, max_x, 100)
                                A, x0, sigma, C = popt
                                y_fit = A * np.exp(-((x_smooth - x0) ** 2) / (2 * sigma ** 2)) + C
                                fit_pen = pg.mkPen(color, width=2, style=Qt.PenStyle.DashLine)
                                self.plot.plot(x_smooth, y_fit, pen=fit_pen)
        else:
            self.plot.setTitle("Peak Amplitude vs Voltage (Log-Log)", color=fg_color)
            self.plot.setLabel('left', 'Peak Amplitude (mOD)', color=fg_color)
            self.plot.setLabel('bottom', 'Voltage (V)', color=fg_color)
            self.plot.setLogMode(x=True, y=True)
            self.plot.showGrid(x=True, y=True)
            
            # Hide regions in log-log plot view
            for region in self.regions:
                region.hide()
            if self._temp_region:
                self._temp_region.hide()
            self._connect_plot_mouse_events(False)
            self.perform_k_analysis()

    def toggle_view(self):
        if self.current_view == "spectrum":
            self.current_view = "k-plot"
            self.btn_toggle_view.setText("📈 Switch to Spectrum")
        else:
            self.current_view = "spectrum"
            self.btn_toggle_view.setText("📊 Switch to Log-Log Plot")
        self.update_view()

    def add_new_range(self):
        if self._selection_mode_active:
            self._cancel_selection_mode()
            return

        if self.current_view != "spectrum":
            self.toggle_view()

        self._selection_mode_active = True
        self._first_click_x = None
        self.results_log.setText("Click on the plot to define the center of your peak range.")
        self._set_ui_selection_mode(True)
        self._connect_plot_mouse_events(True)

    def _connect_plot_mouse_events(self, connect: bool):
        scene = self.plot.scene()
        if connect:
            try: scene.sigMouseClicked.disconnect(self._handle_plot_click)
            except TypeError: pass
            try: scene.sigMouseMoved.disconnect(self._handle_plot_mouse_move)
            except TypeError: pass
            scene.sigMouseClicked.connect(self._handle_plot_click)
            scene.sigMouseMoved.connect(self._handle_plot_mouse_move)
        else:
            try: scene.sigMouseClicked.disconnect(self._handle_plot_click)
            except TypeError: pass
            try: scene.sigMouseMoved.disconnect(self._handle_plot_mouse_move)
            except TypeError: pass

    def _set_region_pen(self, region, pen):
        if hasattr(region, 'lines'):
            for line in region.lines:
                line.setPen(pen)

    def _save_ranges_to_session(self):
        if getattr(self, '_is_loading', False):
            return
        if not self.metadata:
            return
        
        # Ensure analysis_settings exists in metadata
        if "analysis_settings" not in self.metadata:
            self.metadata["analysis_settings"] = {}
            
        ranges_list = []
        for region in self.regions:
            r_min, r_max = region.getRegion()
            ranges_list.append([float(r_min), float(r_max)])
            
        self.metadata["analysis_settings"]["k_analysis_ranges"] = ranges_list
        
        try:
            from utils.project_manager import Session
            Session.save()
        except Exception as e:
            logger.error(f"KAnalysisDashboard: Failed to save session: {e}")

    def fit_gaussian(self, x_slice, y_slice):
        return gaussian_fit(x_slice, y_slice)

    def _handle_plot_click(self, event):
        if not self._selection_mode_active or event.button() != Qt.MouseButton.LeftButton:
            return

        pos = event.scenePos()
        x_coord = self.plot.plotItem.vb.mapSceneToView(pos).x()

        if self._first_click_x is None:
            self._first_click_x = x_coord
            self.results_log.setText("Click again to define the width of your peak range.")
            
            # Calculate a sensible default width based on the current x_data range
            if self.x_data is not None and len(self.x_data) > 1:
                x_range = self.x_data.max() - self.x_data.min()
                default_width = x_range * 0.05 # 5% of the total x-range
            else:
                default_width = 0.1 # Fallback if no x_data or single point

            # Create temp region centered at click
            # Set movable=False so that the second click is not intercepted by the temporary region
            self._temp_region = pg.LinearRegionItem(values=(x_coord - default_width/2, x_coord + default_width/2), movable=False)
            self._temp_region.setZValue(100)
            self._temp_region.setBrush(pg.mkBrush(QColor(255, 255, 0, 50)))
            self._set_region_pen(self._temp_region, pg.mkPen(QColor(255, 255, 0, 200), width=1))
            self.plot.addItem(self._temp_region)
        else:
            # Second click: finalize the width
            center_x = self._first_click_x
            width = abs(x_coord - center_x) * 2
            
            # Ensure a minimum width to avoid zero-width regions
            min_allowed_width = (self.x_data.max() - self.x_data.min()) * 0.005 if self.x_data is not None and len(self.x_data) > 1 else 0.01
            if width < min_allowed_width:
                width = min_allowed_width
            x_start, x_end = center_x - width / 2, center_x + width / 2
            
            if self._temp_region:
                self.plot.removeItem(self._temp_region)
                self._temp_region = None

            self._create_and_add_region(x_start, x_end)
            self._cancel_selection_mode()

    def _handle_plot_mouse_move(self, pos):
        if self._selection_mode_active and self._first_click_x is not None and self._temp_region:
            view_pos = self.plot.plotItem.vb.mapSceneToView(pos)
            if view_pos is None: return
            
            current_x = view_pos.x()
            center_x = self._first_click_x
            
            # Ensure a minimum width
            min_allowed_width = (self.x_data.max() - self.x_data.min()) * 0.005 if self.x_data is not None and len(self.x_data) > 1 else 0.01
            
            width = abs(current_x - center_x) * 2
            if width < min_allowed_width:
                width = min_allowed_width

            self._temp_region.setRegion((center_x - width/2, center_x + width/2))

    def _finalize_temp_region(self):
        if self._temp_region and self._selection_mode_active and self._first_click_x is not None:
            x_start, x_end = self._temp_region.getRegion()
            self.plot.removeItem(self._temp_region)
            self._temp_region = None
            self._create_and_add_region(x_start, x_end)
            self._cancel_selection_mode()

    def _create_and_add_region(self, x_start, x_end):
        new_region = pg.LinearRegionItem(values=(x_start, x_end))
        new_region.setZValue(10)
        
        color_idx = len(self.regions) % 10
        region_color = pg.intColor(color_idx, 10)
        new_region.setBrush(pg.mkBrush(QColor(0, 0, 0, 0)))
        new_region.setHoverBrush(pg.mkBrush(QColor(0, 0, 255, 30)))
        self._set_region_pen(new_region, pg.mkPen(region_color, width=4))

        self.plot.addItem(new_region)
        self.regions.append(new_region)
        
        new_region.sigRegionChangeFinished.connect(self.perform_k_analysis)
        new_region.sigRegionChanged.connect(self._update_region_label)
        
        self.perform_k_analysis()
        self.range_list_widget.setCurrentRow(len(self.regions) - 1)
        self.btn_remove_range.setEnabled(True)

    def _cancel_selection_mode(self):
        self._selection_mode_active = False
        self._first_click_x = None
        if self._temp_region:
            self.plot.removeItem(self._temp_region)
            self._temp_region = None
        self.results_log.clear()
        self._set_ui_selection_mode(False)
        self._connect_plot_mouse_events(False)

    def _set_ui_selection_mode(self, active: bool):
        self.btn_add_range.setEnabled(not active)
        self.btn_remove_range.setEnabled(not active and bool(self.regions))
        self.btn_toggle_view.setEnabled(not active)
        self.range_list_widget.setEnabled(not active)
        self.chk_show_fits.setEnabled(not active)
        if active:
            self.plot.setCursor(Qt.CursorShape.CrossCursor)
        else:
            self.plot.unsetCursor()

    def remove_selected_range(self):
        current_row = self.range_list_widget.currentRow()
        if current_row >= 0 and current_row < len(self.regions):
            region_to_remove = self.regions.pop(current_row)
            self.plot.removeItem(region_to_remove)
            self.range_list_widget.takeItem(current_row)
            self.perform_k_analysis() # Re-run analysis for remaining regions
            if not self.regions:
                self.btn_remove_range.setEnabled(False)

    def clear_all_regions(self, save_to_session=True):
        for region in self.regions:
            self.plot.removeItem(region)
        self.regions.clear()
        self.range_list_widget.clear()
        self.btn_remove_range.setEnabled(False)
        self.k_results.clear()
        self.results_log.clear()
        if save_to_session:
            self._save_ranges_to_session()

    def _update_region_label(self, region_item):
        # Find the index of the region that changed
        try:
            idx = self.regions.index(region_item)
            min_x, max_x = region_item.getRegion()
            item = self.range_list_widget.item(idx)
            if item:
                # Use timer to avoid recursion during dragging
                QTimer.singleShot(0, lambda: item.setText(f"Range {idx+1}: {min_x:.2f} - {max_x:.2f} eV"))
        except ValueError:
            pass # Region might have been removed

    def on_range_selected_from_list(self, row):
        # Highlight the selected region on the plot
        for i, region in enumerate(self.regions):
            if i == row:
                region.setZValue(11) # Bring to front
                self._set_region_pen(region, pg.mkPen('y', width=5)) # Highlight
            else:
                region.setZValue(10)
                color_idx = i % 10
                region_color = pg.intColor(color_idx, 10)
                self._set_region_pen(region, pg.mkPen(region_color, width=4))
        self.btn_remove_range.setEnabled(row >= 0)

    def perform_k_analysis(self, region_item=None):
        return run_k_analysis(
            self.traces,
            self.metadata,
            self.parent_window,
            self.regions,
            self.range_list_widget,
            self.results_log,
            self.current_view,
            self.plot,
            self.update_view,
            self._save_ranges_to_session,
            self.k_results,
            self.chk_show_fits,
            fit_gaussian_fn=self.fit_gaussian,
        )

    def shutdown(self):
        self.clear_all_regions(save_to_session=False)
        logger.info("KAnalysisDashboard shutting down.")

    def apply_theme(self, is_dark: bool):
        self._is_dark = is_dark
        bg = 'k' if is_dark else 'w'
        fg = 'w' if is_dark else '#333333'
        self.plot.setBackground(bg)
        
        axis_pen = pg.mkPen(fg)
        self.plot.getAxis('bottom').setPen(axis_pen)
        self.plot.getAxis('bottom').setTextPen(axis_pen)
        self.plot.getAxis('left').setPen(axis_pen)
        self.plot.getAxis('left').setTextPen(axis_pen)

        # Update region colors if they exist
        for i, region in enumerate(self.regions):
            color_idx = i % 10
            region_color = pg.intColor(color_idx, 10)
            region.setBrush(pg.mkBrush(QColor(0, 0, 0, 0)))
            region.setHoverBrush(pg.mkBrush(QColor(0, 0, 255, 30)))
            self._set_region_pen(region, pg.mkPen(region_color, width=4))
        self.update_view()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    win = QMainWindow()
    win.resize(1000, 600)
    dash = KAnalysisDashboard()
    win.setCentralWidget(dash)
    
    # 1. Load your actual data file
    # Only add a filepath if you are running k_analysis_dashboard.py and not running main.py
    # This is for already compiled EA data into a single file. If all files are separate, use main.py and load each file individually.
    filepath = "Data/AFRL Compiled EA Data/(R)-((3-I)MBA)_2 PbI_4 EA_series_data_295K.csv"
    df = pd.read_csv(filepath)
    
    # 2. Extract X data (Energy) and base Y data (Absorption)
    x = df["Energy (eV)"].values
    absorption = df["Absorption (OD)"].values
    
    # 3. Dynamically parse the EA voltage columns
    real_traces = []
    for col in df.columns:
        if col.startswith("EA"):
            # Use regex to extract the numeric value (e.g., 20 from "EA 20 kV/cm (mOD)")
            match = re.search(r"(\d+)", col)
            voltage_value = float(match.group(1)) if match else 0.0
            
            # Create the clean label (e.g., "20 kV/cm")
            label = col.replace("EA ", "").replace(" (mOD)", "")
            
            real_traces.append({
                "wavelengths": x,
                "ea": df[col].values,
                "label": label,
                "value": voltage_value
            })
            
    # 4. Feed your real data into the dashboard
    dash.traces = real_traces 
    dash.metadata = {"core": {"technique": "EA Voltage Series"}, "analysis_settings": {}}
    dash.x_data = x             # Energy axis
    dash.y_data = absorption    # Absorption background/baseline
    
    dash.update_view()
    
    win.show()
    sys.exit(app.exec())