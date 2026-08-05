import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from utils.project_manager import ProjectManager
from utils.app_logger import logger
from processors.base_processor import BaseProcessor
from utils.colton_math import calculate_true_z
from config.techniques import SCAN_TYPE_COLORS

class ImpedanceCalibrationProcessor(BaseProcessor):
    def __init__(self, parent_window):
        super().__init__(parent_window)

    @staticmethod
    def _find_column(data_dict, candidates):
        normalized = {str(key).strip().lower(): key for key in data_dict.keys()}
        for candidate in candidates:
            key = normalized.get(candidate.lower())
            if key is not None:
                return key

        for key in data_dict.keys():
            normalized_key = str(key).strip().lower()
            for candidate in candidates:
                if candidate.lower() in normalized_key:
                    return key

        return None

    def _load_traces(self, json_data, settings=None):
        """Load scans from the current experiment JSON."""
        return self._load_traces_custom(json_data, settings)

    @staticmethod
    def _complex_trace_components(z_complex):
        z_mag = np.abs(z_complex)
        z_theta = np.degrees(np.angle(z_complex))
        z_real = np.real(z_complex)
        z_imag = np.imag(z_complex)
        return z_mag, z_theta, z_real, z_imag

    @staticmethod
    def _get_plot_values(trace, settings=None):
        settings = settings or {}
        mode = settings.get("impedance_display_mode", "Impedance")
        f_vals = np.asarray(trace.get("f", []), dtype=np.float64)

        if mode == "Capacitance":
            z_imag_vals = np.asarray(trace.get("z_imag", np.zeros_like(f_vals, dtype=np.float64)), dtype=np.float64)
            y_vals = np.full_like(z_imag_vals, np.nan, dtype=np.float64)
            valid = (f_vals != 0) & (z_imag_vals != 0) & np.isfinite(f_vals) & np.isfinite(z_imag_vals)
            y_vals[valid] = 1.0 / (2.0 * np.pi * f_vals[valid] * z_imag_vals[valid])
            return y_vals

        if "z" in trace and trace["z"] is not None:
            return np.asarray(trace["z"], dtype=np.float64)

        z_complex = np.asarray(trace.get("z_real", 0.0), dtype=np.complex128) + 1j * np.asarray(trace.get("z_imag", 0.0), dtype=np.complex128)
        return np.abs(z_complex)

    @staticmethod
    def _calculate_calibrated_sample(z_known_load, z_short, z_sample, z_load, z_open):
        z_known_load = np.asarray(z_known_load, dtype=np.complex128)
        z_short = np.asarray(z_short, dtype=np.complex128)
        z_sample = np.asarray(z_sample, dtype=np.complex128)
        z_load = np.asarray(z_load, dtype=np.complex128)
        z_open = np.asarray(z_open, dtype=np.complex128)

        numerator = (z_short - z_sample) * (z_load - z_open)
        denominator = (z_sample - z_open) * (z_short - z_load)

        calibrated = np.full_like(z_known_load, np.nan + 1j * np.nan, dtype=np.complex128)
        valid = np.isfinite(numerator) & np.isfinite(denominator) & (denominator != 0)
        calibrated[valid] = (z_known_load[valid] * numerator[valid]) / denominator[valid]
        return calibrated

    # I'll override _load_traces_custom because base_processor.load_raw_data is geared towards Absorption/EA
    def _load_traces_custom(self, json_data, settings=None):
        from processors.public.read_colton_files import read_data_simple
        from pathlib import Path
        settings = settings or {}
        data_files = json_data.get("data_files", {})
        
        circuit_model = json_data.get("global_settings", {}).get("circuit_model", settings.get("circuit_model", "Parallel"))
        is_series_mode = (circuit_model.lower() == "series")

        scan_keys = {
            "Open": ("open_file", "show_open_scan"),
            "Short": ("short_file", "show_short_scan"),
            "Load": ("load_file", "show_load_scan"),
            "Known Load": ("known_load_file", "show_known_load_scan"),
            "Sample": ("sample_file", "show_sample_scan"),
            "Sample 2": ("sample2_file", "show_sample2_scan"),
        }

        traces = []
        trace_by_type = {}
        for scan_type, (file_key, toggle_key) in scan_keys.items():
            should_plot = settings.get(toggle_key, True)
            rel_path = data_files.get(file_key)
            if not rel_path:
                continue

            # Resolve path
            if isinstance(rel_path, dict):
                rel_path = rel_path.get("path") or rel_path.get("file")
            
            if not rel_path:
                continue
            
            full_path = Path(self.parent_window.base_dir) / Path(rel_path)
            if not full_path.exists():
                logger.warning(f"Data file not found: {full_path}")
                continue
            
            data_dict = read_data_simple(str(full_path))
            if not data_dict:
                continue
                
            f_key = self._find_column(data_dict, ("F (Hz)", "Freq", "Frequency"))

            if is_series_mode:
                real_key = self._find_column(data_dict, ("R", "R (Ohm)", "R (Ω)", "Resistance"))
                imag_key = self._find_column(data_dict, ("X", "X (Ohm)", "X (Ω)", "Reactance"))
            else:
                real_key = self._find_column(data_dict, ("G", "G (S)", "Conductance"))
                imag_key = self._find_column(data_dict, ("B", "B (S)", "Susceptance"))

            if not real_key or not imag_key:
                real_key = self._find_column(data_dict, ("R", "R (Ohm)", "R (Ω)", "Resistance"))
                imag_key = self._find_column(data_dict, ("X", "X (Ohm)", "X (Ω)", "Reactance"))

            if f_key and real_key and imag_key:
                f_vals = data_dict[f_key]
                real_vals = data_dict[real_key]
                imag_vals = data_dict[imag_key]

                z_true, phi_true, z_real, z_imag = calculate_true_z(real_vals, imag_vals, is_series_mode)

                trace = {
                    "type": scan_type,
                    "f": f_vals,
                    "z": z_true,
                    "phi": phi_true,
                    "z_real": z_real,
                    "z_imag": z_imag,
                    "label": f"{scan_type} Scan"
                }
                trace_by_type[scan_type] = trace
                if should_plot:
                    traces.append(trace)
            else:
                logger.warning(
                    f"Could not find frequency and impedance/admittance columns in {rel_path}. "
                    f"Keys: {list(data_dict.keys())}"
                )

        if settings.get("show_calibrated_sample_scan", False):
            required_types = ["Known Load", "Short", "Load", "Open", "Sample"]
            if all(trace_type in trace_by_type for trace_type in required_types):
                known_load_trace = trace_by_type["Known Load"]
                short_trace = trace_by_type["Short"]
                load_trace = trace_by_type["Load"]
                open_trace = trace_by_type["Open"]
                sample_trace = trace_by_type["Sample"]

                z_known_load = known_load_trace["z_real"] + 1j * known_load_trace["z_imag"]
                z_short = short_trace["z_real"] + 1j * short_trace["z_imag"]
                z_sample = sample_trace["z_real"] + 1j * sample_trace["z_imag"]
                z_load = load_trace["z_real"] + 1j * load_trace["z_imag"]
                z_open = open_trace["z_real"] + 1j * open_trace["z_imag"]

                calibrated_complex = self._calculate_calibrated_sample(
                    z_known_load, z_short, z_sample, z_load, z_open
                )
                z_true, phi_true, z_real, z_imag = self._complex_trace_components(calibrated_complex)

                traces.append({
                    "type": "Calibrated Sample",
                    "f": sample_trace["f"],
                    "z": z_true,
                    "phi": phi_true,
                    "z_real": z_real,
                    "z_imag": z_imag,
                    "label": "Calibrated Sample Scan"
                })
            else:
                logger.warning("Skipping calibrated sample trace because one or more required scans were not loaded.")

        return traces

    def generate_plot(self, figure, ax=None, path=None, **kwargs) -> bool:
        try:
            json_data = self.get_json_data(path)
            settings = self.get_settings(json_data).copy()
            
            if ax is None:
                ax = figure.add_subplot(111)
            
            traces = self._load_traces_custom(json_data, settings)
            if not traces:
                return False

            lw = settings.get("line_width", 1.5)
            mode = settings.get("impedance_display_mode", "Impedance")
            # Default line style is solid
            
            # Use specific colors for scan types if available
            for trace in traces:
                scan_type = trace["type"]
                color_tuple = SCAN_TYPE_COLORS.get(scan_type, ("black", "gray"))
                
                # Check for dark mode to select appropriate color
                is_dark = getattr(self.parent_window, "dark_mode", True)
                color = color_tuple[1] if is_dark else color_tuple[0]

                y_vals = self._get_plot_values(trace, settings)
                ax.plot(trace["f"], y_vals, linewidth=lw, label=trace["label"], color=color)

            ax.set_xscale('log')
            ax.set_yscale('log' if mode == "Impedance" else 'linear')
            ax.set_xlabel("Frequency (Hz)", labelpad=8)
            ax.set_ylabel("Impedance Z (Ohms)" if mode == "Impedance" else "Capacitance (F)", labelpad=8)
            
            ax.grid(True, which="both", ls="--", alpha=0.5)

            if kwargs.get("show_legend", settings.get("show_legend", True)):
                ax.legend(frameon=True, loc="best", fontsize=8)

            for spine in ax.spines.values():
                spine.set_linewidth(1.2)

            return True

        except Exception as e:
            logger.exception(f"ImpedanceCalibrationProcessor.generate_plot error: {e}")
            return False

    def export_data(self, save_path: str, path=None) -> bool:
        try:
            json_data = self.get_json_data(path)
            settings = self.get_settings(json_data)
            traces = self._load_traces_custom(json_data, settings)
            if not traces:
                return False

            export_dict = {}
            for trace in traces:
                prefix = trace["type"]
                # Create separate columns for each scan with frequency, Z, theta, and complex components.
                f_vals = np.asarray(trace["f"], dtype=np.float64)
                z_vals = np.asarray(trace["z"], dtype=np.float64)
                phi_vals = np.asarray(trace.get("phi", np.full_like(z_vals, np.nan, dtype=np.float64)), dtype=np.float64)
                z_real_vals = np.asarray(trace.get("z_real", np.zeros_like(z_vals)), dtype=np.float64)
                z_imag_vals = np.asarray(trace.get("z_imag", np.zeros_like(z_vals)), dtype=np.float64)

                # Calculate capacitance from imaginary impedance: C = 1 / (2*pi*f*X)
                capacitance = np.full_like(z_imag_vals, np.nan, dtype=np.float64)
                valid = (f_vals != 0) & (z_imag_vals != 0) & np.isfinite(f_vals) & np.isfinite(z_imag_vals)
                capacitance[valid] = 1.0 / (2.0 * np.pi * f_vals[valid] * z_imag_vals[valid])

                export_dict[f"{prefix} Frequency (Hz)"] = f_vals
                export_dict[f"{prefix} Z (Ohms)"] = z_vals
                export_dict[f"{prefix} Theta (deg)"] = phi_vals
                export_dict[f"{prefix} R (Ohms)"] = z_real_vals
                export_dict[f"{prefix} X (Ohms)"] = z_imag_vals
                export_dict[f"{prefix} Capacitance (C)"] = capacitance

            # Note: lengths may differ across scan types, pandas will pad shorter columns with NaN.
            df = pd.DataFrame({k: pd.Series(v) for k, v in export_dict.items()})
            df.to_csv(save_path, index=False)
            return True
        except Exception as e:
            logger.exception(f"ImpedanceCalibrationProcessor.export_data error: {e}")
            return False
