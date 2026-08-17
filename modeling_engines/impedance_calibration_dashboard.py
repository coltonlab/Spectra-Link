import numpy as np
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QCheckBox, QComboBox,
    QPushButton, QLabel, QSizePolicy, QFrame, QDoubleSpinBox,
    QButtonGroup
)
from PyQt6.QtCore import Qt

from modeling_engines.base_modeling_dashboard import BaseModelingDashboard
from config.techniques import SCAN_TYPE_COLORS, TRACE_COLORS
from utils.app_logger import logger


class ImpedanceCalibrationDashboard(BaseModelingDashboard):
    """
    Modeling dashboard for impedance calibration experiments.
    Provides controls to toggle individual impedance traces, switch between
    Impedance and Capacitance plot modes, and plot percent error between two
    selected traces based on whatever is currently being displayed.
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
        # Current display mode: "Impedance" or "Capacitance"
        self._display_mode = "Impedance"
        self.build_ui()

    # ── helpers ────────────────────────────────────────────────────────────────

    def _get_y_vals(self, trace: dict, freq_vals: np.ndarray) -> np.ndarray:
        """Return y-values for a trace based on the current display mode."""
        if self._display_mode == "Capacitance":
            z_imag_vals = np.asarray(
                trace.get("z_imag", np.zeros_like(freq_vals, dtype=np.float64)),
                dtype=np.float64,
            )
            y_vals = np.full_like(z_imag_vals, np.nan, dtype=np.float64)
            valid = (
                (freq_vals != 0)
                & (z_imag_vals != 0)
                & np.isfinite(freq_vals)
                & np.isfinite(z_imag_vals)
            )
            y_vals[valid] = 1.0 / (2.0 * np.pi * freq_vals[valid] * z_imag_vals[valid])
            return y_vals
        # Impedance mode
        if "z" in trace and trace["z"] is not None:
            return np.asarray(trace["z"], dtype=np.float64)
        z_complex = np.asarray(trace.get("z_real", 0.0), dtype=np.complex128) + 1j * np.asarray(
            trace.get("z_imag", 0.0), dtype=np.complex128
        )
        return np.abs(z_complex)

    def _apply_freq_mask(self, freq_vals: np.ndarray, y_vals: np.ndarray):
        """Apply the min/max frequency filter and return (masked_freq, masked_y)."""
        min_freq = self.min_freq_spin.value() if self.min_freq_spin.value() > 0 else None
        max_freq = self.max_freq_spin.value() if self.max_freq_spin.value() > 0 else None
        if min_freq is None and max_freq is None:
            return freq_vals, y_vals
        mask = np.ones(len(freq_vals), dtype=bool)
        if min_freq is not None:
            mask &= freq_vals >= min_freq
        if max_freq is not None:
            mask &= freq_vals <= max_freq
        return freq_vals[mask], y_vals[mask]

    # ── UI construction ────────────────────────────────────────────────────────

    def build_ui(self):
        self.setLayout(QHBoxLayout())
        self.layout().setContentsMargins(8, 8, 8, 8)
        self.layout().setSpacing(12)

        # ── Left: Plot area ────────────────────────────────────────────────────
        plot_frame = QVBoxLayout()
        self.figure = Figure(layout="constrained", facecolor="white")
        self.canvas = FigureCanvas(self.figure)
        self.canvas.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

        self.status_label = QLabel("Choose traces to display and enable percent error if needed.")
        self.status_label.setWordWrap(True)
        self.status_label.setStyleSheet("color: gray;")

        # Footer: status on left, average percent-error on right
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

        # ── Right: Controls ────────────────────────────────────────────────────
        control_frame = QFrame()
        control_frame.setLayout(QVBoxLayout())
        control_frame.layout().setContentsMargins(0, 0, 0, 0)
        control_frame.layout().setSpacing(8)

        # ---- Plot Mode Toggle ------------------------------------------------
        control_frame.layout().addWidget(QLabel("<b>Plot Mode</b>"))

        mode_row = QHBoxLayout()
        self.btn_impedance = QPushButton("Impedance")
        self.btn_impedance.setCheckable(True)
        self.btn_impedance.setChecked(True)
        self.btn_impedance.setToolTip("Display raw impedance magnitude (Ω)")

        self.btn_capacitance = QPushButton("Capacitance")
        self.btn_capacitance.setCheckable(True)
        self.btn_capacitance.setChecked(False)
        self.btn_capacitance.setToolTip("Display capacitance derived from imaginary impedance (F)")

        self._mode_group = QButtonGroup(self)
        self._mode_group.setExclusive(True)
        self._mode_group.addButton(self.btn_impedance)
        self._mode_group.addButton(self.btn_capacitance)

        self.btn_impedance.toggled.connect(self._on_mode_toggled)
        self.btn_capacitance.toggled.connect(self._on_plot_settings_changed)

        mode_row.addWidget(self.btn_impedance)
        mode_row.addWidget(self.btn_capacitance)
        control_frame.layout().addLayout(mode_row)

        # ---- Traces & Colors -------------------------------------------------
        control_frame.layout().addSpacing(6)
        control_frame.layout().addWidget(QLabel("<b>Traces &amp; Colors</b>"))
        self.trace_checkboxes = {}
        self.trace_color_combos = {}
        self.trace_alpha_spins = {}

        for trace_type in self.TRACE_TYPES:
            row_widget = QWidget()
            row_layout = QHBoxLayout(row_widget)
            row_layout.setContentsMargins(0, 0, 0, 0)
            row_layout.setSpacing(4)

            checkbox = QCheckBox(trace_type)
            checkbox.setChecked(True)
            checkbox.stateChanged.connect(self._on_plot_settings_changed)
            self.trace_checkboxes[trace_type] = checkbox

            from processors.impedance_calibration_processor import ImpedanceCalibrationProcessor
            default_color = ImpedanceCalibrationProcessor.DEFAULT_TRACE_COLORS.get(trace_type, "black")

            color_combo = QComboBox()
            color_combo.addItems(TRACE_COLORS)
            color_combo.setCurrentText(default_color)
            color_combo.currentTextChanged.connect(self._on_plot_settings_changed)
            self.trace_color_combos[trace_type] = color_combo

            alpha_spin = QDoubleSpinBox()
            alpha_spin.setRange(0.0, 1.0)
            alpha_spin.setSingleStep(0.05)
            alpha_spin.setDecimals(2)
            alpha_spin.setValue(0.7)
            alpha_spin.setToolTip(f"{trace_type} Opacity (α)")
            alpha_spin.setFixedWidth(55)
            alpha_spin.valueChanged.connect(self._on_plot_settings_changed)
            self.trace_alpha_spins[trace_type] = alpha_spin

            row_layout.addWidget(checkbox, stretch=1)
            row_layout.addWidget(color_combo, stretch=0)
            row_layout.addWidget(alpha_spin, stretch=0)

            control_frame.layout().addWidget(row_widget)

        # ---- Frequency Range -------------------------------------------------
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

        # ---- Percent Error ---------------------------------------------------
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

    # ── Slots ─────────────────────────────────────────────────────────────────

    def _on_mode_toggled(self, checked: bool):
        """Update internal display mode when the toggle buttons change."""
        self._display_mode = "Impedance" if self.btn_impedance.isChecked() else "Capacitance"
        self._refresh_plot()

    def _on_plot_settings_changed(self, *_args):
        self._refresh_plot()

    # ── Data ingestion ─────────────────────────────────────────────────────────

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

    # ── Internal helpers ───────────────────────────────────────────────────────

    def _get_trace_by_type(self, trace_type: str):
        for trace in self.traces:
            if trace.get("type") == trace_type:
                return trace
        return None

    def _build_line_color_and_alpha(self, trace_type: str, settings: dict = None):
        color = "black"
        alpha = 0.7
        if trace_type in self.trace_color_combos:
            color = self.trace_color_combos[trace_type].currentText()
        if trace_type in self.trace_alpha_spins:
            alpha = self.trace_alpha_spins[trace_type].value()

        from processors.impedance_calibration_processor import ImpedanceCalibrationProcessor
        proc_color, proc_alpha = ImpedanceCalibrationProcessor._get_trace_color_and_alpha(
            trace_type, settings
        )
        if color == "black" and proc_color != "black":
            color = proc_color
        if alpha == 0.7 and proc_alpha != 0.7:
            alpha = proc_alpha

        return color, alpha

    # ── Main plotting ──────────────────────────────────────────────────────────

    def _refresh_plot(self):
        self.figure.clear()
        ax = self.figure.add_subplot(111)
        ax2 = None
        plotted = False
        self.status_label.setText("")
        self.avg_error_label.setText("Avg % Error: N/A")

        if not self.traces:
            self.status_label.setText("No impedance traces available for this experiment.")
            self.canvas.draw()
            return

        settings = self.metadata.get("analysis_settings", {})
        lw = settings.get("line_width", 1.5)
        is_capacitance = self._display_mode == "Capacitance"

        # ── Draw selected traces ──────────────────────────────────────────────
        for trace_type, checkbox in self.trace_checkboxes.items():
            if not checkbox.isChecked():
                continue
            trace = self._get_trace_by_type(trace_type)
            if trace is None:
                continue

            color, alpha = self._build_line_color_and_alpha(trace_type, settings)
            freq_vals = np.asarray(trace["f"], dtype=np.float64)
            y_vals = self._get_y_vals(trace, freq_vals)

            freq_vals, y_vals = self._apply_freq_mask(freq_vals, y_vals)
            if freq_vals.size == 0:
                continue

            ax.plot(
                freq_vals, y_vals,
                label=trace.get("label"),
                color=color, alpha=alpha, linewidth=lw,
            )
            plotted = True

        # ── Axis formatting ───────────────────────────────────────────────────
        ax.set_xscale("log")
        ax.set_yscale("log" if not is_capacitance else "linear")
        ax.set_xlabel("Frequency (Hz)", labelpad=8)
        ax.set_ylabel(
            "Impedance Z (Ω)" if not is_capacitance else "Capacitance (F)",
            labelpad=8,
        )
        ax.grid(True, which="both", ls="--", alpha=0.5)
        for spine in ax.spines.values():
            spine.set_linewidth(1.2)

        # ── Percent error ─────────────────────────────────────────────────────
        if self.percent_error_checkbox.isChecked():
            ref_name = self.reference_combo.currentText()
            test_name = self.test_combo.currentText()

            if ref_name == "Select a trace..." or test_name == "Select a trace..." or ref_name == test_name:
                self.status_label.setText(
                    "Select two different traces for percent error calculation."
                )
            else:
                ref_trace = self._get_trace_by_type(ref_name)
                test_trace = self._get_trace_by_type(test_name)
                if ref_trace is None or test_trace is None:
                    self.status_label.setText(
                        "Selected percent error traces are not available in the current session."
                    )
                elif len(ref_trace["f"]) != len(test_trace["f"]):
                    self.status_label.setText(
                        "Percent error requires the reference and test traces to share the same frequency axis."
                    )
                else:
                    ref_freq = np.asarray(ref_trace["f"], dtype=np.float64)

                    # Compute y-values in the *currently active display mode*
                    ref_y = self._get_y_vals(ref_trace, ref_freq)
                    test_y = self._get_y_vals(test_trace, ref_freq)

                    ref_freq, ref_y = self._apply_freq_mask(ref_freq, ref_y)
                    _, test_y = self._apply_freq_mask(
                        np.asarray(test_trace["f"], dtype=np.float64), test_y
                    )

                    # Trim to the same length after masking
                    min_len = min(len(ref_y), len(test_y))
                    ref_y = ref_y[:min_len]
                    test_y = test_y[:min_len]
                    ref_freq = ref_freq[:min_len]

                    if ref_freq.size == 0:
                        self.status_label.setText(
                            "Frequency range selected excludes all percent error data."
                        )
                    else:
                        # Percent error on actual plotted magnitudes (works for both Z and C)
                        ref_abs = np.abs(ref_y)
                        test_abs = np.abs(test_y)
                        error_pct = np.full_like(ref_abs, np.nan, dtype=np.float64)
                        valid = np.isfinite(ref_abs) & np.isfinite(test_abs) & (ref_abs != 0)
                        error_pct[valid] = (
                            100.0 * np.abs(test_abs[valid] - ref_abs[valid]) / ref_abs[valid]
                        )

                        ax2 = ax.twinx()
                        ax2.plot(ref_freq, error_pct, linestyle="--", color="tab:red", label="% Error")
                        ax2.set_ylabel("Percent Error (%)", color="tab:red")
                        ax2.tick_params(axis="y", colors="tab:red")
                        ax2.set_yscale("linear")

                        mode_label = "Capacitance" if is_capacitance else "Impedance"
                        self.status_label.setText(
                            f"Percent error plotted on {mode_label} values — "
                            f"reference: {ref_name}, test: {test_name}."
                        )
                        plotted = True

                        valid_mask = np.isfinite(error_pct)
                        if np.any(valid_mask):
                            avg_pct = float(np.nanmean(error_pct[valid_mask]))
                            self.avg_error_label.setText(f"Avg % Error: {avg_pct:.2f}%")

        # ── Legend ────────────────────────────────────────────────────────────
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

    # ── Lifecycle ─────────────────────────────────────────────────────────────

    def shutdown(self):
        self.traces = []
        self.metadata = {}
        self.figure.clear()
        self.canvas.draw()

    def apply_theme(self, is_dark: bool):
        self.figure.set_facecolor("#222" if is_dark else "white")
        self.canvas.draw()
