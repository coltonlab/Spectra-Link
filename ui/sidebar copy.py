from pathlib import Path
from PyQt6.QtWidgets import (
    QFrame, QVBoxLayout, QHBoxLayout, QLabel, QComboBox, 
    QPushButton, QCheckBox, QInputDialog, QMessageBox, QMenu,
    QApplication
)
from PyQt6.QtCore import Qt, pyqtSignal, QMimeData, QPoint, QObject, QThread, pyqtSlot
from PyQt6.QtGui import QDrag, QPixmap, QPainter, QColor

from ui.theme import get_theme
from ui.toggle_switch import ToggleSwitch
from ui.dialogs import NewExperimentDialog
from utils.validators import validate_filename
from utils.network_service import NetworkService
from utils.project_manager import ProjectManager

class ScanningWorker(QObject):
    """Handles blocking I/O operations for the sidebar in a background thread."""
    resultReady = pyqtSignal(str, object)  # task_id, data
    errorOccurred = pyqtSignal(str)

    @pyqtSlot(str, dict)
    def execute_task(self, task_id, params):
        try:
            if task_id == "RESOLVE_ROOT":
                # 1. Get Hosts
                hosts = []
                if params.get("is_remote"):
                    hosts = NetworkService.get_available_hosts()
                
                # 2. Resolve Base Dir
                base_dir = NetworkService.resolve_base_dir(
                    params.get("host"), params.get("is_remote")
                )
                
                # 3. List Collaborators
                collabs = ProjectManager.list_folders(base_dir / "SpectraLink_Data")
                
                self.resultReady.emit(task_id, {"hosts": hosts, "base_dir": base_dir, "collabs": collabs})

            elif task_id == "FETCH_SAMPLES":
                path = params.get("path")
                samples = ProjectManager.list_folders(path)
                self.resultReady.emit(task_id, samples)

            elif task_id == "FETCH_EXPERIMENTS":
                path = params.get("path")
                exps = ProjectManager.list_experiments(path)
                self.resultReady.emit(task_id, exps)

        except Exception as e:
            self.errorOccurred.emit(str(e))

class SidebarWidget(QFrame):
    """
    Encapsulates the left sidebar: networking, theme toggle, 
    and data navigation (Collaborator -> Sample -> Experiment).
    """
    experimentChanged = pyqtSignal()
    requestTask = pyqtSignal(str, dict) # task_id, params

    def __init__(self, parent_window):
        super().__init__()
        self.parent_window = parent_window
        self.setObjectName("sidebar")
        self.setFixedWidth(220)
        self._drag_start_pos = None
        
        # Initialize Background Threading
        self.scanning_thread = QThread()
        self.worker = ScanningWorker()
        self.worker.moveToThread(self.scanning_thread)
        
        # Connect worker signals
        self.requestTask.connect(self.worker.execute_task)
        self.worker.resultReady.connect(self._handle_worker_result)
        self.worker.errorOccurred.connect(self._handle_worker_error)
        self.scanning_thread.start()

        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 14, 12, 14)
        layout.setSpacing(4)

        # ── Connection section ────────────────────────────────────────────────
        layout.addWidget(QLabel("<b>Connection Settings</b>"))
        layout.addSpacing(4)

        self.check_remote = QCheckBox("Remote Mode")
        self.check_remote.setChecked(False)
        self.combo_network = QComboBox()
        self.combo_network.setEnabled(False)

        layout.addWidget(self.check_remote)
        layout.addWidget(self.combo_network)
        layout.addSpacing(4)

        self.btn_refresh = QPushButton("⟳  Refresh")
        self.btn_refresh.setObjectName("btn_refresh")
        self.btn_refresh.clicked.connect(self.refresh_connection)
        layout.addWidget(self.btn_refresh)

        # ── Dark mode toggle ──────────────────────────────────────────────────
        layout.addSpacing(8)
        T = get_theme(self.parent_window.dark_mode)
        self.dark_mode_toggle = ToggleSwitch(
            label="Dark Mode",
            checked=self.parent_window.dark_mode,
            color_on=T.toggle_track_on,
            color_off=T.toggle_track_off,
            thumb_color=T.toggle_thumb,
        )
        self.dark_mode_toggle.toggled.connect(self.parent_window._on_theme_toggle)
        layout.addWidget(self.dark_mode_toggle)

        # ── Divider ───────────────────────────────────────────────────────────
        layout.addSpacing(8)
        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        layout.addWidget(sep)
        layout.addSpacing(4)

        # ── Data navigation ───────────────────────────────────────────────────
        layout.addWidget(QLabel("<b>Data Navigation</b>"))
        layout.addSpacing(4)

        self.combo_collab = QComboBox()
        self.combo_sample = QComboBox()
        self.combo_exp    = QComboBox()

        for cb, label_text in [(self.combo_collab, "Collaborator"),
                               (self.combo_sample, "Sample"),
                               (self.combo_exp,    "Experiment")]:
            lbl = QLabel(label_text)
            lbl.setStyleSheet("font-size: 11px; font-weight: 600; letter-spacing: 0.5px;")
            layout.addWidget(lbl)
            layout.addWidget(cb)
            layout.addSpacing(4)

        layout.addSpacing(12)

        self.btn_new_collab = QPushButton("Add New Collaborator")
        self.btn_new_sample = QPushButton("Add New Sample")
        self.btn_new_exp    = QPushButton("Add New Experiment")

        self.btn_new_collab.clicked.connect(lambda: self.create_new_entry("collab"))
        self.btn_new_sample.clicked.connect(lambda: self.create_new_entry("sample"))
        self.btn_new_exp.clicked.connect(lambda: self.create_new_entry("exp"))

        for btn in (self.btn_new_collab, self.btn_new_sample, self.btn_new_exp):
            layout.addWidget(btn)
            layout.addSpacing(2)

        layout.addStretch()

        layout.addSpacing(12)
        self.btn_report_bug = QPushButton("🐞  Report Bug / Feedback")
        self.btn_report_bug.setObjectName("btn_report_bug")
        self.btn_report_bug.clicked.connect(self._on_report_bug)
        layout.addWidget(self.btn_report_bug)
        # ── Context menus ─────────────────────────────────────────────────────
        self.combo_collab.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.combo_sample.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.combo_exp.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)

        self.combo_collab.customContextMenuRequested.connect(lambda p: self._show_context_menu(p, "collab"))
        self.combo_sample.customContextMenuRequested.connect(lambda p: self._show_context_menu(p, "sample"))
        self.combo_exp.customContextMenuRequested.connect(lambda p: self._show_context_menu(p, "exp"))

        # ── Signals ───────────────────────────────────────────────────────────
        self.check_remote.stateChanged.connect(self.update_root)
        self.combo_network.currentIndexChanged.connect(self.update_root)
        self.combo_collab.currentIndexChanged.connect(self.update_samples)
        self.combo_sample.currentIndexChanged.connect(self.update_experiments)
        self.combo_exp.currentIndexChanged.connect(self.experimentChanged.emit)

        # Enable drag and drop functionality for the experiment selection
        self.combo_exp.installEventFilter(self)

    def apply_theme(self, T, dark_mode: bool):
        self.dark_mode_toggle.updateThemeColors(
            color_on=T.toggle_track_on,
            color_off=T.toggle_track_off,
            thumb_color=T.toggle_thumb,
            label_color=T.text_primary,
        )

    def _set_loading_state(self, is_loading: bool):
        """Disables/Enables UI during async operations."""
        self.btn_refresh.setEnabled(not is_loading)
        self.combo_collab.setEnabled(not is_loading)
        self.combo_sample.setEnabled(not is_loading)
        self.combo_exp.setEnabled(not is_loading)
        if is_loading:
            self.btn_refresh.setText("⏳  Scanning...")
        else:
            self.btn_refresh.setText("⟳  Refresh")

    # ------------------------------------------------------------------ WORKER HANDLERS
    def _handle_worker_result(self, task_id, data):
        self._set_loading_state(False)

        if task_id == "RESOLVE_ROOT":
            # Update Hosts
            if self.check_remote.isChecked():
                self.combo_network.blockSignals(True)
                current = self.combo_network.currentText()
                self.combo_network.clear()
                self.combo_network.addItems(data["hosts"])
                if current in data["hosts"]: 
                    self.combo_network.setCurrentText(current)
                self.combo_network.blockSignals(False)
            
            self.parent_window.base_dir = data["base_dir"]
            
            # Update Collaborators
            self.combo_collab.blockSignals(True)
            self.combo_collab.clear()
            self.combo_collab.addItems(data["collabs"])
            self.combo_collab.blockSignals(False)
            self.update_samples()

        elif task_id == "FETCH_SAMPLES":
            self.combo_sample.blockSignals(True)
            self.combo_sample.clear()
            self.combo_sample.addItems(data)
            self.combo_sample.blockSignals(False)
            self.update_experiments()

        elif task_id == "FETCH_EXPERIMENTS":
            self.combo_exp.blockSignals(True)
            self.combo_exp.clear()
            self.combo_exp.addItems(data)
            self.combo_exp.blockSignals(False)
            self.toggle_buttons()
            self.experimentChanged.emit()

    def _handle_worker_error(self, message):
        self._set_loading_state(False)
        QMessageBox.critical(self, "System Error", f"Background task failed:\n{message}")

    # ------------------------------------------------------------------ DRAG & DROP
    def eventFilter(self, source, event):
        """
        Intercepts mouse events on combo_exp to handle dragging.
        This is more reliable than overriding mouseMoveEvent on the sidebar itself,
        as the ComboBox typically consumes its own mouse events.
        """
        if source is self.combo_exp:
            if event.type() == event.Type.MouseButtonPress:
                if event.button() == Qt.MouseButton.LeftButton:
                    self._drag_start_pos = event.pos()
                    return True  # Intercept the press to prevent the dropdown from opening immediately

            elif event.type() == event.Type.MouseMove:
                if not (event.buttons() & Qt.MouseButton.LeftButton) or self._drag_start_pos is None:
                    return False
                
                # Only start dragging if the mouse has moved far enough
                if (event.pos() - self._drag_start_pos).manhattanLength() < QApplication.startDragDistance():
                    return False
                
                # Store pos and reset state before executing drag to avoid double-triggering
                pos = self._drag_start_pos
                self._drag_start_pos = None 
                self._execute_drag(pos)
                return True # Consume event so the dropdown doesn't pop up during drag

            elif event.type() == event.Type.MouseButtonRelease:
                if event.button() == Qt.MouseButton.LeftButton and self._drag_start_pos is not None:
                    # If we released the button and never moved far enough to drag,
                    # NOW we show the dropdown.
                    self._drag_start_pos = None
                    source.showPopup()
                    return True
                self._drag_start_pos = None
                
        return super().eventFilter(source, event)

    def _execute_drag(self, event_pos):
        """Constructs the payload and starts the drag operation."""
        collab = self.combo_collab.currentText()
        sample = self.combo_sample.currentText()
        exp    = self.combo_exp.currentText()
        
        if not (collab and sample and exp):
            return

        json_path = self.parent_window.base_dir / "SpectraLink_Data" / collab / sample / "JSON" / f"{exp}.json"
        
        drag = QDrag(self)
        mime_data = QMimeData()
        mime_data.setText(str(json_path))  # The 'payload' is the absolute path to the JSON
        drag.setMimeData(mime_data)
        
        # Visual Cue: Create a 'ghost' snapshot of the widget
        pixmap = self.combo_exp.grab()
        
        # Optional: Make the ghost image semi-transparent for a cleaner look
        painter = QPainter(pixmap)
        painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_DestinationIn)
        painter.fillRect(pixmap.rect(), QColor(0, 0, 0, 150)) # 150/255 opacity
        painter.end()

        drag.setPixmap(pixmap)
        drag.setHotSpot(event_pos)
        
        self._drag_start_pos = None # Reset state
        drag.exec(Qt.DropAction.CopyAction)

    # ------------------------------------------------------------------ ROOT LOGIC
    def update_root(self):
        self._set_loading_state(True)
        self.combo_network.setEnabled(self.check_remote.isChecked())
        
        params = {
            "host": self.combo_network.currentText(),
            "is_remote": self.check_remote.isChecked()
        }
        self.requestTask.emit("RESOLVE_ROOT", params)

    def _on_report_bug(self):
        from ui.bug_report_dialog import BugReportDialog
        dlg = BugReportDialog(self.parent_window)
        dlg.exec()

    def refresh_connection(self):
        """Trigger a fresh root resolution and re-scan."""
        # We simply call update_root; the result handler handles the cascading updates.
        self.update_root()

    def refresh_dropdown(self, combo, path):
        """Deprecated: Use background scanning via update_samples/update_experiments instead."""
        combo.blockSignals(True)
        combo.clear()
        combo.addItems(ProjectManager.list_folders(path))
        combo.blockSignals(False)

    def update_samples(self):
        collab = self.combo_collab.currentText()
        if collab:
            self._set_loading_state(True)
            path = self.parent_window.base_dir / "SpectraLink_Data" / collab
            self.requestTask.emit("FETCH_SAMPLES", {"path": path})
        else:
            self.combo_sample.clear()
            self.update_experiments()

    def update_experiments(self):
        collab = self.combo_collab.currentText()
        sample = self.combo_sample.currentText()
        if collab and sample:
            self._set_loading_state(True)
            json_dir = self.parent_window.base_dir / "SpectraLink_Data" / collab / sample / "JSON"
            self.requestTask.emit("FETCH_EXPERIMENTS", {"path": json_dir})
        else:
            self.combo_exp.clear()
            self.toggle_buttons()

    def toggle_buttons(self):
        has_collab = bool(self.combo_collab.currentText())
        has_sample = bool(self.combo_sample.currentText())
        self.btn_new_sample.setEnabled(has_collab)
        self.btn_new_exp.setEnabled(has_sample)

    # ------------------------------------------------------------------ CRUD
    def create_new_entry(self, level):
        old_collab = self.combo_collab.currentText()
        old_sample = self.combo_sample.currentText()

        if level == "exp":
            dlg = NewExperimentDialog(self.parent_window)
            if dlg.exec() != NewExperimentDialog.DialogCode.Accepted: return
            name, technique = dlg.get_values()
            is_valid, err = validate_filename(name)
            if not is_valid:
                QMessageBox.warning(self, "Invalid Name", err)
                return

            try:
                target = self.parent_window.base_dir / "SpectraLink_Data" / old_collab / old_sample / "JSON" / f"{name.strip()}.json"
                if not ProjectManager.create_experiment_template(target, name.strip(), technique):
                    QMessageBox.warning(self, "Exists", "Already exists.")
                    return
                self.refresh_ui_after_creation("exp", name.strip(), old_collab, old_sample)
            except Exception as e: QMessageBox.critical(self, "Error", str(e))
        else:
            name, ok = QInputDialog.getText(self, "New Entry", f"Enter {level} name:")
            if not ok or not name: return
            is_valid, err = validate_filename(name)
            if not is_valid:
                QMessageBox.warning(self, "Invalid Name", err)
                return
            
            # name = name.strip().replace(" ", "_")
            try:
                path = self.parent_window.base_dir / "SpectraLink_Data"
                if level == "collab": ProjectManager.create_folder(path / name)
                else: 
                    target = path / old_collab / name
                    ProjectManager.create_folder(target)
                    ProjectManager.create_folder(target / "JSON")
                self.refresh_ui_after_creation(level, name, old_collab, old_sample)
            except Exception as e: QMessageBox.critical(self, "Error", str(e))

    def refresh_ui_after_creation(self, level, name, old_collab, old_sample):
        self.combo_collab.blockSignals(True)
        self.combo_sample.blockSignals(True)
        self.combo_exp.blockSignals(True)
        self.refresh_dropdown(self.combo_collab, self.parent_window.base_dir / "SpectraLink_Data")

        if level == "collab":
            self.combo_collab.setCurrentText(name)
            self.update_samples()
        elif level == "sample":
            self.combo_collab.setCurrentText(old_collab)
            self.refresh_dropdown(self.combo_sample, self.parent_window.base_dir / "SpectraLink_Data" / old_collab)
            self.combo_sample.setCurrentText(name)
            self.update_experiments()
        elif level == "exp":
            self.combo_collab.setCurrentText(old_collab)
            self.combo_sample.setCurrentText(old_sample)
            self.update_experiments()
            self.combo_exp.setCurrentText(name)

        self.combo_collab.blockSignals(False)
        self.combo_sample.blockSignals(False)
        self.combo_exp.blockSignals(False)
        self.toggle_buttons()
        self.experimentChanged.emit()

    def _show_context_menu(self, pos, level):
        combo = getattr(self, f"combo_{level}")
        current_name = combo.currentText()
        if not current_name: return

        menu = QMenu(self)
        rename_act = menu.addAction(f"Rename '{current_name}'")
        delete_act = menu.addAction(f"Delete '{current_name}'") if level == "exp" else None
        
        action = menu.exec(combo.mapToGlobal(pos))
        if not action: return

        if action == rename_act:
            if level == "collab": self._rename_collab(current_name)
            elif level == "sample": self._rename_sample(current_name)
            else: self._rename_experiment(current_name)
        elif action == delete_act:
            self._delete_experiment(current_name)

    def _rename_collab(self, current_name):
        new_name, ok = QInputDialog.getText(self, "Rename", f"New name for '{current_name}':")
        if not ok or not new_name: return
        try:
            ProjectManager.rename_path(self.parent_window.base_dir / "SpectraLink_Data" / current_name, new_name)
            self.update_root()
            self.combo_collab.setCurrentText(new_name.strip())
        except Exception as e: QMessageBox.critical(self, "Error", str(e))

    def _rename_sample(self, current_name):
        collab = self.combo_collab.currentText()
        new_name, ok = QInputDialog.getText(self, "Rename", f"New name for '{current_name}':")
        if not ok or not new_name: return
        try:
            ProjectManager.rename_path(self.parent_window.base_dir / "SpectraLink_Data" / collab / current_name, new_name)
            self.update_samples()
            self.combo_sample.setCurrentText(new_name.strip())
        except Exception as e: QMessageBox.critical(self, "Error", str(e))

    def _rename_experiment(self, current_name):
        collab = self.combo_collab.currentText()
        sample = self.combo_sample.currentText()
        new_name, ok = QInputDialog.getText(self, "Rename", f"New name for '{current_name}':")
        if not ok or not new_name: return
        try:
            ProjectManager.rename_path(self.parent_window.base_dir / "SpectraLink_Data" / collab / sample / "JSON" / f"{current_name}.json", f"{new_name.strip()}.json")
            self.update_experiments()
            self.combo_exp.setCurrentText(new_name.strip())
        except Exception as e: QMessageBox.critical(self, "Error", str(e))

    def _delete_experiment(self, exp_name):
        collab = self.combo_collab.currentText()
        sample = self.combo_sample.currentText()
        reply = QMessageBox.question(self, "Delete", f"Delete '{exp_name}'?", QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply != QMessageBox.StandardButton.Yes: return
        try:
            ProjectManager.delete_file(self.parent_window.base_dir / "SpectraLink_Data" / collab / sample / "JSON" / f"{exp_name}.json")
            self.update_experiments()
            self.experimentChanged.emit()
        except Exception as e: QMessageBox.critical(self, "Error", str(e))

    def select_path(self, json_path: Path):
        """
        Programmatically sets the sidebar dropdowns to select a specific experiment.
        This will trigger the experimentChanged signal, updating Discovery and Analysis tabs.
        """
        try:
            # Extract parts from the JSON path
            # Example: Data/SpectraLink_Data/Collaborator/Sample/JSON/Experiment.json
            exp_name = json_path.stem
            # The parent of the JSON file is 'JSON', its parent is 'Sample', its parent is 'Collaborator'
            sample_name = json_path.parent.parent.name
            collab_name = json_path.parent.parent.parent.name

            # Block signals to prevent multiple updates during programmatic selection
            self.combo_collab.blockSignals(True)
            self.combo_sample.blockSignals(True)
            self.combo_exp.blockSignals(True)

            # Set Collaborator
            idx_collab = self.combo_collab.findText(collab_name)
            if idx_collab != -1:
                self.combo_collab.setCurrentIndex(idx_collab)
            else:
                print(f"Warning: Collaborator '{collab_name}' not found in sidebar.")
                return

            # Update samples and set Sample
            self.update_samples() # This populates combo_sample based on combo_collab
            idx_sample = self.combo_sample.findText(sample_name)
            if idx_sample != -1:
                self.combo_sample.setCurrentIndex(idx_sample)
            else:
                print(f"Warning: Sample '{sample_name}' not found for '{collab_name}'.")
                return

            # Update experiments and set Experiment
            self.update_experiments() # This populates combo_exp based on combo_sample
            idx_exp = self.combo_exp.findText(exp_name)
            if idx_exp != -1:
                self.combo_exp.setCurrentIndex(idx_exp)
            else:
                print(f"Warning: Experiment '{exp_name}' not found for '{sample_name}'.")
                return

        finally:
            # Always unblock signals, even if an error occurred
            self.combo_collab.blockSignals(False)
            self.combo_sample.blockSignals(False)
            self.combo_exp.blockSignals(False)
            # Emit the signal once after all changes are made
            self.experimentChanged.emit()