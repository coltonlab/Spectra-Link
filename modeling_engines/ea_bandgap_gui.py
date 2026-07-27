import sys
import numpy as np
import pandas as pd
from scipy.special import airy
from scipy.ndimage import gaussian_filter1d
from scipy.optimize import minimize

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QSlider, QGroupBox, QGridLayout, QPushButton, QFileDialog,
    QCheckBox, QMessageBox, QScrollArea
)
from PyQt6.QtCore import Qt

import matplotlib
matplotlib.use('QtAgg')
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
import matplotlib.cm as cm

class EAFitCanvas(FigureCanvas):
    def __init__(self, parent=None, width=7, height=6, dpi=100):
        self.fig = Figure(figsize=(width, height), dpi=dpi)
        super().__init__(self.fig)
        self.setParent(parent)

    def plot_data_and_fit(self, energy, ea_dict, active_fields, Eg, m_eff, gamma, scale, fit_emin, fit_emax, flip_phase=False):
        self.fig.clear()
        ax = self.fig.add_subplot(111)
        
        if energy is None or len(ea_dict) == 0:
            ax.text(0.5, 0.5, "Please Load a CSV File", ha='center', va='center', fontsize=14)
            self.draw()
            return

        # Handle Phase Inversion
        phase_mult = -1.0 if flip_phase else 1.0

        # Physical constants
        hbar = 6.582119569e-16  # eV*s
        e = 1.602176634e-19      # C
        m0 = 9.1093837015e-31    # kg
        m_kg = m_eff * m0
        
        # Extended energy array to prevent edge convolution artifacts
        dE = np.mean(np.diff(energy))
        pad_len = 100
        energy_ext = np.concatenate([
            np.linspace(energy[0] - pad_len*dE, energy[0] - dE, pad_len),
            energy,
            np.linspace(energy[-1] + dE, energy[-1] + pad_len*dE, pad_len)
        ])

        all_fields = sorted(ea_dict.keys())
        colors = cm.get_cmap('plasma')(np.linspace(0.15, 0.85, len(all_fields)))

        for idx, F_kv in enumerate(all_fields):
            # Skip field if untoggled
            if F_kv not in active_fields:
                continue

            ea_raw = ea_dict[F_kv]
            ea_exp = ea_raw * phase_mult
            
            # --- MODEL CALCULATION ---
            F = F_kv * 1e5  # V/m
            hbar_theta_J = ((hbar * 1.60218e-19)**2 * (e * F)**2 / (2 * m_kg))**(1/3)
            hbar_theta = hbar_theta_J / 1.60218e-19  # eV
            
            eta = (Eg - energy_ext) / hbar_theta
            ai, aip, _, _ = airy(eta)
            
            baseline = np.where(eta < 0, np.sqrt(np.maximum(-eta, 0)) / np.pi, 0.0)
            delta_alpha_raw = (aip**2 - eta * ai**2) - baseline
            
            sigma_px = (gamma / 1000.0) / dE
            delta_alpha_ext = gaussian_filter1d(delta_alpha_raw, sigma=max(sigma_px, 0.1))
            
            # Crop padding
            delta_alpha = delta_alpha_ext[pad_len:-pad_len]
            ea_model = scale * delta_alpha

            # Scatter experimental data points
            ax.plot(energy, ea_exp, color=colors[idx], alpha=0.25, label=f'{F_kv:.0f} kV/cm (Data)')
            # Plot smooth theoretical model fit line
            ax.plot(energy, ea_model, color=colors[idx], linewidth=2.0, linestyle='--')

        # Vertical line for Band Gap Eg
        ax.axvline(Eg, color='black', linestyle=':', linewidth=1.5, label=f'$E_G$ = {Eg:.3f} eV')
        
        # Highlight Fit Range Window with vertical red lines
        ax.axvline(fit_emin, color='red', linestyle='--', linewidth=1.0, alpha=0.7, label='Fit Window')
        ax.axvline(fit_emax, color='red', linestyle='--', linewidth=1.0, alpha=0.7)
        ax.axvspan(fit_emin, fit_emax, color='red', alpha=0.05)

        ax.axhline(0, color='gray', linestyle='-', linewidth=0.8, alpha=0.7)

        # Labels and formatting
        ax.set_xlabel('Photon Energy (eV)', fontsize=11, fontweight='bold')
        ax.set_ylabel('$\Delta A$ (mOD)', fontsize=11, fontweight='bold')
        ax.tick_params(direction='in', top=True, right=True, labelsize=10)
        ax.legend(bbox_to_anchor=(1.02, 1), loc='upper left', fontsize=9)

        self.fig.tight_layout()
        self.draw()


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Franz-Keldysh Experimental EA Data Fitter")
        self.resize(1200, 800)

        # Data storage
        self.energy = None
        self.absorption = None
        self.ea_dict = {}
        self.voltage_checkboxes = {}

        # Main Layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)

        # Plot Canvas
        self.canvas = EAFitCanvas(self, width=7, height=6)
        main_layout.addWidget(self.canvas, stretch=3)

        # Control Panel Sidebar
        control_panel = QWidget()
        control_layout = QVBoxLayout(control_panel)

        # 1. File Loader Box
        file_group = QGroupBox("1. Load Data")
        file_layout = QVBoxLayout()
        self.btn_load = QPushButton("Open CSV File")
        self.btn_load.clicked.connect(self.load_file)
        self.lbl_file = QLabel("No file loaded.")
        self.lbl_file.setWordWrap(True)
        file_layout.addWidget(self.btn_load)
        file_layout.addWidget(self.lbl_file)
        file_group.setLayout(file_layout)
        control_layout.addWidget(file_group)

        # 2. Controls & Parameters
        controls_group = QGroupBox("2. Model Controls")
        controls_grid = QGridLayout()

        # Phase Flip Checkbox
        self.chk_flip = QCheckBox("Invert Lock-in Phase (180° Flip)")
        self.chk_flip.stateChanged.connect(self.update_plot)
        controls_grid.addWidget(self.chk_flip, 0, 0, 1, 2)

        # Interactive Sliders
        self.slider_eg = self._create_slider(200, 450, 350, controls_grid, 1, "Bandgap Energy $E_G$ (eV):", lambda v: f"{v/100:.3f} eV")
        self.slider_meff = self._create_slider(1, 100, 15, controls_grid, 2, "Effective Mass $m^*$ ($m_0$):", lambda v: f"{v/100:.2f} m₀")
        self.slider_gamma = self._create_slider(1, 100, 20, controls_grid, 3, "Broadening $\Gamma$ (meV):", lambda v: f"{v} meV")
        self.slider_scale = self._create_slider(1, 20000, 500, controls_grid, 4, "Amplitude Scale:", lambda v: f"{v/10:.1f}")

        controls_group.setLayout(controls_grid)
        control_layout.addWidget(controls_group)

        # 3. Fit Energy Range Selection Box
        range_group = QGroupBox("3. Fit Energy Window")
        range_grid = QGridLayout()
        self.slider_emin = self._create_slider(200, 450, 340, range_grid, 0, "Fit Range Min (eV):", lambda v: f"{v/100:.3f} eV")
        self.slider_emax = self._create_slider(200, 450, 360, range_grid, 1, "Fit Range Max (eV):", lambda v: f"{v/100:.3f} eV")
        range_group.setLayout(range_grid)
        control_layout.addWidget(range_group)

        # 4. Auto-Fit Button
        self.btn_fit = QPushButton("Auto-Fit Parameters to Window")
        self.btn_fit.setStyleSheet("font-weight: bold; background-color: #007ACC; color: white; padding: 8px;")
        self.btn_fit.clicked.connect(self.run_auto_fit)
        control_layout.addWidget(self.btn_fit)

        # 5. Voltage Toggles Group (Under Auto-Fit Button)
        self.voltage_group = QGroupBox("4. Active Voltages")
        self.voltage_layout = QGridLayout()
        self.voltage_group.setLayout(self.voltage_layout)
        control_layout.addWidget(self.voltage_group)

        control_layout.addStretch()
        main_layout.addWidget(control_panel, stretch=1)

    def _create_slider(self, min_v, max_v, default, layout, row, label_text, formatter):
        lbl = QLabel(label_text)
        val_lbl = QLabel(formatter(default))
        slider = QSlider(Qt.Orientation.Horizontal)
        slider.setRange(min_v, max_v)
        slider.setValue(default)
        
        def on_change(val):
            val_lbl.setText(formatter(val))
            self.update_plot()

        slider.valueChanged.connect(on_change)
        layout.addWidget(lbl, row * 2, 0)
        layout.addWidget(val_lbl, row * 2, 1)
        layout.addWidget(slider, row * 2 + 1, 0, 1, 2)
        
        slider.val_lbl = val_lbl
        slider.formatter = formatter
        return slider

    def load_file(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Open EA Data CSV", "", "CSV Files (*.csv);;All Files (*)")
        if file_path:
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
                
                self.lbl_file.setText(f"Loaded: {file_path.split('/')[-1]}\nEnergy Range: {self.energy[0]:.2f} - {self.energy[-1]:.2f} eV")
                
                # Auto-adjust energy sliders range
                min_idx = int(self.energy[0] * 100)
                max_idx = int(self.energy[-1] * 100)
                mid_idx = int(np.mean(self.energy) * 100)
                
                for s in [self.slider_eg, self.slider_emin, self.slider_emax]:
                    s.setRange(min_idx, max_idx)

                self.slider_eg.setValue(mid_idx)
                self.slider_emin.setValue(min_idx)
                self.slider_emax.setValue(max_idx)

                # Rebuild Voltage Toggle Checkboxes
                self._build_voltage_toggles()

                self.update_plot()

            except Exception as e:
                QMessageBox.critical(self, "Error Loading File", f"Could not parse file header/data.\nDetails: {str(e)}")

    def _build_voltage_toggles(self):
        # Clear old checkboxes
        for cb in self.voltage_checkboxes.values():
            cb.deleteLater()
        self.voltage_checkboxes.clear()

        # Populate new checkboxes in a grid layout
        sorted_fields = sorted(self.ea_dict.keys())
        for idx, F_kv in enumerate(sorted_fields):
            cb = QCheckBox(f"{F_kv:.0f} kV/cm")
            cb.setChecked(True)
            cb.stateChanged.connect(self.update_plot)
            
            row = idx // 2
            col = idx % 2
            self.voltage_layout.addWidget(cb, row, col)
            self.voltage_checkboxes[F_kv] = cb

    def _get_active_fields(self):
        return [F_kv for F_kv, cb in self.voltage_checkboxes.items() if cb.isChecked()]

    def update_plot(self):
        if self.energy is None:
            return
            
        Eg = self.slider_eg.value() / 100.0
        m_eff = self.slider_meff.value() / 100.0
        gamma = self.slider_gamma.value()
        scale = self.slider_scale.value() / 10.0
        fit_emin = self.slider_emin.value() / 100.0
        fit_emax = self.slider_emax.value() / 100.0
        flip_phase = self.chk_flip.isChecked()
        active_fields = self._get_active_fields()

        self.canvas.plot_data_and_fit(
            self.energy, self.ea_dict, active_fields, Eg, m_eff, gamma, scale, fit_emin, fit_emax, flip_phase
        )

    def run_auto_fit(self):
        if self.energy is None or len(self.ea_dict) == 0:
            QMessageBox.warning(self, "No Data", "Please load a CSV file first before auto-fitting.")
            return

        active_fields = self._get_active_fields()
        if len(active_fields) == 0:
            QMessageBox.warning(self, "No Active Voltages", "Please toggle ON at least one voltage to fit.")
            return

        # Read Current Slider Settings
        init_Eg = self.slider_eg.value() / 100.0
        init_m = self.slider_meff.value() / 100.0
        init_gamma = float(self.slider_gamma.value())
        init_scale = self.slider_scale.value() / 10.0
        fit_emin = self.slider_emin.value() / 100.0
        fit_emax = self.slider_emax.value() / 100.0
        flip_phase = self.chk_flip.isChecked()
        phase_mult = -1.0 if flip_phase else 1.0

        # Create mask for fit window
        fit_mask = (self.energy >= fit_emin) & (self.energy <= fit_emax)
        if not np.any(fit_mask):
            QMessageBox.warning(self, "Invalid Range", "Selected fit energy range contains no data points.")
            return

        # Physical constants
        hbar = 6.582119569e-16
        e = 1.602176634e-19
        m0 = 9.1093837015e-31
        
        dE = np.mean(np.diff(self.energy))
        pad_len = 100
        energy_ext = np.concatenate([
            np.linspace(self.energy[0] - pad_len*dE, self.energy[0] - dE, pad_len),
            self.energy,
            np.linspace(self.energy[-1] + dE, self.energy[-1] + pad_len*dE, pad_len)
        ])

        def objective_function(params):
            Eg, m_eff, gamma, scale = params
            m_kg = m_eff * m0
            total_error = 0.0

            # ONLY fit across turned-ON active fields
            for F_kv in active_fields:
                ea_raw = self.ea_dict[F_kv]
                ea_exp_window = (ea_raw * phase_mult)[fit_mask]
                F = F_kv * 1e5
                hbar_theta_J = ((hbar * 1.60218e-19)**2 * (e * F)**2 / (2 * m_kg))**(1/3)
                hbar_theta = hbar_theta_J / 1.60218e-19
                
                eta = (Eg - energy_ext) / hbar_theta
                ai, aip, _, _ = airy(eta)
                baseline = np.where(eta < 0, np.sqrt(np.maximum(-eta, 0)) / np.pi, 0.0)
                delta_alpha_raw = (aip**2 - eta * ai**2) - baseline
                
                sigma_px = (gamma / 1000.0) / dE
                delta_alpha_ext = gaussian_filter1d(delta_alpha_raw, sigma=max(sigma_px, 0.1))
                delta_alpha = delta_alpha_ext[pad_len:-pad_len]
                
                model_ea_window = (scale * delta_alpha)[fit_mask]
                total_error += np.sum((ea_exp_window - model_ea_window)**2)

            return total_error

        bounds = [
            (fit_emin, fit_emax),
            (0.01, 2.0),
            (1.0, 100.0),
            (0.01, 2000.0)
        ]

        res = minimize(objective_function, [init_Eg, init_m, init_gamma, init_scale], bounds=bounds, method='L-BFGS-B')

        if res.success:
            opt_Eg, opt_m, opt_gamma, opt_scale = res.x
            
            # Update Model Control Sliders and Labels Live
            self.slider_eg.setValue(int(opt_Eg * 100))
            self.slider_eg.val_lbl.setText(self.slider_eg.formatter(int(opt_Eg * 100)))

            self.slider_meff.setValue(int(opt_m * 100))
            self.slider_meff.val_lbl.setText(self.slider_meff.formatter(int(opt_m * 100)))

            self.slider_gamma.setValue(int(opt_gamma))
            self.slider_gamma.val_lbl.setText(self.slider_gamma.formatter(int(opt_gamma)))

            self.slider_scale.setValue(int(opt_scale * 10))
            self.slider_scale.val_lbl.setText(self.slider_scale.formatter(int(opt_scale * 10)))

            self.update_plot()
            QMessageBox.information(
                self, 
                "Fit Complete", 
                f"Optimal Parameters Extracted ({len(active_fields)} Voltages):\n\n"
                f"Bandgap Eg = {opt_Eg:.4f} eV\n"
                f"Effective Mass m* = {opt_m:.3f} m0\n"
                f"Broadening Gamma = {opt_gamma:.2f} meV\n"
                f"Amplitude Scale = {opt_scale:.1f}"
            )


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())