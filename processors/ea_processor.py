import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from scipy.signal import savgol_filter
from pathlib import Path
from processors.public.read_colton_files import read_data_simple
from mpl_toolkits.axes_grid1.inset_locator import inset_axes
import processors.public.colton_math_functions as cmf
from utils.project_manager import ProjectManager
from processors.base_processor import BaseProcessor

# ──────────────────────────────────────────────────────────────────────────────
# Colorblind-friendly, high-contrast on white
# TRACE_COLORS = ["#1f4e79", "#c0392b", "#1a7a4a"] # No longer used, using colormap

class EAProcessor(BaseProcessor): 
    SMOOTH_WINDOW = 11   # must be odd
    SMOOTH_POLY   = 3
    OFFSET_STEP   = 1.0   # mOD units added per trace index when offset is on

    def __init__(self, parent_window):
        super().__init__(parent_window)

    # ── internal helpers ──────────────────────────────────────────────────────

    def _load_traces(self, json_data):
        """Load traces from the current experiment JSON."""
        data_files = json_data.get("data_files", {})
        tech = json_data.get("core", {}).get("technique", "")
        
        traces = []

        # 1. Load DC Transmission (Denominator for EA)
        dc_file = data_files.get("transmission_file")
        wl_dc, int_dc = self.load_raw_data(dc_file)
        if wl_dc is None:
            return []

        # 2. Load AC components (Voltage or Temperature series)
        scan_list = data_files.get("voltage_scans", []) or data_files.get("temperature_scans", [])
        
        # If no series list, fall back to sample_file
        if not scan_list and data_files.get("sample_file"):
            scan_list = [{"file": data_files.get("sample_file")}]

        # 3. Process each AC trace into EA signal
        for entry in scan_list:
            rel_path = entry.get("file")
            # Determine label
            if "voltage" in entry:
                label = f"{entry['voltage']} V"
            elif "temperature" in entry:
                label = f"{entry['temperature']} K"
            else:
                label = "EA Trace"

            wl_ac, int_ac = self.load_raw_data(rel_path)
            if wl_ac is not None:
                # Interpolate DC onto AC wavelengths
                int_dc_interp = np.interp(wl_ac, wl_dc, int_dc)
                # Use public math function: EA = -log(1 + AC/DC) * 1000
                ea_vals = cmf.EA(int_ac, int_dc_interp)
                
                # Extract numeric value for colormap mapping
                val = entry.get("voltage") or entry.get("temperature") or 0

                traces.append({
                    "wavelengths": wl_ac,
                    "ea": ea_vals,
                    "label": label,
                    "value": val
                })

        return traces

    def _process_trace(
        self, wl: np.ndarray, ea: np.ndarray, settings: dict, trace_idx: int,
    ):
        """
        Apply all active analysis options to one trace.
        Returns (x, y) arrays ready for ax.plot().
        """
        x = wl.copy()
        y = ea.copy()

        # 1. Smooth
        if settings.get("smooth_data"):
            win = self.SMOOTH_WINDOW
            if len(y) > win:
                y = savgol_filter(y, window_length=win, polyorder=self.SMOOTH_POLY)

        # 3. Flip Sign (Phase correction)
        if settings.get("flip_sign"):
            y = -y

        # 4. Normalize (before offset so scale is clean)
        if settings.get("normalize_to_peak"):
            peak = np.max(np.abs(y))
            if peak > 0:
                y = y / peak

        # 5. Vertical offset between traces
        if settings.get("offset_traces"):
            y = y + trace_idx * self.OFFSET_STEP

        # 6. Convert x to eV  (done last so x limits / labels are set once)
        if settings.get("convert_to_ev"):
            with np.errstate(divide="ignore", invalid="ignore"):
                x = np.where(x > 0, 1240.0 / x, np.nan)

        return x, y

    # ── main entry point ──────────────────────────────────────────────────────

    def generate_plot(self, figure, ax=None, path=None, **kwargs) -> bool:
        """Draw all traces onto *figure* according to the current settings."""
        try:
            json_data = self.get_json_data(path)
            settings = self.get_settings(json_data).copy() # Copy to avoid mutating original

            # Global Overrides (Option 1 & 4)
            if kwargs.get("force_unit") == "eV":
                settings["convert_to_ev"] = True
            elif kwargs.get("force_unit") == "nm":
                settings["convert_to_ev"] = False
            
            use_ev = settings.get("convert_to_ev", False)
            lw = settings.get("line_width", kwargs.get("line_width", 1.5))

            if ax is None:
                ax = figure.add_subplot(111)

            # Title handling
            if settings.get("show_title", True):
                title = settings.get("plot_title", "")
                if title and title != "False":
                    ax.set_title(title, pad=15)

            tech = json_data.get("core", {}).get("technique", "")
            # Get colormap for plotting
            colormap_name = settings.get("colormap_name", "viridis") # Default to 'viridis'
            cmap = plt.get_cmap(colormap_name)

            # Load traces once for efficiency and color mapping
            traces = self._load_traces(json_data)
            num_traces = len(traces)
            if num_traces == 0:
                return False

            # Determine values for the colorbar
            vals = [t.get("value", 0) for t in traces]
            vmin, vmax = min(vals), max(vals)
            norm = plt.Normalize(vmin=vmin, vmax=vmax)

            # Add horizontal line at Y=0 if enabled
            if settings.get("show_zero_line"):
                ax.axhline(0, color='Black', linewidth=0.8, linestyle='solid', alpha=0.6, zorder=0)

            # Add vertical reference lines if configured
            v_lines = settings.get("vertical_lines") or []
            for line in (v_lines if isinstance(v_lines, list) else []):
                vx = line.get("x")
                v_lbl = line.get("label", "")
                show_lgnd = line.get("show_legend", True)
                if vx is not None and vx > 0:
                    # Apply unit conversion if necessary (input is now assumed eV)
                    plot_x = vx if use_ev else 1240.0 / vx
                    ax.axvline(
                        plot_x, color='black', linestyle='--', 
                        linewidth=1.0, alpha=0.4, label=v_lbl if show_lgnd else None, zorder=1
                    )

            for idx, trace in enumerate(traces):
                x, y = self._process_trace(
                    trace["wavelengths"],
                    trace["ea"],
                    settings,
                    idx,
                )
                
                # Use physical value for color if a range exists, else fallback to index
                if vmin != vmax:
                    color = cmap(norm(trace.get("value", 0)))
                else:
                    color = cmap(idx / (num_traces - 1) if num_traces > 1 else 0.5)

                ax.plot(x, y, color=color, linewidth=lw)

            # Add slender vertical colorbar on the right if enabled
            if num_traces > 1 and vmin != vmax and settings.get("show_colorbar", True):
                sm = plt.cm.ScalarMappable(cmap=cmap, norm=norm)
                # pad=0.02 pulls it closer, fraction=0.04 makes it thin, aspect=30 makes it tall
                cbar = figure.colorbar(sm, ax=ax, orientation='vertical', pad=0.02, fraction=0.04, aspect=30)
                cb_label = "Voltage (V)" if "Voltage" in tech else "Temp (K)"
                cbar.set_label(cb_label, fontsize=9)
                cbar.ax.tick_params(labelsize=8)

            # Axis labels
            if use_ev:
                ax.set_xlabel("Photon Energy (eV)", labelpad=8)
                # eV data goes high→low from the conversion; invert so
                # energy increases left to right
                # ax.invert_xaxis()
            else:
                ax.set_xlabel("Wavelength (nm)", labelpad=8)

            if settings.get("normalize_to_peak"):
                ax.set_ylabel("Normalized EA (a.u.)", labelpad=8)
            else:
                ax.set_ylabel("Electroabsorption (mOD)", labelpad=8)

            # Legend
            handles, labels = ax.get_legend_handles_labels()
            if handles and kwargs.get("show_legend", settings.get("show_legend")):
                ax.legend(handles, labels, frameon=False, loc="upper right", fontsize=8)

            # Boxed spines (rcParams already mirrors ticks on all 4 sides)
            for spine in ax.spines.values():
                spine.set_linewidth(1.2)

            return True

        except Exception as e:
            print(f"EAProcessor.generate_plot error: {e}")
            return False

    def export_data(self, save_path: str, path=None) -> bool:
        """Exports the processed numerical data to a CSV file."""
        try:
            json_data = self.get_json_data(path)
            settings = self.get_settings(json_data)
            
            traces = self._load_traces(json_data)
            if not traces:
                return False

            export_dict = {}
            use_ev = settings.get("convert_to_ev", False)
            x_label = "Energy (eV)" if use_ev else "Wavelength (nm)"
            
            # Prefix for Y columns based on normalization
            y_prefix = "Normalized EA (a.u.)" if settings.get("normalize_to_peak") else "Electroabsorption (mOD)"

            for i, trace in enumerate(traces):
                x, y = self._process_trace(trace["wavelengths"], trace["ea"], settings, i)
                
                # Only add the X column once
                if x_label not in export_dict:
                    export_dict[x_label] = x
                
                # Create a unique column name for this trace (e.g., "Electroabsorption (mOD) - 100V")
                col_name = f"{y_prefix} - {trace['label']}"
                export_dict[col_name] = y

            df = pd.DataFrame(export_dict)
            df.to_csv(save_path, index=False)
            return True
        except Exception as e:
            print(f"EAProcessor.export_data error: {e}")
            return False
