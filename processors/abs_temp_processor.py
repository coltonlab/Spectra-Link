import numpy as np
import matplotlib.pyplot as plt
from scipy.signal import savgol_filter
from pathlib import Path
from processors.base_processor import BaseProcessor
from utils.app_logger import logger
import processors.public.colton_math_functions as cmf

class ABSTempProcessor(BaseProcessor):
    SMOOTH_WINDOW = 11
    SMOOTH_POLY   = 3
    OFFSET_STEP   = 0.15

    def __init__(self, parent_window):
        super().__init__(parent_window)

    def _load_traces(self, json_data):
        data_files = json_data.get("data_files", {})
        traces = []
        
        # For Absorption, we prioritize the magnitude R (V) to ensure positive intensity
        abs_priority = ["R (V)", "X (V) Phased", "X (V) Phased Average", "Phased (V)", "X (V)"]

        # 1. Load Blank
        wl_b, int_b = self.load_raw_data(data_files.get("blank_file"), priority=abs_priority)
        if wl_b is None:
            logger.warning(f"ABSTempProcessor: Blank file not loaded or found for {json_data.get('core',{}).get('experiment_name')}. Cannot calculate absorbance.")
            return []


        # 2. Get Series
        scan_list = data_files.get("temperature_scans", []) or data_files.get("sample_scans", [])
        if not scan_list and data_files.get("sample_file"):
            scan_list = [{"file": data_files.get("sample_file")}]

        for entry in scan_list:
            rel_path = entry.get("file")
            temp = entry.get("temperature", 0)
            label = f"{temp} K" if temp else "Sample"
            
            wl_s, int_s = self.load_raw_data(rel_path, priority=abs_priority)
            if wl_s is None: continue # Skip this scan if data couldn't be loaded
            if wl_s is not None:
                # Interpolate blank onto sample wavelengths
                int_b_interp = np.interp(wl_s, wl_b, int_b)
                # Ensure intensities are positive for log calculation
                int_s_pos, int_b_pos = np.abs(int_s), np.abs(int_b_interp)
                abs_vals = -np.log10(np.where(int_s_pos/int_b_pos > 0, int_s_pos/int_b_pos, 1e-9))
                
                traces.append({
                    "wavelengths": wl_s,
                    "absorbance": abs_vals,
                    "label": label,
                    "value": temp
                })
        return traces

    def _process_trace(self, wl, ab, settings, trace_idx):
        x, y = wl.copy(), ab.copy()
        if settings.get("smooth_data"):
            if len(y) > self.SMOOTH_WINDOW:
                y = savgol_filter(y, self.SMOOTH_WINDOW, self.SMOOTH_POLY)
        if settings.get("normalize_to_peak"):
            peak = np.max(np.abs(y))
            if peak > 0: y /= peak
        if settings.get("offset_traces"):
            y += trace_idx * self.OFFSET_STEP
        if settings.get("convert_to_ev"):
            x = np.where(x > 0, 1240.0 / x, np.nan)
        return x, y

    def generate_plot(self, figure, ax=None, path=None, **kwargs) -> bool:
        try:
            json_data = self.get_json_data(path)
            settings = self.get_settings(json_data).copy()
            
            if kwargs.get("force_unit") == "eV": settings["convert_to_ev"] = True
            elif kwargs.get("force_unit") == "nm": settings["convert_to_ev"] = False
            
            use_ev = settings.get("convert_to_ev", False)
            lw = settings.get("line_width", kwargs.get("line_width", 1.5))
            ax = ax or figure.add_subplot(111)

            if settings.get("show_title", True):
                title = settings.get("plot_title", "")
                if title and title != "False": ax.set_title(title, pad=15)

            cmap = plt.get_cmap(settings.get("colormap_name", "viridis"))
            traces = self._load_traces(json_data)
            num_traces = len(traces)
            if num_traces == 0:
                logger.warning(f"ABSTempProcessor: No traces loaded for {json_data.get('core',{}).get('experiment_name')}. Plotting skipped.")
                return False


            vals = [t.get("value", 0) for t in traces]
            vmin, vmax = min(vals), max(vals)
            norm = plt.Normalize(vmin=vmin, vmax=vmax)

            # Zero Line & Vertical Lines
            if settings.get("show_zero_line"):
                ax.axhline(0, color='Black', linewidth=0.8, alpha=0.6, zorder=0)
            
            v_lines = settings.get("vertical_lines") or []
            for line in (v_lines if isinstance(v_lines, list) else []):
                vx = line.get("x")
                if vx and vx > 0:
                    plot_x = vx if use_ev else 1240.0 / vx
                    ax.axvline(plot_x, color='black', linestyle='--', linewidth=1.0, alpha=0.4, 
                               label=line.get("label", "") if line.get("show_legend", True) else None)

            for idx, trace in enumerate(traces):
                x, y = self._process_trace(trace["wavelengths"], trace["absorbance"], settings, idx)
                color = cmap(norm(trace.get("value", 0))) if vmin != vmax else cmap(idx/num_traces if num_traces > 1 else 0.5)
                ax.plot(x, y, color=color, linewidth=lw, label=trace["label"])

            # Colorbar
            if num_traces > 1 and vmin != vmax and settings.get("show_colorbar", True):
                sm = plt.cm.ScalarMappable(cmap=cmap, norm=norm)
                cbar = figure.colorbar(sm, ax=ax, orientation='vertical', pad=0.02, fraction=0.04, aspect=30)
                cbar.set_label("Temp (K)", fontsize=9)
                cbar.ax.tick_params(labelsize=8)

            # Formatting
            ax.set_xlabel("Photon Energy (eV)" if use_ev else "Wavelength (nm)", labelpad=8)
            ax.set_ylabel("Normalized Absorbance (a.u.)" if settings.get("normalize_to_peak") else "Absorbance (O.D.)", labelpad=8)

            if kwargs.get("show_legend", settings.get("show_legend")):
                ax.legend(frameon=False, loc="upper right", fontsize=8)

            for spine in ax.spines.values(): spine.set_linewidth(1.2)
            return True
        except Exception as e:
            logger.exception(f"ABSTempProcessor error for path: {path}")
            return False