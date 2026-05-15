from pathlib import Path
from PyQt6.QtWidgets import (
    QFrame, QVBoxLayout, QHBoxLayout, QLabel, QComboBox, 
    QPushButton, QCheckBox, QInputDialog, QMessageBox, QMenu
)
from PyQt6.QtCore import Qt, pyqtSignal

from ui.theme import get_theme
from ui.toggle_switch import ToggleSwitch
from ui.dialogs import NewExperimentDialog
from utils.validators import validate_filename
from utils.network_service import NetworkService
from utils.project_manager import ProjectManager

class SidebarWidget(QFrame):
    """
    Encapsulates the left sidebar: networking, theme toggle, 
    and data navigation (Collaborator -> Sample -> Experiment).
    """
    experimentChanged = pyqtSignal()

    def __init__(self, parent_window):
        super().__init__()
        self.parent_window = parent_window
        self.setObjectName("sidebar")
        self.setFixedWidth(220)
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

    def apply_theme(self, T, dark_mode: bool):
        self.dark_mode_toggle.updateThemeColors(
            color_on=T.toggle_track_on,
            color_off=T.toggle_track_off,
            thumb_color=T.toggle_thumb,
            label_color=T.text_primary,
        )

    # ------------------------------------------------------------------ ROOT LOGIC
    def update_root(self):
        if self.check_remote.isChecked():
            self.combo_network.setEnabled(True)
            valid_hosts = NetworkService.get_available_hosts()

            self.combo_network.blockSignals(True)
            current = self.combo_network.currentText()
            self.combo_network.clear()
            self.combo_network.addItems(valid_hosts)
            if current in valid_hosts: self.combo_network.setCurrentText(current)
            self.combo_network.blockSignals(False)
        else:
            self.combo_network.setEnabled(False)

        self.parent_window.base_dir = NetworkService.resolve_base_dir(
            self.combo_network.currentText(), self.check_remote.isChecked()
        )
        
        self.refresh_dropdown(self.combo_collab, self.parent_window.base_dir / "SpectraLink_Data")
        self.update_samples()

    def refresh_connection(self):
        try:
            cur_collab = self.combo_collab.currentText()
            cur_sample = self.combo_sample.currentText()
            cur_exp    = self.combo_exp.currentText()
            self.update_root()
            if self.combo_collab.findText(cur_collab) != -1:
                self.combo_collab.setCurrentText(cur_collab)
                if self.combo_sample.findText(cur_sample) != -1:
                    self.combo_sample.setCurrentText(cur_sample)
                    if self.combo_exp.findText(cur_exp) != -1:
                        self.combo_exp.setCurrentText(cur_exp)
        except Exception as e:
            QMessageBox.critical(self, "Refresh Failed", str(e))

    def refresh_dropdown(self, combo, path):
        combo.blockSignals(True)
        combo.clear()
        combo.addItems(ProjectManager.list_folders(path))
        combo.blockSignals(False)

    def update_samples(self):
        self.combo_sample.clear()
        self.combo_exp.clear()
        collab = self.combo_collab.currentText()
        if collab:
            self.refresh_dropdown(self.combo_sample, self.parent_window.base_dir / "SpectraLink_Data" / collab)
            self.update_experiments()
        self.toggle_buttons()

    def update_experiments(self):
        self.combo_exp.clear()
        collab = self.combo_collab.currentText()
        sample = self.combo_sample.currentText()
        if collab and sample:
            json_dir = self.parent_window.base_dir / "SpectraLink_Data" / collab / sample / "JSON"
            self.combo_exp.addItems(ProjectManager.list_experiments(json_dir))
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
            
            name = name.strip().replace(" ", "_")
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