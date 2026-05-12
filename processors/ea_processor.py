import numpy as np
import matplotlib.pyplot as plt
from scipy.signal import savgol_filter
from pathlib import Path
from processors.public.read_colton_files import read_data_simple
import processors.public.colton_math_functions as cmf

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
TRACE_COLORS = ["#1f4e79", "#c0392b", "#1a7a4a"]

class EAProcessor:
    SMOOTH_WINDOW = 11   # must be odd
    SMOOTH_POLY   = 3
    OFFSET_STEP   = 1.0   # mOD units added per trace index when offset is on

    def __init__(self, parent_window):
        self.parent_window = parent_window
        apply_publication_style()

    # ── internal helpers ──────────────────────────────────────────────────────

    def _get_settings(self) -> dict:
        return self.parent_window.current_exp_json.get("analysis_settings", {})

    def _load_data(self, rel_path: str):
        """Loads a data file using the public reader and extracts wl/intensity."""
        if not rel_path:
            return None, None
        
        full_path = self.parent_window.base_dir / rel_path
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
        json_data = self.parent_window.current_exp_json
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
                
                traces.append({
                    "wavelengths": wl_ac,
                    "ea": ea_vals,
                    "label": label
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

            use_ev = settings.get("convert_to_ev", False)

            for idx, trace in enumerate(self._load_traces()):
                x, y = self._process_trace(
                    trace["wavelengths"],
                    trace["ea"],
                    settings,
                    idx,
                )
                color = TRACE_COLORS[idx % len(TRACE_COLORS)]
                ax.plot(x, y, color=color, linewidth=1.5, label=trace["label"])

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
            if settings.get("show_legend"):
                ax.legend(frameon=False, loc="upper right")

            # Boxed spines (rcParams already mirrors ticks on all 4 sides)
            for spine in ax.spines.values():
                spine.set_linewidth(1.2)

            figure.tight_layout()
            return True

        except Exception as e:
            print(f"ABSProcessor.generate_plot error: {e}")
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
