import numpy as np
import matplotlib.pyplot as plt
import pandas as pd
from scipy.signal import savgol_filter
from pathlib import Path
from processors.base_processor import BaseProcessor
from utils.app_logger import logger # Import the global logger
import processors.public.colton_math_functions as cmf

class EATempProcessor(BaseProcessor):
    """
    Processor for Electro-Absorption Temperature Series where each temperature
    point has its own paired Transmission (DC) and Voltage (AC) scan.
    """
    SMOOTH_WINDOW = 11
    SMOOTH_POLY   = 3
    OFFSET_STEP   = 1.0  # mOD units

    def __init__(self, parent_window):
        super().__init__(parent_window)

    def _load_traces(self, json_data):
        """
        Groups files by temperature. For each temperature, it looks for a 
        'Voltage' scan and a 'Transmission' scan to calculate the EA signal.
        """
        data_files = json_data.get("data_files", {})
        # Files associated with a local parameter (Temperature) are stored here
        scan_list = data_files.get("temperature_scans", [])
        
        if not scan_list:
            return []

        # Group entries by temperature value
        groups = {}
        for entry in scan_list:
            try:
                # Force temperature to float to avoid string/int key mismatches
                temp = float(entry.get("temperature", 0))
            except (TypeError, ValueError):
                continue

            if temp not in groups:
                groups[temp] = {}
            
            # Map by type: 'Voltage' or 'Transmission'
            # If 'type' is missing from JSON, try to guess from the filename
            stype = entry.get("type") or entry.get("scan_type")
            fpath = entry.get("file")
            if not stype and fpath:
                if "trans" in fpath.lower() or "dc" in fpath.lower(): stype = "Transmission"
                elif "volt" in fpath.lower() or "ac" in fpath.lower(): stype = "Voltage"
            
            logger.debug(f"EATempProcessor: Grouping {fpath} as {stype} for {temp}K")
            if stype:
                groups[temp][stype] = fpath

        traces = []
        # Process in order of increasing temperature
        for temp in sorted(groups.keys()):
            pair = groups[temp]
            ac_path = pair.get("Voltage")
            dc_path = pair.get("Transmission")

            # We need both files at this temperature to compute the signal
            if not ac_path or not dc_path:
                logger.warning(f"EATempProcessor: Skipping {temp}K due to missing AC ({ac_path}) or DC ({dc_path}) file.")
                continue

            wl_ac, int_ac = self.load_raw_data(ac_path)
            wl_dc, int_dc = self.load_raw_data(dc_path)

            logger.debug(f"EATempProcessor: Loaded AC for {temp}K (wl_ac is None: {wl_ac is None}), DC (wl_dc is None: {wl_dc is None})")

            if wl_ac is not None and wl_dc is not None:
                # Safety: Ensure DC isn't zero to avoid NaNs/Infs
                int_dc_safe = np.interp(wl_ac, wl_dc, int_dc)
                int_dc_safe = np.where(int_dc_safe == 0, 1e-9, int_dc_safe)

                ea_vals = cmf.EA(int_ac, int_dc_safe)
                
                traces.append({
                    "wavelengths": wl_ac,
                    "ea": ea_vals,
                    "label": f"{temp} K",
                    "value": temp
                })

        # --- Overlay Absorption Logic ---
        # If a Blank is provided and 'overlay_absorption' is enabled, 
        # calculate ground state absorbance from the Transmission scans.
        if json_data.get("analysis_settings", {}).get("overlay_absorption"):
            logger.debug("EATempProcessor: Attempting to overlay absorption.")
            blank_path = data_files.get("blank_file")
            wl_b, int_b = self.load_raw_data(blank_path)
            if wl_b is not None:
                for trace in traces:
                    # Find the Transmission file used for this temperature
                    temp = trace["value"]
                    dc_path = groups[temp].get("Transmission")
                    if dc_path:
                        wl_s, int_s = self.load_raw_data(dc_path)
                        if wl_s is not None:
                            i0 = np.interp(wl_s, wl_b, int_b)
                            ratio = np.where(i0 != 0, int_s / i0, 1e-9)
                            abs_vals = -np.log10(np.where(ratio > 0, ratio, 1e-9))
                            trace["absorption"] = (wl_s, abs_vals)

        return traces

    def _process_trace(self, wl, ea, settings, trace_idx):
        x, y = wl.copy(), ea.copy()

        # 0. Wavelength Cutoff (nm)
        w_min = settings.get("min_wavelength", 0.0)
        w_max = settings.get("max_wavelength", 10000.0)
        mask = (x >= w_min) & (x <= w_max)
        x, y = x[mask], y[mask]

        if len(x) == 0:
            return x, y

        if settings.get("smooth_data"):
            if len(y) > self.SMOOTH_WINDOW:
                y = savgol_filter(y, self.SMOOTH_WINDOW, self.SMOOTH_POLY)

        if settings.get("flip_sign"):
            y = -y

        if settings.get("normalize_to_peak"):
            peak = np.max(np.abs(y))
            if peak > 0:
                y /= peak

        # 4.5 Scaling Factor
        scaling = settings.get("scaling_factor", 1.0)
        y = y * scaling

        if settings.get("offset_traces"):
            y += trace_idx * self.OFFSET_STEP

        if settings.get("convert_to_ev"):
            with np.errstate(divide="ignore", invalid="ignore"):
                x = np.where(x > 0, 1240.0 / x, np.nan)

        return x, y

    def generate_plot(self, figure, ax=None, path=None, **kwargs) -> bool:
        try:
            json_data = self.get_json_data(path)
            settings = self.get_settings(json_data).copy()
            
            # Global Overrides
            if kwargs.get("force_unit") == "eV": settings["convert_to_ev"] = True
            elif kwargs.get("force_unit") == "nm": settings["convert_to_ev"] = False
            
            use_ev = settings.get("convert_to_ev", False)
            lw = settings.get("line_width", kwargs.get("line_width", 1.5))
            ax = ax or figure.add_subplot(111)

            if settings.get("show_title", True):
                title = settings.get("plot_title", "")
                if title and title != "False": ax.set_title(title, pad=15)

            # Wavelength Cutoff bounds for overlay use
            w_min = settings.get("min_wavelength", 0.0)
            w_max = settings.get("max_wavelength", 10000.0)

            colormap_name = settings.get("colormap_name", "viridis")
            if settings.get("reverse_colormap", False):
                colormap_name += "_r"
            
            cmap = plt.get_cmap(colormap_name)
            traces = self._load_traces(json_data)
            if not traces:
                logger.warning(f"EATempProcessor: No traces loaded for {json_data.get('core',{}).get('experiment_name')}. Plotting skipped.")
                return False

            vals = [t.get("value", 0) for t in traces]
            max_val = max(vals) if vals else 0
            # Anchor 0 to the 0.1 color position and Max data to the 0.9 position.
            # This uses the high-contrast middle 80% of the colormap.
            vmin = -max_val / 8.0 if max_val > 0 else -1.0
            vmax = max_val * 1.125 if max_val > 0 else 1.0


            norm = plt.Normalize(vmin=vmin, vmax=vmax)

            if settings.get("show_zero_line"):
                ax.axhline(0, color='Black', linewidth=0.8, alpha=0.6, zorder=0)
            
            v_lines = settings.get("vertical_lines") or []
            for line in (v_lines if isinstance(v_lines, list) else []):
                vx = line.get("x")
                if vx and vx > 0:
                    plot_x = vx if use_ev else 1240.0 / vx
                    ax.axvline(plot_x, color='black', linestyle='--', linewidth=1.0, alpha=0.4, 
                               label=line.get("label", "") if line.get("show_legend", True) else None)

            # Secondary axis for absorption overlay
            ax_abs = None
            show_abs = settings.get("overlay_absorption", False)

            for idx, trace in enumerate(traces):
                x, y = self._process_trace(trace["wavelengths"], trace["ea"], settings, idx)
                color = cmap(norm(trace.get("value", 0))) if vmin != vmax else cmap(idx/len(traces) if len(traces) > 1 else 0.5)
                ax.plot(x, y, color=color, linewidth=lw, label=trace["label"])

                if show_abs and "absorption" in trace:
                    if ax_abs is None:
                        ax_abs = ax.twinx()
                        ax_abs.set_ylabel("Absorbance (O.D.)", color="gray", alpha=0.7)
                        ax_abs.tick_params(axis='y', labelcolor="gray")
                    wl_abs, vals_abs = trace["absorption"]

                    # Apply wavelength mask to absorption overlay as well
                    abs_mask = (wl_abs >= w_min) & (wl_abs <= w_max)
                    wl_abs, vals_abs = wl_abs[abs_mask], vals_abs[abs_mask]

                    if len(wl_abs) > 0:
                        x_abs = 1240.0 / wl_abs if use_ev else wl_abs
                        ax_abs.plot(x_abs, vals_abs, color=color, linewidth=0.8, linestyle=':', alpha=0.4)

            if len(traces) > 1 and vmin != vmax and settings.get("show_colorbar", True):
                sm = plt.cm.ScalarMappable(cmap=cmap, norm=norm)
                cbar = figure.colorbar(sm, ax=ax, orientation='vertical', pad=0.02, fraction=0.04, aspect=30)
                # Limit the colorbar display to the actual data range [0, Max]
                cbar.ax.set_ylim(0, max_val)
                cbar.set_label("Temp (K)", fontsize=9)
                cbar.ax.tick_params(labelsize=8)

            ax.set_xlabel("Photon Energy (eV)" if use_ev else "Wavelength (nm)", labelpad=8)
            ax.set_ylabel("Normalized EA (a.u.)" if settings.get("normalize_to_peak") else "Electroabsorption (mOD)", labelpad=8)

            if kwargs.get("show_legend", settings.get("show_legend")):
                ax.legend(frameon=False, loc="upper right", fontsize=8)

            for spine in ax.spines.values(): spine.set_linewidth(1.2)
            return True
        except Exception as e:
            logger.exception(f"EATempProcessor.generate_plot error for path: {path}")
            return False

    def export_data(self, save_path: str, path=None) -> bool:
        try:
            json_data = self.get_json_data(path)
            settings = self.get_settings(json_data)
            traces = self._load_traces(json_data)
            if not traces: return False

            export_dict = {}
            use_ev = settings.get("convert_to_ev", False)
            x_label = "Energy (eV)" if use_ev else "Wavelength (nm)"
            y_prefix = "Normalized EA (a.u.)" if settings.get("normalize_to_peak") else "Electroabsorption (mOD)"

            for i, trace in enumerate(traces):
                x, y = self._process_trace(trace["wavelengths"], trace["ea"], settings, i)
                if x_label not in export_dict: export_dict[x_label] = x
                export_dict[f"{y_prefix} - {trace['label']}"] = y

            pd.DataFrame(export_dict).to_csv(save_path, index=False)
            return True
        except Exception as e:
            logger.exception(f"EATempProcessor.export_data error for path: {path}")
            return False