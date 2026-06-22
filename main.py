import sys
import os
from pathlib import Path
from PyQt6.QtWidgets import QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QTabWidget, QSplitter, QSplashScreen, QMessageBox
from PyQt6.QtCore import Qt, pyqtSignal, QStandardPaths, QTimer
from PyQt6.QtGui import QIcon, QPixmap

from ui.theme import get_theme, apply_palette_to_app

# Local Imports from your new folders
from ui.discovery_tab import DiscoveryTab
from ui.analysis_tab import AnalysisTab
from ui.comparison_tab import ComparisonTab
from ui.modeling_tab import ModelingTab # Import ModelingTab from its new location
from ui.stylesheets import build_stylesheet
from utils.app_logger import setup_logging, logger
from ui.sidebar import SidebarWidget

# ──────────────────────────────────────────────────────────────────────────────
import numpy as np # Added for mock data generation
def resource_path(relative_path):
    """ Get absolute path to resource, works for dev and for PyInstaller """
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

def get_base_data_dir():
    """
    Gets a persistent path for data. 
    Avoids sys._MEIPASS because that folder is temporary and deleted on exit.
    """
    # 1. Check for Lab Standard C:\Data (Physical Lab Machine)
    if sys.platform == "win32":
        lab_root = Path("C:/Data")
        if lab_root.exists():
            return lab_root

    # 2. Check for 'Data' folder next to the executable/script (Portable Mode)
    local_data = Path(os.path.abspath(os.path.dirname(sys.argv[0]))) / "Data"
    if local_data.exists():
        return local_data

    # 3. Fallback to User Documents (Standard Installation)
    return Path(QStandardPaths.writableLocation(QStandardPaths.StandardLocation.DocumentsLocation)) / "SpectraLink_Data"

# ──────────────────────────────────────────────────────────────────────────────
#  Main window
# ──────────────────────────────────────────────────────────────────────────────
class SpectraLink(QMainWindow):
    # Global signal to notify tabs when any experiment's underlying JSON data has changed.
    # The string parameter is the absolute path to the modified JSON file.
    experimentDataChanged = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self.setWindowTitle("SPECTRA-LINK | Research Data Management")
        self.resize(1100, 720)
        self.base_dir = get_base_data_dir()
        self.dark_mode = True

        self.init_ui()

        # Set Window Icon using platform-specific format from the bundled Images folder
        icon_ext = 'ico' if sys.platform == 'win32' else 'icns'
        icon_path = resource_path(os.path.join('Images', f'SpectraLink_Icon.{icon_ext}'))
        
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))

    # ------------------------------------------------------------------ INIT UI
    def init_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Use a Splitter to allow resizing the sidebar
        self.splitter = QSplitter(Qt.Orientation.Horizontal)

        self.sidebar = SidebarWidget(self)

        # ── Tabs ──────────────────────────────────────────────────────────────
        content = QWidget()
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(8, 8, 8, 8)

        self.tabs = QTabWidget()
        self.discovery_tab = DiscoveryTab(self)
        self.tabs.addTab(self.discovery_tab, "Discovery/Selection")

        self.analysis_tab = AnalysisTab(self)
        self.tabs.addTab(self.analysis_tab, "Interactive Analysis")

        self.modeling_tab = ModelingTab(self)
        self.tabs.addTab(self.modeling_tab, "Modeling")

        self.comparison_tab = ComparisonTab(self)
        self.tabs.addTab(self.comparison_tab, "Comparison Basket")
        content_layout.addWidget(self.tabs)

        # Add components to splitter
        self.splitter.addWidget(self.sidebar)
        self.splitter.addWidget(content)
        self.splitter.setStretchFactor(1, 1) # Ensure content area expands
        self.splitter.setSizes([220, 880])    # Set initial default width

        main_layout.addWidget(self.splitter)

        # ── Signals ───────────────────────────────────────────────────────────
        self.sidebar.experimentChanged.connect(self._on_exp_changed)
        self.tabs.currentChanged.connect(self._on_tab_changed)

        self.sidebar.update_root()
        self.apply_theme()

    def _on_exp_changed(self):
        self.discovery_tab.refresh_target_label()
        tech = getattr(self.discovery_tab, '_current_technique', None)
        
        # Always notify AnalysisTab to rebuild or clear stale states
        self.analysis_tab.rebuild_settings_header(tech)

        # Delegate modeling logic to the tab itself
        self.modeling_tab.refresh_from_session()
        
        # If the analysis tab is already visible, run analysis for the new experiment
        if self.tabs.currentWidget() == self.analysis_tab:
            self.analysis_tab.execute_plot()

    def _on_tab_changed(self, index):
        """
        When the user switches to the Interactive Analysis tab, automatically
        run the analysis for the currently selected experiment.
        """
        current_widget = self.tabs.widget(index)
        if current_widget == self.analysis_tab:
            # Check if an experiment is loaded before trying to run
            if self.discovery_tab._current_json_path:
                self.analysis_tab.execute_plot()

    # ──────────────────────────────────────────────────────────────────────────
    #  Theme
    # ──────────────────────────────────────────────────────────────────────────
    def _on_theme_toggle(self, is_dark: bool):
        """Slot connected to the ToggleSwitch toggled signal."""
        logger.info(f"Theme toggled: {'Dark' if is_dark else 'Light'} mode")
        self.dark_mode = is_dark
        self.apply_theme()

    def apply_theme(self):
        """
        Apply the full theme from theme.py to the entire application:
          - QSS stylesheet (all widgets, dialogs, menus, tooltips)
          - QPalette (covers native Qt dialogs: QMessageBox, QFileDialog, etc.)
          - ToggleSwitch pill colors
        """
        T = get_theme(self.dark_mode)

        # 1. Stylesheet — covers every QWidget subclass in this app
        QApplication.instance().setStyleSheet(build_stylesheet(T))

        # 2. QPalette — ensures native dialogs (QMessageBox, QFileDialog,
        #    QInputDialog) also inherit the correct colors
        apply_palette_to_app(QApplication.instance(), self.dark_mode)

        # 3. Update the Sidebar (includes ToggleSwitch colors)
        self.sidebar.apply_theme(T, self.dark_mode)
        self.discovery_tab.apply_theme(self.dark_mode)
        self.modeling_tab.apply_theme(self.dark_mode)


# ──────────────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    app = QApplication(sys.argv)
    setup_logging()

    # ── Splash Screen ─────────────────────────────────────────────────────────
    # Load the splash screen image from the bundled Images folder
    splash_path = resource_path(os.path.join('Images', 'SpectraLink Splash Screen.png'))
    splash = None
    if os.path.exists(splash_path):
        pixmap = QPixmap(splash_path)
        splash = QSplashScreen(pixmap)
        splash.show()
        # Process events to ensure the splash screen is painted immediately
        app.processEvents()

    window = SpectraLink()

    if splash:
        splash.finish(window) # Close splash once main window is ready

    window.show()
    sys.exit(app.exec())
