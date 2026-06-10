import uuid
import numpy as np
from scipy.stats import linregress, t
from PyQt6.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QWidget, QFrame,
    QLineEdit, QDoubleSpinBox, QComboBox, QScrollArea, QCheckBox, QMenu
)
from PyQt6.QtCore import Qt, QPoint, QTimer
from modeling_engines.base_engine import BaseModelingEngine
from processors.ea_processor import EAProcessor
from utils.project_manager import ProjectManager
from ui.analysis_settings_panel import CollapsibleSection, _palette
from ui.theme import get_theme

class KAnalysisEngine(BaseModelingEngine):
    """
    Engine for Power-Law (k-analysis) of EA signal vs Electric Field.
    Manages multiple peak markers and their associated search windows.
    """
    def __init__(self, parent_tab):
        super().__init__(parent_tab)
        self.markers_container = None
        self.current_markers = [] # In-memory list of markers
        self.available_fields = [] # Detected voltage/field values

    def build_ui(self, layout: QVBoxLayout):
        """Constructs the UI for managing peak markers in the settings panel."""
        # Sync internal state with persistent storage on UI build/rebuild
        self.current_markers = self._get_saved_markers()

        is_dark = getattr(self.parent_tab.parent_window, "dark_mode", True)
        C = _palette(is_dark)
        
        section = CollapsibleSection("K-Analysis: Peak Tracking", is_dark)
        
        # 1. Add Marker Button
        btn_add = QPushButton("+ Add Peak Marker")
        btn_add.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_add.setStyleSheet(f"""
            QPushButton {{
                background: {section.C['accent']};
                color: white;
                font-weight: bold;
                border-radius: 4px;
                padding: 6px;
            }}
            QPushButton:hover {{ background: {section.C['accent_dim']}; }}
        """)
        btn_add.clicked.connect(self._add_default_marker)
        section.content_layout.addWidget(btn_add)

        # 1.5. Select on Plot Button
        self.btn_select_on_plot = QPushButton("🎯 Select on Plot")
        self.btn_select_on_plot.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_select_on_plot.setStyleSheet(f"""
            QPushButton {{
                background: {C['bg_header']};
                color: {C['text_primary']};
                font-weight: bold;
                border-radius: 4px;
                padding: 6px;
                border: 1px solid {C['border']};
            }}
            QPushButton:hover {{ background: {C['bg_hover']}; }}
        """)
        self.btn_select_on_plot.clicked.connect(self._start_plot_selection_mode)
        section.content_layout.addWidget(self.btn_select_on_plot)

        # 2. List Container
        self.markers_container = QWidget()
        self.markers_layout = QVBoxLayout(self.markers_container)
        self.markers_layout.setContentsMargins(0, 5, 0, 0)
        self.markers_layout.setSpacing(4)
        section.content_layout.addWidget(self.markers_container)

        layout.insertWidget(0, section)
        self._refresh_marker_list_ui()

    def _get_saved_markers(self) -> list:
        """Retrieves the list of markers from the current session JSON."""
        data = ProjectManager.Session.get_data()
        tech_results = data.get("modeling", {}).get("saved_results", {}).get(self.parent_tab._current_technique, {})
        # K-Analysis specific data is stored under its own key within the technique's results
        k_analysis_data = tech_results.get("K-Analysis", {})
        return k_analysis_data.get("peak_markers", [])

    def _refresh_marker_list_ui(self):
        """Clears and rebuilds the list of markers in the UI."""
        if not self.markers_layout:
            return

        is_dark = getattr(self.parent_tab.parent_window, "dark_mode", True)
        C = _palette(is_dark)

        # Clear existing
        while self.markers_layout.count():
            item = self.markers_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        markers = self.current_markers # Use the in-memory list
        if not markers:
            lbl = QLabel("No peaks defined. Click '+' to add.")
            lbl.setStyleSheet(f"color: {C['text_secondary']}; font-style: italic; font-size: 11px;")
            self.markers_layout.addWidget(lbl)
            return

        for m in markers:
            container = QFrame()
            container.setStyleSheet(f"QFrame {{ background: {C['bg_content']}; border: 1px solid {C['border']}; border-radius: 6px; }}")
            cl = QVBoxLayout(container)
            cl.setContentsMargins(8, 8, 8, 8)
            cl.setSpacing(6)

            # --- Top Row: Label and Delete ---
            top_row = QHBoxLayout()

            chk_vis = QCheckBox()
            chk_vis.setFixedWidth(20)
            chk_vis.setChecked(m.get('visible', True))
            chk_vis.toggled.connect(lambda state, mid=m['id']: self._update_marker_field(mid, "visible", state))

            name_edit = QLineEdit(m['label'])
            name_edit.setPlaceholderText("Peak Name")
            name_edit.setStyleSheet(f"background: {C['bg_combo']}; color: {C['text_primary']}; border: none; font-weight: bold;")
            name_edit.editingFinished.connect(lambda e=name_edit, mid=m['id']: self._update_marker_field(mid, "label", e.text()))
            
            btn_del = QPushButton("✕")
            btn_del.setFixedSize(20, 20)
            btn_del.setStyleSheet(f"color: {C['text_secondary']}; border: none;")
            btn_del.clicked.connect(lambda checked, mid=m['id']: self._remove_marker(mid))
            
            top_row.addWidget(chk_vis)
            top_row.addWidget(name_edit)
            top_row.addWidget(btn_del)
            cl.addLayout(top_row)

            # --- Mid Row: Peak Type and Center ---
            mid_row = QHBoxLayout()
            type_combo = QComboBox()
            type_combo.addItems(["max", "min", "abs_extremum"])
            type_combo.setCurrentText(m.get('peak_type', 'abs_extremum'))
            type_combo.currentTextChanged.connect(lambda v, mid=m['id']: self._update_marker_field(mid, "peak_type", v))
            
            # Window Width Control
            width_spin = QDoubleSpinBox()
            width_spin.setRange(0.001, 2.0)
            width_spin.setSingleStep(0.01)
            width_spin.setDecimals(3)
            width_spin.setValue(m.get('search_max_x', 2.05) - m.get('search_min_x', 1.95))
            width_spin.valueChanged.connect(lambda v, mid=m['id']: self._update_marker_field(mid, "width", v))

            center_spin = QDoubleSpinBox()
            center_spin.setRange(0, 10)
            center_spin.setDecimals(3)
            center_spin.setValue(m.get('center_x', 2.0))
            center_spin.setSuffix(" eV")
            center_spin.valueChanged.connect(lambda v, mid=m['id']: self._update_marker_field(mid, "center_x", v))

            mid_row.addWidget(type_combo, 2)
            mid_row.addWidget(center_spin, 3)
            cl.addLayout(mid_row)

            width_row = QHBoxLayout()
            width_row.addWidget(QLabel("Window Width:"))
            width_row.addWidget(width_spin)
            cl.addLayout(width_row)

            # --- Bottom Row: Stats and Exclusions ---
            bottom_row = QHBoxLayout()
            res = self.results.get("peaks", {}).get(m['id'], {})
            stats_lbl = QLabel("No fit yet")
            if res:
                stats_lbl.setText(f"<span style='color:{res['color']};'><b>k={res['k']:.2f}</b> (R²={res['r_squared']:.3f})</span>")
            
            btn_exclude = QPushButton("Exclusions...")
            btn_exclude.setFixedHeight(22)
            btn_exclude.setStyleSheet(f"font-size: 10px; background: {C['bg_header']}; border: 1px solid {C['border']};")
            btn_exclude.clicked.connect(lambda checked, mid=m['id'], btn=btn_exclude: self._show_exclusions_menu(mid, btn))

            bottom_row.addWidget(stats_lbl, stretch=1)
            bottom_row.addWidget(btn_exclude)
            cl.addLayout(bottom_row)

            self.markers_layout.addWidget(container)

    def _start_plot_selection_mode(self):
        """Initiates plot interaction mode to allow user to click on the plot."""
        self.parent_tab._enable_plot_interaction('add_marker')
        self.btn_select_on_plot.setText("Click on plot...")
        self.btn_select_on_plot.setEnabled(False)

    def handle_plot_click(self, x_coord: float):
        """Receives a click event from the plot and creates a new marker."""
        self._add_default_marker(center_x=x_coord)
        self.btn_select_on_plot.setText("🎯 Select on Plot")
        self.btn_select_on_plot.setEnabled(True)

    def _update_marker_field(self, marker_id, field, value):
        """Update a specific field for a marker and trigger save/replot."""
        markers = self.current_markers
        for m in markers:
            if m['id'] == marker_id:
                if field == "center_x":
                    # Shift the entire search window with the center point
                    old_center = m.get('center_x', 2.0)
                    shift = value - old_center
                    m['center_x'] = value
                    m['search_min_x'] = m.get('search_min_x', 1.95) + shift
                    m['search_max_x'] = m.get('search_max_x', 2.05) + shift
                elif field == "width":
                    # Resize window around current center
                    center = m.get('center_x', 2.0)
                    m['search_min_x'] = center - (value / 2)
                    m['search_max_x'] = center + (value / 2)
                else:
                    m[field] = value
                break
        self.current_markers = markers
        self.parent_tab._on_setting_changed("peak_markers", markers)

        # Immediate visual feedback for visibility toggle
        if field == "visible" and self.results:
            self.plot_results(self.parent_tab.figure)
            self.parent_tab.canvas.draw()

    def _show_exclusions_menu(self, marker_id, anchor_widget):
        """Shows a themed popup to toggle specific voltages for this specific peak."""
        markers = self.current_markers
        target = next((m for m in markers if m['id'] == marker_id), None)
        if not target or not self.available_fields: return

        menu = QMenu(anchor_widget)
        excluded = target.get("excluded_fields", [])

        for val in sorted(self.available_fields):
            act = menu.addAction(f"Use {val} V")
            act.setCheckable(True)
            act.setChecked(val not in excluded)
            act.toggled.connect(lambda checked, v=val, mid=marker_id: self._toggle_exclusion(mid, v, not checked))
        
        # Show menu relative to the button
        menu.exec(anchor_widget.mapToGlobal(QPoint(0, anchor_widget.height())))

    def _toggle_exclusion(self, marker_id, value, should_exclude):
        markers = self.current_markers
        for m in markers:
            if m['id'] == marker_id:
                excluded = m.setdefault("excluded_fields", [])
                if should_exclude and value not in excluded:
                    excluded.append(value)
                elif not should_exclude and value in excluded:
                    excluded.remove(value)
                break
        self.current_markers = markers
        self.parent_tab._on_setting_changed("peak_markers", markers)
        self._refresh_marker_list_ui()

    def _add_default_marker(self, center_x: float | None = None):
        """Creates a dummy marker to verify the JSON persistence and UI refresh."""
        # Try to find a sensible default center based on processed data
        center_val = 2.0
        if self.results and self.results.get("x_data") is not None:
            x = self.results["x_data"]
            if len(x) > 0:
                center_val = (np.min(x) + np.max(x)) / 2
        else:
            # Fallback for when modeling hasn't run yet or no data
            pass
        if center_x is not None:
            center_val = center_x
            pass

        width = 0.1
        new_marker = { # Default values for a new marker
            "id": str(uuid.uuid4())[:8],
            "label": f"Peak {len(self._get_saved_markers()) + 1}",
            "center_x": float(center_val),
            "search_min_x": float(center_val - width/2),
            "search_max_x": float(center_val + width/2),
            "peak_type": "abs_extremum",
            "color": "#ff5555",
            "excluded_fields": [],
            "visible": True
        }
        markers = self.current_markers
        markers.append(new_marker) # Add to the list
        self.parent_tab._on_setting_changed("peak_markers", self.current_markers) # Trigger save
        self._refresh_marker_list_ui()

    def _remove_marker(self, marker_id):
        markers = [m for m in self.current_markers if m['id'] != marker_id]
        self.current_markers = markers # Update in-memory list
        self.parent_tab._on_setting_changed("peak_markers", self.current_markers) # Trigger save
        self._refresh_marker_list_ui()

    def run_modeling(self):
        """
        Extracts peak amplitudes from all traces and performs linear regression
        on log10(Amplitude) vs log10(Field/Voltage).
        """
        data = ProjectManager.Session.get_data()
        markers = self.current_markers # Use the list that drives the UI
        self.current_markers = markers # Ensure in-memory list is up-to-date

        # 1. Load and Process Traces using the standard EA Processor
        processor = EAProcessor(self.parent_tab.parent_window)
        traces_raw = processor._load_traces(data)
        if not traces_raw:
            return

        settings = processor.get_settings(data)
        fields = []
        processed_y_sets = []
        x_data = None

        for i, trace in enumerate(traces_raw):
            # x, y here are already energy-converted and phased
            x, y = processor._process_trace(trace["wavelengths"], trace["ea"], settings, i)
            if x_data is None: 
                x_data = x
            
            val = trace.get("value", 0)
            fields.append(val)
            processed_y_sets.append(y)

        fields = np.array(fields)
        self.available_fields = list(np.unique(fields)) # Store for UI
        valid_field_mask = (fields > 0) # Logarithms require positive non-zero values
        
        # 2. Initialize results with base data (Crucial for subplot rendering)
        self.results = {
            "peaks": {},
            "x_data": x_data,
            "y_sets": processed_y_sets,
            "fields": fields
        }

        if not markers:
            return

        for m in markers:
            amplitudes = []
            # Create a mask for the defined search window
            window_mask = (x_data >= m['search_min_x']) & (x_data <= m['search_max_x'])
            
            if not np.any(window_mask):
                print(f"Warning: No data points in window for peak '{m['label']}'")
                continue
            
            for y_set in processed_y_sets:
                y_win = y_set[window_mask]
                ptype = m.get('peak_type', 'abs_extremum')
                
                if ptype == "max":
                    amp = np.max(y_win)
                elif ptype == "min":
                    amp = np.min(y_win)
                else: # abs_extremum - safest initial guess
                    amp = y_win[np.argmax(np.abs(y_win))]
                
                # We use the absolute amplitude for power-law scaling
                amplitudes.append(np.abs(amp))
            
            amplitudes = np.array(amplitudes)
            
            # --- Apply Exclusions ---
            all_points_mask = valid_field_mask & (amplitudes > 0)
            fit_mask = all_points_mask.copy()
            excluded = m.get("excluded_fields", [])
            for i, f_val in enumerate(fields):
                if f_val in excluded:
                    fit_mask[i] = False

            if np.sum(fit_mask) < 2:
                continue

            # Regression on non-excluded points
            log_f_fit = np.log10(fields[fit_mask])
            log_a_fit = np.log10(amplitudes[fit_mask])
            res = linregress(log_f_fit, log_a_fit)
            
            # Store results and metadata for plotting
            log_f_all = np.log10(fields[all_points_mask])
            log_a_all = np.log10(amplitudes[all_points_mask])
            rel_fit_mask = fit_mask[all_points_mask]

            self.results["peaks"][m['id']] = {
                "label": m['label'],
                "color": m.get('color', '#ff5555'),
                "k": res.slope,
                "r_squared": res.rvalue**2,
                "k_error": res.stderr,
                "log_fields_all": log_f_all,
                "log_amps_all": log_a_all,
                "rel_fit_mask": rel_fit_mask,
                "fit_line_x": log_f_fit,
                "fit_line_y": res.intercept + res.slope * log_f_fit
            }

        # Safely trigger UI refresh on main thread
        QTimer.singleShot(0, self._refresh_marker_list_ui)

    def plot_results(self, figure):
        """Plots the Log-Log power law dependence for all tracked peaks."""
        figure.clear()
        
        peaks_results = self.results.get("peaks", {})
        spectra_x = self.results.get("x_data")
        spectra_y = self.results.get("y_sets")

        if spectra_x is None:
            ax = figure.add_subplot(111)
            ax.text(0.5, 0.5, "No modeling data available.\nAdd markers to start.", 
                    ha='center', va='center', transform=ax.transAxes, alpha=0.5)
            figure.canvas.draw()
            return

        # Create a 2-row layout: Top for spectra overview, Bottom for k-analysis fit
        axs = figure.subplots(2, 1, height_ratios=[1, 1.2], sharex=False)
        ax_spec, ax_log = axs[0], axs[1]

        # --- 1. Top Subplot: Spectra & Search Windows ---
        if spectra_y:
            for y_set in spectra_y:
                # Plot all traces in a dimmed color to provide context without clutter
                ax_spec.plot(spectra_x, y_set, color='gray', alpha=0.2, linewidth=0.6)
            
            # Highlight the search windows defined by the markers
            markers = self.current_markers
            for m in markers:
                if not m.get('visible', True): continue
                ax_spec.axvspan(m.get('search_min_x', 1.95), m.get('search_max_x', 2.05), 
                                color=m.get('color', '#ff5555'), alpha=0.15)
                # Small label above the window
                ax_spec.text((m.get('search_min_x', 1.95) + m.get('search_max_x', 2.05))/2, 1.01, 
                             m.get('label', 'Peak'), ha='center', va='bottom', color=m.get('color', '#ff5555'), 
                             fontsize=8, fontweight='bold', transform=ax_spec.get_xaxis_transform())

        ax_spec.set_ylabel(r"$\Delta T/T$ (mOD)")
        ax_spec.set_title("Traces and Tracking Windows")
        ax_spec.grid(True, linestyle=':', alpha=0.3)

        # --- 2. Bottom Subplot: Log-Log power law dependence (Existing Logic) ---
        if not peaks_results:
             ax_log.text(0.5, 0.5, "No fits yet.\nAdjust markers to trigger fit.", 
                        ha='center', va='center', transform=ax_log.transAxes, alpha=0.5)
             figure.canvas.draw()
             return

        for pid, pdata in peaks_results.items():
            # Respect visibility setting for the fit lines and data points
            m_config = next((m for m in self.current_markers if m['id'] == pid), None)
            if m_config and not m_config.get('visible', True): continue

            mask = pdata.get('rel_fit_mask', [])
            if len(mask) == 0: continue

            # Plot excluded points as dimmed 'x'
            ax_log.plot(pdata['log_fields_all'][~mask], pdata['log_amps_all'][~mask], 'x',
                        color=pdata['color'], alpha=0.15, markersize=4)
            
            # Plot included points as circles
            ax_log.plot(pdata['log_fields_all'][mask], pdata['log_amps_all'][mask], 'o',
                        color=pdata['color'], alpha=0.5, markersize=5)
            
            # Plot the resulting linear fit line
            ax_log.plot(pdata['fit_line_x'], pdata['fit_line_y'], '-', 
                        color=pdata['color'], linewidth=2,
                        label=f"{pdata['label']} ($k$={pdata['k']:.2f})")

            # Live Slope Tooltip: Annotate the slope value at the end of the fit line
            if len(pdata['fit_line_x']) > 0:
                ax_log.annotate(
                    f"$k$={pdata['k']:.2f}",
                    xy=(pdata['fit_line_x'][-1], pdata['fit_line_y'][-1]),
                    xytext=(5, 5), textcoords='offset points',
                    color=pdata['color'], fontweight='bold',
                    bbox=dict(boxstyle='round,pad=0.2', fc='white', alpha=0.7, ec='none')
                )

        ax_log.set_xlabel(r"$\log_{10}$ (Electric Field / Voltage)")
        ax_log.set_ylabel(r"$\log_{10}$ (|$\Delta T/T$|)")
        ax_log.set_title("EA Power-Law Dependence ($k$-analysis)")
        
        # Only show legend if there are actual labels to display
        if any(line.get_label() and not line.get_label().startswith('_') for line in ax_log.lines):
            ax_log.legend(frameon=False, fontsize=9)
        ax_log.grid(True, linestyle=':', alpha=0.3)