import sys
import numpy as np
import pandas as pd
from scipy.optimize import curve_fit

from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QPushButton, QFileDialog, QSlider, 
                             QLabel, QCheckBox, QDoubleSpinBox, QGroupBox, QScrollArea)
from PyQt6.QtCore import Qt

import matplotlib
matplotlib.use('Qt5Agg')
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure

# ==========================================
# CORE MATHEMATICAL COMPONENTS
# ==========================================
def gaussian(x, amp, cen, wid):
    return amp * np.exp(-((x - cen) ** 2) / (2 * wid ** 2))

def lorentzian(x, amp, cen, wid):
    return (amp * wid**2) / ((x - cen)**2 + wid**2)

def pseudo_voigt(x, amp, cen, wid, eta):
    return eta * lorentzian(x, amp, cen, wid) + (1 - eta) * gaussian(x, amp, cen, wid)

def linear_bg(x, m, b):
    return m * x + b

def sigmoid_step(x, amp, eg, dx):
    """Models the step-like absorption onset of the bandgap continuum."""
    # Prevent divide by zero or extreme exponentials
    dx = max(dx, 1e-5)
    return amp / (1.0 + np.exp(-(x - eg) / dx))

def evaluate_total_model(x, params):
    """
    Evaluates the full combined physical system based on an explicit parameter map:
    params = [p1_on, a1, c1, w1, e1,  p2_on, a2, c2, w2, e2,  m, b, bg_amp, eg, dx]
    """
    p1_on, a1, c1, w1, e1, p2_on, a2, c2, w2, e2, m, b, bg_amp, eg, dx = params
    
    y = np.zeros_like(x)
    if p1_on:
        y += pseudo_voigt(x, a1, c1, w1, e1)
    if p2_on:
        y += pseudo_voigt(x, a2, c2, w2, e2)
        
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
# MAIN PYQT6 APPLICATION WINDOW
# ==========================================
class AdvancedExcitonFitter(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Interactive 15K Exciton & Continuum Fitter")
        
        # Initialize default synthetic data closely matching your 15K spectral profiles
        self.x_data = np.linspace(2.1, 3.3, 600)
        default_params = [True, 1.2, 2.56, 0.015, 0.4, False, 0.4, 2.60, 0.03, 0.5, -0.1, 0.5, 0.8, 2.83, 0.02]
        self.y_data = evaluate_total_model(self.x_data, default_params) + np.random.normal(0, 0.015, 600)
        
        self.slider_registry = {}
        self.init_ui()
        self.update_plots()

    def init_ui(self):
        main_widget = QWidget()
        main_layout = QHBoxLayout(main_widget)
        
        # Left Side: Scrollable Area for complex slider matrix
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_content = QWidget()
        controls_layout = QVBoxLayout(scroll_content)
        
        # --- Group 1: File Input & Boundaries ---
        data_group = QGroupBox("Data Boundaries")
        data_lay = QVBoxLayout()
        self.btn_load = QPushButton("Load CSV Spectral File")
        self.btn_load.clicked.connect(self.load_file)
        data_lay.addWidget(self.btn_load)
        
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
        self.spin_max_e.setValue(3.2)
        self.spin_max_e.setSingleStep(0.05)
        self.spin_max_e.valueChanged.connect(self.update_plots)
        range_lay.addWidget(self.spin_max_e)
        data_lay.addLayout(range_lay)
        data_group.setLayout(data_lay)
        controls_layout.addWidget(data_group)

        # --- Group 2: Background & Continuum ---
        bg_group = QGroupBox("Background & Bandgap Continuum")
        bg_lay = QVBoxLayout()
        self.bg_m = self.create_slider_row(bg_lay, "Slope (m):", -200, 200, -10, 0.01)
        self.bg_b = self.create_slider_row(bg_lay, "Intercept (b):", -200, 500, 40, 0.01)
        self.step_amp = self.create_slider_row(bg_lay, "Gap Step Amp:", 0, 400, 80, 0.01)
        self.step_eg = self.create_slider_row(bg_lay, "Bandgap Eg (eV):", 1500, 3500, 2830, 0.001)
        self.step_dx = self.create_slider_row(bg_lay, "Step Curve (dx):", 1, 200, 20, 0.001)
        bg_group.setLayout(bg_lay)
        controls_layout.addWidget(bg_group)

        # --- Group 3: Peak 1 ---
        self.p1_group = QGroupBox("Exciton Peak 1")
        self.p1_group.setCheckable(True)
        self.p1_group.setChecked(True)
        self.p1_group.toggled.connect(self.update_plots)
        p1_lay = QVBoxLayout()
        self.p1_amp = self.create_slider_row(p1_lay, "Amplitude:", 0, 500, 120, 0.01)
        self.p1_cen = self.create_slider_row(p1_lay, "Center (eV):", 1500, 3500, 2560, 0.001)
        self.p1_wid = self.create_slider_row(p1_lay, "Width (eV):", 1, 200, 15, 0.001)
        self.p1_eta = self.create_slider_row(p1_lay, "Lorentz Mix (η):", 0, 100, 40, 0.01)
        self.p1_group.setLayout(p1_lay)
        controls_layout.addWidget(self.p1_group)

        # --- Group 4: Peak 2 ---
        self.p2_group = QGroupBox("Exciton Peak 2")
        self.p2_group.setCheckable(True)
        self.p2_group.setChecked(False)
        self.p2_group.toggled.connect(self.update_plots)
        p2_lay = QVBoxLayout()
        self.p2_amp = self.create_slider_row(p2_lay, "Amplitude:", 0, 500, 40, 0.01)
        self.p2_cen = self.create_slider_row(p2_lay, "Center (eV):", 1500, 3500, 2600, 0.001)
        self.p2_wid = self.create_slider_row(p2_lay, "Width (eV):", 1, 200, 30, 0.001)
        self.p2_eta = self.create_slider_row(p2_lay, "Lorentz Mix (η):", 0, 100, 50, 0.01)
        self.p2_group.setLayout(p2_lay)
        controls_layout.addWidget(self.p2_group)

        # --- Fitting Execution Trigger ---
        self.btn_fit = QPushButton("Run Scipy Math Optimization")
        self.btn_fit.setStyleSheet("font-weight: bold; background-color: #2E7D32; color: white; padding: 10px;")
        self.btn_fit.clicked.connect(self.execute_fit)
        controls_layout.addWidget(self.btn_fit)
        
        self.lbl_results = QLabel("Adjust parameters visually to build initial guesses.")
        self.lbl_results.setWordWrap(True)
        controls_layout.addWidget(self.lbl_results)
        controls_layout.addStretch()
        
        scroll_area.setWidget(scroll_content)
        main_layout.addWidget(scroll_area, stretch=1)
        
        # Right Side: Plot Display Canvas
        self.canvas = MplCanvas(self, width=7, height=6)
        main_layout.addWidget(self.canvas, stretch=2)
        
        self.setCentralWidget(main_widget)
        self.resize(1200, 800)

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
        lock_cb.setToolTip("Freeze this parameter during math optimization fits")
        
        slider.valueChanged.connect(lambda v: val_lbl.setText(f"{v * scale:.3f}"))
        slider.valueChanged.connect(self.update_plots)
        lock_cb.toggled.connect(self.update_plots)
        
        row.addWidget(slider)
        row.addWidget(val_lbl)
        row.addWidget(lock_cb)
        parent_layout.addLayout(row)
        
        row_dict = {"slider": slider, "scale": scale, "label": val_lbl, "lock": lock_cb}
        return row_dict

    def get_val(self, d):
        return d["slider"].value() * d["scale"]

    def set_val(self, d, val):
        d["slider"].blockSignals(True)
        int_val = int(round(val / d["scale"]))
        d["slider"].setValue(int_val)
        d["label"].setText(f"{val:.3f}")
        d["slider"].blockSignals(False)

    def gather_all_parameters(self):
        """Returns parameters in order mapped to evaluate_total_model."""
        return [
            self.p1_group.isChecked(),
            self.get_val(self.p1_amp), self.get_val(self.p1_cen), self.get_val(self.p1_wid), self.get_val(self.p1_eta),
            self.p2_group.isChecked(),
            self.get_val(self.p2_amp), self.get_val(self.p2_cen), self.get_val(self.p2_wid), self.get_val(self.p2_eta),
            self.get_val(self.bg_m), self.get_val(self.bg_b),
            self.get_val(self.step_amp), self.get_val(self.step_eg), self.get_val(self.step_dx)
        ]

    def load_file(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Open Data CSV", "", "CSV Files (*.csv)")
        if file_path:
            try:
                df = pd.read_csv(file_path)
                self.x_data = df['Energy (eV)'].values
                self.y_data = df['Absorption (OD)'].values
                self.spin_min_e.setValue(np.min(self.x_data))
                self.spin_max_e.setValue(np.max(self.x_data))
                self.update_plots()
                self.lbl_results.setText("Loaded target dataset successfully.")
            except Exception as e:
                self.lbl_results.setText(f"File loading failure: {str(e)}")

    def update_plots(self):
        min_e, max_e = self.spin_min_e.value(), self.spin_max_e.value()
        mask = (self.x_data >= min_e) & (self.x_data <= max_e)
        
        params = self.gather_all_parameters()
        p1_on, a1, c1, w1, e1, p2_on, a2, c2, w2, e2, m, b, bg_amp, eg, dx = params

        self.canvas.axes.cla()
        
        # 1. Plot Experimental Raw Data
        self.canvas.axes.plot(self.x_data, self.y_data, color='lightgray', label='Full Dataset')
        self.canvas.axes.scatter(self.x_data[mask], self.y_data[mask], color='black', s=5, alpha=0.4, label='Fit Region')

        # 2. Deconvolute Subcomponents across smooth domain
        x_smooth = np.linspace(min_e, max_e, 700)
        
        # Plot isolated baseline background (Linear + Sigmoid Step)
        y_bg_total = linear_bg(x_smooth, m, b) + sigmoid_step(x_smooth, bg_amp, eg, dx)
        self.canvas.axes.plot(x_smooth, y_bg_total, color='orange', linestyle=':', linewidth=2, label='Total Background Tail')
        
        if p1_on:
            self.canvas.axes.plot(x_smooth, pseudo_voigt(x_smooth, a1, c1, w1, e1) + y_bg_total, 'b--', alpha=0.7, label='Peak 1 + BG')
        if p2_on:
            self.canvas.axes.plot(x_smooth, pseudo_voigt(x_smooth, a2, c2, w2, e2) + y_bg_total, 'g--', alpha=0.7, label='Peak 2 + BG')

        # 3. Combined Total Fit Curve
        y_total = evaluate_total_model(x_smooth, params)
        self.canvas.axes.plot(x_smooth, y_total, 'r-', linewidth=2.5, label='Total Combined Model')

        self.canvas.axes.set_xlabel("Energy (eV)")
        self.canvas.axes.set_ylabel("Absorption (OD)")
        self.canvas.axes.set_xlim(min_e - 0.02, max_e + 0.02)
        self.canvas.axes.legend(loc='upper right')
        self.canvas.draw()

    def execute_fit(self):
        min_e, max_e = self.spin_min_e.value(), self.spin_max_e.value()
        mask = (self.x_data >= min_e) & (self.x_data <= max_e)
        x_fit, y_fit = self.x_data[mask], self.y_data[mask]

        # Define explicit order arrays mapping slider entries
        all_keys = ['a1', 'c1', 'w1', 'e1', 'a2', 'c2', 'w2', 'e2', 'm', 'b', 'bg_amp', 'eg', 'dx']
        widgets = [self.p1_amp, self.p1_cen, self.p1_wid, self.p1_eta,
                   self.p2_amp, self.p2_cen, self.p2_wid, self.p2_eta,
                   self.bg_m, self.bg_b, self.step_amp, self.step_eg, self.step_dx]
        
        p1_on = self.p1_group.isChecked()
        p2_on = self.p2_group.isChecked()

        # Fallback absolute fitting constraints 
        hard_bounds = {
            'a1': (0, np.inf), 'c1': (min_e, max_e), 'w1': (0.002, 0.4), 'e1': (0.0, 1.0),
            'a2': (0, np.inf), 'c2': (min_e, max_e), 'w2': (0.002, 0.4), 'e2': (0.0, 1.0),
            'm': (-10, 10), 'b': (-5, 5), 'bg_amp': (0, np.inf), 'eg': (min_e, max_e), 'dx': (0.002, 0.3)
        }

        free_names = []
        p0_free = []
        bounds_low = []
        bounds_high = []
        fixed_values = {}

        # Sort variables into dynamic Free vs Fixed lists based on UI states
        for key, wdg in zip(all_keys, widgets):
            is_peak1_param = key in ['a1', 'c1', 'w1', 'e1']
            is_peak2_param = key in ['a2', 'c2', 'w2', 'e2']
            
            # If parent peak group is disabled, force its values to zero and lock them
            if (is_peak1_param and not p1_on) or (is_peak2_param and not p2_on):
                fixed_values[key] = 0.0
            elif wdg["lock"].isChecked():
                fixed_values[key] = self.get_val(wdg)
            else:
                free_names.append(key)
                p0_free.append(self.get_val(wdg))
                bounds_low.append(hard_bounds[key][0])
                bounds_high.append(hard_bounds[key][1])

        if not free_names:
            self.lbl_results.setText("Optimization Aborted: All parameter controls are locked.")
            return

        # Core operational wrapper function processed dynamically by curve_fit
        def scikit_fitting_target(x, *args):
            arg_list = list(args)
            eval_map = []
            free_idx = 0
            
            for key in all_keys:
                if key in fixed_values:
                    eval_map.append(fixed_values[key])
                else:
                    eval_map.append(arg_list[free_idx])
                    free_idx += 1
            
            # Reconstruct the vector structural array expected by model
            full_params = [p1_on, eval_map[0], eval_map[1], eval_map[2], eval_map[3],
                           p2_on, eval_map[4], eval_map[5], eval_map[6], eval_map[7],
                           eval_map[8], eval_map[9], eval_map[10], eval_map[11], eval_map[12]]
            return evaluate_total_model(x, full_params)

        try:
            popt, _ = curve_fit(scikit_fitting_target, x_fit, y_fit, p0=p0_free, bounds=(bounds_low, bounds_high))
            
            # Map optimized results back onto free sliders
            for name, opt_val in zip(free_names, popt):
                wdg_item = widgets[all_keys.index(name)]
                self.set_val(wdg_item, opt_val)

            summary = "<b>Optimized Fit Output Parameters:</b><br>"
            if p1_on:
                summary += f"Peak 1: E={self.get_val(self.p1_cen):.3f} eV, Amp={self.get_val(self.p1_amp):.3f}, η={self.get_val(self.p1_eta):.2f}<br>"
            if p2_on:
                summary += f"Peak 2: E={self.get_val(self.p2_cen):.3f} eV, Amp={self.get_val(self.p2_amp):.3f}, η={self.get_val(self.p2_eta):.2f}<br>"
            summary += f"Bandgap Onset (Eg): {self.get_val(self.step_eg):.3f} eV"
            
            self.lbl_results.setText(summary)
            self.update_plots()

        except Exception as e:
            self.lbl_results.setText(f"Fit failed to converge: {str(e)}.<br>Refine baseline sliders manually before refitting.")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = AdvancedExcitonFitter()
    window.show()
    sys.exit(app.exec())