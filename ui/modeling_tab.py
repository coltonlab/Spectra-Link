from PyQt6.QtWidgets import (
    QComboBox, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame, QPushButton,
    QSizePolicy
)
from PyQt6.QtCore import Qt, QTimer, QThread, QObject, pyqtSignal, pyqtSlot
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qtagg import NavigationToolbar2QT as NavigationToolbar
from matplotlib.figure import Figure

from ui.modeling_settings_panel import ModelingSettingsPanel # New import
from ui.theme import get_theme
from ui.modeling_settings_panel import _palette # For button styling
from utils.project_manager import ProjectManager

class ModelingWorker(QObject):
    """Handles heavy mathematical fitting in a background thread."""
    finished = pyqtSignal()
    error = pyqtSignal(str)

    def __init__(self, engine):
        super().__init__()
        self.engine = engine

    @pyqtSlot()
    def run(self):
        try:
            self.engine.run_modeling()
            self.finished.emit()
        except Exception as e:
            self.error.emit(str(e))

class ModelingTab(QWidget):

    """
    UI Skeleton for advanced data modeling.
   Provides a sidebar for specific model parameters and a central plot
   for visualizing data-to-model fits.
    """
    def __init__(self, parent_window):
        super().__init__()
        self.parent_window = parent_window
        self._current_experiment_path = None # To store the path of the currently selected experiment
        self._current_technique = None
        self.active_engine = None # The current modeling plugin
        self._is_stale = False    # Tracks if analysis settings changed since last fit

        # Threading infrastructure
        self._worker_thread = None
        self._worker = None

        self._plot_interaction_mode = None # e.g., 'add_marker', 'define_range'
        self._mpl_cid = None # Matplotlib connection ID for mouse events
        
        self._autosave_timer = QTimer()
        self._autosave_timer.setSingleShot(True)
        self._autosave_timer.setInterval(800)
        self._autosave_timer.timeout.connect(self._write_json)

        self.modeling_settings_panel = ModelingSettingsPanel(self.parent_window)
        self.modeling_settings_panel.settingChanged.connect(self._on_setting_changed)
        self.modeling_settings_panel.hide()
        self._init_ui()
        self.apply_theme(self.parent_window.dark_mode)





    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # 1. Status Bar (Top) ──────────────────────────────────────────────────
        self.status_frame = QFrame()
        self.status_frame.setFixedHeight(34)
        status_layout = QHBoxLayout(self.status_frame)
        status_layout.setContentsMargins(12, 0, 12, 0)
        
        self.lbl_save_status = QLabel("")
        self.lbl_stale_warning = QLabel("⚠️  Fit is stale")
        self.btn_settings = QPushButton("⚙  Modeling Settings")
        self.btn_settings.setCheckable(True)
        self.btn_settings.clicked.connect(self.toggle_settings_panel)
        self.btn_run = QPushButton("▶  Run Model")
        self.btn_run.clicked.connect(self.update_plot)
        self.btn_run.setEnabled(False)
        self.combo_model_selector = QComboBox()
        self.combo_model_selector.setMinimumWidth(150)
        self.combo_model_selector.currentIndexChanged.connect(self._on_model_selection_changed)
        
        self.lbl_status = QLabel("No selection")
        self.lbl_technique = QLabel("") # Re-add lbl_technique to the layout

        status_layout.addWidget(self.btn_run)
        status_layout.addWidget(self.combo_model_selector)
        status_layout.addWidget(self.btn_settings)
        status_layout.addWidget(self.lbl_status)
        status_layout.addWidget(self.lbl_stale_warning)
        status_layout.addStretch()
        status_layout.addWidget(self.lbl_technique) # Add lbl_technique to the far right
        status_layout.addWidget(self.lbl_save_status)
        layout.addWidget(self.status_frame)
        # 2. Main Workspace ────────────────────────────────────────────────────
        workspace_layout = QVBoxLayout() # Changed to QVBoxLayout as sidebar is removed
        workspace_layout.setSpacing(0)

        # Central Plot Area
        plot_container = QFrame() # Changed to QFrame for consistent styling
        plot_layout = QVBoxLayout(plot_container)
        plot_layout.setContentsMargins(0, 0, 0, 0)
        plot_layout.setSpacing(0)

        self.figure = Figure(layout='constrained', facecolor="white")
        self.canvas = FigureCanvas(self.figure)
        self.canvas.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.nav_toolbar = NavigationToolbar(self.canvas, self)
        
        # Placeholder for dynamic UI, now in the main plot area
        self.placeholder_label = QLabel("Select an experiment to load model tools.")
        self.placeholder_label.setWordWrap(True)
        self.placeholder_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        plot_layout.addWidget(self.placeholder_label, stretch=1) # Add placeholder to plot area
        
        plot_layout.addWidget(self.nav_toolbar)
        plot_layout.addWidget(self.canvas)
        
        workspace_layout.addWidget(plot_container, stretch=1)
        layout.addLayout(workspace_layout)
        
    def toggle_settings_panel(self):
        if self.modeling_settings_panel.isVisible():
            self.modeling_settings_panel.hide()
        else:
            # Position it near the button but slightly offset
            btn_pos = self.btn_settings.mapToGlobal(self.btn_settings.rect().bottomLeft())
            self.modeling_settings_panel.move(btn_pos.x(), btn_pos.y() + 10)
            self.modeling_settings_panel.show()
        self.btn_settings.setChecked(self.modeling_settings_panel.isVisible())

    def _on_setting_changed(self, key: str, value):
        """
        Captures changes from the modeling panel and pushes them to the session.
        Triggers the autosave timer.
        """
        if not self._current_experiment_path:
            return

        data = ProjectManager.Session.get_data()
        modeling = data.setdefault("modeling", {})
        saved_results = modeling.setdefault("saved_results", {})
        tech_results = saved_results.setdefault(self._current_technique, {}) # Results for the current technique

        if key == "selected_model":
            tech_results[key] = value # Save which model is selected
        elif self.active_engine:
            # Use the display name from the selector to match factory keys and engine lookup logic
            engine_name = self.combo_model_selector.currentText()
            engine_data = tech_results.setdefault(engine_name, {})
            engine_data[key] = value
        else:
            # Fallback for general settings not tied to a specific engine
            tech_results[key] = value

        self._schedule_autosave()
    def _on_model_selection_changed(self, index: int):
        """Instantiates the new engine and rebuilds the settings panel."""
        if not self._current_technique:
            return

        selected_model_name = self.combo_model_selector.currentText()
        if not selected_model_name:
            self.active_engine = None
            self.modeling_settings_panel.rebuild(self._current_technique, {}, None)
            return

        from modeling_engines.factory import create_modeling_engine
        self.active_engine = create_modeling_engine(selected_model_name, self._current_technique, self)
        
        # Save the selected model to JSON
        self._on_setting_changed("selected_model", selected_model_name)

        # Rebuild panel and plot with the new active engine
        self.modeling_settings_panel.rebuild(self._current_technique, {}, self.active_engine)
        # Removed automatic update_plot() call

    def _on_plot_click(self, event):
        """Handles clicks on the Matplotlib canvas when in interactive mode."""
        if event.inaxes and event.button == 1: # Left click within axes
            if self._plot_interaction_mode == 'add_marker':
                if self.active_engine and hasattr(self.active_engine, 'handle_plot_click'):
                    self.active_engine.handle_plot_click(event.xdata)
                self._disable_plot_interaction()
            # Add other interaction modes here if needed

    def _enable_plot_interaction(self, mode: str):
        """Enables interactive mode for the plot, disabling default navigation."""
        if self._plot_interaction_mode: # Already in an interaction mode
            self._disable_plot_interaction()

        self._plot_interaction_mode = mode
        self.canvas.setCursor(Qt.CursorShape.CrossCursor)
        
        # Disable Matplotlib's default navigation
        self.nav_toolbar.set_active(None) # Disables all active modes (zoom, pan)
        self.nav_toolbar.update() # Refresh toolbar buttons

        # Connect our custom click handler
        self._mpl_cid = self.canvas.mpl_connect('button_press_event', self._on_plot_click)
        self.lbl_status.setText(f"Click on plot to {mode.replace('_', ' ')}...")
        self.btn_run.setEnabled(False) # Disable run button during interaction

    def _disable_plot_interaction(self):
        """Disables interactive mode for the plot, re-enabling default navigation."""
        if self._mpl_cid:
            self.canvas.mpl_disconnect(self._mpl_cid)
            self._mpl_cid = None

        self._plot_interaction_mode = None
        self.canvas.setCursor(Qt.CursorShape.ArrowCursor)

        # Re-enable Matplotlib's default navigation (if any were active before)
        # For simplicity, we just reset to default state.
        self.nav_toolbar.set_active('PAN') # Or 'ZOOM', or None if no default active
        self.nav_toolbar.update()
        self.lbl_status.setText("Ready") # Or restore previous status
        self.btn_run.setEnabled(True) # Re-enable run button

    def update_plot(self):
        """
        Triggers the active engine to recalculate in the background.
        """
        if not self.active_engine:
            return

        # If a worker thread is already running, do nothing
        if self._worker_thread and self._worker_thread.isRunning():
            return
        
        # Clean up any previous worker/thread objects if they haven't been fully deleted yet
        if self._worker_thread: self._worker_thread.deleteLater()
        if self._worker: self._worker.deleteLater()

        self.lbl_stale_warning.setVisible(False)
        self.lbl_status.setText("⚙️  Calculating fit...")
        
        self._worker_thread = QThread()
        self._worker = ModelingWorker(self.active_engine)
        self._worker.moveToThread(self._worker_thread)
        
        self._worker_thread.started.connect(self._worker.run)
        self._worker.finished.connect(self._on_modeling_finished)
        self._worker.error.connect(self._on_modeling_error)
        
        # Connect cleanup: quit the thread, then delete worker and thread objects
        self._worker.finished.connect(self._worker_thread.quit) # Tell thread to stop its event loop
        self._worker_thread.finished.connect(self._worker.deleteLater) # Delete worker when thread is truly finished
        self._worker_thread.finished.connect(self._worker_thread.deleteLater) # Delete thread when it's truly finished
        
        # Crucially, clear Python references *after* deletion is scheduled
        self._worker_thread.finished.connect(lambda: setattr(self, '_worker_thread', None))
        self._worker.finished.connect(lambda: setattr(self, '_worker', None))
        
        self._worker_thread.start()
        self.btn_run.setEnabled(False) # Prevent overlapping runs

    def _on_modeling_finished(self):
        """Update the UI on the main thread after background math is done."""
        if self.active_engine:
            self.active_engine.plot_results(self.figure)
            self.canvas.draw()
        
        self._is_stale = False
        self.btn_run.setEnabled(True)
        self.lbl_status.setText("Fit Complete")

    def _on_modeling_error(self, message):
        self.btn_run.setEnabled(True)
        self.lbl_status.setText(f"❌ Modeling Error: {message}")

    def on_external_data_changed(self, path_str):
        """
        Connected to main_window.experimentDataChanged.
        If the current experiment was updated in Analysis, mark our fit as stale.
        """
        if self._current_experiment_path and str(self._current_experiment_path) == path_str:
            # Only mark as stale if it's NOT our own autosave (which doesn't affect math data)
            # Note: In a production app, we'd check if 'analysis_settings' specifically changed.
            self._is_stale = True
            self.apply_theme(self.parent_window.dark_mode) # Update visibility/colors

    def _schedule_autosave(self):
        T = get_theme(self.parent_window.dark_mode)
        self.lbl_save_status.setText("Unsaved changes…")
        self.lbl_save_status.setStyleSheet(f"color: {T.save_pending_fg}; font-size: 10px; font-style: italic; background: transparent;")
        self._autosave_timer.start()

    def _write_json(self):
        if ProjectManager.Session.save():
            T = get_theme(self.parent_window.dark_mode)
            self.lbl_save_status.setText("✓  Saved")
            self.lbl_save_status.setStyleSheet(f"color: {T.save_success_fg}; font-size: 10px; font-style: italic; background: transparent;")
            # Notify other components that JSON on disk has been updated
            self.parent_window.experimentDataChanged.emit(str(self._current_experiment_path))

    def apply_theme(self, is_dark: bool):
        T = get_theme(is_dark)
        
        # Status Bar styling
        self.status_frame.setStyleSheet(f"background-color: {T.bg_main}; border-bottom: 1px solid {T.border};")
        self.lbl_status.setStyleSheet(f"color: {T.text_secondary}; font-style: italic; font-size: 11px; background: transparent;")
        
        self.lbl_stale_warning.setStyleSheet(f"color: {T.error}; font-weight: bold; font-size: 10px; margin-right: 10px;")
        self.lbl_stale_warning.setVisible(self._is_stale)
        
        # Save status styling (handling current state color)
        if "Unsaved" in self.lbl_save_status.text():
            self.lbl_save_status.setStyleSheet(f"color: {T.save_pending_fg}; font-size: 10px; font-style: italic; background: transparent;")
        else:
            self.lbl_save_status.setStyleSheet(f"color: {T.save_success_fg}; font-size: 10px; font-style: italic; background: transparent;")

        # Get the panel's palette for consistent accent color
        C = _palette(is_dark) # Re-using _palette from analysis_settings_panel
        
        btn_base_style = f"""
            QPushButton {{
                color: {C['text_primary']};
                border: none;
                font-weight: 600;
                padding: 5px 12px;
                border-radius: 4px;
            }}
            QPushButton:disabled {{
                background-color: {T.bg_secondary};
                color: {T.text_disabled};
            }}
        """
        
        self.btn_settings.setStyleSheet(btn_base_style + f"""
            QPushButton {{ background-color: {C['accent']}; }}
            QPushButton:hover, QPushButton:checked {{ background-color: {C['accent_dim']}; }}
        """)
        
        self.btn_run.setStyleSheet(btn_base_style + f"""
            QPushButton {{ background-color: {T.success}; }}
            QPushButton:hover {{ background-color: {T.btn_add_hover}; }}
        """)
        
        # Plot area styling (now contains the placeholder)
        self.placeholder_label.setStyleSheet(f"color: {T.text_secondary}; font-style: italic; font-size: 11px; background: transparent;")
        
        # Apply theme to the settings panel itself
        self.modeling_settings_panel.apply_theme(is_dark)

    def refresh_target_label(self):
        """Called whenever the active experiment session changes."""
        json_path = ProjectManager.Session.get_path()
        if json_path:
            self._current_experiment_path = json_path
            exp_name = json_path.stem
            sample_name = json_path.parent.parent.name
            
            self.lbl_status.setText("Ready")
            
            data = ProjectManager.Session.get_data()
            self._current_technique = data.get("core", {}).get("technique", "Unknown")
            
            self.placeholder_label.setVisible(False) # Hide placeholder when experiment is selected
            
            # Instantiate the appropriate modeling engine via factory
            from modeling_engines.factory import get_available_models, create_modeling_engine
            available_models = get_available_models(self._current_technique)
            
            self.combo_model_selector.blockSignals(True)
            self.combo_model_selector.clear()
            if available_models:
                self.combo_model_selector.addItems(sorted(available_models.keys()))
                self.combo_model_selector.setEnabled(True)
            else:
                self.combo_model_selector.addItem("No Models Available")
                self.combo_model_selector.setEnabled(False)
            self.combo_model_selector.blockSignals(False)


            # Pass the engine and saved settings to the panel
            saved_modeling = data.get("modeling", {}).get("saved_results", {}).get(self._current_technique, {}) # This will be the dict for the current technique
            selected_model_name = saved_modeling.get("selected_model")

            if selected_model_name and selected_model_name in available_models:
                self.combo_model_selector.setCurrentText(selected_model_name)
                self.active_engine = create_modeling_engine(selected_model_name, self._current_technique, self)
            elif available_models: # Default to the first available model if none saved or saved one is invalid
                self.combo_model_selector.setCurrentIndex(0)
                self.active_engine = create_modeling_engine(self.combo_model_selector.currentText(), self._current_technique, self)
            else:
                self.active_engine = None

            self.modeling_settings_panel.rebuild(
                self._current_technique, 
                saved_modeling, 
                self.active_engine
            )
            self.btn_run.setEnabled(True)
        else:
            self.lbl_status.setText("No selection")
            self.lbl_save_status.setText("")
            self._current_technique = None
            self.active_engine = None
            self.btn_run.setEnabled(False)
            self.combo_model_selector.blockSignals(True)
            self.combo_model_selector.clear()
            self.combo_model_selector.addItem("No Experiment Selected")
            self.combo_model_selector.setEnabled(False)
            self.combo_model_selector.blockSignals(False)
            self.placeholder_label.setVisible(True) # Show placeholder when no experiment
            self._current_experiment_path = None
            self.modeling_settings_panel.rebuild("None", {}, None)
