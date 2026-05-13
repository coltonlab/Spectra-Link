import sys
import os
import json
from pathlib import Path
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout,
    QHBoxLayout, QTabWidget, QComboBox, QPushButton,
    QLabel, QInputDialog, QMessageBox, QFileDialog,
    QCheckBox, QTableWidget, QTableWidgetItem, QHeaderView,
    QAbstractItemView, QDoubleSpinBox, QFrame,
    QDialog, QLineEdit, QDialogButtonBox, QFormLayout, QMenu
)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QColor, QBrush, QPalette
import platform
import re
import socket

# ── Theme system ──────────────────────────────────────────────────────────────
from ui.theme import get_theme, apply_palette_to_app

# ── Toggle switch ─────────────────────────────────────────────────────────────
from ui.toggle_switch import ToggleSwitch

# Local Imports from your new folders
from config.techniques import TECHNIQUE_CONFIG
from ui.discovery_tab import DiscoveryTab
from ui.analysis_tab import AnalysisTab
from ui.dialogs import NewExperimentDialog
from utils.validators import validate_filename


# ──────────────────────────────────────────────────────────────────────────────
#  Helper: build a full stylesheet from a ThemeColors token set
# ──────────────────────────────────────────────────────────────────────────────
def build_stylesheet(T) -> str:
    """
    Generate a QSS stylesheet from a ThemeColors instance.
    Covers every widget class used in SpectraLink so that background,
    text, borders, dialogs, tooltips and icons all follow the palette.
    """
    return f"""
/* ── Global ─────────────────────────────────────────────────────────────── */
QWidget {{
    background-color: {T.bg_main};
    color: {T.text_primary};
    font-family: "Segoe UI", "Helvetica Neue", sans-serif;
    font-size: 13px;
}}

/* ── Main window ─────────────────────────────────────────────────────────── */
QMainWindow {{
    background-color: {T.bg_main};
}}

/* ── Sidebar / panels (QFrame used as sidebar container) ─────────────────── */
QFrame#sidebar {{
    background-color: {T.bg_secondary};
    border-right: 1px solid {T.separator};
}}

/* ── Labels ──────────────────────────────────────────────────────────────── */
QLabel {{
    background-color: transparent;
    color: {T.text_primary};
}}
QLabel[class="secondary"] {{
    color: {T.text_secondary};
    font-size: 11px;
}}

/* ── Section headers (bold labels) ──────────────────────────────────────── */
QLabel b {{
    color: {T.text_primary};
}}

/* ── Combo boxes ─────────────────────────────────────────────────────────── */
QComboBox {{
    background-color: {T.bg_input};
    color: {T.text_primary};
    border: 1px solid {T.border};
    border-radius: 4px;
    padding: 4px 8px;
    selection-background-color: {T.accent};
    selection-color: {T.accent_text};
}}
QComboBox:focus {{
    border: 1px solid {T.border_focus};
}}
QComboBox:disabled {{
    color: {T.text_disabled};
    background-color: {T.bg_secondary};
}}
QComboBox QAbstractItemView {{
    background-color: {T.bg_input};
    color: {T.text_primary};
    border: 1px solid {T.border};
    selection-background-color: {T.accent};
    selection-color: {T.accent_text};
    outline: none;
}}
QComboBox::drop-down {{
    border: none;
    width: 20px;
}}
QComboBox::down-arrow {{
    image: none;
    border-left: 4px solid transparent;
    border-right: 4px solid transparent;
    border-top: 5px solid {T.text_secondary};
    margin-right: 6px;
}}

/* ── Push buttons ────────────────────────────────────────────────────────── */
QPushButton {{
    background-color: {T.bg_btn};
    color: {T.text_btn};
    border: 1px solid {T.border};
    border-radius: 4px;
    padding: 5px 12px;
}}
QPushButton:hover {{
    background-color: {T.bg_btn_hover};
    border: 1px solid {T.accent};
}}
QPushButton:pressed {{
    background-color: {T.accent};
    color: {T.accent_text};
}}
QPushButton:disabled {{
    color: {T.text_disabled};
    background-color: {T.bg_secondary};
    border: 1px solid {T.separator};
}}

/* ── Action buttons ──────────────────────────────────────────────────────── */
QPushButton#btn_add {{
    background-color: {T.btn_add};
    color: {T.accent_text};
    border: none;
}}
QPushButton#btn_add:hover {{
    background-color: {T.btn_add_hover};
}}
QPushButton#btn_remove {{
    background-color: {T.btn_remove};
    color: {T.accent_text};
    border: none;
}}
QPushButton#btn_remove:hover {{
    background-color: {T.btn_remove_hover};
}}
QPushButton#btn_clear {{
    background-color: {T.btn_clear};
    color: {T.accent_text};
    border: none;
}}
QPushButton#btn_clear:hover {{
    background-color: {T.btn_clear_hover};
}}

/* ── Refresh button ──────────────────────────────────────────────────────── */
QPushButton#btn_refresh {{
    background-color: {T.accent};
    color: {T.accent_text};
    border: none;
    font-weight: 600;
    border-radius: 4px;
    padding: 5px 12px;
}}
QPushButton#btn_refresh:hover {{
    background-color: {T.accent_hover};
}}

/* ── CheckBox ────────────────────────────────────────────────────────────── */
QCheckBox {{
    color: {T.text_primary};
    spacing: 6px;
    background-color: transparent;
}}
QCheckBox::indicator {{
    width: 14px;
    height: 14px;
    border: 1px solid {T.border};
    border-radius: 3px;
    background-color: {T.bg_input};
}}
QCheckBox::indicator:checked {{
    background-color: {T.accent};
    border-color: {T.accent};
}}
QCheckBox::indicator:checked:hover {{
    background-color: {T.accent_hover};
}}
QCheckBox:disabled {{
    color: {T.text_disabled};
}}

/* ── Tab widget ──────────────────────────────────────────────────────────── */
QTabWidget::pane {{
    background-color: {T.bg_main};
    border: 1px solid {T.border};
    border-radius: 4px;
}}
QTabBar::tab {{
    background-color: {T.bg_secondary};
    color: {T.text_secondary};
    border: 1px solid {T.border};
    border-bottom: none;
    padding: 6px 16px;
    border-top-left-radius: 4px;
    border-top-right-radius: 4px;
    margin-right: 2px;
}}
QTabBar::tab:selected {{
    background-color: {T.bg_main};
    color: {T.text_primary};
    border-bottom: 2px solid {T.accent};
}}
QTabBar::tab:hover:!selected {{
    background-color: {T.bg_btn_hover};
    color: {T.text_primary};
}}

/* ── Table ───────────────────────────────────────────────────────────────── */
QTableWidget {{
    background-color: {T.bg_table};
    alternate-background-color: {T.bg_table_alt};
    color: {T.text_primary};
    gridline-color: {T.separator};
    border: 1px solid {T.border};
    selection-background-color: {T.accent};
    selection-color: {T.accent_text};
}}
QTableWidget::item {{
    padding: 4px 8px;
    border: none;
}}
QTableWidget::item:selected {{
    background-color: {T.accent};
    color: {T.accent_text};
}}
QHeaderView::section {{
    background-color: {T.bg_header};
    color: {T.text_secondary};
    border: none;
    border-right: 1px solid {T.separator};
    border-bottom: 1px solid {T.separator};
    padding: 5px 8px;
    font-weight: 600;
    font-size: 11px;
    text-transform: uppercase;
    letter-spacing: 0.5px;
}}

/* ── Scroll bars ─────────────────────────────────────────────────────────── */
QScrollBar:vertical {{
    background: {T.bg_secondary};
    width: 8px;
    border: none;
}}
QScrollBar::handle:vertical {{
    background: {T.border};
    border-radius: 4px;
    min-height: 20px;
}}
QScrollBar::handle:vertical:hover {{
    background: {T.accent};
}}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
    height: 0;
}}
QScrollBar:horizontal {{
    background: {T.bg_secondary};
    height: 8px;
    border: none;
}}
QScrollBar::handle:horizontal {{
    background: {T.border};
    border-radius: 4px;
    min-width: 20px;
}}
QScrollBar::handle:horizontal:hover {{
    background: {T.accent};
}}
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
    width: 0;
}}

/* ── Line / text inputs ──────────────────────────────────────────────────── */
QLineEdit, QTextEdit, QPlainTextEdit {{
    background-color: {T.bg_input};
    color: {T.text_primary};
    border: 1px solid {T.border};
    border-radius: 4px;
    padding: 4px 8px;
    selection-background-color: {T.accent};
    selection-color: {T.accent_text};
}}
QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus {{
    border: 1px solid {T.border_focus};
}}

/* ── Spin boxes ──────────────────────────────────────────────────────────── */
QDoubleSpinBox, QSpinBox {{
    background-color: {T.bg_input};
    color: {T.text_primary};
    border: 1px solid {T.border};
    border-radius: 4px;
    padding: 3px 6px;
}}
QDoubleSpinBox:focus, QSpinBox:focus {{
    border: 1px solid {T.border_focus};
}}
QDoubleSpinBox::up-button, QSpinBox::up-button,
QDoubleSpinBox::down-button, QSpinBox::down-button {{
    background-color: {T.bg_btn};
    border: none;
    width: 16px;
}}
QDoubleSpinBox::up-button:hover, QSpinBox::up-button:hover,
QDoubleSpinBox::down-button:hover, QSpinBox::down-button:hover {{
    background-color: {T.bg_btn_hover};
}}

/* ── Tooltip ─────────────────────────────────────────────────────────────── */
QToolTip {{
    background-color: {T.bg_tooltip};
    color: {T.text_primary};
    border: 1px solid {T.border};
    border-radius: 3px;
    padding: 4px 8px;
    font-size: 12px;
}}

/* ── Dialog boxes ────────────────────────────────────────────────────────── */
QDialog {{
    background-color: {T.bg_main};
    color: {T.text_primary};
}}
QDialogButtonBox QPushButton {{
    min-width: 80px;
    padding: 5px 14px;
}}

/* ── Message boxes ───────────────────────────────────────────────────────── */
QMessageBox {{
    background-color: {T.bg_main};
    color: {T.text_primary};
}}
QMessageBox QLabel {{
    color: {T.text_primary};
}}

/* ── Input dialog ────────────────────────────────────────────────────────── */
QInputDialog {{
    background-color: {T.bg_main};
    color: {T.text_primary};
}}

/* ── File dialog ─────────────────────────────────────────────────────────── */
QFileDialog {{
    background-color: {T.bg_main};
    color: {T.text_primary};
}}

/* ── Menu (context menus) ────────────────────────────────────────────────── */
QMenu {{
    background-color: {T.bg_input};
    color: {T.text_primary};
    border: 1px solid {T.border};
    border-radius: 4px;
    padding: 4px;
}}
QMenu::item {{
    padding: 5px 20px 5px 12px;
    border-radius: 3px;
}}
QMenu::item:selected {{
    background-color: {T.accent};
    color: {T.accent_text};
}}
QMenu::separator {{
    height: 1px;
    background-color: {T.separator};
    margin: 3px 6px;
}}

/* ── Frames / separators ─────────────────────────────────────────────────── */
QFrame[frameShape="4"],
QFrame[frameShape="5"] {{
    color: {T.separator};
    background-color: {T.separator};
}}

/* ── Status / badge labels ───────────────────────────────────────────────── */
QLabel#badge_none {{
    background-color: {T.badge_none_bg};
    color: {T.badge_none_fg};
    border-radius: 4px;
    padding: 4px 10px;
    font-size: 11px;
}}
"""


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

    # ------------------------------------------------------------------ ROOT
    def update_root(self):
        if self.check_remote.isChecked():
            self.combo_network.setEnabled(True)

            all_hosts = [
                r"\\1.coltonlab.byu.edu\C$",
                r"\\2.coltonlab.byu.edu\C$",
                r"\\3.coltonlab.byu.edu\C$",
            ]
            valid_hosts = []
            for host in all_hosts:
                host_ip = host.strip('\\').split('\\')[0]
                try:
                    socket.create_connection((host_ip, 445), timeout=0.2)
                    valid_hosts.append(host)
                except Exception:
                    continue

            self.combo_network.blockSignals(True)
            current = self.combo_network.currentText()
            self.combo_network.clear()
            self.combo_network.addItems(valid_hosts)
            if current in valid_hosts:
                self.combo_network.setCurrentText(current)
            self.combo_network.blockSignals(False)

            raw_path = self.combo_network.currentText()
            if not raw_path:
                self.base_dir = Path("Data")
            else:
                if platform.system() == "Darwin":
                    # On Mac, SMB shares are typically mounted under /Volumes/ShareName
                    share_name = raw_path.split('\\')[-1]
                    self.base_dir = Path("/Volumes") / share_name / "Data"
                    print("Macs are the best")
                else:
                    self.base_dir = Path(raw_path) / "Data"
        else:
            self.combo_network.setEnabled(False)
            self.base_dir = Path("Data")
        self.refresh_dropdown(self.combo_collab, self.base_dir / "SpectraLink_Data")
        self.update_samples()

    # ------------------------------------------------------------------ CONNECTION
    def refresh_connection(self):
        try:
            current_collab = self.combo_collab.currentText()
            current_sample = self.combo_sample.currentText()
            current_exp    = self.combo_exp.currentText()
            self.update_root()
            self.refresh_dropdown(self.combo_collab, self.base_dir / "SpectraLink_Data")
            if self.combo_collab.findText(current_collab) != -1:
                self.combo_collab.setCurrentText(current_collab)
                self.refresh_dropdown(self.combo_sample, self.base_dir / "SpectraLink_Data" / current_collab)
                if self.combo_sample.findText(current_sample) != -1:
                    self.combo_sample.setCurrentText(current_sample)
                    json_dir = self.base_dir / "SpectraLink_Data" / current_collab / current_sample / "JSON"
                    self.combo_exp.clear()
                    if json_dir.exists():
                        self.combo_exp.addItems(
                            sorted(f.stem for f in json_dir.glob("*.json"))
                        )
                    if self.combo_exp.findText(current_exp) != -1:
                        self.combo_exp.setCurrentText(current_exp)

            self.combo_collab.blockSignals(False)
            self.combo_sample.blockSignals(False)
            self.combo_exp.blockSignals(False)

            self.toggle_buttons()
            self.discovery_tab.refresh_target_label()

        except Exception as e:
            QMessageBox.critical(self, "Refresh Failed", str(e))

    # ------------------------------------------------------------------ INIT UI
    def init_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # ── Sidebar (QFrame for targeted styling) ─────────────────────────────
        sidebar_frame = QFrame()
        sidebar_frame.setObjectName("sidebar")
        sidebar_frame.setFixedWidth(220)
        sidebar = QVBoxLayout(sidebar_frame)
        sidebar.setContentsMargins(12, 14, 12, 14)
        sidebar.setSpacing(4)

        # ── Connection section ────────────────────────────────────────────────
        conn_label = QLabel("<b>Connection Settings</b>")
        sidebar.addWidget(conn_label)
        sidebar.addSpacing(4)

        self.check_remote = QCheckBox("Remote Mode")
        self.check_remote.setChecked(False)
        self.combo_network = QComboBox()
        self.combo_network.setEnabled(False)

        sidebar.addWidget(self.check_remote)
        sidebar.addWidget(self.combo_network)
        sidebar.addSpacing(4)

        self.btn_refresh = QPushButton("⟳  Refresh")
        self.btn_refresh.setObjectName("btn_refresh")
        self.btn_refresh.clicked.connect(self.refresh_connection)
        sidebar.addWidget(self.btn_refresh)

        # sidebar.addSpacing(4)
        # self.label_status = QLabel("● Checking…")
        # self.label_status.setStyleSheet("font-size: 11px;")
        # sidebar.addWidget(self.label_status)

        # ── Dark mode toggle (ToggleSwitch from toggle_switch.py) ─────────────
        sidebar.addSpacing(8)
        T = get_theme(self.dark_mode)
        self.dark_mode_toggle = ToggleSwitch(
            label="Dark Mode",
            checked=self.dark_mode,
            color_on=T.toggle_track_on,
            color_off=T.toggle_track_off,
            thumb_color=T.toggle_thumb,
        )
        self.dark_mode_toggle.toggled.connect(self._on_theme_toggle)
        sidebar.addWidget(self.dark_mode_toggle)

        # ── Divider ───────────────────────────────────────────────────────────
        sidebar.addSpacing(8)
        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sidebar.addWidget(sep)
        sidebar.addSpacing(4)

        # ── Data navigation ───────────────────────────────────────────────────
        sidebar.addWidget(QLabel("<b>Data Navigation</b>"))
        sidebar.addSpacing(4)

        self.combo_collab = QComboBox()
        self.combo_sample = QComboBox()
        self.combo_exp    = QComboBox()

        for cb, label_text in [(self.combo_collab, "Collaborator"),
                               (self.combo_sample, "Sample"),
                               (self.combo_exp,    "Experiment")]:
            lbl = QLabel(label_text)
            lbl.setStyleSheet("font-size: 11px; font-weight: 600; letter-spacing: 0.5px;")
            sidebar.addWidget(lbl)
            sidebar.addWidget(cb)
            sidebar.addSpacing(4)

        sidebar.addSpacing(12)

        self.btn_new_collab = QPushButton("Add New Collaborator")
        self.btn_new_sample = QPushButton("Add New Sample")
        self.btn_new_exp    = QPushButton("Add New Experiment")

        self.btn_new_collab.clicked.connect(lambda: self.create_new_entry("collab"))
        self.btn_new_sample.clicked.connect(lambda: self.create_new_entry("sample"))
        self.btn_new_exp.clicked.connect(lambda: self.create_new_entry("exp"))

        for btn in (self.btn_new_collab, self.btn_new_sample, self.btn_new_exp):
            sidebar.addWidget(btn)
            sidebar.addSpacing(2)

        sidebar.addStretch()
        main_layout.addWidget(sidebar_frame)

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

        # ── Context menus on combo boxes ──────────────────────────────────────
        self.combo_collab.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.combo_sample.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.combo_exp.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)

        self.combo_collab.customContextMenuRequested.connect(
            lambda pos: self._show_context_menu(pos, "collab"))
        self.combo_sample.customContextMenuRequested.connect(
            lambda pos: self._show_context_menu(pos, "sample"))
        self.combo_exp.customContextMenuRequested.connect(
            lambda pos: self._show_context_menu(pos, "exp"))

        # ── Signals ───────────────────────────────────────────────────────────
        self.check_remote.stateChanged.connect(self.update_root)
        self.combo_network.currentIndexChanged.connect(self.update_root)
        self.combo_collab.currentIndexChanged.connect(self.update_samples)
        self.combo_sample.currentIndexChanged.connect(self.update_experiments)
        self.combo_exp.currentIndexChanged.connect(self._on_exp_changed)

        self.update_root()
        self.toggle_buttons()
        self.apply_theme()

    def _on_exp_changed(self):
        self.toggle_buttons()
        self.discovery_tab.refresh_target_label()
        if hasattr(self, 'tabs') and self.tabs.count() > 1:
            analysis_tab = self.tabs.widget(1)
            tech = getattr(self.discovery_tab, '_current_technique', None)
            if analysis_tab and hasattr(analysis_tab, 'rebuild_settings_header') and tech:
                analysis_tab.rebuild_settings_header(tech)

    # ------------------------------------------------------------------ HELPERS
    def toggle_buttons(self):
        has_collab = bool(self.combo_collab.currentText())
        has_sample = bool(self.combo_sample.currentText())
        self.btn_new_collab.setEnabled(True)
        self.btn_new_sample.setEnabled(has_collab)
        self.btn_new_exp.setEnabled(has_sample)

    def update_samples(self):
        self.combo_sample.clear()
        self.combo_exp.clear()
        collab = self.combo_collab.currentText()
        if collab:
            self.refresh_dropdown(self.combo_sample,
                                  self.base_dir / "SpectraLink_Data" / collab)
            self.update_experiments()
        self.toggle_buttons()
        self.discovery_tab.refresh_target_label()

    def update_experiments(self):
        self.combo_exp.clear()
        collab = self.combo_collab.currentText()
        sample = self.combo_sample.currentText()
        if collab and sample:
            json_dir = self.base_dir / "SpectraLink_Data" / collab / sample / "JSON"
            if json_dir.exists():
                self.combo_exp.addItems(
                    sorted(f.stem for f in json_dir.glob("*.json"))
                )
        self.toggle_buttons()
        self.discovery_tab.refresh_target_label()

    def refresh_dropdown(self, combo, path):
        combo.blockSignals(True)
        combo.clear()
        try:
            with os.scandir(path) as it:
                items = [entry.name for entry in it
                         if entry.is_dir() and not entry.name.startswith('.')]
                combo.addItems(sorted(items))
        except Exception:
            pass
        combo.blockSignals(False)

    # ------------------------------------------------------------------ CREATE
    def create_new_entry(self, level):
        old_collab = self.combo_collab.currentText()
        old_sample = self.combo_sample.currentText()

        if level == "exp":
            while True:
                dlg = NewExperimentDialog(self)
                if dlg.exec() != QDialog.DialogCode.Accepted:
                    return
                name, technique = dlg.get_values()
                is_valid, error_msg = validate_filename(name)
                if not is_valid:
                    QMessageBox.warning(self, "Invalid Name",
                        f"Cannot create experiment:\n\n{error_msg}")
                    continue
                break

            name = name.strip().replace(" ", "_")
            try:
                json_dir    = self.base_dir / "SpectraLink_Data" / old_collab / old_sample / "JSON"
                json_dir.mkdir(parents=True, exist_ok=True)
                target_file = json_dir / f"{name}.json"
                if target_file.exists():
                    QMessageBox.warning(self, "Exists", "Already exists.")
                    return
                with open(target_file, 'w') as f:
                    json.dump({
                        "core": {
                            "experiment_name": name,
                            "technique":       technique,
                            "schema_version":  "1.0.0"
                        },
                        "data_files":  {},
                        "parameters":  {"temperature": 295.0}
                    }, f, indent=4)
                self.refresh_ui_after_creation("exp", name, old_collab, old_sample)
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Could not create: {e}")
        else:
            while True:
                name, ok = QInputDialog.getText(
                    self, "New Entry", f"Enter {level} name:")
                if not ok:
                    return
                is_valid, error_msg = validate_filename(name)
                if not is_valid:
                    QMessageBox.warning(self, "Invalid Name",
                        f"Cannot create {level}:\n\n{error_msg}")
                    continue
                break

            name = name.strip().replace(" ", "_")
            try:
                if level == "collab":
                    (self.base_dir / "SpectraLink_Data" / name).mkdir(
                        parents=True, exist_ok=True)
                elif level == "sample":
                    target = self.base_dir / "SpectraLink_Data" / old_collab / name
                    target.mkdir(parents=True, exist_ok=True)
                    (target / "JSON").mkdir(exist_ok=True)
                self.refresh_ui_after_creation(level, name, old_collab, old_sample)
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Could not create: {e}")

    def refresh_ui_after_creation(self, level, name, old_collab, old_sample):
        self.combo_collab.blockSignals(True)
        self.combo_sample.blockSignals(True)
        self.combo_exp.blockSignals(True)

        self.refresh_dropdown(self.combo_collab, self.base_dir / "SpectraLink_Data")

        if level == "collab":
            self.combo_collab.setCurrentText(name)
            self.update_samples()
        elif level == "sample":
            self.combo_collab.setCurrentText(old_collab)
            self.refresh_dropdown(self.combo_sample,
                                  self.base_dir / "SpectraLink_Data" / old_collab)
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
        self.discovery_tab.refresh_target_label()

    def _show_context_menu(self, pos, level):
        if level == "collab":
            combo = self.combo_collab
        elif level == "sample":
            combo = self.combo_sample
        else:
            combo = self.combo_exp

        current_name = combo.currentText()
        if not current_name:
            return

        menu = QMenu(self)
        rename_action = menu.addAction(f"Rename '{current_name}'")

        delete_action = None
        if level == "exp":
            menu.addSeparator()
            delete_action = menu.addAction(f"Delete '{current_name}'")

        action = menu.exec(combo.mapToGlobal(pos))

        if action == rename_action:
            if level == "collab":
                self._rename_collab(current_name)
            elif level == "sample":
                self._rename_sample(current_name)
            else:
                self._rename_experiment(current_name)
        elif action == delete_action and level == "exp":
            self._delete_experiment(current_name)

    def _rename_collab(self, current_name):
        new_name, ok = QInputDialog.getText(
            self, "Rename Collaborator",
            f"Enter new name for '{current_name}':"
        )
        if not ok or not new_name:
            return
        is_valid, err = validate_filename(new_name)
        if not is_valid:
            QMessageBox.warning(self, "Invalid Name", f"Cannot rename:\n\n{err}")
            return
        new_name = new_name.strip().replace(" ", "_")
        try:
            old_path = self.base_dir / "SpectraLink_Data" / current_name
            new_path = self.base_dir / "SpectraLink_Data" / new_name
            old_path.rename(new_path)
            self.update_root()
            self.combo_collab.setCurrentText(new_name)
            QMessageBox.information(self, "Renamed",
                f"Collaborator '{current_name}' renamed to '{new_name}'.")
        except Exception as e:
            QMessageBox.critical(self, "Rename Failed",
                f"Could not rename collaborator: {e}")

    def _rename_sample(self, current_name):
        collab = self.combo_collab.currentText()
        if not collab:
            QMessageBox.warning(self, "No Collaborator",
                "Please select a collaborator first.")
            return
        new_name, ok = QInputDialog.getText(
            self, "Rename Sample",
            f"Enter new name for '{current_name}':"
        )
        if not ok or not new_name:
            return
        is_valid, err = validate_filename(new_name)
        if not is_valid:
            QMessageBox.warning(self, "Invalid Name", f"Cannot rename:\n\n{err}")
            return
        new_name = new_name.strip().replace(" ", "_")
        try:
            old_path = self.base_dir / "SpectraLink_Data" / collab / current_name
            new_path = self.base_dir / "SpectraLink_Data" / collab / new_name
            old_path.rename(new_path)
            self.update_samples()
            self.combo_sample.setCurrentText(new_name)
            QMessageBox.information(self, "Renamed",
                f"Sample '{current_name}' renamed to '{new_name}'.")
        except Exception as e:
            QMessageBox.critical(self, "Rename Failed",
                f"Could not rename sample: {e}")

    def _rename_experiment(self, current_name):
        collab = self.combo_collab.currentText()
        sample = self.combo_sample.currentText()
        if not collab or not sample:
            QMessageBox.warning(self, "No Context",
                "Please select a collaborator and sample first.")
            return
        new_name, ok = QInputDialog.getText(
            self, "Rename Experiment",
            f"Enter new name for '{current_name}':"
        )
        if not ok or not new_name:
            return
        is_valid, err = validate_filename(new_name)
        if not is_valid:
            QMessageBox.warning(self, "Invalid Name", f"Cannot rename:\n\n{err}")
            return
        new_name = new_name.strip().replace(" ", "_")
        try:
            json_dir = self.base_dir / "SpectraLink_Data" / collab / sample / "JSON"
            old_path = json_dir / f"{current_name}.json"
            new_path = json_dir / f"{new_name}.json"
            old_path.rename(new_path)
            self.update_experiments()
            self.combo_exp.setCurrentText(new_name)
            QMessageBox.information(self, "Renamed",
                f"Experiment '{current_name}' renamed to '{new_name}'.")
        except Exception as e:
            QMessageBox.critical(self, "Rename Failed",
                f"Could not rename experiment: {e}")

    def _delete_experiment(self, exp_name):
        collab = self.combo_collab.currentText()
        sample = self.combo_sample.currentText()
        if not collab or not sample:
            QMessageBox.warning(self, "No Context",
                "Please select a collaborator and sample first.")
            return
        reply = QMessageBox.question(
            self, "Delete Experiment",
            f"Are you sure you want to delete the experiment '{exp_name}'?\n\n"
            "This will permanently delete the JSON file and all associated data.\n"
            "This action cannot be undone.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        if reply != QMessageBox.StandardButton.Yes:
            return
        try:
            json_path = (self.base_dir / "SpectraLink_Data" /
                         collab / sample / "JSON" / f"{exp_name}.json")
            if json_path.exists():
                json_path.unlink()
                QMessageBox.information(self, "Deleted",
                    f"Experiment '{exp_name}' has been deleted.")
            else:
                QMessageBox.warning(self, "Not Found",
                    f"Experiment file not found: {json_path}")
            self.update_experiments()
            self.discovery_tab.refresh_target_label()
        except Exception as e:
            QMessageBox.critical(self, "Delete Failed",
                f"Could not delete experiment: {e}")

    # ── Analysis tab support ───────────────────────────────────────────────────
    @property
    def current_exp_json(self):
        if not hasattr(self, '_cached_json'):
            self._cached_json = {}
        json_path = getattr(self.discovery_tab, '_current_json_path', None)
        if not json_path:
            return self._cached_json
        try:
            with open(json_path, 'r') as f:
                self._cached_json = json.load(f)
            return self._cached_json
        except Exception as e:
            QMessageBox.warning(self, "Error Reading JSON",
                f"Could not read experiment: {e}")
            return {}

    def save_current_json(self):
        json_path = getattr(self.discovery_tab, '_current_json_path', None)
        if not json_path:
            QMessageBox.warning(self, "Error", "No experiment selected to save")
            return False
        try:
            with open(json_path, 'w') as f:
                json.dump(self._cached_json, f, indent=4)
            return True
        except Exception as e:
            QMessageBox.critical(self, "Save Error",
                f"Could not save experiment: {e}")
            return False

    # ──────────────────────────────────────────────────────────────────────────
    #  Theme
    # ──────────────────────────────────────────────────────────────────────────
    def _on_theme_toggle(self, is_dark: bool):
        """Slot connected to the ToggleSwitch toggled signal."""
        self.dark_mode = is_dark
        self.apply_theme()
        if hasattr(self, 'discovery_tab'):
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

        # 3. Update the ToggleSwitch pill colors to match the new theme
        if hasattr(self, 'dark_mode_toggle'):
            self.dark_mode_toggle.updateThemeColors(
                color_on=T.toggle_track_on,
                color_off=T.toggle_track_off,
                thumb_color=T.toggle_thumb,
                label_color=T.text_primary,
            )

        # # 4. Status label color
        # if hasattr(self, 'label_status'):
        #     self.label_status.setStyleSheet(
        #         f"color: {T.text_secondary}; font-size: 11px;"
        #     )


# ──────────────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = SpectraLink()
    window.show()
    sys.exit(app.exec())
