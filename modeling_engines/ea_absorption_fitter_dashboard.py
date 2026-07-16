import sys
import numpy as np
import pandas as pd
from scipy.optimize import curve_fit

from PyQt6.QtWidgets import (QWidget, QVBoxLayout, 
                             QHBoxLayout, QPushButton, QSlider, 
                             QLabel, QCheckBox, QDoubleSpinBox, QGroupBox, QScrollArea)
from PyQt6.QtCore import Qt, QTimer

import matplotlib
matplotlib.use('Qt5Agg')
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT as NavigationToolbar
from matplotlib.figure import Figure

from modeling_engines.base_modeling_dashboard import BaseModelingDashboard

# ==========================================
# CORE MATHEMATICAL COMPONENTS
# ==========================================
def gaussian(x, amp, cen, wid):
    return amp * np.exp(-((x - cen) ** 2) / (2 * wid ** 2))

def lorentzian(x, amp, cen, wid):
    return (amp * wid**2) / ((x - cen)**2 + wid**2)
def pseudo_voigt(x, amp, cen, wid, eta):
    return eta * lorentzian(x, amp, cen, wid) + (1 - eta) * gaussian(x, amp, cen, wid)

def asymmetric_exciton(x, amp, cen, wid, eta, eu):
    eu = max(eu, 1e-5) 
    core = pseudo_voigt(x, amp, cen, wid, eta)
    tail = amp * np.exp((x - cen) / eu)
    return np.where(x >= cen, core, np.maximum(core, tail))

def linear_bg(x, m, b):
    return m * x + b

def sigmoid_step(x, amp, eg, dx):
    dx = max(dx, 1e-5)
    return amp / (1.0 + np.exp(-(x - eg) / dx))

def evaluate_total_model(x, params):
    p1_on, a1, c1, w1, e1, eu1, p2_on, a2, c2, w2, e2, eu2, m, b, bg_amp, eg, dx = params
    y = np.zeros_like(x)
    if p1_on:
        y += asymmetric_exciton(x, a1, c1, w1, e1, eu1)
    if p2_on:
        y += asymmetric_exciton(x, a2, c2, w2, e2, eu2)
    y += linear_bg(x, m, b)
    y += sigmoid_step(x, bg_amp, eg, dx)
    return y

# ==========================================
# INTERACTIVE GRAPHIC CANVAS
# ==========================================
class MplCanvas(FigureCanvas):
    def __init__(self, parent=None, width=6, height=5, dpi=100):
        fig = Figure(figsize=(width, height), dpi=dpi)
        self.axes = fig.add_subplot(111)
        super().__init__(fig)

# ==========================================
# MAIN DASHBOARD WIDGET
# ==========================================
class EAAbsorptionFitterDashboard(BaseModelingDashboard):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent_window = getattr(parent, 'parent_window', None)
        
        self.x_data = None
        self.y_data = None
        self.metadata = {}
        self._is_loading = False
        self.plot_mode = "standard"
        
        self.save_timer = QTimer(self)
        self.save_timer.setSingleShot(True)
        self.save_timer.setInterval(1000)
        self.save_timer.timeout.connect(self.save_parameters_to_session)
        
        self.slider_registry = {}
        self.build_ui()

    def build_ui(self):
        main_layout = QHBoxLayout(self)
        
        # Left Side Controls (Scrollable)
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_content = QWidget()
        controls_layout = QVBoxLayout(scroll_content)
        
        # --- Data Boundaries ---
        data_group = QGroupBox("Data Boundaries")
        data_lay = QVBoxLayout()
        # The data loading button from the standalone is removed since data comes from set_active_data
        
        range_lay = QHBoxLayout()
        range_lay.addWidget(QLabel("Min E (eV):"))
        self.spin_min_e = QDoubleSpinBox()
        self.spin_min_e.setRange(1.0, 4.0)
        self.spin_min_e.setValue(2.2)
        self.spin_min_e.setSingleStep(0.05)
        self.spin_min_e.valueChanged.connect(self.update_plots)
        range_lay.addWidget(self.spin_min_e)
        
        range_lay.addWidget(QLabel("Max E (eV):"))
        self.spin_max_e = QDoubleSpinBox()
        self.spin_max_e.setRange(1.0, 4.0)
        self.spin_max_e.setValue(3.1)
        self.spin_max_e.setSingleStep(0.05)
        self.spin_max_e.valueChanged.connect(self.update_plots)
        range_lay.addWidget(self.spin_max_e)
        data_lay.addLayout(range_lay)
        data_group.setLayout(data_lay)
        controls_layout.addWidget(data_group)

        # --- Background & Continuum ---
        bg_group = QGroupBox("Background & Bandgap Continuum")
        bg_lay = QVBoxLayout()
        self.bg_m = self.create_slider_row(bg_lay, "Slope (m):", -200, 200, -10, 0.01)
        self.bg_b = self.create_slider_row(bg_lay, "Intercept (b):", -500, 500, 40, 0.01)
        self.step_amp = self.create_slider_row(bg_lay, "Gap Step Amp:", 0, 400, 80, 0.01)
        self.step_eg = self.create_slider_row(bg_lay, "Bandgap Eg (eV):", 1500, 3500, 2830, 0.001)
        self.step_dx = self.create_slider_row(bg_lay, "Step Curve (dx):", 1, 200, 20, 0.001)
        bg_group.setLayout(bg_lay)
        controls_layout.addWidget(bg_group)

        # --- Peak 1 (Now with Urbach E) ---
        self.p1_group = QGroupBox("Exciton Peak 1 (Main)")
        self.p1_group.setCheckable(True)
        self.p1_group.setChecked(True)
        self.p1_group.toggled.connect(self.update_plots)
        p1_lay = QVBoxLayout()
        self.p1_amp = self.create_slider_row(p1_lay, "Amplitude:", 0, 500, 120, 0.01)
        self.p1_cen = self.create_slider_row(p1_lay, "Center (eV):", 1500, 3500, 2560, 0.001)
        self.p1_wid = self.create_slider_row(p1_lay, "Core Width:", 1, 200, 15, 0.001)
        self.p1_eta = self.create_slider_row(p1_lay, "Lorentz Mix (η):", 0, 100, 20, 0.01)
        self.p1_eu = self.create_slider_row(p1_lay, "Urbach E (eV):", 0, 200, 25, 0.001)
        self.p1_group.setLayout(p1_lay)
        controls_layout.addWidget(self.p1_group)

        # --- Peak 2 (Now with Urbach E) ---
        self.p2_group = QGroupBox("Exciton Peak 2 (Secondary)")
        self.p2_group.setCheckable(True)
        self.p2_group.setChecked(False)
        self.p2_group.toggled.connect(self.update_plots)
        p2_lay = QVBoxLayout()
        self.p2_amp = self.create_slider_row(p2_lay, "Amplitude:", 0, 500, 40, 0.01)
        self.p2_cen = self.create_slider_row(p2_lay, "Center (eV):", 1500, 3500, 2600, 0.001)
        self.p2_wid = self.create_slider_row(p2_lay, "Core Width:", 1, 200, 30, 0.001)
        self.p2_eta = self.create_slider_row(p2_lay, "Lorentz Mix (η):", 0, 100, 50, 0.01)
        self.p2_eu = self.create_slider_row(p2_lay, "Urbach E (eV):", 1, 200, 10, 0.001)
        self.p2_group.setLayout(p2_lay)
        controls_layout.addWidget(self.p2_group)

        self.btn_fit = QPushButton("Run Scipy Math Optimization")
        self.btn_fit.setStyleSheet("font-weight: bold; background-color: #2E7D32; color: white; padding: 10px;")
        self.btn_fit.clicked.connect(self.execute_fit)
        controls_layout.addWidget(self.btn_fit)
        
        # --- Derivative Toggle ---
        self.btn_toggle_plot = QPushButton("Toggle Derivative Plot")
        self.btn_toggle_plot.clicked.connect(self.toggle_plot_mode)
        controls_layout.addWidget(self.btn_toggle_plot)
        
        self.deriv_mix_group = QGroupBox("Derivative Scaling")
        deriv_lay = QVBoxLayout()
        self.deriv_1st_amp = self.create_slider_row(deriv_lay, "1st Deriv Amp:", 0, 500, 100, 0.01)
        self.deriv_2nd_amp = self.create_slider_row(deriv_lay, "2nd Deriv Amp:", 0, 500, 100, 0.01)
        
        self.chk_show_ea = QCheckBox("Show EA Data on Secondary Y-Axis")
        self.chk_show_ea.toggled.connect(self.update_plots)
        deriv_lay.addWidget(self.chk_show_ea)
        
        self.deriv_mix_group.setLayout(deriv_lay)
        controls_layout.addWidget(self.deriv_mix_group)
        self.deriv_mix_group.setVisible(False)
        
        self.lbl_results = QLabel("Adjust parameters visually. Watch the Urbach E slider alter the low-energy shoulder.")
        self.lbl_results.setWordWrap(True)
        controls_layout.addWidget(self.lbl_results)
        controls_layout.addStretch()
        
        scroll_area.setWidget(scroll_content)
        main_layout.addWidget(scroll_area, stretch=1)
        
        # Right Side: Canvas and Toolbar
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        
        self.canvas = MplCanvas(self, width=7, height=6)
        self.toolbar = NavigationToolbar(self.canvas, self)
        
        right_layout.addWidget(self.toolbar)
        right_layout.addWidget(self.canvas)
        
        main_layout.addWidget(right_widget, stretch=2)

    def create_slider_row(self, parent_layout, label_text, s_min, s_max, s_init, scale):
        row = QHBoxLayout()
        lbl = QLabel(label_text)
        lbl.setMinimumWidth(100)
        row.addWidget(lbl)
        
        slider = QSlider(Qt.Orientation.Horizontal)
        slider.setRange(s_min, s_max)
        slider.setValue(s_init)
        
        val_lbl = QLabel(f"{s_init * scale:.3f}")
        val_lbl.setMinimumWidth(50)
        lock_cb = QCheckBox("Lock")
        
        slider.valueChanged.connect(lambda v, l=val_lbl, sc=scale: l.setText(f"{v * sc:.3f}"))
        slider.valueChanged.connect(self.update_plots)
        lock_cb.toggled.connect(self.update_plots)
        
        row.addWidget(slider)
        row.addWidget(val_lbl)
        row.addWidget(lock_cb)
        parent_layout.addLayout(row)
        return {"slider": slider, "scale": scale, "label": val_lbl, "lock": lock_cb}

    def get_val(self, d): 
        return d["slider"].value() * d["scale"]

    def set_val(self, d, val):
        d["slider"].blockSignals(True)
        d["slider"].setValue(int(round(val / d["scale"])))
        d["label"].setText(f"{val:.3f}")
        d["slider"].blockSignals(False)

    def gather_all_parameters(self):
        return [
            self.p1_group.isChecked(),
            self.get_val(self.p1_amp), self.get_val(self.p1_cen), self.get_val(self.p1_wid), self.get_val(self.p1_eta), self.get_val(self.p1_eu),
            self.p2_group.isChecked(),
            self.get_val(self.p2_amp), self.get_val(self.p2_cen), self.get_val(self.p2_wid), self.get_val(self.p2_eta), self.get_val(self.p2_eu),
            self.get_val(self.bg_m), self.get_val(self.bg_b),
            self.get_val(self.step_amp), self.get_val(self.step_eg), self.get_val(self.step_dx)
        ]

    def set_active_data(self, x_data: np.ndarray, y_data: np.ndarray, metadata_dict: dict):
        self._is_loading = True
        self.metadata = metadata_dict
        self.ea_x_data = x_data
        self.ea_y_data = y_data

        
        try:
            from processors.factory import get_processor
            processor = get_processor("Absorption", self.parent_window)
            
            data_files = metadata_dict.get("data_files", {}).copy()
            if "transmission_file" in data_files and "sample_file" not in data_files:
                data_files["sample_file"] = data_files["transmission_file"]
            
            temp_metadata = metadata_dict.copy()
            temp_metadata["data_files"] = data_files
            settings = temp_metadata.get("analysis_settings", {})
            
            traces = processor._load_traces(temp_metadata, settings=settings)
            if traces:
                abs_x = traces[0]["wavelengths"]
                abs_y = traces[0]["absorbance"]
                abs_x, abs_y = processor._process_trace(abs_x, abs_y, settings, 0)
                self.x_data = abs_x
                self.y_data = abs_y
            else:
                self.x_data = x_data
                self.y_data = y_data
        except Exception:
            self.x_data = x_data
            self.y_data = y_data
        
        if self.x_data is not None and len(self.x_data) > 0:
            self.spin_min_e.setValue(float(np.min(self.x_data)))
            self.spin_max_e.setValue(float(np.max(self.x_data)))
            
        saved_data = self.metadata.get("analysis_settings", {}).get("ea_absorption_fitter_data")
        if saved_data:
            if "min_e" in saved_data:
                self.spin_min_e.setValue(saved_data["min_e"])
            if "max_e" in saved_data:
                self.spin_max_e.setValue(saved_data["max_e"])
                
            saved_params = saved_data.get("params")
            if saved_params and len(saved_params) == 17:
                p1_on, a1, c1, w1, e1, eu1, p2_on, a2, c2, w2, e2, eu2, m, b, bg_amp, eg, dx = saved_params
                self.p1_group.setChecked(p1_on)
                self.p2_group.setChecked(p2_on)
                
                widgets = [self.p1_amp, self.p1_cen, self.p1_wid, self.p1_eta, self.p1_eu,
                           self.p2_amp, self.p2_cen, self.p2_wid, self.p2_eta, self.p2_eu,
                           self.bg_m, self.bg_b, self.step_amp, self.step_eg, self.step_dx]
                
                vals = [a1, c1, w1, e1, eu1, a2, c2, w2, e2, eu2, m, b, bg_amp, eg, dx]
                for wdg, val in zip(widgets, vals):
                    self.set_val(wdg, val)
                    
        self._is_loading = False
        self.update_plots()

    def toggle_plot_mode(self):
        if self.plot_mode == "standard":
            self.plot_mode = "derivatives"
            self.btn_toggle_plot.setText("Switch to Standard Plot")
            self.deriv_mix_group.setVisible(True)
        else:
            self.plot_mode = "standard"
            self.btn_toggle_plot.setText("Toggle Derivative Plot")
            self.deriv_mix_group.setVisible(False)
        self.update_plots()

    def update_plots(self):
        if self.x_data is None or self.y_data is None:
            return
            
        min_e, max_e = self.spin_min_e.value(), self.spin_max_e.value()
        mask = (self.x_data >= min_e) & (self.x_data <= max_e)
        params = self.gather_all_parameters()
        p1_on, a1, c1, w1, e1, eu1, p2_on, a2, c2, w2, e2, eu2, m, b, bg_amp, eg, dx = params

        self.canvas.axes.cla()
        if hasattr(self, 'ax2') and self.ax2 is not None:
            try:
                self.ax2.remove()
            except Exception:
                pass
            self.ax2 = None
            
        if self.plot_mode == "standard":
            self.canvas.axes.plot(self.x_data, self.y_data, color='lightgray', label='Full Dataset')
            if np.any(mask):
                self.canvas.axes.scatter(self.x_data[mask], self.y_data[mask], color='black', s=5, alpha=0.4, label='Fit Region')

            x_smooth = np.linspace(min_e, max_e, 700)
            y_bg = linear_bg(x_smooth, m, b) + sigmoid_step(x_smooth, bg_amp, eg, dx)
            self.canvas.axes.plot(x_smooth, y_bg, color='orange', linestyle=':', linewidth=2, label='Background')
            
            if p1_on:
                self.canvas.axes.plot(x_smooth, asymmetric_exciton(x_smooth, a1, c1, w1, e1, eu1) + y_bg, 'b--', alpha=0.7, label='Peak 1 (w/ Tail)')
            if p2_on:
                self.canvas.axes.plot(x_smooth, asymmetric_exciton(x_smooth, a2, c2, w2, e2, eu2) + y_bg, 'g--', alpha=0.7, label='Peak 2 (w/ Tail)')

            y_total = evaluate_total_model(x_smooth, params)
            self.canvas.axes.plot(x_smooth, y_total, 'r-', linewidth=2.5, label='Total Model')

            self.canvas.axes.set_xlabel("Energy (eV)")
            self.canvas.axes.set_ylabel("Absorption (OD)")
            self.canvas.axes.set_xlim(min_e - 0.02, max_e + 0.02)
            self.canvas.axes.legend(loc='upper right')
        else:
            x_smooth = np.linspace(min_e, max_e, 700)
            y_total = evaluate_total_model(x_smooth, params)
            
            # Calculate derivatives
            dy = np.gradient(y_total, x_smooth)
            d2y = np.gradient(dy, x_smooth)
            
            # Normalize
            max_dy = np.max(np.abs(dy))
            max_d2y = np.max(np.abs(d2y))
            dy_norm = dy / max_dy if max_dy != 0 else dy
            d2y_norm = d2y / max_d2y if max_d2y != 0 else d2y
            
            amp1 = self.get_val(self.deriv_1st_amp)
            amp2 = self.get_val(self.deriv_2nd_amp)
            
            combined = amp1 * dy_norm + amp2 * d2y_norm
            
            self.canvas.axes.plot(x_smooth, amp1 * dy_norm, 'b--', alpha=0.5, label='1st Deriv')
            self.canvas.axes.plot(x_smooth, amp2 * d2y_norm, 'g--', alpha=0.5, label='2nd Deriv')
            self.canvas.axes.plot(x_smooth, combined, 'r-', linewidth=2.5, label=f'Mixed')
            self.canvas.axes.set_xlabel("Energy (eV)")
            self.canvas.axes.set_ylabel("Derivative Signal (Arbitrary)")
            self.canvas.axes.set_xlim(min_e - 0.02, max_e + 0.02)
            
            if self.chk_show_ea.isChecked() and hasattr(self, 'ea_x_data') and self.ea_x_data is not None:
                self.ax2 = self.canvas.axes.twinx()
                self.ax2.plot(self.ea_x_data, self.ea_y_data, color='gray', alpha=0.6, label='EA Data')
                self.ax2.set_ylabel("EA Data", color='gray')
                self.ax2.tick_params(axis='y', labelcolor='gray')
                
                # Align zeros
                y1_min, y1_max = self.canvas.axes.get_ylim()
                y2_min, y2_max = self.ax2.get_ylim()
                
                y1_min = min(y1_min, -1e-6)
                y2_min = min(y2_min, -1e-6)
                y1_max = max(y1_max, 1e-6)
                y2_max = max(y2_max, 1e-6)
                
                self.canvas.axes.set_ylim(y1_min, y1_max)
                self.ax2.set_ylim(y2_min, y2_max)

                ratio1 = y1_max / -y1_min
                ratio2 = y2_max / -y2_min
                
                if ratio1 > ratio2:
                    self.ax2.set_ylim(top=-y2_min * ratio1)
                else:
                    self.canvas.axes.set_ylim(top=-y1_min * ratio2)
                    
                y1_min, y1_max = self.canvas.axes.get_ylim()
                y2_min, y2_max = self.ax2.get_ylim()
                
                ratio1_neg = -y1_min / y1_max
                ratio2_neg = -y2_min / y2_max
                
                if ratio1_neg > ratio2_neg:
                    self.ax2.set_ylim(bottom=-y2_max * ratio1_neg)
                else:
                    self.canvas.axes.set_ylim(bottom=-y1_max * ratio2_neg)

                lines_1, labels_1 = self.canvas.axes.get_legend_handles_labels()
                lines_2, labels_2 = self.ax2.get_legend_handles_labels()
                self.canvas.axes.legend(lines_1 + lines_2, labels_1 + labels_2, loc='upper right')
            else:
                self.canvas.axes.legend(loc='upper right')
            
        self.canvas.draw()
        
        if not self._is_loading:
            self.save_timer.start()

    def save_parameters_to_session(self):
        if self._is_loading or not self.metadata:
            return
            
        if "analysis_settings" not in self.metadata:
            self.metadata["analysis_settings"] = {}
            
        self.metadata["analysis_settings"]["ea_absorption_fitter_data"] = {
            "min_e": self.spin_min_e.value(),
            "max_e": self.spin_max_e.value(),
            "params": self.gather_all_parameters()
        }
        
        try:
            from utils.project_manager import Session
            Session.save()
        except Exception:
            pass

    def execute_fit(self):
        if self.x_data is None or self.y_data is None:
            self.lbl_results.setText("No data available to fit.")
            return
            
        min_e, max_e = self.spin_min_e.value(), self.spin_max_e.value()
        mask = (self.x_data >= min_e) & (self.x_data <= max_e)
        x_fit, y_fit = self.x_data[mask], self.y_data[mask]

        if len(x_fit) == 0:
            self.lbl_results.setText("No data points in fit region.")
            return

        all_keys = ['a1', 'c1', 'w1', 'e1', 'eu1', 'a2', 'c2', 'w2', 'e2', 'eu2', 'm', 'b', 'bg_amp', 'eg', 'dx']
        widgets = [self.p1_amp, self.p1_cen, self.p1_wid, self.p1_eta, self.p1_eu,
                   self.p2_amp, self.p2_cen, self.p2_wid, self.p2_eta, self.p2_eu,
                   self.bg_m, self.bg_b, self.step_amp, self.step_eg, self.step_dx]
        
        p1_on, p2_on = self.p1_group.isChecked(), self.p2_group.isChecked()

        hard_bounds = {
            'a1': (0, np.inf), 'c1': (min_e, max_e), 'w1': (0.002, 0.4), 'e1': (0.0, 1.0), 'eu1': (0.001, 0.3),
            'a2': (0, np.inf), 'c2': (min_e, max_e), 'w2': (0.002, 0.4), 'e2': (0.0, 1.0), 'eu2': (0.001, 0.3),
            'm': (-10, 10), 'b': (-5, 5), 'bg_amp': (0, np.inf), 'eg': (min_e, max_e), 'dx': (0.002, 0.3)
        }

        free_names, p0_free, bounds_low, bounds_high, fixed_values = [], [], [], [], {}

        for key, wdg in zip(all_keys, widgets):
            if (key in ['a1', 'c1', 'w1', 'e1', 'eu1'] and not p1_on) or \
               (key in ['a2', 'c2', 'w2', 'e2', 'eu2'] and not p2_on):
                fixed_values[key] = 0.0
            elif wdg["lock"].isChecked():
                fixed_values[key] = self.get_val(wdg)
            else:
                free_names.append(key); p0_free.append(self.get_val(wdg))
                bounds_low.append(hard_bounds[key][0]); bounds_high.append(hard_bounds[key][1])

        if not free_names: 
            self.lbl_results.setText("Optimization Aborted: All parameter controls are locked.")
            return

        def scikit_fitting_target(x, *args):
            arg_list = list(args)
            eval_map = [fixed_values[k] if k in fixed_values else arg_list.pop(0) for k in all_keys]
            
            full_params = [p1_on, eval_map[0], eval_map[1], eval_map[2], eval_map[3], eval_map[4],
                           p2_on, eval_map[5], eval_map[6], eval_map[7], eval_map[8], eval_map[9],
                           eval_map[10], eval_map[11], eval_map[12], eval_map[13], eval_map[14]]
            return evaluate_total_model(x, full_params)

        try:
            popt, _ = curve_fit(scikit_fitting_target, x_fit, y_fit, p0=p0_free, bounds=(bounds_low, bounds_high))
            
            for name, opt_val in zip(free_names, popt):
                self.set_val(widgets[all_keys.index(name)], opt_val)

            summary = "<b>Fit Complete! Key Structural Parameters:</b><br>"
            if p1_on:
                summary += f"Peak 1: E={self.get_val(self.p1_cen):.3f} eV, <b>Urbach Energy (Eu) = {self.get_val(self.p1_eu)*1000:.1f} meV</b><br>"
            if p2_on:
                summary += f"Peak 2: E={self.get_val(self.p2_cen):.3f} eV, <b>Urbach Energy (Eu) = {self.get_val(self.p2_eu)*1000:.1f} meV</b><br>"
            self.lbl_results.setText(summary)
            self.update_plots()

        except Exception as e:
            self.lbl_results.setText(f"Fit failed: {str(e)}.<br>Try adjusting the sliders closer to the data.")

    def shutdown(self):
        # Clean up memory and widgets when destroyed
        self.canvas.axes.cla()
        self.x_data = None
        self.y_data = None
