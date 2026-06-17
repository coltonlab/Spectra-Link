from abc import ABCMeta, abstractmethod
import numpy as np
from PyQt6.QtWidgets import QWidget

class _WidgetABCMeta(ABCMeta, type(QWidget)):
    pass

class BaseModelingDashboard(QWidget, metaclass=_WidgetABCMeta):
    """
    Abstract Base Class for all Spectra-Link Modeling Dashboards.
    
    Every experimental model (e.g., FK-Analysis, Gaussian Fitting) must inherit 
    from this class. It enforces a standard interface that allows the main 
    application to dynamically load, update, and clean up modeling widgets.
    """

    def __init__(self, parent=None):
        """
        Initialize the dashboard. 
        Child classes should call build_ui() within their own __init__ or 
        rely on the main app lifecycle to trigger it.
        """
        super().__init__(parent)

    @abstractmethod
    def set_active_data(self, x_data: np.ndarray, y_data: np.ndarray, metadata_dict: dict):
        """
        The primary data 'handshake' method.
        
        Args:
            x_data (np.ndarray): The independent variable (e.g., Wavelength or Energy).
            y_data (np.ndarray): The dependent variable (e.g., Absorption or EA signal).
            metadata_dict (dict): The full experiment configuration from the JSON session,
                                 useful for retrieving temperature, field, or units.
        """
        pass

    @abstractmethod
    def build_ui(self):
        """
        Abstract method to construct the dashboard's layout.
        
        Child classes should implement this to create their specific nested layouts,
        pyqtgraph PlotWidgets, parameter sliders, and text output areas.
        """
        pass

    @abstractmethod
    def shutdown(self):
        """
        Cleanup protocol called before the widget is unmounted or destroyed.
        
        Implementations should:
        1. Stop any running QThreads or background workers.
        2. Disconnect any global signals (e.g., ProjectManager signals).
        3. Explicitly clear large numpy arrays if necessary to help GC.
        4. Close or clear pyqtgraph PlotWidgets.
        """
        pass

    def apply_theme(self, is_dark: bool):
        """
        Optional: Override this if the specific dashboard requires 
        custom plotting colors or stylesheet logic when themes change.
        """
        pass