from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QLabel, QFrame, QCheckBox, QFileDialog, QSizePolicy,
)
from PyQt6.QtCore import Qt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT as NavigationToolbar
from matplotlib.figure import Figure
from pathlib import Path

from utils.project_manager import ProjectManager
from config.techniques import TECHNIQUE_CONFIG, ANALYSIS_OPTION_META
 

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
        self._checkboxes: dict[str, QCheckBox] = {}   # key → widget
        self._current_technique: str | None = None
        self._init_ui()

    # ──────────────────────────────────────────────────────────────────────────
    # UI construction
    # ──────────────────────────────────────────────────────────────────────────

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

        self.status_label = QLabel("Ready")
        self.status_label.setStyleSheet("color: grey; font-style: italic;")

        ctrl_layout.addWidget(self.btn_run)
        ctrl_layout.addWidget(self.btn_save)
        ctrl_layout.addSpacing(12)
        ctrl_layout.addWidget(self.status_label)
        ctrl_layout.addStretch()
        root.addWidget(ctrl_frame)

        # 2. Options toolbar ───────────────────────────────────────────────────
        self.options_frame = QFrame()
        self.options_frame.setFrameShape(QFrame.Shape.StyledPanel)
        self.options_frame.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed
        )
        self._options_layout = QHBoxLayout(self.options_frame)
        self._options_layout.setContentsMargins(8, 4, 8, 4)
        self._options_layout.setSpacing(16)

        # Placeholder label shown before any experiment is loaded
        self._options_placeholder = QLabel(
            "Select an experiment to see analysis options."
        )
        self._options_placeholder.setStyleSheet("color: grey; font-style: italic;")
        self._options_layout.addWidget(self._options_placeholder)
        self._options_layout.addStretch()

        root.addWidget(self.options_frame)

        # Thin separator
        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setFrameShadow(QFrame.Shadow.Sunken)
        root.addWidget(sep)

        # 3. Plot area ─────────────────────────────────────────────────────────
        self.figure = Figure(tight_layout=True, facecolor="white")
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

    # ──────────────────────────────────────────────────────────────────────────
    # Options toolbar — rebuild when technique changes
    # ──────────────────────────────────────────────────────────────────────────

    def rebuild_options_toolbar(self, technique: str):
        """
        Clear old checkboxes and build new ones from TECHNIQUE_CONFIG.
        Called by the discovery tab whenever the user selects an experiment.
        """
        self._current_technique = technique
        self._checkboxes.clear()

        # Remove all existing widgets
        while self._options_layout.count():
            item = self._options_layout.takeAt(0)
            w = item.widget()
            if w:
                w.deleteLater()

        cfg = TECHNIQUE_CONFIG.get(technique, {})
        options: list[str] = cfg.get("analysis_options", [])

        if not options:
            lbl = QLabel("No analysis options for this technique.")
            lbl.setStyleSheet("color: grey; font-style: italic;")
            self._options_layout.addWidget(lbl)
            self._options_layout.addStretch()
            return

        # Section header label
        header = QLabel(f"{technique} — Analysis Options")
        header.setStyleSheet("font-weight: bold; padding-right: 8px;")
        self._options_layout.addWidget(header)

        # Thin vertical divider
        div = QFrame()
        div.setFrameShape(QFrame.Shape.VLine)
        div.setFrameShadow(QFrame.Shadow.Sunken)
        self._options_layout.addWidget(div)

        # Retrieve saved states from the experiment JSON
        saved: dict = ProjectManager.Session.get_data().get(
            "analysis_settings", {}
        )

        for key in options:
            meta = ANALYSIS_OPTION_META.get(key, {})
            label_text = meta.get("label", key.replace("_", " ").title())
            tooltip     = meta.get("tooltip", "")

            cb = QCheckBox(label_text)
            cb.setToolTip(tooltip)
            cb.setChecked(saved.get(key, False))

            # Live replot on toggle
            cb.toggled.connect(
                lambda checked, k=key: self._on_option_toggled(k, checked)
            )

            self._checkboxes[key] = cb
            self._options_layout.addWidget(cb)

        self._options_layout.addStretch()

    # ──────────────────────────────────────────────────────────────────────────
    # Alias kept for backward compatibility with existing callers
    # ──────────────────────────────────────────────────────────────────────────
    def rebuild_settings_header(self, technique: str):
        self.rebuild_options_toolbar(technique)

    # ──────────────────────────────────────────────────────────────────────────
    # Checkbox handler
    # ──────────────────────────────────────────────────────────────────────────

    def _on_option_toggled(self, key: str, checked: bool):
        """Persist checkbox state to JSON then immediately replot."""
        json_data = ProjectManager.Session.get_data()
        if "analysis_settings" not in json_data:
            json_data["analysis_settings"] = {}
        json_data["analysis_settings"][key] = checked

        # Persist to disk
        ProjectManager.Session.save()

        # Live replot
        self.execute_plot()

    # Public alias used by external callers in the original code
    def update_setting(self, key: str, value: bool):
        self._on_option_toggled(key, value)

    # ──────────────────────────────────────────────────────────────────────────
    # Plotting
    # ──────────────────────────────────────────────────────────────────────────

    def execute_plot(self):
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

        processor = self._get_processor(tech)
        if processor is None:
            self.status_label.setText(f"No processor for '{tech}'")
            return

        success = processor.generate_plot(self.figure)
        if success:
            self.canvas.draw()
            self.status_label.setText("Plot updated")
        else:
            self.status_label.setText("Error in processing")

    def _get_processor(self, tech: str):
        """Instantiate the correct processor based on the technique name."""
        tech_lower = tech.lower()

        if "electro" in tech_lower or tech_lower.startswith("ea"):
            from processors.ea_processor import EAProcessor
            return EAProcessor(self.parent_window)

        if "circular" in tech_lower or "cd" in tech_lower:
            # Placeholder — wire up CDProcessor when ready
            from processors.abs_processor import ABSProcessor
            return ABSProcessor(self.parent_window)

        if "photoluminescence" in tech_lower or "pl" in tech_lower:
            # Placeholder — wire up PLProcessor when ready
            from processors.abs_processor import ABSProcessor
            return ABSProcessor(self.parent_window)

        # Default: absorption
        from processors.abs_processor import ABSProcessor
        return ABSProcessor(self.parent_window)

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
        processor = self._get_processor(tech)
        if processor:
            processor.save_fixed_plot(self.figure, file_path)
            self.status_label.setText(f"Exported: {Path(file_path).name}")
