from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QLabel, QFrame, QCheckBox, QFileDialog, QSizePolicy, QComboBox
)
from PyQt6.QtCore import Qt
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qtagg import NavigationToolbar2QT as NavigationToolbar
from matplotlib.figure import Figure
from pathlib import Path

from utils.project_manager import ProjectManager
from config.techniques import TECHNIQUE_CONFIG, ANALYSIS_OPTION_META
from processors.factory import get_processor
from ui.analysis_settings_panel import AnalysisSettingsPanel, _palette
 

class AnalysisTab(QWidget):
    """
    Two-section layout:

    ┌─────────────────────────────────────────────────────┐
    │  [Run Analysis]  [Save for Publication]   status…   │  ← control bar
    ├─────────────────────────────────────────────────────┤
    │  ── Absorption — Analysis Options ──────────────    │
    │  ☑ Smooth Data  ☑ Flip Y-axis  ☐ Convert X → eV …  │  ← options toolbar
    ├─────────────────────────────────────────────────────┤
    │  [matplotlib nav toolbar]                           │
    │                                                     │
    │            scientific plot (white bg)               │
    │                                                     │
    └─────────────────────────────────────────────────────┘

    Options are technique-specific: they come from TECHNIQUE_CONFIG
    → "analysis_options" and ANALYSIS_OPTION_META for labels/tooltips.
    Each checkbox auto-saves to the JSON and triggers an immediate replot.
    """

    def __init__(self, parent_window):
        super().__init__()
        self.parent_window = parent_window
        self._current_technique: str | None = None
        self._current_processor = None
        self._settings_panel = AnalysisSettingsPanel(self.parent_window)
        self._settings_panel.settingChanged.connect(self._on_setting_changed)
        self._init_ui()

    def _init_ui(self):
        root = QVBoxLayout(self)
        root.setSpacing(0)
        root.setContentsMargins(0, 0, 0, 0)

        # 1. Top control bar ───────────────────────────────────────────────────
        ctrl_frame = QFrame()
        ctrl_frame.setFrameShape(QFrame.Shape.StyledPanel)
        ctrl_layout = QHBoxLayout(ctrl_frame)
        ctrl_layout.setContentsMargins(8, 6, 8, 6)

        self.btn_run = QPushButton("Run Analysis")
        self.btn_run.setStyleSheet("font-weight: bold; padding: 5px 12px;")
        self.btn_run.clicked.connect(self.execute_plot)

        self.btn_save = QPushButton("Save for Publication")
        self.btn_save.setStyleSheet("padding: 5px 12px;")
        self.btn_save.clicked.connect(self.save_publication_plot)

        self.btn_export = QPushButton("📤  Export Data")
        self.btn_export.setStyleSheet("padding: 5px 12px;")
        self.btn_export.clicked.connect(self.export_processed_data)
        
        # Get the panel's palette for consistent accent color
        is_dark = getattr(self.parent_window, "dark_mode", True)
        C = _palette(is_dark)
        
        self.btn_settings = QPushButton("⚙  Analysis Settings")
        self.btn_settings.setStyleSheet(f"""
            QPushButton {{
                background-color: {C['accent']};
                color: {C['text_primary']};
                border: none;
                font-weight: 600;
                padding: 5px 12px;
                border-radius: 4px;
            }}
            QPushButton:hover, QPushButton:checked {{
                background-color: {C['accent_dim']};
            }}
        """)
        self.btn_settings.setCheckable(True)
        self.btn_settings.clicked.connect(self.toggle_settings_panel)

        self.status_label = QLabel("Ready")
        self.status_label.setStyleSheet("color: grey; font-style: italic;")

        ctrl_layout.addWidget(self.btn_run)
        ctrl_layout.addWidget(self.btn_save)
        ctrl_layout.addWidget(self.btn_export)
        ctrl_layout.addSpacing(8)
        ctrl_layout.addWidget(self.btn_settings)
        ctrl_layout.addSpacing(12)
        ctrl_layout.addWidget(self.status_label)
        ctrl_layout.addStretch()
        root.addWidget(ctrl_frame)

        # Thin separator
        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setFrameShadow(QFrame.Shadow.Sunken)
        root.addWidget(sep)

        # 3. Plot area ─────────────────────────────────────────────────────────
        self.figure = Figure(layout='constrained', facecolor="white")
        self.canvas = FigureCanvas(self.figure)
        self.canvas.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding
        )

        # Matplotlib's built-in zoom/pan/home/save toolbar
        self.nav_toolbar = NavigationToolbar(self.canvas, self)

        plot_frame = QFrame()
        plot_layout = QVBoxLayout(plot_frame)
        plot_layout.setContentsMargins(4, 4, 4, 4)
        plot_layout.setSpacing(0)
        plot_layout.addWidget(self.nav_toolbar)
        plot_layout.addWidget(self.canvas)

        root.addWidget(plot_frame, stretch=1)

    def toggle_settings_panel(self):
        if self._settings_panel.isVisible():
            self._settings_panel.hide()
        else:
            # Position it near the button but slightly offset
            btn_pos = self.btn_settings.mapToGlobal(self.btn_settings.rect().bottomLeft())
            self._settings_panel.move(btn_pos.x(), btn_pos.y() + 10)
            self._settings_panel.show()
        self.btn_settings.setChecked(self._settings_panel.isVisible())

    def rebuild_options_toolbar(self, technique: str):
        """
        Updates the floating settings panel with new technique options.
        """
        self._current_technique = technique
        self._current_processor = get_processor(technique, self.parent_window)

        # Retrieve and initialize saved states from the experiment JSON
        json_data = ProjectManager.Session.get_data()
        if "analysis_settings" not in json_data:
            json_data["analysis_settings"] = {}
        saved = json_data["analysis_settings"]

        cfg = TECHNIQUE_CONFIG.get(technique, {})
        options: list[str] = cfg.get("analysis_options", [])
        # Ensure all available options are populated in the session data with defaults upon initialization
        modified = False
        for key in options:
            if key not in saved:
                meta = ANALYSIS_OPTION_META.get(key, {})
                w_type = meta.get("type", "checkbox")
                if w_type == "combo":
                    opts = meta.get("options", [])
                    saved[key] = meta.get("default", opts[0] if opts else "")
                elif w_type == "list_of_dicts":
                    saved[key] = meta.get("default", [])
                elif w_type == "text":
                    saved[key] = meta.get("default", "")
                else:
                    saved[key] = meta.get("default", False)
                modified = True

        if modified:
            ProjectManager.Session.save()

        self._settings_panel.rebuild(technique, saved)

    # ──────────────────────────────────────────────────────────────────────────
    # Alias kept for backward compatibility with existing callers
    # ──────────────────────────────────────────────────────────────────────────
    def rebuild_settings_header(self, technique: str):
        self.rebuild_options_toolbar(technique)

    # ──────────────────────────────────────────────────────────────────────────
    # Checkbox handler
    # ──────────────────────────────────────────────────────────────────────────

    def _on_setting_changed(self, key: str, value):
        """Persist setting state to JSON then immediately replot."""
        json_data = ProjectManager.Session.get_data()
        if "analysis_settings" not in json_data:
            json_data["analysis_settings"] = {}
        json_data["analysis_settings"][key] = value

        # Persist to disk
        ProjectManager.Session.save()
        
        # Notify other tabs (Comparison Basket) that this experiment's settings changed
        self.parent_window.experimentDataChanged.emit(str(ProjectManager.Session.get_path()))

        self.execute_plot(trigger_key=key)

    # Public alias used by external callers in the original code
    def update_setting(self, key: str, value):
        self._on_setting_changed(key, value)
    def _on_option_toggled(self, key: str, checked: bool):
        self._on_setting_changed(key, checked)

    # ──────────────────────────────────────────────────────────────────────────
    # Plotting
    # ──────────────────────────────────────────────────────────────────────────

    def execute_plot(self, trigger_key: str | None = None):
        """Select the correct processor and redraw the canvas."""
        tech = self._current_technique
        if not tech:
            # Fall back to the discovery tab's selection if available
            discovery = getattr(self.parent_window, "discovery_tab", None)
            tech = getattr(discovery, "_current_technique", None)
        if not tech:
            self.status_label.setText("Error: No experiment selected")
            return

        self.status_label.setText("Processing…")
        self.figure.clear()

        if self._current_processor is None:
            self.status_label.setText(f"No processor for '{tech}'")
            return

        success = self._current_processor.generate_plot(self.figure)
        if success:
            self.canvas.draw()
            self.status_label.setText("Plot updated")
        else: # If generate_plot returned False
            self.status_label.setText(f"Error in processing '{tech}' (processor returned False or no data)")

    # ──────────────────────────────────────────────────────────────────────────
    # Publication export
    # ──────────────────────────────────────────────────────────────────────────

    def save_publication_plot(self):
        """Open a save dialog and export the figure at journal dimensions."""
        # Default fallbacks
        initial_dir = Path(self.parent_window.base_dir)
        default_name = "publication_plot.pdf"
        
        discovery = getattr(self.parent_window, "discovery_tab", None)
        if discovery and discovery._current_json_path:
            # 1. Directory: The sample folder (parent of the JSON folder)
            initial_dir = discovery._current_json_path.parent.parent

            # 2. Filename: <Shorthand>_<SampleFolder>_<Experiment>.pdf
            full_tech = discovery._current_technique or "Technique"

            # Define shorthand mapping for the filename
            tech_map = {
                "Absorption": "ABS",
                "EA Voltage Series": "EA",
                "Circular Dichroism (CD)": "CD",
                "Photoluminescence (PL)": "PL"
            }
            tech_name = tech_map.get(full_tech, full_tech)

            sample_name = initial_dir.name
            exp_name    = discovery._current_json_path.stem
            default_name = f"{tech_name} - {sample_name} - {exp_name}.pdf"

        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Save Publication Plot",
            str(initial_dir / default_name),
            "PDF (*.pdf);;PNG (*.png);;SVG (*.svg)",
        )
        if not file_path:
            return

        tech = self._current_technique or ""
        if self._current_processor:
            self._current_processor.save_fixed_plot(self.figure, file_path)
            self.status_label.setText(f"Exported: {Path(file_path).name}")

    def export_processed_data(self):
        """Exports the processed numerical data to a CSV file."""
        if not self._current_processor:
            self.status_label.setText("Error: No data to export")
            return

        # Determine the default location and filename
        initial_dir = Path(self.parent_window.base_dir)
        default_name = "data_export.csv"
        
        discovery = getattr(self.parent_window, "discovery_tab", None)
        if discovery and discovery._current_json_path:
            initial_dir = discovery._current_json_path.parent.parent
            full_tech = discovery._current_technique or "Technique"
            
            tech_map = {
                "Absorption": "ABS",
                "EA Voltage Series": "EA",
                "Circular Dichroism (CD)": "CD",
                "Photoluminescence (PL)": "PL"
            }
            tech_name = tech_map.get(full_tech, "DATA")
            sample_name = initial_dir.name
            exp_name = discovery._current_json_path.stem
            default_name = f"{tech_name}_Export_{sample_name}_{exp_name}.csv"

        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Export Processed Data",
            str(initial_dir / default_name),
            "CSV Files (*.csv);;Text Files (*.txt)"
        )

        if not file_path:
            return

        success = self._current_processor.export_data(file_path)
        if success:
            self.status_label.setText(f"Data exported to {Path(file_path).name}")
        else:
            self.status_label.setText("Export failed")
