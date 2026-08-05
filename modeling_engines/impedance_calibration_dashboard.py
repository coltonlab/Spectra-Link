import numpy as np
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QCheckBox, QComboBox,
    QPushButton, QLabel, QSizePolicy, QFrame, QDoubleSpinBox
)
from PyQt6.QtCore import Qt

from modeling_engines.base_modeling_dashboard import BaseModelingDashboard
from config.techniques import SCAN_TYPE_COLORS
from utils.app_logger import logger


class ImpedanceCalibrationDashboard(BaseModelingDashboard):
    """
    Modeling dashboard for impedance calibration experiments.
    Provides controls to toggle individual impedance traces and plot percent error
    between two selected traces.
    """

    TRACE_TYPES = [
        "Open",
        "Short",
        "Load",
        "Known Load",
        "Sample",
        "Sample 2",
        "Calibrated Sample",
    ]

    def __init__(self, parent=None):
        super().__init__(parent)
        self.traces = []
        self.metadata = {}
        self._active_plot = None
        self.build_ui()

    def build_ui(self):
        self.setLayout(QHBoxLayout())
        self.layout().setContentsMargins(8, 8, 8, 8)
        self.layout().setSpacing(12)

        # Left: Plot area
        plot_frame = QVBoxLayout()
        self.figure = Figure(layout="constrained", facecolor="white")
        self.canvas = FigureCanvas(self.figure)
        self.canvas.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

        self.status_label = QLabel("Choose traces to display and enable percent error if needed.")
        self.status_label.setWordWrap(True)
        self.status_label.setStyleSheet("color: gray;")

        # Footer area: status on left, average percent-error on right
        footer = QFrame()
        footer.setLayout(QHBoxLayout())
        footer.layout().setContentsMargins(0, 0, 0, 0)
        footer.layout().setSpacing(6)

        self.avg_error_label = QLabel("Avg % Error: N/A")
        self.avg_error_label.setStyleSheet("color: darkred; font-weight: 600;")
        self.avg_error_label.setAlignment(Qt.AlignmentFlag.AlignRight)

        footer.layout().addWidget(self.status_label, stretch=1)
        footer.layout().addWidget(self.avg_error_label, stretch=0)

        plot_frame.addWidget(self.canvas, stretch=1)
        plot_frame.addWidget(footer)

        # Right: Controls
        control_frame = QFrame()
        control_frame.setLayout(QVBoxLayout())
        control_frame.layout().setContentsMargins(0, 0, 0, 0)
        control_frame.layout().setSpacing(8)

        control_frame.layout().addWidget(QLabel("<b>Trace Visibility</b>"))
        self.trace_checkboxes = {}
        for trace_type in self.TRACE_TYPES:
            checkbox = QCheckBox(trace_type)
            checkbox.setChecked(True)
            checkbox.stateChanged.connect(self._on_plot_settings_changed)
            self.trace_checkboxes[trace_type] = checkbox
            control_frame.layout().addWidget(checkbox)

        control_frame.layout().addSpacing(12)
        control_frame.layout().addWidget(QLabel("<b>Frequency Range</b>"))

        self.min_freq_spin = QDoubleSpinBox()
        self.min_freq_spin.setRange(0.0, 1e12)
        self.min_freq_spin.setDecimals(2)
        self.min_freq_spin.setSingleStep(1.0)
        self.min_freq_spin.setSpecialValueText("Auto")
        self.min_freq_spin.setValue(0.0)
        self.min_freq_spin.valueChanged.connect(self._on_plot_settings_changed)
        control_frame.layout().addWidget(QLabel("Min Frequency (Hz)"))
        control_frame.layout().addWidget(self.min_freq_spin)

        self.max_freq_spin = QDoubleSpinBox()
        self.max_freq_spin.setRange(0.0, 1e12)
        self.max_freq_spin.setDecimals(2)
        self.max_freq_spin.setSingleStep(1.0)
        self.max_freq_spin.setSpecialValueText("Auto")
        self.max_freq_spin.setValue(0.0)
        self.max_freq_spin.valueChanged.connect(self._on_plot_settings_changed)
        control_frame.layout().addWidget(QLabel("Max Frequency (Hz)"))
        control_frame.layout().addWidget(self.max_freq_spin)

        control_frame.layout().addSpacing(12)
        control_frame.layout().addWidget(QLabel("<b>Percent Error Options</b>"))

        self.percent_error_checkbox = QCheckBox("Show Percent Error")
        self.percent_error_checkbox.stateChanged.connect(self._on_plot_settings_changed)
        control_frame.layout().addWidget(self.percent_error_checkbox)

        control_frame.layout().addWidget(QLabel("Reference Trace"))
        self.reference_combo = QComboBox()
        self.reference_combo.currentIndexChanged.connect(self._on_plot_settings_changed)
        control_frame.layout().addWidget(self.reference_combo)

        control_frame.layout().addWidget(QLabel("Test Trace"))
        self.test_combo = QComboBox()
        self.test_combo.currentIndexChanged.connect(self._on_plot_settings_changed)
        control_frame.layout().addWidget(self.test_combo)

        self.refresh_button = QPushButton("Refresh Plot")
        self.refresh_button.clicked.connect(self._refresh_plot)
        control_frame.layout().addWidget(self.refresh_button)
        control_frame.layout().addStretch()

        self.layout().addLayout(plot_frame, stretch=4)
        self.layout().addWidget(control_frame, stretch=1)

    def set_active_data(self, x_data: np.ndarray, y_data: np.ndarray, metadata_dict: dict):
        """Accept the impedance trace list via metadata and redraw the plot."""
        self.metadata = metadata_dict or {}
        self.traces = self.metadata.get("trace_data", []) or []
        self._populate_trace_selectors()
        self._refresh_plot()

    def _populate_trace_selectors(self):
        trace_names = [trace["type"] for trace in self.traces]
        items = ["Select a trace..."] + trace_names

        self.reference_combo.blockSignals(True)
        self.test_combo.blockSignals(True)
        self.reference_combo.clear()
        self.test_combo.clear()
        self.reference_combo.addItems(items)
        self.test_combo.addItems(items)
        self.reference_combo.blockSignals(False)
        self.test_combo.blockSignals(False)

    def _on_plot_settings_changed(self, *_args):
        self._refresh_plot()

    def _get_trace_by_type(self, trace_type: str):
        for trace in self.traces:
            if trace.get("type") == trace_type:
                return trace
        return None

    def _build_line_color(self, trace_type: str):
        color_tuple = SCAN_TYPE_COLORS.get(trace_type, ("black", "gray"))
        is_dark = getattr(self.window(), "dark_mode", True)
        return color_tuple[1] if is_dark else color_tuple[0]

    def _calculate_percent_error(self, z_ref, z_test):
        z_ref = np.asarray(z_ref, dtype=np.complex128)
        z_test = np.asarray(z_test, dtype=np.complex128)
        mag_ref = np.abs(z_ref)
        mag_test = np.abs(z_test)
        error = np.full_like(mag_ref, np.nan, dtype=np.float64)
        valid = np.isfinite(mag_ref) & np.isfinite(mag_test) & (mag_ref != 0)
        error[valid] = 100.0 * np.abs(mag_test[valid] - mag_ref[valid]) / mag_ref[valid]
        return error

    def _refresh_plot(self):
        self.figure.clear()
        ax = self.figure.add_subplot(111)
        ax2 = None
        plotted = False
        self.status_label.setText("")

        if not self.traces:
            self.status_label.setText("No impedance traces available for this experiment.")
            self.canvas.draw()
            return

        settings = self.metadata.get("analysis_settings", {})
        lw = settings.get("line_width", 1.5)
        mode = settings.get("impedance_display_mode", "Impedance")

        for trace_type, checkbox in self.trace_checkboxes.items():
            if not checkbox.isChecked():
                continue
            trace = self._get_trace_by_type(trace_type)
            if trace is None:
                continue

            color = self._build_line_color(trace_type)
            freq_vals = np.asarray(trace["f"])
            if mode == "Capacitance":
                z_imag_vals = np.asarray(trace.get("z_imag", np.zeros_like(freq_vals, dtype=np.float64)), dtype=np.float64)
                y_vals = np.full_like(z_imag_vals, np.nan, dtype=np.float64)
                valid = (freq_vals != 0) & (z_imag_vals != 0) & np.isfinite(freq_vals) & np.isfinite(z_imag_vals)
                y_vals[valid] = 1.0 / (2.0 * np.pi * freq_vals[valid] * z_imag_vals[valid])
            else:
                if "z" in trace and trace["z"] is not None:
                    y_vals = np.asarray(trace["z"])
                else:
                    z_complex = np.asarray(trace.get("z_real", 0.0)) + 1j * np.asarray(trace.get("z_imag", 0.0))
                    y_vals = np.abs(z_complex)

            min_freq = self.min_freq_spin.value() if self.min_freq_spin.value() > 0 else None
            max_freq = self.max_freq_spin.value() if self.max_freq_spin.value() > 0 else None
            if min_freq is not None or max_freq is not None:
                mask = np.ones_like(freq_vals, dtype=bool)
                if min_freq is not None:
                    mask &= (freq_vals >= min_freq)
                if max_freq is not None:
                    mask &= (freq_vals <= max_freq)
                freq_vals = freq_vals[mask]
                y_vals = y_vals[mask]

            if freq_vals.size == 0:
                continue

            ax.plot(freq_vals, y_vals, label=trace.get("label"), color=color, linewidth=lw)
            plotted = True

        # Match processor plotting: log-log for impedance, linear for capacitance
        ax.set_xscale("log")
        ax.set_yscale("log" if mode == "Impedance" else "linear")
        ax.set_xlabel("Frequency (Hz)", labelpad=8)
        ax.set_ylabel("Impedance Z (Ohms)" if mode == "Impedance" else "Capacitance (F)", labelpad=8)
        ax.grid(True, which="both", ls="--", alpha=0.5)

        for spine in ax.spines.values():
            spine.set_linewidth(1.2)

        # Reset avg label to N/A by default; will update below if we compute error
        self.avg_error_label.setText("Avg % Error: N/A")
        if self.percent_error_checkbox.isChecked():
            ref_name = self.reference_combo.currentText()
            test_name = self.test_combo.currentText()
            if ref_name == "Select a trace..." or test_name == "Select a trace..." or ref_name == test_name:
                self.status_label.setText("Select two different traces for percent error calculation.")
            else:
                ref_trace = self._get_trace_by_type(ref_name)
                test_trace = self._get_trace_by_type(test_name)
                if ref_trace is None or test_trace is None:
                    self.status_label.setText("Selected percent error traces are not available in the current session.")
                elif len(ref_trace["f"]) != len(test_trace["f"]):
                    self.status_label.setText("Percent error requires the reference and test traces to share the same frequency axis.")
                else:
                    ref_freq = np.asarray(ref_trace["f"])
                    test_freq = np.asarray(test_trace["f"])
                    min_freq = self.min_freq_spin.value() if self.min_freq_spin.value() > 0 else None
                    max_freq = self.max_freq_spin.value() if self.max_freq_spin.value() > 0 else None
                    mask = None
                    if min_freq is not None or max_freq is not None:
                        mask = np.ones_like(ref_freq, dtype=bool)
                        if min_freq is not None:
                            mask &= (ref_freq >= min_freq)
                        if max_freq is not None:
                            mask &= (ref_freq <= max_freq)
                        ref_freq = ref_freq[mask]
                        test_freq = test_freq[mask]

                    if ref_freq.size == 0:
                        self.status_label.setText("Frequency range selected excludes all percent error data.")
                    else:
                        z_ref = np.asarray(ref_trace["z_real"]) + 1j * np.asarray(ref_trace["z_imag"])
                        z_test = np.asarray(test_trace["z_real"]) + 1j * np.asarray(test_trace["z_imag"])
                        if mask is not None:
                            z_ref = z_ref[mask]
                            z_test = z_test[mask]
                        error_pct = self._calculate_percent_error(z_ref, z_test)
                        ax2 = ax.twinx()
                        ax2.plot(ref_freq, error_pct, linestyle="--", color="tab:red", label="% Error")
                        ax2.set_ylabel("Percent Error (%)", color="tab:red")
                        ax2.tick_params(axis="y", colors="tab:red")
                        ax2.set_yscale("linear")
                        self.status_label.setText("Percent error plotted using the selected reference and test traces.")
                        plotted = True

                        # Compute average percent error over finite values in the current plotted range
                        valid_mask = np.isfinite(error_pct)
                        if np.any(valid_mask):
                            avg_pct = float(np.nanmean(error_pct[valid_mask]))
                            self.avg_error_label.setText(f"Avg % Error: {avg_pct:.2f}%")
                        else:
                            self.avg_error_label.setText("Avg % Error: N/A")

        if plotted and self.trace_checkboxes["Calibrated Sample"].isChecked():
            # Ensure calibrated sample line is visible in the legend if selected.
            pass

        if plotted and self.metadata.get("analysis_settings", {}).get("show_legend", True):
            handles, labels = ax.get_legend_handles_labels()
            if ax2 is not None:
                handles2, labels2 = ax2.get_legend_handles_labels()
                handles += handles2
                labels += labels2
            if handles:
                ax.legend(handles, labels, frameon=True, loc="best", fontsize=8)

        if not plotted:
            self.status_label.setText("No traces selected for plotting.")

        self.canvas.draw()

    def shutdown(self):
        self.traces = []
        self.metadata = {}
        self.figure.clear()
        self.canvas.draw()

    def apply_theme(self, is_dark: bool):
        self.figure.set_facecolor("#222" if is_dark else "white")
        self.canvas.draw()
