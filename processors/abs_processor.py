import numpy as np
import matplotlib.pyplot as plt
from scipy.signal import savgol_filter
from pathlib import Path
from processors.public.read_colton_files import read_data_simple
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
TRACE_COLORS = ["#1f4e79", "#c0392b", "#1a7a4a"]

class ABSProcessor:
    SMOOTH_WINDOW = 11   # must be odd
    SMOOTH_POLY   = 3
    OFFSET_STEP   = 0.15  # O.D. units added per trace index when offset is on

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
            int_key = "Phased (V)" if "Phased (V)" in data_dict else "R (V)"
            
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

        # 1. Load Blank/Baseline
        wl_b, int_b = self._load_data(data_files.get("blank_file"))

        # 2. Identify Sample Traces
        samples = [] # list of (rel_path, label)
        if "Series" in tech:
            # ABS Temp Series uses 'temperature_scans'
            for entry in data_files.get("temperature_scans", []):
                samples.append((entry.get("file"), f"{entry.get('temperature')} K"))
        else:
            # Standard Absorption
            samples.append((data_files.get("sample_file"), "Sample"))

        # 3. Process each sample into Absorbance
        for rel_path, label in samples:
            wl_s, int_s = self._load_data(rel_path)
            if wl_s is not None:
                abs_vals = self._calculate_absorbance(wl_s, int_s, wl_b, int_b)
                traces.append({
                    "wavelengths": wl_s,
                    "absorbance": abs_vals,
                    "label": label
                })

        return traces

    def _calculate_absorbance(self, wl_s, int_s, wl_b, int_b):
        """
        Calculates Absorbance = -log10(I_sample / I_blank).
        Interpolates blank data to match sample wavelengths if needed.
        """
        if wl_s is None or int_s is None:
            return None
        
        # If no blank, assume baseline is 1.0 (no correction)
        i0 = np.interp(wl_s, wl_b, int_b) if (wl_b is not None) else np.ones_like(int_s)
        
        with np.errstate(divide='ignore', invalid='ignore'):
            ratio = int_s / i0
            abs_vals = -np.log10(np.where(ratio > 0, ratio, 1e-9))
        return abs_vals

    def _process_trace(
        self,
        wl: np.ndarray,
        ab: np.ndarray,
        settings: dict,
        trace_idx: int,
    ):
        """
        Apply all active analysis options to one trace.
        Returns (x, y) arrays ready for ax.plot().
        """
        x = wl.copy()
        y = ab.copy()

        # 1. Smooth
        if settings.get("smooth_data"):
            win = self.SMOOTH_WINDOW
            if len(y) > win:
                y = savgol_filter(y, window_length=win, polyorder=self.SMOOTH_POLY)

        # 3. Normalize (before offset so scale is clean)
        if settings.get("normalize_to_peak"):
            peak = np.max(np.abs(y))
            if peak > 0:
                y = y / peak

        # 4. Vertical offset between traces
        if settings.get("offset_traces"):
            y = y + trace_idx * self.OFFSET_STEP

        # 5. Convert x to eV  (done last so x limits / labels are set once)
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
                    trace["absorbance"],
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
                ax.set_ylabel("Normalized Absorbance (a.u.)", labelpad=8)
            else:
                ax.set_ylabel("Absorbance (O.D.)", labelpad=8)

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


if __name__ == "__main__":
    # This block allows you to test the processor without running the main UI.
    class MockWindow:
        def __init__(self):
            # Set this to your project root or data root
            self.base_dir = Path(__file__).parent.parent
            
            # Example JSON structure as if it were loaded from DiscoveryTab
            self.current_exp_json = {
                "core": {"technique": "Absorption"},
                "data_files": {
                    "blank_file": "Data\\2026-05-06\\Blank AFRL Old L-Ala PbI3 #1 295K.xls",   # Replace with a real relative path to test
                    "sample_file": "Data\\2026-05-06\\Transmission AFRL Old L-Ala PbI3 #1 16K.xls",  # Replace with a real relative path to test
                },
                "analysis_settings": {
                    "smooth_data": True,
                    "show_legend": True,
                    "convert_to_ev": False
                }
            }
        def save_current_json(self): pass

    # Create dummy data if no files provided
    win = MockWindow()
    processor = ABSProcessor(win)

    # # If no files are specified above, we'll override _load_traces for a quick visual test
    # if win.current_exp_json["data_files"]["sample_file"] is None:
    #     print("No files specified in MockWindow. Using synthetic data for demonstration.")
    #     def mock_load():
    #         wl = np.linspace(350, 800, 200)
    #         return [{
    #             "wavelengths": wl,
    #             "absorbance": 0.5 * np.exp(-((wl-500)/50)**2) + np.random.normal(0, 0.01, 200),
    #             "label": "Synthetic Test"
    #         }]
    #     processor._load_traces = mock_load

    fig = plt.figure(figsize=(6, 5))
    success = processor.generate_plot(fig)
    
    if success:
        plt.show()