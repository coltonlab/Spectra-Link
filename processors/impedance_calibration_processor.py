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

    def _load_traces(self, json_data, settings=None):
        """Load scans from the current experiment JSON."""
        settings = settings or {}
        data_files = json_data.get("data_files", {})
        
        circuit_model = settings.get("circuit_model", "Parallel")
        is_series_mode = (circuit_model.lower() == "series")

        scan_keys = {
            "Open": ("open_file", "show_open_scan"),
            "Short": ("short_file", "show_short_scan"),
            "Load": ("load_file", "show_load_scan"),
            "Known Load": ("known_load_file", "show_known_load_scan"),
            "Sample": ("sample_file", "show_sample_scan"),
        }

        traces = []
        for scan_type, (file_key, toggle_key) in scan_keys.items():
            if not settings.get(toggle_key, True):
                continue
                
            rel_path = data_files.get(file_key)
            if not rel_path:
                continue

            # Need to prioritize finding frequency and Z
            # read_data_simple returns a dictionary of numpy arrays
            data_dict = self.load_raw_data(rel_path, priority=["Z"])
            # wait, load_raw_data uses self.load_raw_data(rel_path, priority=["Z"]). 
            # But load_raw_data in base_processor might return only (x, y). 
            pass

        return traces

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
        }

        traces = []
        for scan_type, (file_key, toggle_key) in scan_keys.items():
            if not settings.get(toggle_key, True):
                continue
                
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
                
            # Find Frequency column
            f_key = next((k for k in data_dict.keys() if "F (Hz)" in k or "Freq" in k), None)
            z_key = next((k for k in data_dict.keys() if k.strip() == "Z"), None)
            phi_key = next((k for k in data_dict.keys() if k.strip() == "Phi"), None)
            
            if f_key and z_key and phi_key:
                f_vals = data_dict[f_key]
                z_raw = data_dict[z_key]
                phi_raw = data_dict[phi_key]
                
                z_true, phi_true = calculate_true_z(z_raw, phi_raw, is_series_mode)
                
                traces.append({
                    "type": scan_type,
                    "f": f_vals,
                    "z": z_true,
                    "phi": phi_true,
                    "label": f"{scan_type} Scan"
                })
            else:
                logger.warning(f"Could not find F (Hz), Z, or Phi columns in {rel_path}. Keys: {list(data_dict.keys())}")

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
            # Default line style is solid
            
            # Use specific colors for scan types if available
            for trace in traces:
                scan_type = trace["type"]
                color_tuple = SCAN_TYPE_COLORS.get(scan_type, ("black", "gray"))
                
                # Check for dark mode to select appropriate color
                is_dark = getattr(self.parent_window, "dark_mode", True)
                color = color_tuple[1] if is_dark else color_tuple[0]

                # We can also respect global trace color if desired, but for multiple scans, distinct colors are better.
                ax.plot(trace["f"], trace["z"], linewidth=lw, label=trace["label"], color=color)

            ax.set_xscale('log')
            ax.set_yscale('log')
            ax.set_xlabel("Frequency (Hz)", labelpad=8)
            ax.set_ylabel("Impedance Z (Ohms)", labelpad=8)
            
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
                # Create separate columns for each scan
                export_dict[f"{prefix} Freq (Hz)"] = trace["f"]
                export_dict[f"{prefix} Z (Ohms)"] = trace["z"]
                export_dict[f"{prefix} Phi (deg)"] = trace["phi"]

            # Note: lengths might differ slightly, pandas will handle it by padding with NaN if we construct properly
            df = pd.DataFrame({k: pd.Series(v) for k, v in export_dict.items()})
            df.to_csv(save_path, index=False)
            return True
        except Exception as e:
            logger.exception(f"ImpedanceCalibrationProcessor.export_data error: {e}")
            return False
