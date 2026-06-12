from pathlib import Path
from PyQt6.QtWidgets import (
    QFrame, QVBoxLayout, QHBoxLayout, QLabel, QComboBox, QTreeView,
    QPushButton, QCheckBox, QInputDialog, QMessageBox, QMenu,
    QApplication
)
from PyQt6.QtCore import Qt, pyqtSignal, QMimeData, QPoint, QObject, QThread, pyqtSlot, QModelIndex, QPersistentModelIndex, QTimer
from PyQt6.QtGui import QDrag, QPixmap, QPainter, QColor, QStandardItemModel, QStandardItem

from ui.theme import get_theme
from ui.toggle_switch import ToggleSwitch
from ui.dialogs import NewExperimentDialog
from utils.validators import validate_filename
from utils.network_service import NetworkService
from utils.app_logger import logger # Import the global logger
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
                
                # 3. List Collaborators (Recursive Scan)
                data_root = base_dir / "SpectraLink_Data"
                tree_data = {}
                
                if data_root.exists():
                    collabs = ProjectManager.list_folders(data_root)
                    for c in collabs:
                        c_path = data_root / c
                        tree_data[c] = {}
                        samples = ProjectManager.list_folders(c_path)
                        for s in samples:
                            s_path = c_path / s
                            if s == "Comparison Plots":
                                # Configs are stored directly in this folder
                                exps = ProjectManager.list_experiments(s_path)
                            else:
                                json_dir = s_path / "JSON"
                                exps = ProjectManager.list_experiments(json_dir) if json_dir.exists() else []
                            tree_data[c][s] = exps
                
                self.resultReady.emit(task_id, {
                    "hosts": hosts, 
                    "base_dir": base_dir,
                    "tree_data": tree_data
                })

        except Exception as e:
            self.errorOccurred.emit(f"Error in ScanningWorker: {e}") # Emit more descriptive error

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
        self.setMinimumWidth(180)
        self.setMaximumWidth(500)
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

        self.tree_view = QTreeView()
        self.tree_model = QStandardItemModel()
        self.tree_model.setHorizontalHeaderLabels(["Research Hierarchy"])
        self.tree_view.setModel(self.tree_model)
        self.tree_view.setEditTriggers(QTreeView.EditTrigger.NoEditTriggers)
        self.tree_view.setHeaderHidden(True)
        self.tree_view.setIndentation(12)
        self.tree_view.setAnimated(True)
        self.tree_view.setExpandsOnDoubleClick(False)
        
        # Drag and Drop
        self.tree_view.viewport().installEventFilter(self)
        self.tree_view.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.tree_view.customContextMenuRequested.connect(self._show_tree_context_menu)

        layout.addWidget(self.tree_view, stretch=1)

        # Removed buttons for New Collaborator/Sample/Experiment
        layout.addSpacing(12)
        self.btn_report_bug = QPushButton("🐞  Report Bug / Feedback")
        self.btn_report_bug.setObjectName("btn_report_bug")
        self.btn_report_bug.clicked.connect(self._on_report_bug)
        layout.addWidget(self.btn_report_bug)

        # ── Signals ───────────────────────────────────────────────────────────
        self.check_remote.stateChanged.connect(self.update_root)
        self.combo_network.currentIndexChanged.connect(self.update_root)
        self.tree_view.selectionModel().selectionChanged.connect(self._on_tree_selection_changed)
        self.tree_view.clicked.connect(self._on_tree_clicked)
        self.tree_view.activated.connect(self._on_tree_clicked)

    def apply_theme(self, T, dark_mode: bool):
        self.dark_mode_toggle.updateThemeColors(
            color_on=T.toggle_track_on,
            color_off=T.toggle_track_off,
            thumb_color=T.toggle_thumb,
            label_color=T.text_primary,
        )
        self.tree_view.setStyleSheet(f"QTreeView {{ border: none; background: transparent; }}")

    def _set_loading_state(self, is_loading: bool):
        """Disables/Enables UI during async operations."""
        self.btn_refresh.setEnabled(not is_loading)
        self.tree_view.setEnabled(not is_loading)
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
            
            # Ensure base_dir is updated before triggering children fetch
            self.parent_window.base_dir = Path(data["base_dir"])
            self._populate_tree(data["tree_data"])
            self.toggle_buttons()

    def _handle_worker_error(self, message):
        self._set_loading_state(False)
        logger.error(f"Background task failed: {message}") # Log the error
        QMessageBox.warning(self, "Connection Error", f"The sidebar could not be populated:\n{message}")

    def _populate_tree(self, tree_dict):
        """Rebuilds the entire tree structure from the provided dictionary."""
        # 1. Capture current expanded state and selection
        expanded_collabs = set()
        expanded_samples = set()
        current_path = ProjectManager.Session.get_path()
        current_path_str = str(current_path) if current_path else None

        for i in range(self.tree_model.rowCount()):
            c_idx = self.tree_model.index(i, 0)
            if self.tree_view.isExpanded(c_idx):
                c_item = self.tree_model.item(i)
                c_name = c_item.text()
                expanded_collabs.add(c_name)
                for j in range(c_item.rowCount()):
                    s_idx = self.tree_model.index(j, 0, c_idx)
                    if self.tree_view.isExpanded(s_idx):
                        expanded_samples.add((c_name, c_item.child(j).text()))

        # 2. Rebuild the model
        self.tree_view.selectionModel().blockSignals(True)
        self.tree_view.setUpdatesEnabled(False)
        self.tree_model.clear()
        self.tree_model.setHorizontalHeaderLabels(["Research Hierarchy"])
        
        target_idx = None

        for collab, samples in sorted(tree_dict.items()):
            c_item = QStandardItem(collab)
            c_item.setData("collab", Qt.ItemDataRole.UserRole + 1)
            self.tree_model.appendRow(c_item)
            
            if collab in expanded_collabs:
                self.tree_view.setExpanded(c_item.index(), True)

            for sample, exps in sorted(samples.items()):
                is_config_dir = (sample == "Comparison Plots")
                s_item = QStandardItem(sample)
                s_item.setData("sample" if not is_config_dir else "config_dir", Qt.ItemDataRole.UserRole + 1)
                c_item.appendRow(s_item)
                
                if (collab, sample) in expanded_samples:
                    self.tree_view.setExpanded(s_item.index(), True)

                for exp in sorted(exps):
                    e_item = QStandardItem(exp)
                    e_item.setData("exp" if not is_config_dir else "config", Qt.ItemDataRole.UserRole + 1)
                    
                    if is_config_dir:
                        path = self.parent_window.base_dir / "SpectraLink_Data" / collab / sample / f"{exp}.json"
                    else:
                        path = self.parent_window.base_dir / "SpectraLink_Data" / collab / sample / "JSON" / f"{exp}.json"
                    
                    path_str = str(path)
                    e_item.setData(path_str, Qt.ItemDataRole.UserRole)
                    s_item.appendRow(e_item)
                    
                    if path_str == current_path_str:
                        target_idx = e_item.index()

        # 3. Restore signals and selection
        if target_idx:
            self.tree_view.setCurrentIndex(target_idx)
            self.tree_view.scrollTo(target_idx)

        self.tree_view.setUpdatesEnabled(True)
        self.tree_view.selectionModel().blockSignals(False)


    # ------------------------------------------------------------------ DRAG & DROP
    def eventFilter(self, source, event):
        """
        Intercepts mouse events on the tree viewport to handle dragging.
        Filtering the viewport ensures coordinates align with indexAt() and visualRect()
        which are used to identify the dragged item and create the ghost image.
        """
        if source is self.tree_view.viewport():
            if event.type() == event.Type.MouseButtonPress:
                if event.button() == Qt.MouseButton.LeftButton:
                    self._drag_start_pos = event.pos()

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
                self._drag_start_pos = None
                
        return super().eventFilter(source, event)

    def _execute_drag(self, event_pos):
        """Constructs the payload and starts the drag operation."""
        index = self.tree_view.indexAt(event_pos)
        if not index.isValid(): return
        
        item = self.tree_model.itemFromIndex(index)
        if item.data(Qt.ItemDataRole.UserRole + 1) != "exp":
            return # Only drag experiment files

        json_path = item.data(Qt.ItemDataRole.UserRole)
        
        drag = QDrag(self)
        mime_data = QMimeData()
        mime_data.setText(str(json_path))  # Ensure payload is a string path
        drag.setMimeData(mime_data)
        
        # Visual Cue: Create a high-quality 'ghost' snapshot of the actual rendered item
        rect = self.tree_view.visualRect(index)
        if rect.isEmpty(): return

        # Grab the item exactly as it appears in the tree (includes icons, fonts, and colors)
        full_pixmap = self.tree_view.viewport().grab(rect)
        
        # Create a semi-transparent version for a professional 'floating' effect
        pixmap = QPixmap(full_pixmap.size())
        pixmap.fill(Qt.GlobalColor.transparent)
        painter = QPainter(pixmap)
        painter.setOpacity(0.7)
        painter.drawPixmap(0, 0, full_pixmap)
        painter.end()

        drag.setPixmap(pixmap)
        drag.setHotSpot(event_pos - rect.topLeft())
        
        self._drag_start_pos = None # Reset state

        # Execute the drag; this blocks until the user releases the mouse
        drag.exec(Qt.DropAction.CopyAction)

        # After release, programmatically select and load the experiment in the sidebar
        self.tree_view.setCurrentIndex(index)
        self._on_tree_clicked(index)

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

    def _on_tree_clicked(self, index):
        """
        Handles logic on mouse release (click) or activation (Enter key).
        Separating this from selection allows drag-and-drop to start without
        triggering heavy JSON loading immediately on press.
        """
        if not index.isValid(): return
        
        item = self.tree_model.itemFromIndex(index)
        if not item: return
        level = item.data(Qt.ItemDataRole.UserRole + 1)

        if level == "exp":
            # Load the experiment only when a full click (release) occurs
            path = Path(item.data(Qt.ItemDataRole.UserRole))
            ProjectManager.Session.load_experiment(path)
            self.experimentChanged.emit()
        elif level == "config":
            # Switch to Comparison Tab and load the configuration
            path = Path(item.data(Qt.ItemDataRole.UserRole))
            self.parent_window.tabs.setCurrentWidget(self.parent_window.comparison_tab)
            self.parent_window.comparison_tab.load_config_from_path(path)
        else:
            # Toggle expansion for folders
            if self.tree_view.isExpanded(index):
                self.tree_view.collapse(index)
            else:
                self.tree_view.expand(index)

    def _on_tree_selection_changed(self):
        """Handles highlight changes. Heavy data loading is deferred to _on_tree_clicked."""
        index = self.tree_view.currentIndex()
        is_exp = False
        
        if index.isValid():
            item = self.tree_model.itemFromIndex(index)
            if item:
                is_exp = (item.data(Qt.ItemDataRole.UserRole + 1) == "exp")
        
        if not is_exp:
            # If we select a folder or nothing, clear the active experiment view
            ProjectManager.Session.clear()
            self.experimentChanged.emit()

        self.toggle_buttons()

    def toggle_buttons(self):
        """Updates button enablement based on current selection."""
        index = self.tree_view.currentIndex()
        level = ""
        if index.isValid():
            level = self.tree_model.itemFromIndex(index).data(Qt.ItemDataRole.UserRole + 1)
        
        # Note: Creation buttons are now removed, but we keep this logic 
        # if we add specific context-sensitive buttons later.
        pass

    # ------------------------------------------------------------------ CRUD
    def create_new_entry(self, level, current_item=None):
        """
        Creates a new file system entry. 
        If current_item is provided, it uses that as the parent context.
        """
        if current_item is None:
            index = self.tree_view.currentIndex()
            current_item = self.tree_model.itemFromIndex(index) if index.isValid() else None

        if level == "exp":
            if not current_item: 
                QMessageBox.warning(self, "No Context", "Please right-click a Sample to add an experiment.")
                return
                
            dlg = NewExperimentDialog(self.parent_window)
            if dlg.exec() != NewExperimentDialog.DialogCode.Accepted: return
            name, technique = dlg.get_values()
            
            # Resolve path logic
            sample_item = current_item if current_item.data(Qt.ItemDataRole.UserRole + 1) == "sample" else current_item.parent()
            collab_item = sample_item.parent()
            
            try:
                target = self.parent_window.base_dir / "SpectraLink_Data" / collab_item.text() / sample_item.text() / "JSON" / f"{name.strip()}.json"
                if not ProjectManager.create_experiment_template(target, name.strip(), technique):
                    QMessageBox.warning(self, "Exists", "Already exists.")
                    return
                self.update_root() # Full refresh
                logger.info(f"New experiment '{name}' created at {target}")
            except Exception as e: QMessageBox.critical(self, "Error", str(e))
        else:
            name, ok = QInputDialog.getText(self, "New Entry", f"Enter {level} name:")
            if not ok or not name: return

            try:
                path = self.parent_window.base_dir / "SpectraLink_Data"
                if level == "collab": 
                    target = path / name
                    ProjectManager.create_folder(target)
                    ProjectManager.create_folder(target / "Comparison Plots")
                else: 
                    collab_name = current_item.text() if current_item.data(Qt.ItemDataRole.UserRole + 1) == "collab" else current_item.parent().text()
                    target = path / collab_name / name
                    ProjectManager.create_folder(target)
                    ProjectManager.create_folder(target / "JSON")
                self.update_root() # Full refresh
                logger.info(f"New {level} '{name}' created.")
            except Exception as e: QMessageBox.critical(self, "Error", str(e))

    def _show_tree_context_menu(self, pos):
        index = self.tree_view.indexAt(pos)
        menu = QMenu(self)

        # 1. Right-click on empty space: Global actions
        if not index.isValid():
            add_collab_act = menu.addAction("Add New Collaborator")
            menu.addSeparator()
            expand_all_act = menu.addAction("Expand All")
            collapse_all_act = menu.addAction("Collapse All")
            
            action = menu.exec(self.tree_view.mapToGlobal(pos))
            if action == add_collab_act:
                self.create_new_entry("collab")
            elif action == expand_all_act:
                self.tree_view.expandAll()
            elif action == collapse_all_act:
                self.tree_view.collapseAll()
            return

        # 2. Right-click on a specific item: Context-aware actions
        item = self.tree_model.itemFromIndex(index)
        level = item.data(Qt.ItemDataRole.UserRole + 1)
        current_name = item.text()

        add_act = None
        if level == "collab":
            add_act = menu.addAction("Add New Sample...")
            menu.addSeparator() # Add separator after "Add New Sample"
        elif level == "sample":
            add_act = menu.addAction("Add New Experiment...")

        rename_act = menu.addAction(f"Rename '{current_name}'")
        delete_act = None
        if level == "exp" or level == "config": # Add delete action for both experiments and configs
            delete_act = menu.addAction(f"Delete '{current_name}'")
        
        menu.addSeparator()
        expand_all_act = menu.addAction("Expand All")
        collapse_all_act = menu.addAction("Collapse All")

        action = menu.exec(self.tree_view.mapToGlobal(pos))
        if not action: return

        if action == add_act:
            self.create_new_entry("sample" if level == "collab" else "exp", item)
        elif action == rename_act:
            self._rename_item(item, level)
        elif action == delete_act and level == "config":
            self._delete_comparison_config(item)
        elif action == delete_act and level == "exp": # Handle experiment deletion
            self._delete_experiment(item)
        elif action == expand_all_act:
            self.tree_view.expandAll()
        elif action == collapse_all_act:
            self.tree_view.collapseAll()

    def _rename_item(self, item, level):
        new_name, ok = QInputDialog.getText(self, "Rename", f"New name for '{item.text()}':")
        if not ok or not new_name: return
        
        try:
            old_path = None
            if level == "collab":
                old_path = self.parent_window.base_dir / "SpectraLink_Data" / item.text()
            elif level == "sample":
                old_path = self.parent_window.base_dir / "SpectraLink_Data" / item.parent().text() / item.text()
            elif level == "exp":
                old_path = Path(item.data(Qt.ItemDataRole.UserRole))
            
            ProjectManager.rename_path(old_path, new_name if level != "exp" else f"{new_name}.json")
            self.update_root() # Full refresh
            logger.info(f"Renamed {level} from '{old_path.name}' to '{new_name}'")

        except Exception as e: QMessageBox.critical(self, "Error", str(e))

    def _delete_experiment(self, item):
        reply = QMessageBox.question(self, "Delete", f"Delete '{item.text()}'?", QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply != QMessageBox.StandardButton.Yes: return
        try:
            ProjectManager.delete_file(Path(item.data(Qt.ItemDataRole.UserRole)))
            self.update_root() # Full refresh
            logger.info(f"Deleted experiment: {item.text()}")

        except Exception as e: QMessageBox.critical(self, "Error", str(e))

    def _delete_comparison_config(self, item):
        """Deletes a comparison configuration file from disk."""
        file_path = Path(item.data(Qt.ItemDataRole.UserRole))
        reply = QMessageBox.question(self, "Delete", f"Delete '{item.text()}'?", QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply != QMessageBox.StandardButton.Yes: return
        try:
            ProjectManager.delete_file(Path(item.data(Qt.ItemDataRole.UserRole)))
            self.update_root() # Full refresh
            logger.info(f"Deleted comparison configuration: {item.text()}")

        except Exception as e: QMessageBox.critical(self, "Error", str(e))

    def select_path(self, json_path: Path):
        """Programmatically find and select the experiment in the tree."""
        path_str = str(json_path)
        for row in range(self.tree_model.rowCount()):
            c_item = self.tree_model.item(row)
            for s_row in range(c_item.rowCount()):
                s_item = c_item.child(s_row)
                for e_row in range(s_item.rowCount()):
                    e_item = s_item.child(e_row)
                    if e_item.data(Qt.ItemDataRole.UserRole) == path_str:
                        self.tree_view.setCurrentIndex(e_item.index())
                        self.tree_view.scrollTo(e_item.index())
                        self._on_tree_clicked(e_item.index())
                        return