import sys
import numpy as np
import pyqtgraph as pg
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
    QApplication, QMainWindow, QPushButton, QTextEdit, QFrame, QListWidget, QListWidgetItem, QGraphicsView,
    QCheckBox
)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QColor

# Local Imports
try:
    from modeling_engines.base_modeling_dashboard import BaseModelingDashboard
except (ImportError, ModuleNotFoundError):
    from base_modeling_dashboard import BaseModelingDashboard

try:
    from processors.factory import get_processor
    from utils.app_logger import logger
except (ImportError, ModuleNotFoundError):
    import os
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
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
        
        # --- Left Side: Plotting Area ---
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        
        self.plot = pg.PlotWidget(title="EA Voltage Series")
        self.plot.showGrid(x=True, y=True)
        self.plot.setMouseTracking(True) # Enable mouse tracking for dynamic resizing
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
        
        self.btn_add_range = QPushButton("➕ Add Peak Range")
        self.btn_add_range.clicked.connect(self.add_new_range)
        controls.addWidget(self.btn_add_range)
        
        self.btn_remove_range = QPushButton("➖ Remove Selected Range")
        self.btn_remove_range.clicked.connect(self.remove_selected_range)
        self.btn_remove_range.setEnabled(False) # Initially disabled
        controls.addWidget(self.btn_remove_range)
        
        controls.addWidget(QLabel("<b>Active Ranges:</b>"))
        self.range_list_widget = QListWidget()
        self.range_list_widget.currentRowChanged.connect(self.on_range_selected_from_list)
        controls.addWidget(self.range_list_widget)
        
        self.btn_toggle_view = QPushButton("📊 Switch to Log-Log Plot")
        self.btn_toggle_view.clicked.connect(self.toggle_view)
        controls.addWidget(self.btn_toggle_view)
        
        self.chk_show_fits = QCheckBox("Show Gaussian Fits")
        self.chk_show_fits.setChecked(True)
        self.chk_show_fits.stateChanged.connect(self.update_view)
        controls.addWidget(self.chk_show_fits)
        
        controls.addStretch()
        
        layout.addWidget(left_panel, stretch=4)
        layout.addWidget(right_panel, stretch=1)

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

        if self.current_view == "spectrum":
            self.plot.setTitle("EA Voltage Series Spectrum")
            self.plot.setLabel('left', 'EA Signal', units='mOD')
            self.plot.setLabel('bottom', 'Energy', units='eV')
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
                self.plot.plot(x, y, pen=color, name=raw_trace['label'])
                
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
            self.plot.setTitle("Peak Amplitude vs Voltage (Log-Log)")
            self.plot.setLabel('left', 'Peak Amplitude (mOD)')
            self.plot.setLabel('bottom', 'Voltage (V)')
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
        if len(x_slice) < 4:
            return None
        
        # Initial guesses
        idx_max = np.argmax(np.abs(y_slice))
        x0_guess = x_slice[idx_max]
        A_guess = y_slice[idx_max]
        sigma_guess = (x_slice.max() - x_slice.min()) / 4.0
        if sigma_guess <= 0:
            sigma_guess = 0.01
        C_guess = np.mean(y_slice)
        
        p0 = [A_guess, x0_guess, sigma_guess, C_guess]
        
        def gauss(x, A, x0, sigma, C):
            return A * np.exp(-((x - x0) ** 2) / (2 * sigma ** 2)) + C
            
        try:
            from scipy.optimize import curve_fit
            popt, _ = curve_fit(gauss, x_slice, y_slice, p0=p0, maxfev=2000)
            popt[2] = abs(popt[2])
            return popt  # [A, x0, sigma, C]
        except Exception:
            return None

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
        new_region.setBrush(pg.mkBrush(region_color.lighter(150)))
        self._set_region_pen(new_region, pg.mkPen(region_color, width=2))

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
                self._set_region_pen(region, pg.mkPen('y', width=3)) # Highlight
            else:
                region.setZValue(10)
                color_idx = i % 10
                region_color = pg.intColor(color_idx, 10)
                self._set_region_pen(region, pg.mkPen(region_color, width=2))
        self.btn_remove_range.setEnabled(row >= 0)

    def perform_k_analysis(self, region_item=None):
        # Re-evaluate all regions and update k_results
        self.k_results.clear()
        self.results_log.clear()
        
        if not self.traces: return

        processor = get_processor(self.metadata.get("core", {}).get("technique"), self.parent_window)
        settings = self.metadata.get("analysis_settings", {})
        
        for idx, region in enumerate(self.regions):
            min_x, max_x = region.getRegion()
            voltages = []
            peaks = []
            
            for i, raw_trace in enumerate(self.traces):
                x, y = processor._process_trace(raw_trace['wavelengths'], raw_trace['ea'], settings, i)
                
                mask = (x >= min_x) & (x <= max_x)
                if np.any(mask):
                    voltages.append(raw_trace.get('value', 0))
                    x_slice = x[mask]
                    y_slice = y[mask]
                    popt = self.fit_gaussian(x_slice, y_slice)
                    if popt is not None:
                        A, x0, sigma, C = popt
                        fit_y = A * np.exp(-((x_slice - x0) ** 2) / (2 * sigma ** 2)) + C
                        peaks.append(np.max(np.abs(fit_y)))
                    else:
                        peaks.append(np.max(np.abs(y_slice)))
            
            v_arr = np.array(voltages)
            p_arr = np.array(peaks)
            
            # Filter out zeros for log-log fit
            mask = (v_arr > 0) & (p_arr > 0)
            if np.sum(mask) >= 2:
                log_v = np.log10(v_arr[mask])
                log_p = np.log10(p_arr[mask])
                
                # Linear Fit: log(P) = k * log(V) + C
                k, intercept = np.polyfit(log_v, log_p, 1)
                self.k_results.append({'id': idx, 'min_x': min_x, 'max_x': max_x, 'k': k, 'intercept': intercept, 'voltages': v_arr[mask], 'peaks': p_arr[mask]})
                
                # Update list widget item
                item = self.range_list_widget.item(idx)
                if item:
                    item.setText(f"Range {idx+1}: {min_x:.2f}-{max_x:.2f} eV (k={k:.3f})")
                else:
                    self.range_list_widget.addItem(f"Range {idx+1}: {min_x:.2f}-{max_x:.2f} eV (k={k:.3f})")
                self.results_log.append(f"Range {idx+1} ({min_x:.2f}-{max_x:.2f} eV): <b>k = {k:.3f}</b>")
            else:
                self.results_log.append(f"Range {idx+1} ({min_x:.2f}-{max_x:.2f} eV): Not enough data points for fit.")
            self.results_log.append("-" * 20)

        # Now plot all results if in k-plot view
        if self.current_view == "k-plot" and self.k_results:
            self.plot.clear()
            for result in self.k_results:
                color_idx = result['id'] % 10
                plot_color = pg.intColor(color_idx, 10)
                
                self.plot.plot(result['voltages'], result['peaks'], pen=None, symbol='o', symbolBrush=plot_color, name=f"Data R{result['id']+1}")
                # Plot Fit Line
                fit_v = np.linspace(min(result['voltages']), max(result['voltages']), 100)
                fit_p = 10**(result['k'] * np.log10(fit_v) + result['intercept'])
                self.plot.plot(fit_v, fit_p, pen=pg.mkPen(plot_color, width=2), name=f"Fit R{result['id']+1} (k={result['k']:.2f})")
        elif self.current_view == "spectrum":
            self.update_view()
        
        self._save_ranges_to_session()

    def shutdown(self):
        self.clear_all_regions(save_to_session=False)
        logger.info("KAnalysisDashboard shutting down.")

    def apply_theme(self, is_dark: bool):
        bg = 'k' if is_dark else 'w'
        self.plot.setBackground(bg)
        # Update region colors if they exist
        for i, region in enumerate(self.regions):
            color_idx = i % 10
            region_color = pg.intColor(color_idx, 10)
            region.setBrush(pg.mkBrush(region_color.lighter(150)))
            self._set_region_pen(region, pg.mkPen(region_color, width=2))

if __name__ == "__main__":
    app = QApplication(sys.argv)
    win = QMainWindow()
    win.resize(1000, 600)
    dash = KAnalysisDashboard()
    win.setCentralWidget(dash)
    
    # Mock EA data for standalone testing (similar to EAProcessor output)
    x = np.linspace(1.5, 2.5, 500)
    mock_traces = []
    for v in np.linspace(0.5, 5.0, 5): # Simulate 5 voltage traces
        y_base = np.sin((x-1.8)*20) * np.exp(-(x-2)**2 / 0.05) * (v**2) * 0.1
        noise = np.random.normal(0, 0.005, 500)
        mock_traces.append({
            "wavelengths": x,
            "ea": y_base + noise,
            "label": f"{v:.1f} V",
            "value": v
        })
    dash.traces = mock_traces # Directly set traces for standalone test
    dash.metadata = {"core": {"technique": "EA Voltage Series"}, "analysis_settings": {}}
    dash.x_data = x # Set x_data for range calculation
    dash.y_data = y_base # Set y_data for range calculation
    dash.update_view()
    
    win.show()
    sys.exit(app.exec())