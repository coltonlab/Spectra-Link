from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFrame, 
    QSpinBox, QLabel, QSizePolicy, QPushButton, QMenu, QMessageBox, QFileDialog, QInputDialog
)
from PyQt6.QtCore import Qt
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qtagg import NavigationToolbar2QT as NavigationToolbar
from matplotlib.figure import Figure
from pathlib import Path
from ui.comparison_settings_panel import ComparisonSettingsPanel
from utils.project_manager import ProjectManager
import json
from utils.app_logger import logger # Import the global logger
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
        
        self.btn_save_config = QPushButton("Save Configuration")
        self.btn_save_config.clicked.connect(self._save_comparison_config)
        ctrl_layout.addWidget(self.btn_save_config)
        
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

        # --- Reset Defaults Submenu ---
        reset_menu = menu.addMenu("Reset to Defalt Settings")
        for path_str in paths:
            path_obj = Path(path_str)
            display_name = f"{path_obj.parent.parent.name} / {path_obj.stem}"
            action = reset_menu.addAction(display_name)
            action.triggered.connect(lambda checked, p=path_str: self._reset_experiment_settings(p))

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

    def _reset_experiment_settings(self, path_str: str):
        """Clears the analysis settings for a specific experiment JSON file on disk."""
        path_obj = Path(path_str)
        reply = QMessageBox.question(
            self, "Reset to Default",
            f"Are you sure you want to reset all analysis settings for '{path_obj.stem}' back to default?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            try:
                # 1. Read the JSON file
                with open(path_str, 'r') as f:
                    data = json.load(f)
                
                # 2. Clear the settings (the system will use factory defaults when empty)
                data["analysis_settings"] = {}
                
                # 3. Write back to disk
                with open(path_str, 'w') as f:
                    json.dump(data, f, indent=4)
                
                # 4. Invalidate the memory cache
                if path_str in self._json_cache:
                    del self._json_cache[path_str]
                
                # 5. Notify the rest of the app to update (e.g., Analysis and Discovery tabs)
                self.parent_window.experimentDataChanged.emit(path_str)
                
                # 6. If this file is the active session, reload the session object
                if str(ProjectManager.Session.get_path()) == path_str:
                    ProjectManager.Session.load_experiment(path_obj)
                
                self.rebuild_plots()
            except Exception as e:
                print(f"ComparisonTab: Error resetting settings for {path_str}: {e}")

    def _remove_single_experiment(self, rc, path_str):
        """Removes a single experiment from a specific grid cell."""
        if rc in self.grid_data and path_str in self.grid_data[rc]:
            self.grid_data[rc].remove(path_str)
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
            event.acceptProposedAction()
            self.rebuild_plots()

    def _save_comparison_config(self):
        """
        Saves the current comparison grid configuration to the 'Comparison Plots' folder
        of the collaborator associated with the experiment in the top-left cell (0,0).
        """
        # 1. Identify reference experiment from the Row 1, Col 1 cell (index 0,0)
        paths = self.grid_data.get((0, 0), []) # This is a list of paths
        if not paths:
            QMessageBox.warning(self, "Missing Reference", 
                "Please add at least one experiment to the top-left cell (Row 1, Col 1) "
                "so the system knows which collaborator folder to save in.")
            return

        # 2. Extract collaborator name from the reference path
        # Structure: .../SpectraLink_Data/[Collaborator]/[Sample]/JSON/[File].json
        ref_path = Path(paths[0])
        try:
            collab_name = ref_path.parent.parent.parent.name
            save_dir = self.parent_window.base_dir / "SpectraLink_Data" / collab_name / "Comparison Plots"
            save_dir.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            QMessageBox.critical(self, "Path Error", f"Could not determine save location: {e}")
            return

        data_root = self.parent_window.base_dir / "SpectraLink_Data"

        # 3. Ask user for a filename via text input
        name, ok = QInputDialog.getText(self, "Save Comparison Plot", "Enter a name for this comparison configuration:")
        if not ok or not name.strip():
            return
        
        file_path = save_dir / f"{name.strip()}.json"

        try:
            # Convert tuple keys in grid_data to strings for JSON serialization
            serializable_grid_data = {
                f"{r},{c}": [
                    {
                        "path": Path(path_str).relative_to(data_root).as_posix(),
                        "analysis_settings": (
                            # Try to get from cache first, otherwise hit disk
                            self._json_cache.get(path_str, {}).get("analysis_settings") or 
                            (lambda p: (json.load(open(p, 'r', encoding='utf-8')) if Path(p).exists() else {}).get("analysis_settings", {}))(path_str)
                            if not self._json_cache.get(path_str) else 
                            self._json_cache[path_str].get("analysis_settings", {})
                        ) if path_str in self._json_cache else 
                        json.load(open(path_str, 'r', encoding='utf-8')).get("analysis_settings", {}) if Path(path_str).exists() else {}
                    }
                    for path_str in paths_list
                ]
                for (r, c), paths_list in self.grid_data.items()
            }
            
            config_data = {
                "rows": self.rows,
                "cols": self.cols,
                "grid_data": serializable_grid_data,
                "settings": self.settings_panel.get_settings()
            }
            
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(config_data, f, indent=4)
            
            logger.info(f"Comparison configuration saved to: {file_path}")
            
            # Refresh sidebar so the new config appears in the tree
            self.parent_window.sidebar.update_root()
            
        except Exception as e:
            QMessageBox.critical(self, "Save Error", f"Failed to save configuration: {e}")
            logger.exception(f"Error saving comparison configuration to {file_path}")

    def load_config_from_path(self, file_path: Path):
        """Loads a comparison configuration from a specific file path."""
        data_root = self.parent_window.base_dir / "SpectraLink_Data"

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                config_data = json.load(f)
            
            # Validate required keys
            if not all(k in config_data for k in ["rows", "cols", "grid_data", "settings"]):
                raise ValueError("Invalid configuration file format.")
            
            # Clear current grid and cache
            self.clear_grid()
            
            # Update rows and cols
            self.rows = config_data["rows"]
            self.cols = config_data["cols"]
            self.spin_rows.setValue(self.rows)
            self.spin_cols.setValue(self.cols)
            
            # Deserialize grid_data: convert string keys back to tuples
            self.grid_data = {
                tuple(map(int, k.split(','))): v
                for k, v in config_data["grid_data"].items()
            }
            
            # Apply individual experiment analysis settings
            new_grid_data = {}
            for (r, c), experiments_with_settings in self.grid_data.items():
                paths_for_cell = []
                for exp_data in experiments_with_settings:
                    rel_path = exp_data["path"]
                    path_obj = data_root / rel_path
                    path_str = str(path_obj)
                    loaded_analysis_settings = exp_data["analysis_settings"]
                    
                    # Update the actual experiment JSON file on disk safely
                    if path_obj.exists():
                        try:
                            with open(path_str, 'r', encoding='utf-8') as f:
                                exp_json = json.load(f)
                            exp_json["analysis_settings"] = loaded_analysis_settings
                            with open(path_str, 'w', encoding='utf-8') as f:
                                json.dump(exp_json, f, indent=4)
                        except Exception as e:
                            logger.error(f"Failed to update settings for {path_str}: {e}")
                    
                    # Invalidate cache and notify other tabs
                    if path_str in self._json_cache: 
                        del self._json_cache[path_str]
                    
                    # If this experiment is the active session, reload it to reflect changes in Analysis Tab
                    if str(ProjectManager.Session.get_path()) == path_str:
                        ProjectManager.Session.load_experiment(path_obj)
                        
                    self.parent_window.experimentDataChanged.emit(path_str)
                    paths_for_cell.append(path_str)
                new_grid_data[(r, c)] = paths_for_cell
            self.grid_data = new_grid_data
            
            # Apply settings to the settings panel
            self.settings_panel.set_settings(config_data["settings"])
            
            self.rebuild_plots()
            logger.info(f"Comparison configuration loaded from: {file_path}")
        except Exception as e:
            QMessageBox.critical(self, "Load Error", f"Failed to load configuration: {e}")
            logger.exception(f"Error loading comparison configuration from {file_path}")

    def rebuild_plots(self):
        """Re-generates the grid of subplots based on current rows/cols and grid_data."""
        from processors.factory import get_processor
        gs = self.settings_panel.get_settings()
        
        self.figure.clear()
        self._axes_map = {}

        # Apply the spacing from the settings panel using the constrained layout engine
        # this replaces subplots_adjust which is incompatible with this engine.
        self.figure.set_constrained_layout_pads(wspace=gs["wspace"], hspace=gs["hspace"])
        
        # Use squeeze=False so axes is always a 2D array [row, col]
        # sharex=True/all enables linked zooming and panning across the entire grid
        axes = self.figure.subplots(self.rows, self.cols, sharex=True, squeeze=False)
        
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
                        
                        tech = data.get("core", {}).get("technique", "Unknown") # Provide default
                        processor = get_processor(tech, self.parent_window)
                        
                        # Pass global overrides to the processor
                        processor.generate_plot(
                            self.figure, ax=ax, path=path, 
                            force_unit=force_unit,         # Option 1
                            line_width=gs["line_width"],   # Option 4
                            show_legend=(gs["legend_mode"] == "Individual") # Option 3
                        )
                    except Exception:
                        logger.exception(f"ComparisonTab: Error rendering experiment from path: {path}")

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

        # Constrained layout handles the final alignment automatically
        self.canvas.draw()