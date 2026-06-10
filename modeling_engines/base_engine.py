from abc import ABC, abstractmethod
from matplotlib.figure import Figure
from PyQt6.QtWidgets import QVBoxLayout

class BaseModelingEngine(ABC):
    """
    Abstract Base Class for all modeling and fitting plugins.
    Defines how models interact with the UI, data session, and plots.
    """
    def __init__(self, parent_tab):
        self.parent_tab = parent_tab
        self.results = {}

    @abstractmethod
    def build_ui(self, layout: QVBoxLayout):
        """Construct the UI widgets (parameters, buttons) for the modeling side-panel."""
        pass

    @abstractmethod
    def run_modeling(self):
        """
        Execute the mathematical calculations. 
        Should pull data from ProjectManager.Session.
        """
        pass

    @abstractmethod
    def plot_results(self, figure: Figure):
        """Update the canvas figure with the fit result overlaid on experimental data."""
        pass

    def get_results(self) -> dict:
        """Return the calculated results/parameters for persistence in JSON."""
        return self.results