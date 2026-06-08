import numpy as np
import matplotlib.pyplot as plt
from scipy.signal import savgol_filter
from pathlib import Path
from utils.project_manager import ProjectManager
from processors.base_processor import BaseProcessor

# ──────────────────────────────────────────────────────────────────────────────
# Colorblind-friendly, high-contrast on white
PRIMARY_TRACE_COLOR = "#1f4e79"  # Standard dark blue for single absorption plots

class ABSProcessor(BaseProcessor):
    SMOOTH_WINDOW = 11   # must be odd
    SMOOTH_POLY   = 3
    OFFSET_STEP   = 0.15  # O.D. units added per trace index when offset is on

    def __init__(self, parent_window):
        super().__init__(parent_window)

    # ── internal helpers ──────────────────────────────────────────────────────

    def _load_traces(self, json_data, json_path=None):
        """Load traces from the current experiment JSON."""
        data_files = json_data.get("data_files", {})
        
        # Extract the "Global Sample Name" from the experiment's folder structure
        # Structure: .../SpectraLink_Data/Collaborator/SampleName/JSON/Experiment.json
        target_path = json_path or self.data_path
        label = Path(target_path).parent.parent.name if target_path else "Sample"

        traces = []

        # 1. Load Blank/Baseline
        wl_b, int_b = self.load_raw_data(data_files.get("blank_file"))

        # 2. Identify Sample Trace
        samples = [(data_files.get("sample_file"), label)]

        # 3. Process each sample into Absorbance
        for rel_path, label in samples:
            wl_s, int_s = self.load_raw_data(rel_path)
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

        # 0. Wavelength Cutoff (nm)
        # Applied first so smoothing/normalization ignores cropped data
        w_min = settings.get("min_wavelength", 0.0)
        w_max = settings.get("max_wavelength", 10000.0)
        mask = (x >= w_min) & (x <= w_max)
        x = x[mask]
        y = y[mask]

        if len(x) == 0:
            return x, y

        # 1. Smooth
        if settings.get("smooth_data"):
            win = int(settings.get("smooth_window", self.SMOOTH_WINDOW))
            poly = int(settings.get("smooth_poly", self.SMOOTH_POLY))

            # Savitzky-Golay requirements: win > poly
            if poly >= win:
                poly = win - 1

            if len(y) > win:
                y = savgol_filter(y, window_length=win, polyorder=poly)

        # 3. Normalize (before offset so scale is clean)
        if settings.get("normalize_to_peak"):
            peak = np.max(np.abs(y))
            if peak > 0:
                y = y / peak

        # 3.5 Scaling Factor
        scaling = settings.get("scaling_factor", 1.0)
        y = y * scaling

        # 4. Vertical offset between traces
        if settings.get("offset_traces"):
            y = y + trace_idx * self.OFFSET_STEP

        # 5. Convert x to eV  (done last so x limits / labels are set once)
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
            json_path = path or self.data_path

            # Global Overrides (Option 1)
            if kwargs.get("force_unit") == "eV":
                settings["convert_to_ev"] = True
            elif kwargs.get("force_unit") == "nm":
                settings["convert_to_ev"] = False

            if ax is None:
                ax = figure.add_subplot(111)

            use_ev = settings.get("convert_to_ev", False)

            # Title handling
            if settings.get("show_title", True):
                title = settings.get("plot_title", "")
                if title and title != "False":
                    ax.set_title(title, pad=15)
            
            traces = self._load_traces(json_data, json_path)
            if not traces:
                return False

            # Add vertical reference lines if configured
            v_lines = settings.get("vertical_lines") or []
            for line in (v_lines if isinstance(v_lines, list) else []):
                vx = line.get("x")
                v_lbl = line.get("label", "")
                show_lgnd = line.get("show_legend", True)
                if vx is not None and vx > 0:
                    # Apply unit conversion if necessary (input is assumed eV)
                    plot_x = vx if use_ev else 1240.0 / vx
                    ax.axvline(
                        plot_x, color='black', linestyle='--', 
                        linewidth=1.0, alpha=0.4, label=v_lbl if show_lgnd else None, zorder=1
                    )

            trace = traces[0]
            x, y = self._process_trace(trace["wavelengths"], trace["absorbance"], settings, 0)

            lw = settings.get("line_width", kwargs.get("line_width", 1.5))
            # Use color from analysis settings if defined, else default blue
            color = settings.get("trace_color", PRIMARY_TRACE_COLOR)
            ax.plot(x, y, color=color, linewidth=lw, label=trace["label"])

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
            # Respect global override for showing individual legends (Option 3)
            if kwargs.get("show_legend", settings.get("show_legend")):
                ax.legend(frameon=False, loc="upper right", fontsize=8)

            # Boxed spines (rcParams already mirrors ticks on all 4 sides)
            for spine in ax.spines.values():
                spine.set_linewidth(1.2)

            return True

        except Exception as e:
            print(f"ABSProcessor.generate_plot error: {e}")
            return False

# if __name__ == "__main__":
#     # This block allows you to test the processor without running the main UI.
#     class MockWindow:
#         def __init__(self):
#             # Set this to your project root or data root
#             self.base_dir = Path(__file__).parent.parent
            
#             # Example JSON structure as if it were loaded from DiscoveryTab
#             self.current_exp_json = {
#                 "core": {"technique": "Absorption"},
#                 "data_files": {
#                     "blank_file": "Data\\2026-05-06\\Blank AFRL Old L-Ala PbI3 #1 295K.xls",   # Replace with a real relative path to test
#                     "sample_file": "Data\\2026-05-06\\Transmission AFRL Old L-Ala PbI3 #1 16K.xls",  # Replace with a real relative path to test
#                 },
#                 "analysis_settings": {
#                     "smooth_data": True,
#                     "show_legend": True,
#                     "convert_to_ev": False
#                 }
#             }
#         def save_current_json(self): pass

#     # Create dummy data if no files provided
#     win = MockWindow()
#     processor = ABSProcessor(win)

#     fig = plt.figure(figsize=(6, 5))
#     success = processor.generate_plot(fig)
    
#     if success:
#         plt.show()
