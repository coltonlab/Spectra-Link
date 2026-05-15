import matplotlib.pyplot as plt
from pathlib import Path
from utils.project_manager import ProjectManager
from processors.public.read_colton_files import read_data_simple

class BaseProcessor:
    """Base class for all spectroscopic data processors to eliminate code duplication."""
    
    def __init__(self, parent_window):
        self.parent_window = parent_window
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
        if not rel_path:
            return None, None
        
        full_path = self.parent_window.base_dir / Path(rel_path)
        if not full_path.exists():
            return None, None

        try:
            data_dict = read_data_simple(str(full_path))
            wl_key = next((k for k in data_dict.keys() if "Spectr" in k), None)
            int_key = next((k for k in data_dict.keys() if "Phased" in k or "R (V)" in k), None)
            
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