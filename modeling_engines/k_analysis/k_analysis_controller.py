from __future__ import annotations

import os
import sys

import numpy as np
import pyqtgraph as pg
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor
from PyQt6.QtWidgets import QHBoxLayout, QMenu, QListWidgetItem

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

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
    from modeling_engines.k_analysis.k_analysis_interactions import KAnalysisInteractionController
except (ImportError, ModuleNotFoundError):
    from k_analysis_ui import build_k_analysis_ui
    from k_analysis_analysis import fit_gaussian as gaussian_fit, perform_k_analysis as run_k_analysis
    from k_analysis_interactions import KAnalysisInteractionController


class KAnalysisAppController:
    """Application-level controller for the k-analysis dashboard workflow."""

    def __init__(self, dashboard):
        self.dashboard = dashboard

    def initialize(self) -> None:
        layout = QHBoxLayout(self.dashboard)
        layout.setContentsMargins(10, 10, 10, 10)

        self.dashboard.ui = build_k_analysis_ui(self.dashboard)
        layout.addWidget(self.dashboard.ui)

        self.dashboard.plot = self.dashboard.ui.plot
        self.dashboard.results_log = self.dashboard.ui.results_log
        self.dashboard.btn_add_range = self.dashboard.ui.btn_add_range
        self.dashboard.btn_remove_range = self.dashboard.ui.btn_remove_range
        self.dashboard.range_list_widget = self.dashboard.ui.range_list_widget
        self.dashboard.btn_toggle_view = self.dashboard.ui.btn_toggle_view
        self.dashboard.chk_show_fits = self.dashboard.ui.chk_show_fits
        self.dashboard.chk_show_cooks = self.dashboard.ui.chk_show_cooks
        self.dashboard.curve_list_widget = self.dashboard.ui.curve_list_widget

        self.dashboard.region_curve_filters = []

        self.dashboard.interactions = KAnalysisInteractionController(self.dashboard)
        self._connect_signals()

    def _connect_signals(self) -> None:
        self.dashboard.btn_add_range.clicked.connect(self.add_new_range)
        self.dashboard.btn_remove_range.clicked.connect(self.remove_selected_range)
        self.dashboard.range_list_widget.currentRowChanged.connect(self.on_range_selected_from_list)
        self.dashboard.range_list_widget.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.dashboard.range_list_widget.customContextMenuRequested.connect(self._show_range_context_menu)
        self.dashboard.btn_toggle_view.clicked.connect(self.toggle_view)
        self.dashboard.chk_show_fits.stateChanged.connect(self.update_view)
        self.dashboard.chk_show_cooks.stateChanged.connect(self.update_view)
        self.dashboard.curve_list_widget.itemChanged.connect(self.on_curve_item_changed)

    def set_active_data(self, x_data, y_data, metadata_dict) -> None:
        """Re-loads the whole series using the EAProcessor logic."""
        self.dashboard._is_loading = True
        try:
            self.dashboard.x_data = x_data
            self.dashboard.y_data = y_data
            self.dashboard.metadata = metadata_dict

            self.dashboard.clear_all_regions(save_to_session=False)
            self.dashboard.k_results = []

            processor = get_processor("EA Voltage Series", self.dashboard.parent_window)
            self.dashboard.traces = processor._load_traces(metadata_dict)

            self.update_view()

            saved_ranges = self.dashboard.metadata.get("analysis_settings", {}).get("k_analysis_ranges", [])
            for saved_range in saved_ranges:
                if len(saved_range) == 2:
                    self._create_and_add_region(saved_range[0], saved_range[1])
        finally:
            self.dashboard._is_loading = False
            self._save_ranges_to_session()

    def update_view(self) -> None:
        if not self.dashboard.traces:
            return

        for item in self.dashboard.plot.getPlotItem().items[:]:
            if not isinstance(item, pg.LinearRegionItem):
                self.dashboard.plot.removeItem(item)

        processor = get_processor(self.dashboard.metadata.get("core", {}).get("technique"), self.dashboard.parent_window)
        settings = self.dashboard.metadata.get("analysis_settings", {})

        fg_color = '#ffffff' if getattr(self.dashboard, '_is_dark', True) else '#333333'
        if self.dashboard.current_view == "spectrum":
            self.dashboard.plot.setTitle("EA Voltage Series Spectrum", color=fg_color)
            self.dashboard.plot.setLabel('left', 'EA Signal', units='mOD', color=fg_color)
            self.dashboard.plot.setLabel('bottom', 'Energy', units='eV', color=fg_color)
            self.dashboard.plot.setLogMode(x=False, y=False)
            self.dashboard.plot.showGrid(x=True, y=True)

            for region in self.dashboard.regions:
                if region not in self.dashboard.plot.getPlotItem().items:
                    self.dashboard.plot.addItem(region)
                region.show()
            if self.dashboard._temp_region:
                if self.dashboard._temp_region not in self.dashboard.plot.getPlotItem().items:
                    self.dashboard.plot.addItem(self.dashboard._temp_region)
                self.dashboard._temp_region.show()
            self._connect_plot_mouse_events(True)

            for i, raw_trace in enumerate(self.dashboard.traces):
                x, y = processor._process_trace(raw_trace['wavelengths'], raw_trace['ea'], settings, i)
                color = pg.intColor(i, len(self.dashboard.traces))
                self.dashboard.plot.plot(x, y, pen=pg.mkPen(color, width=2), name=raw_trace['label'])

                if self.dashboard.chk_show_fits.isChecked():
                    for region_index, region in enumerate(self.dashboard.regions):
                        if region_index < len(self.dashboard.region_curve_filters):
                            enabled_indices = set(self.dashboard.region_curve_filters[region_index])
                        else:
                            enabled_indices = None

                        if enabled_indices is not None and i not in enabled_indices:
                            continue

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
                                self.dashboard.plot.plot(x_smooth, y_fit, pen=fit_pen)
        else:
            self.dashboard.plot.setTitle("Peak Amplitude vs Voltage (Log-Log)", color=fg_color)
            self.dashboard.plot.setLabel('left', 'Peak Amplitude (mOD)', color=fg_color)
            self.dashboard.plot.setLabel('bottom', 'Voltage (V)', color=fg_color)
            self.dashboard.plot.setLogMode(x=True, y=True)
            self.dashboard.plot.showGrid(x=True, y=True)

            for region in self.dashboard.regions:
                region.hide()
            if self.dashboard._temp_region:
                self.dashboard._temp_region.hide()
            self._connect_plot_mouse_events(False)
            self.perform_k_analysis()

    def toggle_view(self) -> None:
        if self.dashboard.current_view == "spectrum":
            self.dashboard.current_view = "k-plot"
            self.dashboard.btn_toggle_view.setText("📈 Switch to Spectrum")
        else:
            self.dashboard.current_view = "spectrum"
            self.dashboard.btn_toggle_view.setText("📊 Switch to Log-Log Plot")
        self.update_view()

    def add_new_range(self) -> None:
        if self.dashboard._selection_mode_active:
            self._cancel_selection_mode()
            return

        if self.dashboard.current_view != "spectrum":
            self.toggle_view()

        self.dashboard._selection_mode_active = True
        self.dashboard._first_click_x = None
        self.dashboard.results_log.setText("Click on the plot to define the center of your peak range.")
        self._set_ui_selection_mode(True)
        self._connect_plot_mouse_events(True)

    def _connect_plot_mouse_events(self, connect: bool) -> None:
        self.dashboard.interactions.connect_plot_mouse_events(connect)

    def _set_region_pen(self, region, pen) -> None:
        self.dashboard.interactions.set_region_pen(region, pen)

    def _save_ranges_to_session(self) -> None:
        if getattr(self.dashboard, '_is_loading', False):
            return
        if not self.dashboard.metadata:
            return

        if "analysis_settings" not in self.dashboard.metadata:
            self.dashboard.metadata["analysis_settings"] = {}

        ranges_list = []
        for region in self.dashboard.regions:
            r_min, r_max = region.getRegion()
            ranges_list.append([float(r_min), float(r_max)])

        self.dashboard.metadata["analysis_settings"]["k_analysis_ranges"] = ranges_list

        try:
            from utils.project_manager import Session
            Session.save()
        except Exception as exc:
            logger.error(f"KAnalysisDashboard: Failed to save session: {exc}")

    def fit_gaussian(self, x_slice, y_slice):
        return gaussian_fit(x_slice, y_slice)

    def _handle_plot_click(self, event) -> None:
        self.dashboard.interactions.handle_plot_click(event)

    def _handle_plot_mouse_move(self, pos) -> None:
        self.dashboard.interactions.handle_plot_mouse_move(pos)

    def _finalize_temp_region(self) -> None:
        self.dashboard.interactions.finalize_temp_region()

    def _create_and_add_region(self, x_start, x_end) -> None:
        self.dashboard.interactions.create_and_add_region(x_start, x_end)
        new_region = self.dashboard.regions[-1]
        self.dashboard.region_curve_filters.append(self._default_curve_indices_for_region(new_region))
        self.perform_k_analysis()
        self.dashboard.range_list_widget.setCurrentRow(len(self.dashboard.regions) - 1)
        self.dashboard.btn_remove_range.setEnabled(True)
        self._populate_curve_list_for_region(len(self.dashboard.regions) - 1)

    def _cancel_selection_mode(self) -> None:
        self.dashboard.interactions.cancel_selection_mode()

    def _set_ui_selection_mode(self, active: bool) -> None:
        self.dashboard.interactions.set_ui_selection_mode(active)

    def remove_selected_range(self) -> None:
        current_row = self.dashboard.range_list_widget.currentRow()
        if current_row >= 0 and current_row < len(self.dashboard.regions):
            region_to_remove = self.dashboard.regions.pop(current_row)
            self.dashboard.plot.removeItem(region_to_remove)
            self.dashboard.range_list_widget.takeItem(current_row)
            if current_row < len(self.dashboard.region_curve_filters):
                self.dashboard.region_curve_filters.pop(current_row)
            self.perform_k_analysis()
            if not self.dashboard.regions:
                self.dashboard.btn_remove_range.setEnabled(False)
                self._clear_curve_list()

    def clear_all_regions(self, save_to_session=True) -> None:
        for region in self.dashboard.regions:
            self.dashboard.plot.removeItem(region)
        self.dashboard.regions.clear()
        self.dashboard.range_list_widget.clear()
        self.dashboard.region_curve_filters.clear()
        self.dashboard.btn_remove_range.setEnabled(False)
        self.dashboard.k_results.clear()
        self.dashboard.results_log.clear()
        self._clear_curve_list()
        if save_to_session:
            self._save_ranges_to_session()

    def _update_region_label(self, region_item) -> None:
        self.dashboard.interactions.update_region_label(region_item)

    def on_range_selected_from_list(self, row) -> None:
        self.dashboard.interactions.on_range_selected_from_list(row)
        self._populate_curve_list_for_region(row)

    def on_curve_item_changed(self, item) -> None:
        if item is None:
            return
        current_row = self.dashboard.range_list_widget.currentRow()
        if current_row < 0 or current_row >= len(self.dashboard.regions):
            return

        trace_index = item.data(Qt.ItemDataRole.UserRole)
        if trace_index is None:
            return

        if item.checkState() == Qt.CheckState.Checked:
            self.dashboard.region_curve_filters[current_row].add(trace_index)
        else:
            self.dashboard.region_curve_filters[current_row].discard(trace_index)

        self.perform_k_analysis()

    def _show_range_context_menu(self, point) -> None:
        row = self.dashboard.range_list_widget.currentRow()
        if row < 0:
            return
        menu = QMenu(self.dashboard.range_list_widget)
        action = menu.addAction("Edit curves for this range")
        action.triggered.connect(lambda: self._populate_curve_list_for_region(row))
        menu.exec(self.dashboard.range_list_widget.mapToGlobal(point))

    def _populate_curve_list_for_region(self, row) -> None:
        self.dashboard.curve_list_widget.blockSignals(True)
        self.dashboard.curve_list_widget.clear()

        if row < 0 or row >= len(self.dashboard.regions):
            self.dashboard.curve_list_widget.setEnabled(False)
            self.dashboard.curve_list_widget.blockSignals(False)
            return

        region = self.dashboard.regions[row]
        available_indices = self._get_trace_indices_for_region(region)
        if row >= len(self.dashboard.region_curve_filters):
            self.dashboard.region_curve_filters.extend([set() for _ in range(len(self.dashboard.region_curve_filters), row + 1)])
            selected_indices = set(available_indices)
        else:
            selected_indices = set(self.dashboard.region_curve_filters[row])
            if not selected_indices:
                selected_indices = set(available_indices)
            selected_indices &= set(available_indices)
        self.dashboard.region_curve_filters[row] = selected_indices

        if not available_indices:
            item = QListWidgetItem("No curves overlap this range")
            item.setFlags(Qt.ItemFlag.NoItemFlags)
            self.dashboard.curve_list_widget.addItem(item)
            self.dashboard.curve_list_widget.setEnabled(False)
            self.dashboard.curve_list_widget.blockSignals(False)
            return

        for idx in available_indices:
            raw_trace = self.dashboard.traces[idx]
            label = raw_trace.get("label", f"Curve {idx + 1}")
            item = QListWidgetItem(label)
            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            item.setCheckState(Qt.CheckState.Checked if idx in selected_indices else Qt.CheckState.Unchecked)
            item.setData(Qt.ItemDataRole.UserRole, idx)
            self.dashboard.curve_list_widget.addItem(item)

        self.dashboard.curve_list_widget.setEnabled(True)
        self.dashboard.curve_list_widget.blockSignals(False)

    def _clear_curve_list(self) -> None:
        self.dashboard.curve_list_widget.blockSignals(True)
        self.dashboard.curve_list_widget.clear()
        self.dashboard.curve_list_widget.setEnabled(False)
        self.dashboard.curve_list_widget.blockSignals(False)

    def _get_trace_indices_for_region(self, region) -> list[int]:
        processor = get_processor(self.dashboard.metadata.get("core", {}).get("technique"), self.dashboard.parent_window)
        settings = self.dashboard.metadata.get("analysis_settings", {})
        min_x, max_x = region.getRegion()
        indices = []
        for i, raw_trace in enumerate(self.dashboard.traces):
            x, y = processor._process_trace(raw_trace["wavelengths"], raw_trace["ea"], settings, i)
            mask = (x >= min_x) & (x <= max_x)
            if np.any(mask):
                indices.append(i)
        return indices

    def _default_curve_indices_for_region(self, region) -> set[int]:
        return set(self._get_trace_indices_for_region(region))

    def perform_k_analysis(self, region_item=None):
        return run_k_analysis(
            self.dashboard.traces,
            self.dashboard.metadata,
            self.dashboard.parent_window,
            self.dashboard.regions,
            self.dashboard.range_list_widget,
            self.dashboard.results_log,
            self.dashboard.current_view,
            self.dashboard.plot,
            self.update_view,
            self._save_ranges_to_session,
            self.dashboard.k_results,
            self.dashboard.chk_show_fits,
            self.dashboard.region_curve_filters,
            fit_gaussian_fn=self.fit_gaussian,
            show_studentized_res=self.dashboard.chk_show_cooks.isChecked(),
        )

    def shutdown(self) -> None:
        self.clear_all_regions(save_to_session=False)
        logger.info("KAnalysisDashboard shutting down.")

    def apply_theme(self, is_dark: bool) -> None:
        self.dashboard._is_dark = is_dark
        bg = 'k' if is_dark else 'w'
        fg = 'w' if is_dark else '#333333'
        self.dashboard.plot.setBackground(bg)

        axis_pen = pg.mkPen(fg)
        self.dashboard.plot.getAxis('bottom').setPen(axis_pen)
        self.dashboard.plot.getAxis('bottom').setTextPen(axis_pen)
        self.dashboard.plot.getAxis('left').setPen(axis_pen)
        self.dashboard.plot.getAxis('left').setTextPen(axis_pen)

        for i, region in enumerate(self.dashboard.regions):
            color_idx = i % 10
            region_color = pg.intColor(color_idx, 10)
            region.setBrush(pg.mkBrush(QColor(0, 0, 0, 0)))
            region.setHoverBrush(pg.mkBrush(QColor(0, 0, 255, 30)))
            self._set_region_pen(region, pg.mkPen(region_color, width=4))
        self.update_view()
