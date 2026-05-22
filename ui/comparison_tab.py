from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFrame, 
    QSpinBox, QLabel, QSizePolicy, QPushButton, QMenu
)
from PyQt6.QtCore import Qt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT as NavigationToolbar
from matplotlib.figure import Figure
from pathlib import Path
from ui.comparison_settings_panel import ComparisonSettingsPanel
import json
import matplotlib.pyplot as plt

class ComparisonTab(QWidget):
    """
    Staging area for comparing multiple experiments in a grid.
    Supports dragging experiments from the sidebar onto specific cells for subplots or overlays.
    """
    def __init__(self, parent_window):
        super().__init__()
        self.parent_window = parent_window
        
        # Internal Data Structure: (row, col) -> [list of absolute paths to .json]
        # This mapping allows for multiple experiments (overlays) in a single subplot cell.
        self.grid_data = {}
        self._axes_map = {}      # Maps Matplotlib Axes -> (row, col)
        self._json_cache = {}    # Caches JSON content to avoid redundant disk I/O (Option 5)
        
        self.rows = 2
        self.cols = 1

        # Comparison settings panel
        self.settings_panel = ComparisonSettingsPanel(self.parent_window)
        self.settings_panel.settingChanged.connect(self.rebuild_plots)
        
        # Listen for changes made in Analysis or Discovery tabs
        self.parent_window.experimentDataChanged.connect(self._on_external_data_changed)

        self.setAcceptDrops(True)
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # 1. Top Control Toolbar
        ctrl_frame = QFrame()
        ctrl_frame.setFrameShape(QFrame.Shape.StyledPanel)
        ctrl_layout = QHBoxLayout(ctrl_frame)
        ctrl_layout.setContentsMargins(8, 6, 8, 6)

        ctrl_layout.addWidget(QLabel("<b>Grid Layout:</b>"))

        self.btn_settings = QPushButton("⚙  Visual Settings")
        self.btn_settings.setCheckable(True)
        self.btn_settings.clicked.connect(self.toggle_settings_panel)
        ctrl_layout.addWidget(self.btn_settings)
        
        self.spin_rows = QSpinBox()
        self.spin_rows.setRange(1, 4)
        self.spin_rows.setValue(self.rows)
        self.spin_rows.valueChanged.connect(self._on_grid_changed)
        
        self.spin_cols = QSpinBox()
        self.spin_cols.setRange(1, 4)
        self.spin_cols.setValue(self.cols)
        self.spin_cols.valueChanged.connect(self._on_grid_changed)

        ctrl_layout.addWidget(QLabel("Rows:"))
        ctrl_layout.addWidget(self.spin_rows)
        ctrl_layout.addWidget(QLabel("Cols:"))
        ctrl_layout.addWidget(self.spin_cols)
        
        ctrl_layout.addSpacing(20)
        
        self.btn_clear = QPushButton("Clear Grid")
        self.btn_clear.clicked.connect(self.clear_grid)
        ctrl_layout.addWidget(self.btn_clear)
        
        ctrl_layout.addStretch()
        layout.addWidget(ctrl_frame)

        # 2. Plot Area (Matplotlib Canvas)
        self.figure = Figure(layout='constrained', facecolor="white")
        self.canvas = FigureCanvas(self.figure)
        self.canvas.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.nav_toolbar = NavigationToolbar(self.canvas, self)
        
        # Connect Matplotlib events for right-click interaction (Option 6)
        self.canvas.mpl_connect('button_press_event', self._on_canvas_click)

        plot_frame = QFrame()
        plot_layout = QVBoxLayout(plot_frame)
        plot_layout.setContentsMargins(4, 4, 4, 4)
        plot_layout.setSpacing(0)
        plot_layout.addWidget(self.nav_toolbar)
        plot_layout.addWidget(self.canvas)
        
        layout.addWidget(plot_frame, stretch=1)
        
        self.rebuild_plots()

    def _on_external_data_changed(self, path_str):
        """Invalidates cache and refreshes plot if the changed data is in the grid."""
        if path_str in self._json_cache:
            del self._json_cache[path_str]
        
        # Only trigger a full rebuild if this experiment is actually currently in our grid
        for paths in self.grid_data.values():
            if path_str in paths:
                self.rebuild_plots()
                break

    def toggle_settings_panel(self):
        if self.settings_panel.isVisible():
            self.settings_panel.hide()
        else:
            btn_pos = self.btn_settings.mapToGlobal(self.btn_settings.rect().bottomLeft())
            self.settings_panel.move(btn_pos.x(), btn_pos.y() + 10)
            self.settings_panel.show()
        self.btn_settings.setChecked(self.settings_panel.isVisible())

    def _on_grid_changed(self):
        self.rows = self.spin_rows.value()
        self.cols = self.spin_cols.value()
        self.rebuild_plots()

    def _on_canvas_click(self, event):
        """Handles mouse clicks on the Matplotlib canvas."""
        # Right click = 3
        if event.button != 3 or event.inaxes is None:
            return
            
        # Identify the grid coordinate from the clicked axis
        target_rc = None
        for rc, ax in self._axes_map.items():
            if ax == event.inaxes:
                target_rc = rc
                break
        
        if target_rc:
            self._show_context_menu(target_rc, event)

    def _show_context_menu(self, rc, event):
        """Shows a menu to manage experiments in a specific cell."""
        paths = self.grid_data.get(rc, [])
        if not paths:
            return

        menu = QMenu(self)
        menu.addSection(f"Cell {rc[0]+1}, {rc[1]+1}")

        # --- Edit Settings Submenu ---
        edit_menu = menu.addMenu("Edit Settings")
        for path_str in paths:
            path_obj = Path(path_str)
            display_name = f"{path_obj.parent.parent.name} / {path_obj.stem}"
            action = edit_menu.addAction(display_name)
            action.triggered.connect(lambda checked, p=path_str: self._edit_experiment_settings(p))

        # --- Remove Plot Submenu ---
        remove_menu = menu.addMenu("Remove Plot")
        for path_str in paths:
            path_obj = Path(path_str)
            display_name = f"{path_obj.parent.parent.name} / {path_obj.stem}"
            action = remove_menu.addAction(display_name)
            action.triggered.connect(lambda checked, p=path_str: self._remove_single_experiment(rc, p))

        menu.addSeparator()
        clear_act = menu.addAction("Clear All in Cell")
        clear_act.triggered.connect(lambda: self._clear_cell(rc))

        menu.exec(self.canvas.mapToGlobal(self.canvas.mapFromGlobal(self.mapToGlobal(event.guiEvent.pos()))))

    def _edit_experiment_settings(self, json_path: str):
        """
        Selects the given experiment in the sidebar and opens the Analysis Settings panel.
        """
        # 1. Select the experiment in the sidebar
        self.parent_window.sidebar.select_path(Path(json_path))

        # 2. Switch to the Analysis tab
        # self.parent_window.tabs.setCurrentWidget(self.parent_window.analysis_tab)

        # 3. Open the Analysis Settings panel if it's not already visible
        if not self.parent_window.analysis_tab._settings_panel.isVisible():
            self.parent_window.analysis_tab.toggle_settings_panel()

    def _remove_single_experiment(self, rc, path_str):
        """Removes a single experiment from a specific grid cell."""
        if rc in self.grid_data and path in self.grid_data[rc]:
            self.grid_data[rc].remove(path)
            # If the list for this cell becomes empty, remove the key from grid_data
            if not self.grid_data[rc]:
                del self.grid_data[rc]
            self.rebuild_plots()

    def _clear_cell(self, rc):
        if rc in self.grid_data:
            del self.grid_data[rc]
            self.rebuild_plots()

    def clear_grid(self):
        self.grid_data = {}
        self._json_cache = {} # Clear memory cache as well
        self.rebuild_plots()

    def dragEnterEvent(self, event):
        if event.mimeData().hasText():
            event.acceptProposedAction()

    def dropEvent(self, event):
        path_str = event.mimeData().text()
        # Calculate which grid cell the user dropped the file on
        canvas_pos = self.canvas.mapFromGlobal(self.mapToGlobal(event.position().toPoint()))
        
        col = int(canvas_pos.x() / (self.canvas.width() / self.cols))
        row = int(canvas_pos.y() / (self.canvas.height() / self.rows))
        
        # Clamp to ensure we are within grid bounds
        row = max(0, min(row, self.rows - 1))
        col = max(0, min(col, self.cols - 1))
        
        key = (row, col)
        if key not in self.grid_data:
            self.grid_data[key] = []
        
        if path_str not in self.grid_data[key]:
            self.grid_data[key].append(path_str)
            self.rebuild_plots()

    def rebuild_plots(self):
        """Re-generates the grid of subplots based on current rows/cols and grid_data."""
        from processors.factory import get_processor
        gs = self.settings_panel.get_settings()
        
        self.figure.clear()
        self._axes_map = {}
        
        # Use squeeze=False so axes is always a 2D array [row, col]
        # sharex=True enables linked zooming across all subplots
        axes = self.figure.subplots(self.rows, self.cols, sharex=True, squeeze=False)
        
        # Option 2: Layout Geometry
        self.figure.subplots_adjust(hspace=gs["hspace"], wspace=gs["wspace"])
        
        # Option 1: Unit Police Logic
        force_unit = None
        if gs["force_unit"] != "None (Use Saved)":
            force_unit = "eV" if "eV" in gs["force_unit"] else "nm"
        
        for r in range(self.rows):
            for c in range(self.cols):
                ax = axes[r, c]
                self._axes_map[(r, c)] = ax
                
                paths = self.grid_data.get((r, c), [])
                if not paths:
                    # Show clean placeholder if cell is empty
                    msg = "Drop Experiment Here"
                    if self.rows > 2 or self.cols > 2: msg = "Drop Here"
                    ax.text(0.5, 0.5, msg, ha='center', va='center', 
                            alpha=0.3, transform=ax.transAxes, fontsize=9)
                    continue
                
                # Overlay Loop: Render every experiment assigned to this grid cell
                for i, path in enumerate(paths):
                    try:
                        # OPTION 5: Check local JSON cache before hitting disk
                        if path in self._json_cache:
                            data = self._json_cache[path]
                        else:
                            with open(path, 'r') as f:
                                data = json.load(f)
                            if len(self._json_cache) < 50: # Cap cache size
                                self._json_cache[path] = data
                        
                        tech = data.get("core", {}).get("technique")
                        processor = get_processor(tech, self.parent_window)
                        
                        # Pass global overrides to the processor
                        processor.generate_plot(
                            self.figure, ax=ax, path=path, 
                            force_unit=force_unit,         # Option 1
                            line_width=gs["line_width"],   # Option 4
                            show_legend=(gs["legend_mode"] == "Individual") # Option 3
                        )
                    except Exception as e:
                        print(f"ComparisonTab: Error rendering {path}: {e}")

                # Option 2: Clean outer look
                if gs["label_outer"]:
                    ax.label_outer()

        # Option 3: Global Legend Logic
        if gs["legend_mode"] == "Global Figure Legend":
            handles, labels = [], []
            for ax in self._axes_map.values():
                h, l = ax.get_legend_handles_labels()
                handles.extend(h); labels.extend(l)
            # Remove duplicates for the figure legend
            by_label = dict(zip(labels, handles))
            if by_label:
                self.figure.legend(by_label.values(), by_label.keys(), loc='upper center', 
                                   bbox_to_anchor=(0.5, 1.02), ncol=3, frameon=False)

        self.canvas.draw()