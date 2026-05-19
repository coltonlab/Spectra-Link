import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path
from utils.project_manager import ProjectManager
from processors.public.read_colton_files import read_data_simple

class BaseProcessor:
    """Base class for all spectroscopic data processors to eliminate code duplication."""
    
    def __init__(self, parent_window):
        self.parent_window = parent_window
        self._raw_traces = None  # Cache for calculated physics traces
        self.apply_publication_style()

    def apply_publication_style(self):
        plt.rcParams.update({
            "font.family": "serif",
            "font.serif": ["Times New Roman"],
            "font.size": 10,
            "axes.linewidth": 1.2,
            "xtick.direction": "in",
            "ytick.direction": "in",
            "savefig.dpi": 300,
        })

    def get_settings(self) -> dict:
        return ProjectManager.Session.get_data().get("analysis_settings", {})

    def load_raw_data(self, rel_path):
        """Standardized data loader for all children."""
        # Handle input types (dict from JSON or Path objects)
        if isinstance(rel_path, dict):
            rel_path = rel_path.get("path") or rel_path.get("file")
        
        if isinstance(rel_path, Path):
            rel_path = str(rel_path)
            
        if not rel_path:
            return None, None
        
        full_path = Path(self.parent_window.base_dir) / Path(rel_path)
        if not full_path.exists():
            return None, None

        try:
            data_dict = read_data_simple(str(full_path))
            keys = list(data_dict.keys())
            wl_key = next((k for k in data_dict.keys() if "Spectr" in k), None)
            
            # Priority list: We want signed data (Phased X) over unsigned magnitude (R)
            priority = ["X (V) Phased", "X (V) Phased Average", "Phased (V)", "R (V)", "X (V)"]
            int_key = next((p for p in priority if p in data_dict), None)

            if wl_key and int_key:
                return data_dict[wl_key], data_dict[int_key]
        except Exception as e:
            print(f"Error loading {rel_path}: {e}")
        return None, None

    def save_fixed_plot(self, figure, file_path: str):
        """Common export logic for all processors."""
        orig_size = figure.get_size_inches()
        figure.set_size_inches(3.5, 2.8)
        plt.rcParams["font.size"] = 8
        figure.savefig(file_path, dpi=600, bbox_inches="tight", facecolor="white")
        figure.set_size_inches(orig_size)
        plt.rcParams["font.size"] = 10