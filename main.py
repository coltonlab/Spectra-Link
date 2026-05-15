import sys
from pathlib import Path
from PyQt6.QtWidgets import QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QTabWidget
from PyQt6.QtCore import Qt

from ui.theme import get_theme, apply_palette_to_app

# Local Imports from your new folders
from ui.discovery_tab import DiscoveryTab
from ui.analysis_tab import AnalysisTab
from ui.stylesheets import build_stylesheet
from ui.sidebar import SidebarWidget

# ──────────────────────────────────────────────────────────────────────────────
#  Main window
# ──────────────────────────────────────────────────────────────────────────────
class SpectraLink(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("SPECTRA-LINK | Research Data Management")
        self.resize(1100, 720)
        self.base_dir = Path("Data")
        self.dark_mode = True
        self.init_ui()

    # ------------------------------------------------------------------ INIT UI
    def init_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        self.sidebar = SidebarWidget(self)
        main_layout.addWidget(self.sidebar)

        # ── Tabs ──────────────────────────────────────────────────────────────
        content = QWidget()
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(8, 8, 8, 8)

        self.tabs = QTabWidget()
        self.discovery_tab = DiscoveryTab(self)
        self.tabs.addTab(self.discovery_tab, "Discovery/Selection")

        self.analysis_tab = AnalysisTab(self)
        self.tabs.addTab(self.analysis_tab, "Interactive Analysis")

        self.tabs.addTab(QWidget(), "Comparison Basket")
        content_layout.addWidget(self.tabs)
        main_layout.addWidget(content, 1)

        # ── Signals ───────────────────────────────────────────────────────────
        self.sidebar.experimentChanged.connect(self._on_exp_changed)

        self.sidebar.update_root()
        self.apply_theme()

    def _on_exp_changed(self):
        self.discovery_tab.refresh_target_label()
        tech = getattr(self.discovery_tab, '_current_technique', None)
        if tech:
            self.analysis_tab.rebuild_settings_header(tech)

    # ──────────────────────────────────────────────────────────────────────────
    #  Theme
    # ──────────────────────────────────────────────────────────────────────────
    def _on_theme_toggle(self, is_dark: bool):
        """Slot connected to the ToggleSwitch toggled signal."""
        self.dark_mode = is_dark
        self.apply_theme()
        self.discovery_tab.apply_theme(is_dark)

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


# ──────────────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = SpectraLink()
    window.show()
    sys.exit(app.exec())
