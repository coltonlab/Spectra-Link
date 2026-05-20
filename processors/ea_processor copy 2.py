import numpy as np
import matplotlib.pyplot as plt
from scipy.signal import savgol_filter
from pathlib import Path
from processors.public.read_colton_files import read_data_simple
from mpl_toolkits.axes_grid1.inset_locator import inset_axes
import processors.public.colton_math_functions as cmf
from utils.project_manager import ProjectManager

# ──────────────────────────────────────────────────────────────────────────────
# Publication-style Matplotlib settings
# ──────────────────────────────────────────────────────────────────────────────
def apply_publication_style():
    """Sets global Matplotlib parameters for paper-ready plots."""
    plt.rcParams.update({
        "font.family":       "serif",
        "font.serif":        ["Times New Roman"],
        "font.size":         10,
        "axes.titlesize":    10,
        "axes.labelsize":    10,
        "xtick.labelsize":   8,
        "ytick.labelsize":   8,
        "legend.fontsize":   8,
        "axes.linewidth":    1.2,
        "lines.linewidth":   1.5,
        "xtick.direction":   "in",
        "ytick.direction":   "in",
        "xtick.major.size":  5,
        "ytick.major.size":  5,
        "xtick.top":         True,   # mirror ticks → boxed look
        "ytick.right":       True,
        "savefig.dpi":       300,
        "axes.grid":         False,
        "figure.facecolor":  "white",
        "axes.facecolor":    "white",
    })


# ──────────────────────────────────────────────────────────────────────────────
# Colorblind-friendly, high-contrast on white
# TRACE_COLORS = ["#1f4e79", "#c0392b", "#1a7a4a"] # No longer used, using colormap

class EAProcessor: 
    SMOOTH_WINDOW = 11   # must be odd
    SMOOTH_POLY   = 3
    OFFSET_STEP   = 1.0   # mOD units added per trace index when offset is on

    def __init__(self, parent_window):
        self.parent_window = parent_window
        apply_publication_style()

    # ── internal helpers ──────────────────────────────────────────────────────

    def _get_settings(self) -> dict:
        return ProjectManager.Session.get_data().get("analysis_settings", {})

    def _load_data(self, rel_path):
        """Loads a data file using the public reader and extracts wl/intensity."""
        if isinstance(rel_path, dict):
            rel_path = rel_path.get("path") or rel_path.get("file")

        if isinstance(rel_path, Path):
            rel_path = str(rel_path)

        if not rel_path:
            return None, None
        
        full_path = self.parent_window.base_dir / Path(rel_path)
        if not full_path.exists():
            print(f"File not found: {full_path}")
            return None, None

        try:
            # read_data_simple returns a dict of numpy arrays (already phased)
            data_dict = read_data_simple(str(full_path))
            
            # Detect columns: look for Spectrometer (WL) and Phased/R (Intensity)
            wl_key = next((k for k in data_dict.keys() if "Spectr" in k), None)
            # Use Phased (V) if available (phased by read_data_simple), else R (V)
            int_key = "X (V) Phased" if "X (V) Phased" in data_dict else "R (V)"
            
            if wl_key and int_key in data_dict:
                return data_dict[wl_key], data_dict[int_key]
        except Exception as e:
            print(f"Error loading {rel_path}: {e}")
        return None, None

    def _load_traces(self):
        """Load traces from the current experiment JSON."""
        json_data = ProjectManager.Session.get_data()
        data_files = json_data.get("data_files", {})
        tech = json_data.get("core", {}).get("technique", "")
        
        traces = []

        # 1. Load DC Transmission (Denominator for EA)
        dc_file = data_files.get("transmission_file")
        wl_dc, int_dc = self._load_data(dc_file)
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

            wl_ac, int_ac = self._load_data(rel_path)
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

    def generate_plot(self, figure) -> bool:
        """Draw all traces onto *figure* according to the current settings."""
        try:
            settings = self._get_settings()
            ax = figure.add_subplot(111)
            ax_abs = None  # Track secondary axis for legend

            use_ev = settings.get("convert_to_ev", False)

            # Get sample and experiment names for the title
            json_data = ProjectManager.Session.get_data()
            data_files = json_data.get("data_files", {})
            json_path = ProjectManager.Session.get_path()
            tech = json_data.get("core", {}).get("technique", "")
            if json_path:
                sample_name = json_path.parent.parent.name
            else:
                sample_name = json_data.get("core", {}).get("sample_name", "Unknown Sample")
            experiment_name = json_data.get("core", {}).get("experiment_name", "Unknown Experiment")
            ax.set_title(f"{sample_name} - {experiment_name}", pad=15)

            # Get colormap for plotting
            colormap_name = settings.get("colormap_name", "viridis") # Default to 'viridis'
            cmap = plt.get_cmap(colormap_name)

            # Load traces once for efficiency and color mapping
            traces = self._load_traces()
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

            # Overlay Absorption Trace (Behind)
            if settings.get("overlay_absorption"):
                blank_file = data_files.get("blank_file")
                dc_file = data_files.get("transmission_file")
                wl_b, int_b = self._load_data(blank_file)
                wl_dc, int_dc = self._load_data(dc_file)

                if wl_b is not None and wl_dc is not None:
                    # Interpolate DC onto Blank wavelengths
                    int_b_interp = np.interp(wl_dc, wl_b, int_b)
                    # Calculate Absorbance = -log10(Trans / Blank)
                    with np.errstate(divide='ignore', invalid='ignore'):
                        abs_vals = -np.log10(np.where(int_dc/int_b_interp > 0, int_dc/int_b_interp, 1e-9))
                    
                    ax_abs = ax.twinx()
                    
                    # Process absorption without EA-specific flipping or normalization
                    abs_settings = settings.copy()
                    abs_settings.update({"flip_sign": False, "normalize_to_peak": False, "offset_traces": False})
                    
                    x_abs, y_abs = self._process_trace(wl_dc, abs_vals, abs_settings, 0)
                    
                    # Plot absorption behind EA
                    ax_abs.plot(x_abs, y_abs, color='gray', linewidth=1.0, alpha=0.3, label='Absorption', zorder=0)
                    ax_abs.set_ylabel("Absorbance (O.D.)", labelpad=8, color='gray')
                    ax_abs.tick_params(axis='y', colors='gray', labelsize=8)
                    
                    # Move EA axes to the front
                    ax.set_zorder(ax_abs.get_zorder() + 1)
                    ax.patch.set_visible(False)
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

                ax.plot(x, y, color=color, linewidth=1.5, label=trace["label"])

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

            # Unified Legend Handling
            if settings.get("show_legend"):
                h1, l1 = ax.get_legend_handles_labels()
                if ax_abs:
                    h2, l2 = ax_abs.get_legend_handles_labels()
                    h1 += h2
                    l1 += l2
                if h1:
                    ax.legend(h1, l1, frameon=False, loc="upper right")

            # Boxed spines (rcParams already mirrors ticks on all 4 sides)
            for spine in ax.spines.values():
                spine.set_linewidth(1.2)

            return True

        except Exception as e:
            print(f"EAProcessor.generate_plot error: {e}")
            return False








    # ── publication export ────────────────────────────────────────────────────
    def save_fixed_plot(self, figure, file_path: str):
        """
        Re-draws the figure at strict journal dimensions and saves.
        Single-column width = 3.5 in  |  height = 2.8 in  (4:3 ratio)
        """
        orig_size = figure.get_size_inches()
        figure.set_size_inches(3.5, 2.8)
        plt.rcParams["font.size"] = 8

        figure.savefig(
            file_path, dpi=600, bbox_inches="tight", facecolor="white"
        )

        # Restore UI state
        figure.set_size_inches(orig_size)
        plt.rcParams["font.size"] = 10
