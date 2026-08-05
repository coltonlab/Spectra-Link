import numpy as np
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QComboBox, QFrame
from PyQt6.QtCore import Qt
from modeling_engines.base_modeling_dashboard import BaseModelingDashboard
from modeling_engines.registry import MODELING_REGISTRY
from utils.app_logger import logger
from processors.factory import get_processor
from ui.theme import get_theme # Import get_theme for placeholder styling

class ModelingTab(QWidget):
    """
    A dynamic container widget for hosting various modeling dashboards.
    Acts as a blank stage where different BaseModelingDashboard subclasses
    can be mounted, unmounted, and managed.
    """
    def __init__(self, parent_window):
        super().__init__(parent_window)
        self.parent_window = parent_window
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(0)

        # 1. Header Area for Model Selection
        self.header_frame = QFrame()
        self.header_layout = QHBoxLayout(self.header_frame)
        self.header_layout.setContentsMargins(12, 8, 12, 8)
        
        self.header_layout.addWidget(QLabel("<b>Available Models:</b>"))
        
        self.model_selector = QComboBox()
        self.model_selector.setMinimumWidth(250)
        self.model_selector.currentIndexChanged.connect(self._on_model_selection_changed)
        self.header_layout.addWidget(self.model_selector)
        self.header_layout.addStretch()
        
        self.layout.addWidget(self.header_frame)

        # 2. The Dynamic Stage
        self._stage_widget = QWidget()
        self._stage_layout = QVBoxLayout(self._stage_widget)
        self._stage_layout.setContentsMargins(0, 0, 0, 0)
        self._current_dashboard: BaseModelingDashboard | None = None
        
        # Placeholder for when no dashboard is loaded
        self._placeholder_label = QLabel("Select an experiment to load a modeling tool.")
        self._placeholder_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._stage_layout.addWidget(self._placeholder_label)

        self.layout.addWidget(self._stage_widget, stretch=1)

        # Internal state to store the current data context
        self._active_data_context = {"x": None, "y": None, "meta": None}
        self._available_classes = []

    def refresh_from_session(self):
        """
        Called when the session changes. Rebuilds the data context and refreshes the active dashboard.
        """
        from utils.project_manager import Session

        data = Session.get_data()
        previous_dashboard_class = type(self._current_dashboard) if self._current_dashboard is not None else None

        # Clear UI if no data
        if not data:
            self.model_selector.clear()
            self.load_modeling_dashboard(None, None, None, {})
            return

        tech = data.get("core", {}).get("technique")

        # ── Data Handshake ──────────────────────────────────────────────────
        # Use the processor to get the actual processed data from the session
        processor = get_processor(tech, self.parent_window)
        try:
            settings = data.get("analysis_settings", {})
            # For modeling we want all raw traces available (including hidden scans)
            if tech == "Impedance Calibration":
                # Force visibility for all scan types so calibrated sample is generated
                settings_all = dict(settings)
                for key in ("show_open_scan", "show_short_scan", "show_load_scan", "show_known_load_scan", "show_sample_scan", "show_sample2_scan", "show_calibrated_sample_scan"):
                    settings_all[key] = True
                try:
                    raw_traces = processor._load_traces_custom(data, settings_all)
                except Exception:
                    raw_traces = processor._load_traces(data)

                if raw_traces:
                    self._active_data_context = {
                        "x": None,
                        "y": None,
                        "meta": {
                            "core": data.get("core", {}),
                            "analysis_settings": settings,
                            "trace_data": raw_traces,
                        },
                    }
                else:
                    self._active_data_context = {"x": None, "y": None, "meta": data}
            else:
                raw_traces = processor._load_traces(data)
                if raw_traces:
                    # Determine primary data key (ea for EA series, absorbance for ABS)
                    d_key = "ea" if "ea" in raw_traces[0] else "absorbance"
                    x, y = processor._process_trace(raw_traces[0]["wavelengths"], raw_traces[0][d_key], settings, 0)
                    self._active_data_context = {"x": x, "y": y, "meta": data}
                else:
                    self._active_data_context = {"x": None, "y": None, "meta": data}
        except Exception as e:
            logger.error(f"ModelingTab: Failed to prepare data context: {e}")
            self._active_data_context = {"x": None, "y": None, "meta": data}

        # Update the model selection list
        self._available_classes = MODELING_REGISTRY.get(tech, [])

        self.model_selector.blockSignals(True)
        self.model_selector.clear()
        self.model_selector.addItem("None (Select a tool to begin)")
        for cls in self._available_classes:
            self.model_selector.addItem(cls.__name__)
        self.model_selector.setCurrentIndex(0)
        self.model_selector.blockSignals(False)

        if previous_dashboard_class is not None:
            self.load_modeling_dashboard(previous_dashboard_class, None, None, self._active_data_context["meta"])
        else:
            # Clear the stage (so it doesn't run a model on start up)
            self.load_modeling_dashboard(None, None, None, {})

    def _on_model_selection_changed(self, index):
        """Triggered when the user picks a specific engine from the dropdown."""
        if index <= 0: # "None" selected
            self.load_modeling_dashboard(None, None, None, {})
            return

        # Subtract 1 because index 0 is the "None" placeholder
        selected_class = self._available_classes[index - 1]
        ctx = self._active_data_context
        self.load_modeling_dashboard(selected_class, ctx["x"], ctx["y"], ctx["meta"])

    def load_modeling_dashboard(self, dashboard_class: type[BaseModelingDashboard] | None, x_data: np.ndarray, y_data: np.ndarray, metadata: dict):
        """
        Loads a new modeling dashboard into the tab, replacing any existing one.
        If dashboard_class is None, the tab will be cleared and a placeholder shown.

        Args:
            dashboard_class (type[BaseModelingDashboard] | None): The class of the dashboard to instantiate, or None to clear.
            x_data (np.ndarray): The independent variable data.
            y_data (np.ndarray): The dependent variable data.
            metadata (dict): Associated metadata for the experiment.
        """
        # 1. Eviction: Check if there is already a dashboard widget mounted
        if self._current_dashboard is not None:
            logger.info(f"Evicting existing dashboard: {type(self._current_dashboard).__name__}")
            self._current_dashboard.shutdown() # Call cleanup method
            self._stage_layout.removeWidget(self._current_dashboard)
            self._current_dashboard.deleteLater() # Safely delete the widget
            self._current_dashboard = None
        
        if dashboard_class is None:
            # If dashboard_class is None, clear the tab and show placeholder
            self._placeholder_label.setText("Select an experiment to load a modeling tool.")
            self._placeholder_label.show()
            return

        # Hide placeholder if a dashboard is being loaded
        self._placeholder_label.hide()

        try:
            # 2. Injection: Instantiate the new dashboard_class
            new_dashboard = dashboard_class(self)
            self._current_dashboard = new_dashboard
            logger.info(f"Injecting new dashboard: {type(self._current_dashboard).__name__}")

            # 3. Data Hand-off: Call .set_active_data()
            self._current_dashboard.set_active_data(x_data, y_data, metadata)

            # 4. Mounting: Add the new widget to the tab's main layout
            self._stage_layout.addWidget(self._current_dashboard)
        except Exception as e:
            logger.error(f"Failed to load modeling dashboard {dashboard_class.__name__}: {e}")
            self._placeholder_label.setText(f"Error loading dashboard: {e}")
            self._placeholder_label.show()
        
        # Apply current theme to the new dashboard
        window = self.window()
        if window and hasattr(window, "dark_mode"):
            self.apply_theme(window.dark_mode)

    def apply_theme(self, is_dark: bool):
        """Propagates theme changes to the currently active dashboard."""
        if self._current_dashboard:
            self._current_dashboard.apply_theme(is_dark)
        
        # Also update placeholder label color
        T = get_theme(is_dark)
        self.header_frame.setStyleSheet(f"""
            QFrame {{ 
                background-color: {T.bg_secondary}; 
                border-bottom: 1px solid {T.border};
            }}
            QLabel {{ color: {T.text_primary}; }}
        """)
        self.model_selector.setStyleSheet(f"background-color: {T.combo_bg}; color: {T.combo_fg};")
        self._placeholder_label.setStyleSheet(f"color: {T.text_secondary};")