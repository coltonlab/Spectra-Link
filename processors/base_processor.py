import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path
import json
from utils.project_manager import ProjectManager
from processors.public.read_colton_files import read_data_simple
from utils.app_logger import logger # Import the global logger

class BaseProcessor:
    """Base class for all spectroscopic data processors to eliminate code duplication."""
    
    def __init__(self, parent_window, data_path=None):
        self.parent_window = parent_window
        self.data_path = Path(data_path) if data_path else None
        self._raw_traces = None  # Cache for calculated physics traces
        self.apply_publication_style()

    def apply_publication_style(self):
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

    def get_json_data(self, path=None):
        """Helper to get experiment JSON data either from a path or current session."""
        target_path = path or self.data_path
        if target_path:
            try:
                with open(target_path, 'r') as f:
                    return json.load(f)
            except Exception as e:
                logger.exception(f"BaseProcessor: Error loading JSON from {target_path}")
                return {}
        return ProjectManager.Session.get_data()

    def get_settings(self, json_data=None) -> dict:
        """Get analysis settings from provided JSON data or fallback to session."""
        data = json_data if json_data is not None else self.get_json_data()
        return data.get("analysis_settings", {})

    def load_raw_data(self, rel_path, priority=None):
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
            logger.warning(f"Data file not found: {full_path}")
            return None, None

        try:
            data_dict = read_data_simple(str(full_path))
            if not data_dict:
                logger.warning(f"File loaded but contained no data: {rel_path}")
                return None, None

            # More flexible wavelength detection
            wl_key = next((k for k in data_dict.keys() if any(x in k for x in ["Spectr", "Wavelength", "Energy", "nm", "eV"])), None)
            
            # Default priority list: We want signed data (Phased X) over unsigned magnitude (R)
            search_priority = priority or ["X (V) Phased", "X (V) Phased Average", "Phased (V)", "R (V)", "X (V)"]
            int_key = next((p for p in search_priority if p in data_dict), None)

            if wl_key and int_key:
                return data_dict[wl_key], data_dict[int_key]
            
            logger.warning(f"Could not find required columns in {rel_path}. Keys found: {list(data_dict.keys())}")
        except Exception as e:
            logger.exception(f"Error loading raw data from {rel_path}")
        return None, None

    def save_fixed_plot(self, figure, file_path: str):
        """Common export logic for all processors."""
        orig_size = figure.get_size_inches()
        figure.set_size_inches(3.5, 2.8)
        plt.rcParams["font.size"] = 8
        figure.savefig(file_path, dpi=600, bbox_inches="tight", facecolor="white")
        figure.set_size_inches(orig_size)
        plt.rcParams["font.size"] = 10