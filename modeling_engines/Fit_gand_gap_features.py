import sys
import json
import os
import numpy as np
import pandas as pd
from scipy.interpolate import CubicSpline
from scipy.optimize import curve_fit

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QGroupBox, QGridLayout, QPushButton, QFileDialog,
    QCheckBox, QMessageBox, QDoubleSpinBox, QScrollArea, QTextEdit
)
from PyQt6.QtCore import Qt, QTimer

import matplotlib
matplotlib.use('QtAgg')
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qtagg import NavigationToolbar2QT as NavigationToolbar
from matplotlib.figure import Figure
import matplotlib.cm as cm


# --- Fitting Helper Functions ---
def asymmetric_lorentzian(E, E0, A0, gamma_left, gamma_right, y_offset):
    """Asymmetric Lorentzian line shape with independent left/right HWHM broadening."""
    gamma = np.where(E < E0, gamma_left, gamma_right)
    return y_offset + A0 / (1.0 + ((E - E0) / np.maximum(gamma, 1e-6))**2)


def fit_feature_advanced(sub_E, sub_EA, mode='max'):
    """
    Fits sub-window EA data using:
    - Cubic Spline Root Finding for Zero-Crossings ('zero')
    - Asymmetric Lorentzian Fit for Peaks/Troughs ('max' / 'min')
    """
    if len(sub_EA) < 4:
        # Fallback for insufficient points
        idx = np.argmax(sub_EA) if mode == 'max' else (np.argmin(sub_EA) if mode == 'min' else np.argmin(np.abs(sub_EA)))
        return sub_E[idx], sub_EA[idx], sub_E, sub_EA

    # Dense mesh for smooth diagnostic curve rendering
    E_dense = np.linspace(sub_E[0], sub_E[-1], 200)

    if mode == 'zero':
        # --- ZERO CROSSING: Cubic Spline Root Finding ---
        try:
            cs = CubicSpline(sub_E, sub_EA)
            roots = cs.roots()
            # Find root strictly within bounds
            valid_roots = roots[(roots >= sub_E[0]) & (roots <= sub_E[-1])]
            
            if len(valid_roots) > 0:
                # Pick root closest to discrete zero-crossing
                idx_discrete = np.argmin(np.abs(sub_EA))
                best_root = valid_roots[np.argmin(np.abs(valid_roots - sub_E[idx_discrete]))]
                return best_root, 0.0, E_dense, cs(E_dense)
        except Exception:
            pass

        # Linear fallback if spline root fails
        p = np.polyfit(sub_E, sub_EA, 1)
        z_E = -p[1] / p[0] if p[0] != 0 else sub_E[np.argmin(np.abs(sub_EA))]
        return z_E, 0.0, E_dense, np.poly1d(p)(E_dense)

    else:
        # --- PEAKS & TROUGHS: Asymmetric Lorentzian Fit ---
        idx_ext = np.argmax(sub_EA) if mode == 'max' else np.argmin(sub_EA)
        E0_init = sub_E[idx_ext]
        A0_init = sub_EA[idx_ext] - np.min(sub_EA) if mode == 'max' else sub_EA[idx_ext] - np.max(sub_EA)
        y_off_init = np.min(sub_EA) if mode == 'max' else np.max(sub_EA)
        gamma_init = (sub_E[-1] - sub_E[0]) / 4.0

        p0 = [E0_init, A0_init, gamma_init, gamma_init, y_off_init]
        bounds = (
            [sub_E[0], -np.inf if mode == 'min' else 0, 1e-5, 1e-5, -np.inf],
            [sub_E[-1], 0 if mode == 'min' else np.inf, (sub_E[-1]-sub_E[0]), (sub_E[-1]-sub_E[0]), np.inf]
        )

        try:
            popt, _ = curve_fit(asymmetric_lorentzian, sub_E, sub_EA, p0=p0, bounds=bounds, maxfev=2000)
            E0_fit, A0_fit, g_l, g_r, y_off = popt
            
            fit_dense = asymmetric_lorentzian(E_dense, *popt)
            peak_amp = asymmetric_lorentzian(E0_fit, *popt)
            return E0_fit, peak_amp, E_dense, fit_dense
        except Exception:
            # Quadratic fallback if non-linear solver fails to converge
            p = np.polyfit(sub_E, sub_EA, 2)
            if p[0] != 0:
                E0_quad = -p[1] / (2 * p[0])
                if sub_E[0] <= E0_quad <= sub_E[-1]:
                    return E0_quad, np.poly1d(p)(E0_quad), E_dense, np.poly1d(p)(E_dense)

            return sub_E[idx_ext], sub_EA[idx_ext], E_dense, sub_EA[0]*np.ones_like(E_dense)


class MultiViewCanvas(FigureCanvas):
    def __init__(self, parent=None, width=7, height=6, dpi=100):
        self.fig = Figure(figsize=(width, height), dpi=dpi)
        super().__init__(self.fig)
        self.setParent(parent)

    def plot_spectrum_view(self, energy, ea_dict, active_fields, flip_phase, feature_windows, show_windows, show_peaks, extracted):
        self.fig.clear()
        ax = self.fig.add_subplot(111)
        
        if energy is None or len(ea_dict) == 0:
            ax.text(0.5, 0.5, "Please Load a CSV File", ha='center', va='center', fontsize=14)
            self.draw()
            return

        phase_mult = -1.0 if flip_phase else 1.0
        all_fields = sorted(ea_dict.keys())
        colors = cm.get_cmap('plasma')(np.linspace(0.15, 0.85, len(all_fields)))

        for idx, F_kv in enumerate(all_fields):
            if F_kv not in active_fields:
                continue
            ea_exp = ea_dict[F_kv] * phase_mult
            ax.plot(energy, ea_exp, color=colors[idx], linewidth=1.5, label=f'{F_kv:.0f} kV/cm')

        ax.axhline(0, color='gray', linestyle='--', linewidth=0.8, alpha=0.7)

        if show_windows:
            feat_colors = {'d': 'green', 'e': 'blue', 'f': 'red', 'g': 'purple', 'h': 'orange'}
            for key, (w_min, w_max) in feature_windows.items():
                if w_max > w_min:
                    ax.axvspan(w_min, w_max, color=feat_colors[key], alpha=0.15, label=f'Window {key}')

        if show_peaks:
            feat_marker_colors = {'d': 'darkgreen', 'e': 'darkblue', 'f': 'crimson', 'g': 'darkmagenta', 'h': 'darkorange'}
            for key in ['d', 'e', 'f', 'g', 'h']:
                E_vals = extracted[key]['E']
                Amp_vals = extracted[key]['Amp']
                if len(E_vals) > 0:
                    ax.scatter(E_vals, Amp_vals, color=feat_marker_colors[key], s=35, zorder=5, edgecolors='black', label=f'Peak {key}')

        ax.set_xlabel('Photon Energy (eV)', fontsize=11, fontweight='bold')
        ax.set_ylabel('$\Delta A$ (mOD)', fontsize=11, fontweight='bold')
        ax.set_title('Experimental EA Spectra & Feature Extraction', fontweight='bold')
        ax.tick_params(direction='in', top=True, right=True, labelsize=10)
        ax.legend(bbox_to_anchor=(1.02, 1), loc='upper left', fontsize=9)

        self.fig.tight_layout()
        self.draw()

    def plot_scaling_view(self, fields_kv, extracted):
        self.fig.clear()
        ax1 = self.fig.add_subplot(211)
        ax2 = self.fig.add_subplot(212)
        
        if len(fields_kv) == 0:
            ax1.text(0.5, 0.5, "No Active Fields Selected", ha='center', va='center')
            self.draw()
            return

        F_array = np.array(fields_kv)
        # Convert F to F^(2/3) for exact linear scaling based on electro-optic energy
        F_23 = F_array ** (2/3)
        
        E_d = np.array(extracted['d']['E'])
        E_e = np.array(extracted['e']['E'])
        E_f = np.array(extracted['f']['E'])
        E_g = np.array(extracted['g']['E'])

        # --- Top Plot: F^(2/3) Scaling in meV with Linear Fits ---
        def plot_spacing_fit(E1, E2, color, marker, label_prefix):
            if len(E1) == len(F_array) and len(E1) > 1:
                # Convert to meV
                dE_meV = np.abs(E1 - E2) * 1000.0 
                
                # Linear fit with covariance to get uncertainty
                poly, cov = np.polyfit(F_23, dE_meV, 1, cov=True)
                slope, intercept = poly
                err_slope = np.sqrt(np.diag(cov))[0]
                
                fit_line = slope * F_23 + intercept
                
                ax1.plot(F_23, dE_meV, marker, color=color, markersize=6, linestyle='', label=f'{label_prefix} Data')
                ax1.plot(F_23, fit_line, '--', color=color, alpha=0.7, 
                         label=f'{label_prefix} Fit: slope = {slope:.2f} ± {err_slope:.2f}')

        plot_spacing_fit(E_d, E_f, 'green', 'o', '$\Delta E_{df}$')
        plot_spacing_fit(E_d, E_g, 'purple', 's', '$\Delta E_{dg}$')
        plot_spacing_fit(E_e, E_g, 'blue', '^', '$\Delta E_{eg}$')

        ax1.set_xlabel('Electric Field $F^{2/3}$ ((kV/cm)$^{2/3}$)', fontweight='bold')
        ax1.set_ylabel('Energy Difference $\Delta E$ (meV)', fontweight='bold')
        ax1.set_title('Feature Energy Spacings vs. $F^{2/3}$ (meV)', fontweight='bold')
        ax1.legend(fontsize=8)
        ax1.grid(True, linestyle=':', alpha=0.6)

        # --- Bottom Plot: Log-Log Amplitude Scaling with Uncertainty ---
        Amp_d = np.abs(np.array(extracted['d']['Amp']))
        Amp_f = np.abs(np.array(extracted['f']['Amp']))

        for key, amp, col in [('d (Peak)', Amp_d, 'green'), ('f (Trough)', Amp_f, 'red')]:
            if len(amp) > 1 and np.all(amp > 0):
                log_F = np.log(F_array)
                log_A = np.log(amp)
                
                weights = F_array / np.sum(F_array)
                # Include cov=True for uncertainty
                poly, cov = np.polyfit(log_F, log_A, 1, w=np.sqrt(weights), cov=True)
                slope_n = poly[0]
                err_n = np.sqrt(np.diag(cov))[0]
                intercept = poly[1]
                
                fit_amp = np.exp(intercept) * (F_array ** slope_n)
                ax2.loglog(F_array, amp, 'o', color=col, label=f'{key} Data')
                ax2.loglog(F_array, fit_amp, '--', color=col, 
                           label=f'{key} Fit: $n = {slope_n:.3f} \pm {err_n:.3f}$')

        ax2.set_xlabel('Electric Field $F$ (kV/cm) [Log Scale]', fontweight='bold')
        ax2.set_ylabel('Amplitude $|\Delta A|$ (mOD) [Log Scale]', fontweight='bold')
        ax2.set_title('Weighted Log-Log Amplitude Scaling Analysis', fontweight='bold')
        ax2.legend(fontsize=8)
        ax2.grid(True, which="both", linestyle=':', alpha=0.6)

        self.fig.tight_layout()
        self.draw()

    def plot_fit_diagnostics_view(self, fields_kv, extracted, fit_curves):
        """View 3: Individual Window Diagnostic Subplots showing fitted curves vs raw data."""
        self.fig.clear()
        
        if len(fields_kv) == 0:
            ax = self.fig.add_subplot(111)
            ax.text(0.5, 0.5, "No Active Fields Selected", ha='center', va='center')
            self.draw()
            return

        keys = ['d', 'e', 'f', 'g', 'h']
        titles = ['d (Peak: Asym. Lorentzian)', 'e (Zero: Cubic Spline)', 
                  'f (Trough: Asym. Lorentzian)', 'g (Zero: Cubic Spline)', 'h (Peak: Asym. Lorentzian)']
        
        colors = cm.get_cmap('plasma')(np.linspace(0.15, 0.85, len(fields_kv)))

        for idx, key in enumerate(keys):
            ax = self.fig.add_subplot(2, 3, idx + 1)
            
            for f_idx, F_kv in enumerate(fields_kv):
                c = colors[f_idx]
                if f_idx < len(fit_curves[key]):
                    sub_E, sub_EA, E_dense, EA_fit = fit_curves[key][f_idx]
                    E_peak = extracted[key]['E'][f_idx]
                    Amp_peak = extracted[key]['Amp'][f_idx]

                    # Plot Raw Data Points
                    ax.plot(sub_E, sub_EA, 'o', color=c, markersize=3, alpha=0.6)
                    # Plot Continuous Fit Model
                    ax.plot(E_dense, EA_fit, '-', color=c, linewidth=1.2, label=f'{F_kv:.0f} kV/cm' if idx == 0 else "")
                    # Plot Extracted Extrema Location
                    ax.plot(E_peak, Amp_peak, 'x', color='black', markersize=6, markeredgewidth=1.5)

            ax.axhline(0, color='gray', linestyle='--', linewidth=0.7, alpha=0.5)
            ax.set_title(titles[idx], fontsize=9, fontweight='bold')
            ax.set_xlabel('eV', fontsize=8)
            ax.set_ylabel('$\Delta A$', fontsize=8)
            ax.tick_params(labelsize=8)
            ax.grid(True, linestyle=':', alpha=0.5)

        # Legend on first subplot
        self.fig.axes[0].legend(fontsize=7, loc='best')
        self.fig.suptitle('Sub-window Fit Diagnostics (Data Points vs. Model Curves)', fontsize=12, fontweight='bold')
        self.fig.tight_layout()
        self.draw()


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Franz-Keldysh Feature Analyzer")
        self.resize(1350, 850)

        self.data_file_path = ""
        self.json_config_path = "last_config.json"
        self.energy = None
        self.absorption = None
        self.ea_dict = {}
        self.voltage_checkboxes = {}
        self.current_view = 0  # 0: Spectra, 1: Scaling, 2: Fit Diagnostics

        self.autosave_timer = QTimer(self)
        self.autosave_timer.setSingleShot(True)
        self.autosave_timer.setInterval(1000)
        self.autosave_timer.timeout.connect(self.save_json_config_auto)

        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)

        # Left Container: Toolbar & Canvas
        plot_container = QVBoxLayout()
        self.canvas = MultiViewCanvas(self, width=7, height=6)
        self.toolbar = NavigationToolbar(self.canvas, self)
        
        self.btn_switch_view = QPushButton("🔄 Cycle View: [1. EA Spectra] ➔ [2. Scaling Fits] ➔ [3. Window Fit Diagnostics]")
        self.btn_switch_view.setStyleSheet("font-weight: bold; background-color: #2196F3; color: white; padding: 10px;")
        self.btn_switch_view.clicked.connect(self.toggle_graph_view)
        
        plot_container.addWidget(self.btn_switch_view)
        plot_container.addWidget(self.toolbar)
        plot_container.addWidget(self.canvas, stretch=1)
        main_layout.addLayout(plot_container, stretch=3)

        # Right Sidebar: Controls
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        control_panel = QWidget()
        control_layout = QVBoxLayout(control_panel)

        # 1. JSON & CSV File Controls
        group_json = QGroupBox("1. Preset & CSV Data File")
        json_box = QVBoxLayout()
        
        btn_layout = QHBoxLayout()
        self.btn_load_json = QPushButton("📂 Import JSON")
        self.btn_load_json.clicked.connect(self.import_json_dialog)
        self.btn_save_json = QPushButton("💾 Export JSON")
        self.btn_save_json.clicked.connect(self.export_json_dialog)
        btn_layout.addWidget(self.btn_load_json)
        btn_layout.addWidget(self.btn_save_json)
        json_box.addLayout(btn_layout)

        self.btn_load_csv = QPushButton("Open CSV File")
        self.btn_load_csv.clicked.connect(self.load_csv_dialog)
        self.lbl_file = QLabel("No file loaded.")
        self.lbl_file.setWordWrap(True)
        
        self.lbl_save_status = QLabel("Auto-save: Ready")
        self.lbl_save_status.setStyleSheet("color: gray; font-size: 10px;")

        json_box.addWidget(self.btn_load_csv)
        json_box.addWidget(self.lbl_file)
        json_box.addWidget(self.lbl_save_status)
        group_json.setLayout(json_box)
        control_layout.addWidget(group_json)

        # 2. View Options
        group_view = QGroupBox("2. Display Options")
        view_box = QVBoxLayout()
        self.chk_flip = QCheckBox("Invert Lock-in Phase (180° Flip)")
        self.chk_flip.stateChanged.connect(self._on_user_action)

        self.chk_show_windows = QCheckBox("Show Feature Windows Shading")
        self.chk_show_windows.setChecked(True)
        self.chk_show_windows.stateChanged.connect(self._on_user_action)

        self.chk_show_peaks = QCheckBox("Show Extracted Peak Markers")
        self.chk_show_peaks.setChecked(True)
        self.chk_show_peaks.stateChanged.connect(self._on_user_action)

        view_box.addWidget(self.chk_flip)
        view_box.addWidget(self.chk_show_windows)
        view_box.addWidget(self.chk_show_peaks)
        group_view.setLayout(view_box)
        control_layout.addWidget(group_view)

        # 3. Feature Windows Setup
        group_features = QGroupBox("3. Feature Search Windows (eV)")
        grid_feat = QGridLayout()
        self.feature_boxes = {}
        
        features = [('d (Peak)', 'd', 2.770, 2.820),
                    ('e (Zero)', 'e', 2.820, 2.835),
                    ('f (Trough)', 'f', 2.835, 2.865),
                    ('g (Zero)', 'g', 2.875, 2.895),
                    ('h (Peak)', 'h', 2.880, 2.925)]

        for idx, (label, key, d_min, d_max) in enumerate(features):
            lbl_title = QLabel(f"<b>Feature {label}</b>")
            grid_feat.addWidget(lbl_title, idx, 0, 1, 2)
            
            box_min = self._create_spinbox(d_min)
            box_max = self._create_spinbox(d_max)
            
            grid_feat.addWidget(QLabel("Min:"), idx, 2)
            grid_feat.addWidget(box_min, idx, 3)
            grid_feat.addWidget(QLabel("Max:"), idx, 4)
            grid_feat.addWidget(box_max, idx, 5)
            
            self.feature_boxes[key] = (box_min, box_max)

        group_features.setLayout(grid_feat)
        control_layout.addWidget(group_features)

        # 4. Voltage Toggles
        self.group_voltage = QGroupBox("4. Active Voltages")
        self.layout_voltage = QGridLayout()
        self.group_voltage.setLayout(self.layout_voltage)
        control_layout.addWidget(self.group_voltage)

        # 5. Numerical Results Summary
        group_results = QGroupBox("5. Extracted Slopes & Spacings")
        res_layout = QVBoxLayout()
        self.txt_results = QTextEdit()
        self.txt_results.setReadOnly(True)
        self.txt_results.setFixedHeight(180)
        res_layout.addWidget(self.txt_results)
        group_results.setLayout(res_layout)
        control_layout.addWidget(group_results)

        control_layout.addStretch()
        scroll_area.setWidget(control_panel)
        main_layout.addWidget(scroll_area, stretch=1)

        if os.path.exists(self.json_config_path):
            self.load_json_config(self.json_config_path)

    def _create_spinbox(self, default_val):
        spin = QDoubleSpinBox()
        spin.setRange(0.0, 10.0)
        spin.setDecimals(3)
        spin.setSingleStep(0.005)
        spin.setValue(default_val)
        spin.valueChanged.connect(self._on_user_action)
        return spin

    def _on_user_action(self):
        self.update_gui()
        self.lbl_save_status.setText("Auto-save: Waiting for inactivity...")
        self.autosave_timer.start()

    def load_csv_file(self, file_path):
        if not file_path or not os.path.exists(file_path):
            return False
        try:
            df = pd.read_csv(file_path)
            df = df.sort_values(by=df.columns[0], ascending=True).reset_index(drop=True)
            
            self.energy = df.iloc[:, 0].values
            self.absorption = df.iloc[:, 1].values
            
            self.ea_dict = {}
            for col in df.columns[2:]:
                if "EA" in col:
                    field_kv = float(col.replace("EA", "").replace("kV/cm", "").replace("(mOD)", "").strip())
                    self.ea_dict[field_kv] = df[col].values
            
            self.data_file_path = file_path
            self.lbl_file.setText(f"Loaded CSV: {os.path.basename(file_path)}")
            
            e_min, e_max = self.energy[0], self.energy[-1]
            for box_min, box_max in self.feature_boxes.values():
                box_min.setRange(e_min, e_max)
                box_max.setRange(e_min, e_max)

            self._build_voltage_toggles()
            return True
        except Exception as e:
            QMessageBox.critical(self, "Error Loading CSV", f"Could not parse file.\nDetails: {str(e)}")
            return False

    def load_csv_dialog(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Open EA Data CSV", "", "CSV Files (*.csv);;All Files (*)")
        if file_path:
            if self.load_csv_file(file_path):
                self._on_user_action()

    def _build_voltage_toggles(self, selected_states=None):
        for cb in self.voltage_checkboxes.values():
            cb.deleteLater()
        self.voltage_checkboxes.clear()

        sorted_fields = sorted(self.ea_dict.keys())
        for idx, F_kv in enumerate(sorted_fields):
            cb = QCheckBox(f"{F_kv:.0f} kV/cm")
            is_checked = selected_states.get(str(F_kv), True) if selected_states else True
            cb.setChecked(is_checked)
            cb.stateChanged.connect(self._on_user_action)
            self.layout_voltage.addWidget(cb, idx // 2, idx % 2)
            self.voltage_checkboxes[F_kv] = cb

    def _get_active_fields(self):
        return [F_kv for F_kv, cb in self.voltage_checkboxes.items() if cb.isChecked()]

    def collect_config_dict(self):
        active_voltages = {str(F_kv): cb.isChecked() for F_kv, cb in self.voltage_checkboxes.items()}
        feature_windows = {
            k: [box_min.value(), box_max.value()]
            for k, (box_min, box_max) in self.feature_boxes.items()
        }
        return {
            "data_file_path": self.data_file_path,
            "invert_phase": self.chk_flip.isChecked(),
            "show_windows": self.chk_show_windows.isChecked(),
            "show_peaks": self.chk_show_peaks.isChecked(),
            "feature_windows": feature_windows,
            "active_voltages": active_voltages
        }

    def save_json_config_auto(self):
        try:
            config = self.collect_config_dict()
            with open(self.json_config_path, 'w') as f:
                json.dump(config, f, indent=4)
            self.lbl_save_status.setText(f"Auto-saved: {os.path.basename(self.json_config_path)}")
        except Exception:
            self.lbl_save_status.setText("Auto-save failed.")

    def export_json_dialog(self):
        path, _ = QFileDialog.getSaveFileName(self, "Export Config JSON", "ea_config.json", "JSON Files (*.json)")
        if path:
            try:
                config = self.collect_config_dict()
                with open(path, 'w') as f:
                    json.dump(config, f, indent=4)
                self.json_config_path = path
                QMessageBox.information(self, "Export Successful", f"Saved to {os.path.basename(path)}")
            except Exception as e:
                QMessageBox.critical(self, "Error Exporting JSON", str(e))

    def import_json_dialog(self):
        path, _ = QFileDialog.getOpenFileName(self, "Import Config JSON", "", "JSON Files (*.json)")
        if path:
            self.load_json_config(path)

    def load_json_config(self, json_path):
        if not os.path.exists(json_path):
            return
        try:
            with open(json_path, 'r') as f:
                config = json.load(f)

            self.blockSignals(True)
            self.json_config_path = json_path
            data_file = config.get("data_file_path", "")
            
            if data_file and os.path.exists(data_file):
                self.load_csv_file(data_file)

            self.chk_flip.setChecked(config.get("invert_phase", False))
            self.chk_show_windows.setChecked(config.get("show_windows", True))
            self.chk_show_peaks.setChecked(config.get("show_peaks", True))

            feat_wins = config.get("feature_windows", {})
            for key, (box_min, box_max) in self.feature_boxes.items():
                if key in feat_wins:
                    box_min.setValue(feat_wins[key][0])
                    box_max.setValue(feat_wins[key][1])

            saved_voltages = config.get("active_voltages", {})
            if self.ea_dict:
                self._build_voltage_toggles(saved_voltages)

            self.blockSignals(False)
            self.update_gui()
            self.lbl_save_status.setText(f"Loaded preset: {os.path.basename(json_path)}")

        except Exception as e:
            self.blockSignals(False)
            QMessageBox.critical(self, "Error Loading JSON", str(e))

    def toggle_graph_view(self):
        self.current_view = (self.current_view + 1) % 3
        self.update_gui()

    def update_gui(self):
        if self.energy is None:
            return

        active_fields = self._get_active_fields()
        flip_phase = self.chk_flip.isChecked()
        show_windows = self.chk_show_windows.isChecked()
        show_peaks = self.chk_show_peaks.isChecked()

        feature_windows = {
            k: (box_min.value(), box_max.value())
            for k, (box_min, box_max) in self.feature_boxes.items()
        }

        phase_mult = -1.0 if flip_phase else 1.0
        extracted = {k: {'E': [], 'Amp': []} for k in ['d', 'e', 'f', 'g', 'h']}
        fit_curves = {k: [] for k in ['d', 'e', 'f', 'g', 'h']}
        
        for F_kv in active_fields:
            ea_exp = self.ea_dict[F_kv] * phase_mult
            for k in ['d', 'e', 'f', 'g', 'h']:
                w_min, w_max = feature_windows[k]
                mask = (self.energy >= w_min) & (self.energy <= w_max)
                if np.any(mask):
                    sub_E, sub_EA = self.energy[mask], ea_exp[mask]
                    mode = 'max' if k in ['d', 'h'] else ('min' if k == 'f' else 'zero')
                    
                    fit_E, fit_Amp, E_dense, EA_fit = fit_feature_advanced(sub_E, sub_EA, mode=mode)
                    
                    extracted[k]['E'].append(fit_E)
                    extracted[k]['Amp'].append(fit_Amp)
                    fit_curves[k].append((sub_E, sub_EA, E_dense, EA_fit))

        # Render View based on current_view state
        if self.current_view == 0:
            self.canvas.plot_spectrum_view(
                self.energy, self.ea_dict, active_fields, flip_phase,
                feature_windows, show_windows, show_peaks, extracted
            )
        elif self.current_view == 1:
            self.canvas.plot_scaling_view(active_fields, extracted)
        else:
            self.canvas.plot_fit_diagnostics_view(active_fields, extracted, fit_curves)

        # --- Update Text Summary Box with Uncertainties ---
        summary = ""
        F_arr = np.array(active_fields)
        F_23 = F_arr ** (2/3)
        E_d, E_e, E_f, E_g = (np.array(extracted[k]['E']) for k in ['d', 'e', 'f', 'g'])
        
        if len(active_fields) > 1:
            summary += f"<b>Spacing Fits vs F<sup>2/3</sup> (Slope in meV/(kV/cm)<sup>2/3</sup>):</b><br>"
            
            def get_spacing_stats(E1, E2, label):
                if len(E1) == len(F_arr):
                    dE_meV = np.abs(E1 - E2) * 1000.0
                    poly, cov = np.polyfit(F_23, dE_meV, 1, cov=True)
                    err = np.sqrt(np.diag(cov))[0]
                    return f"• {label} slope = {poly[0]:.2f} ± {err:.2f}<br>"
                return ""

            summary += get_spacing_stats(E_d, E_f, "|E_d - E_f|")
            summary += get_spacing_stats(E_d, E_g, "|E_d - E_g|")
            summary += get_spacing_stats(E_e, E_g, "|E_e - E_g|")
            summary += "<br>"

            Amp_d = np.abs(np.array(extracted['d']['Amp']))
            Amp_f = np.abs(np.array(extracted['f']['Amp']))
            w = np.sqrt(F_arr / np.sum(F_arr))

            summary += f"<b>Weighted Field Exponents (log-log):</b><br>"
            if len(Amp_d) == len(F_arr) and np.all(Amp_d > 0):
                poly, cov = np.polyfit(np.log(F_arr), np.log(Amp_d), 1, w=w, cov=True)
                summary += f"• Peak 'd' slope n = {poly[0]:.3f} ± {np.sqrt(np.diag(cov))[0]:.3f}<br>"
            if len(Amp_f) == len(F_arr) and np.all(Amp_f > 0):
                poly, cov = np.polyfit(np.log(F_arr), np.log(Amp_f), 1, w=w, cov=True)
                summary += f"• Trough 'f' slope n = {poly[0]:.3f} ± {np.sqrt(np.diag(cov))[0]:.3f}<br>"

        self.txt_results.setHtml(summary)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())