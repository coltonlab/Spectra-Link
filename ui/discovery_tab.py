import sys
import os
import json
from pathlib import Path
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout,
    QHBoxLayout, QTabWidget, QComboBox, QPushButton,
    QLabel, QInputDialog, QMessageBox, QFileDialog,
    QCheckBox, QTableWidget, QTableWidgetItem, QHeaderView,
    QAbstractItemView, QSpinBox, QDoubleSpinBox, QFrame,
    QDialog, QLineEdit, QPlainTextEdit, QDialogButtonBox, QFormLayout, QMenu
)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QColor, QBrush
import platform
import re

from config.techniques import TECHNIQUE_CONFIG, SCAN_TYPE_COLORS
# from ui.dialogs import NewExperimentDialog
from ui.theme import get_theme
from utils.validators import validate_filename

# ──────────────────────────────────────────────────────────────────────────────
#  Discovery / Selection tab
# ──────────────────────────────────────────────────────────────────────────────
class DiscoveryTab(QWidget):
    def __init__(self, parent_window):
        super().__init__()
        self.parent_window = parent_window
        self._current_technique = None
        self._current_json_path = None
        self._autosave_pending  = False
        self._last_file_dir     = None 
        self._param_widgets: dict = {} 

        self._autosave_timer = QTimer()
        self._autosave_timer.setSingleShot(True)
        self._autosave_timer.setInterval(800)
        self._autosave_timer.timeout.connect(self._write_json)

        self._build_ui()
        # Initialize theme state
        self.apply_theme(self.parent_window.dark_mode)

    def apply_theme(self, is_dark: bool):
        """Updates all stylesheet-heavy components based on theme."""
        T = get_theme(is_dark)
        
        # 1. Labels and Titles
        self.lbl_title.setStyleSheet(f"font-size: 15px; font-weight: bold; color: {T.text_primary};")
        self.lbl_save_status.setStyleSheet(f"color: {T.text_secondary}; font-size: 10px; font-style: italic;")
        
        # Update target label color based on status
        if "No experiment" in self.lbl_target.text():
            self.lbl_target.setStyleSheet(f"color: {T.target_no_exp_fg}; font-style: italic; font-size: 11px;")
        else:
            self.lbl_target.setStyleSheet(f"color: {T.target_exp_fg}; font-style: normal; font-size: 11px;")

        # 2. Parameters Frame
        self.params_frame.setStyleSheet(f"""
            QFrame {{
                background-color: {T.bg_main};
                border: 1px solid {T.border};
                border-radius: 6px;
            }}
        """)
        self.params_header.setStyleSheet(f"color: {T.text_secondary}; font-size: 10px; font-weight: bold; text-transform: uppercase; border: none; background: transparent;")
        self.params_placeholder.setStyleSheet(f"color: {T.text_secondary}; font-style: italic; font-size: 11px; border: none; background: transparent;")

        # 3. Table Styles
        table_selected_bg = T.table_selected_bg_dark if is_dark else T.table_selected_bg_light
        self.table.setStyleSheet(f"""
            QTableWidget {{
                background-color: {T.bg_table}; gridline-color: {T.border};
                color: {T.text_primary}; font-size: 12px;
                border: 1px solid {T.border}; border-radius: 4px;
            }}
            QTableWidget::item:selected {{ background-color: {table_selected_bg}; color: {T.accent_text}; }}
            QHeaderView::section {{
                background-color: {T.table_header_bg}; 
                color: {T.table_header_fg};
                padding: 5px; border: none;
                border-bottom: 1px solid {T.border};
                font-weight: bold; font-size: 11px;
            }}
        """)

        # 4. Input Widgets (ComboBoxes and SpinBoxes in the table)
        # These are usually refreshed when the table is rebuilt, but we can set defaults
        self._set_badge_style(self._current_technique)

        # Update existing input widgets in the table (ComboBox, SpinBox, Notes)
        for row in range(self.table.rowCount()):
            for col in range(self.table.columnCount()):
                w = self.table.cellWidget(row, col)
                if isinstance(w, (QComboBox, QDoubleSpinBox, QLineEdit, QPlainTextEdit)):
                    w.setStyleSheet(self._get_widget_style(w, is_dark))
        
        self._update_global_params_style(is_dark)

        # 6. Refresh existing table rows for theme-specific colors
        for row in range(self.table.rowCount()):
            combo = self.table.cellWidget(row, 1)
            if combo:
                # Update the row background
                self._update_row_color(row, combo.currentText())

    def _get_widget_style(self, widget, is_dark):
        T = get_theme(is_dark)
        if isinstance(widget, QComboBox):
            return f"QComboBox {{ background-color: {T.combo_bg}; color: {T.combo_fg}; border: 1px solid {T.combo_border}; border-radius: 3px; padding: 2px 6px; min-width: 100px; }} QComboBox::drop-down {{ border: none; }}"
        elif isinstance(widget, QDoubleSpinBox):
            if widget.isEnabled():
                return f"QDoubleSpinBox {{ background-color: {T.spin_bg}; color: {T.spin_fg}; border: 1px solid {T.spin_border}; border-radius: 3px; padding: 2px 4px; min-width: 80px; }}"
            return f"QDoubleSpinBox {{ background-color: {T.spin_disabled_bg}; color: {T.spin_disabled_fg}; border: 1px solid {T.spin_border}; border-radius: 3px; padding: 2px 4px; min-width: 80px; }}"
        elif isinstance(widget, (QLineEdit, QPlainTextEdit)):
            cls = "QLineEdit" if isinstance(widget, QLineEdit) else "QPlainTextEdit"
            return f"{cls} {{ background-color: {T.bg_input}; color: {T.text_primary}; border: 1px solid {T.border}; border-radius: 3px; padding: 2px 6px; min-width: 100px; }}"
        return ""

    def _update_global_params_style(self, is_dark):
        for widget in self._param_widgets.values():
            widget.setStyleSheet(self._get_widget_style(widget, is_dark))

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(16, 16, 16, 16)
        root.setSpacing(10)

        # Header
        header = QHBoxLayout()
        self.lbl_title = QLabel("Discovery / Selection") 
        header.addWidget(self.lbl_title)
        header.addStretch()

        self.lbl_technique_badge = QLabel("—")
        self.lbl_technique_badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_technique_badge.setFixedHeight(34)
        self.lbl_technique_badge.setMinimumWidth(220)
        header.addWidget(self.lbl_technique_badge)
        root.addLayout(header)

        # Divider
        self.line = QFrame()
        self.line.setFrameShape(QFrame.Shape.HLine)
        root.addWidget(self.line)

        # Status row
        status_row = QHBoxLayout()
        self.lbl_target = QLabel("No experiment selected.")
        status_row.addWidget(self.lbl_target)
        status_row.addStretch()

        self.lbl_save_status = QLabel("")
        status_row.addWidget(self.lbl_save_status)
        root.addLayout(status_row)

        # Parameters panel
        self.params_frame = QFrame()
        self.params_frame.setMinimumHeight(90)
        self.params_frame.setMaximumHeight(140)

        params_inner = QVBoxLayout(self.params_frame)
        params_inner.setContentsMargins(12, 8, 12, 8)
        params_inner.setSpacing(8)

        self.params_header = QLabel("Experiment Parameters")
        params_inner.addWidget(self.params_header)

        self._params_dynamic_layout = QHBoxLayout()
        self._params_dynamic_layout.setSpacing(12)
        params_inner.addLayout(self._params_dynamic_layout)

        self.params_placeholder = QLabel("Select an experiment to load or add files.")
        self.params_placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
        params_inner.addWidget(self.params_placeholder, stretch=1)
        root.addWidget(self.params_frame)

        # Table
        self.table = QTableWidget()
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.verticalHeader().setVisible(False)
        self.table.itemChanged.connect(self._schedule_autosave)
        root.addWidget(self.table, stretch=1)

        # Buttons (Keep colors consistent but adjust text color if needed)
        btn_row = QHBoxLayout()
        self.btn_add    = QPushButton("＋  Add Files")
        self.btn_remove = QPushButton("✕  Remove Selected")
        self.btn_clear  = QPushButton("Clear All")

        self.btn_add.clicked.connect(self._add_files)
        self.btn_remove.clicked.connect(self._remove_selected)
        self.btn_clear.clicked.connect(self._clear_all)

        T = get_theme(self.parent_window.dark_mode)
        self.btn_add.setStyleSheet(f"QPushButton {{ background-color: {T.btn_add}; color: {T.text_btn}; border: none; padding: 7px 16px; border-radius: 4px; font-size: 12px; }} QPushButton:hover {{ background-color: {T.btn_add_hover}; }}")
        self.btn_remove.setStyleSheet(f"QPushButton {{ background-color: {T.btn_remove}; color: {T.text_btn}; border: none; padding: 7px 16px; border-radius: 4px; font-size: 12px; }} QPushButton:hover {{ background-color: {T.btn_remove_hover}; }}")
        self.btn_clear.setStyleSheet(f"QPushButton {{ background-color: {T.btn_clear}; color: {T.text_btn}; border: none; padding: 7px 16px; border-radius: 4px; font-size: 12px; }} QPushButton:hover {{ background-color: {T.btn_clear_hover}; }}")
        
        btn_row.addWidget(self.btn_add)
        btn_row.addWidget(self.btn_remove)
        btn_row.addWidget(self.btn_clear)
        btn_row.addStretch()
        root.addLayout(btn_row)

        self._rebuild_columns_for_technique(None)

    def _make_spin_style(self, is_dark=None):
        # Fallback to current parent state if not provided
        dark = is_dark if is_dark is not None else self.parent_window.dark_mode
        T = get_theme(dark)
        return f"QDoubleSpinBox {{ background-color: {T.spin_bg}; color: {T.spin_fg}; border: 1px solid {T.spin_border}; border-radius: 3px; padding: 2px 4px; min-width: 80px; }}"

    def _disabled_spin_style(self):
        dark = self.parent_window.dark_mode
        T = get_theme(dark)
        return f"QDoubleSpinBox {{ background-color: {T.spin_disabled_bg}; color: {T.spin_disabled_fg}; border: 1px solid {T.spin_border}; border-radius: 3px; padding: 2px 4px; min-width: 80px; }}"

    # ... Include other helper methods, ensuring they use self.parent_window.dark_mode for logic ...
    # ------------------------------------------------------------------ BADGE
    def _set_badge_style(self, technique):
        if technique and technique in TECHNIQUE_CONFIG:
            cfg = TECHNIQUE_CONFIG[technique]
            self.lbl_technique_badge.setText(technique)
            self.lbl_technique_badge.setStyleSheet(f"""
                QLabel {{
                    background-color: {cfg['badge_color']};
                    color: {cfg['badge_text_color']};
                    border-radius: 6px; font-size: 14px;
                    font-weight: bold; padding: 0 16px; letter-spacing: 1px;
                }}
            """)
        else:
            T = get_theme(self.parent_window.dark_mode)
            self.lbl_technique_badge.setText("No experiment selected")
            self.lbl_technique_badge.setStyleSheet(f"""
                QLabel {{
                    background-color: {T.badge_none_bg}; color: {T.badge_none_fg};
                    border-radius: 6px; font-size: 12px;
                    font-weight: bold; padding: 0 16px;
                }}
            """)

    # ------------------------------------------------------------------ PARAMETER UI
    def rebuild_parameter_ui(self, technique: str | None) -> None:
        """
        Dynamically rebuild the Experiment Parameters panel for *technique*.

        Reads TECHNIQUE_CONFIG[technique]["global_params"] — a list of dicts:
            [
                {"key": "temperature", "label": "Temperature (K)",
                 "min": 0, "max": 9999, "default": 295, "step": 1, "decimals": 0},
                ...
            ]

        Stores live widget references in self._param_widgets so that
        _write_json / _load_from_json can read/write parameters generically.
        """
        T = get_theme(self.parent_window.dark_mode)
        SPINBOX_STYLE = f"""
            QDoubleSpinBox {{
                background-color: {T.spin_bg}; color: {T.spin_fg};
                border: 1px solid {T.spin_border}; border-radius: 3px;
                padding: 4px 8px; min-width: 80px;
            }}
            QDoubleSpinBox:disabled {{
                background-color: {T.spin_disabled_bg}; color: {T.spin_disabled_fg};
            }}
        """
        LABEL_STYLE = f"color: {T.text_secondary}; font-size: 12px; border: none; background: transparent;"

        # ── 1. Clear previous dynamic widgets ────────────────────────────────
        self._param_widgets = {}
        while self._params_dynamic_layout.count():
            item = self._params_dynamic_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        # ── 2. No technique → show placeholder ───────────────────────────────
        if technique is None or technique not in TECHNIQUE_CONFIG:
            self.params_placeholder.setVisible(True)
            return

        cfg           = TECHNIQUE_CONFIG[technique]
        global_params = cfg.get("global_params", [])

        self.params_placeholder.setVisible(not bool(global_params))

        # ── 3. Build one input widget per global_param entry ────────────────
        for param in global_params:
            key        = param["key"]
            label      = param.get("label", key)
            param_type = param.get("type", "numeric")
            default    = param.get("default", "" if param_type == "text" else 0.0)

            lbl = QLabel(f"{label}:")
            lbl.setStyleSheet(LABEL_STYLE)

            if param_type == "text":
                widget = QLineEdit(str(default))
                widget.setStyleSheet(self._get_widget_style(widget, self.parent_window.dark_mode))
                widget.textChanged.connect(self._schedule_autosave)
            else:
                mn       = param.get("min",      0.0)
                mx       = param.get("max",   9999.0)
                step     = param.get("step",     1.0)
                decimals = param.get("decimals",   0)

                widget = QDoubleSpinBox()
                widget.setRange(mn, mx)
                widget.setSingleStep(step)
                widget.setDecimals(decimals)
                try:
                    widget.setValue(float(default))
                except (TypeError, ValueError):
                    widget.setValue(0.0)
                widget.setStyleSheet(self._get_widget_style(widget, self.parent_window.dark_mode))
                widget.valueChanged.connect(self._schedule_autosave)

            self._params_dynamic_layout.addWidget(lbl)
            self._params_dynamic_layout.addWidget(widget)
            self._param_widgets[key] = widget

        self._params_dynamic_layout.addStretch()

    # ------------------------------------------------------------------ COLUMNS
    def _rebuild_columns_for_technique(self, technique):
        """Wipe table and rebuild headers for the given technique."""
        self.table.blockSignals(True)
        self.table.clear()
        self.table.setRowCount(0)
        self.table.blockSignals(False)

        if technique is None or technique not in TECHNIQUE_CONFIG:
            cols = ["Filename", "Scan Type", "Notes", "Full Path"]
            self.table.setColumnCount(len(cols))
            for i in range(self.table.columnCount()):
                self.table.setColumnHidden(i, False)
            self.table.setHorizontalHeaderLabels(cols)
            hh = self.table.horizontalHeader()
            hh.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents) # Filename
            hh.setSectionResizeMode(1, QHeaderView.ResizeMode.Fixed)          # Scan Type
            self.table.setColumnWidth(1, 120)
            hh.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)          # Notes
            self.table.setColumnHidden(len(cols)-1, True) # Hide Path
            return

        cfg         = TECHNIQUE_CONFIG[technique]
        local_param = cfg.get("local_param")
        has_local   = local_param is not None
        cols        = ["Filename", "Scan Type"]
        if has_local:
            cols.append(local_param["label"])
        cols.append("Notes")
        cols.append("Full Path")

        self.table.setColumnCount(len(cols))
        for i in range(self.table.columnCount()):
            self.table.setColumnHidden(i, False)
        self.table.setHorizontalHeaderLabels(cols)
        hh = self.table.horizontalHeader()
        hh.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents) # Filename
        hh.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)          # Scan Type
        if has_local:
            hh.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents) # Local
            hh.setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)          # Notes
        else:
            hh.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)          # Notes
        self.table.setColumnHidden(len(cols)-1, True) # Hide Path

    # ------------------------------------------------------------------ REFRESH TARGET
    def refresh_target_label(self):
        """Called by main window whenever sidebar selection changes.
        Reloads the table from the JSON of the selected experiment."""
        pw     = self.parent_window
        collab = pw.combo_collab.currentText()
        sample = pw.combo_sample.currentText()
        exp    = pw.combo_exp.currentText()

        if collab and sample and exp:
            self.lbl_target.setText(f"Target →  {collab}  /  {sample}  /  {exp}.json")
            T = get_theme(pw.dark_mode)
            self.lbl_target.setStyleSheet(f"color: {T.target_exp_fg}; font-style: normal; font-size: 11px;")
            json_path = pw.base_dir / "SpectraLink_Data" / collab / sample / "JSON" / f"{exp}.json"
            self._current_json_path = json_path
            # Populate the main window's JSON cache
            if hasattr(pw, '_cached_json'):
                try:
                    with open(json_path, 'r') as f:
                        pw._cached_json = json.load(f)
                except Exception:
                    pw._cached_json = {}
            technique = self._read_technique_from_json(json_path)
            self._current_technique = technique
            self._set_badge_style(technique)
            self._rebuild_columns_for_technique(technique)
            self.rebuild_parameter_ui(technique)
            self._load_from_json(json_path)
        else:
            self.lbl_target.setText("No experiment selected — use the sidebar to select or create one.")
            T = get_theme(pw.dark_mode)
            self.lbl_target.setStyleSheet(f"color: {T.target_no_exp_fg}; font-style: italic; font-size: 11px;")
            self._current_json_path = None
            self._current_technique = None
            self._set_badge_style(None)
            self._rebuild_columns_for_technique(None)
            self.rebuild_parameter_ui(None)
            self.lbl_save_status.setText("")

    # ------------------------------------------------------------------ LOAD FROM JSON
    def _load_from_json(self, json_path):
        """Populate the table from an existing experiment JSON."""
        try:
            with open(json_path, 'r') as f:
                data = json.load(f)
        except Exception:
            return

        technique = data.get("core", {}).get("technique")
        if not technique or technique not in TECHNIQUE_CONFIG:
            return

        cfg         = TECHNIQUE_CONFIG[technique]
        local_param = cfg.get("local_param")
        has_local   = local_param is not None
        local_key   = local_param["key"] if has_local else None
        key_map     = cfg["json_key_map"]
        data_files  = data.get("data_files", {})
        parameters  = data.get("parameters", {})

        # Restore global parameter widget values
        for key, widget in self._param_widgets.items():
            val = parameters.get(key)
            if val is None:
                continue
            if isinstance(widget, QDoubleSpinBox):
                try:
                    widget.setValue(float(val))
                except (TypeError, ValueError):
                    pass
            elif isinstance(widget, QLineEdit):
                widget.setText(str(val))

        # Build a list of (relative_path, scan_type, local_value_or_None, notes) tuples
        entries = []

        # Flat key entries (Blank, Transmission, Reference, Background, Sample)
        reverse_map = {v: k for k, v in key_map.items()}
        for json_key, scan_type in reverse_map.items():
            if json_key == "none_files": continue
            val = data_files.get(json_key)
            if val:
                if isinstance(val, dict):
                    entries.append((val.get("path", ""), scan_type, None, val.get("notes", "")))
                else:
                    entries.append((val, scan_type, None, ""))

        # Local-param scan list (e.g. voltage_scans, temperature_scans)
        if has_local:
            list_key = f"{local_key}_scans"
            for item in data_files.get(list_key, []):
                if isinstance(item, dict):
                    entries.append((
                        item.get("file", ""),
                        item.get("scan_type", ""),
                        item.get(local_key, local_param.get("default", 0)),
                        item.get("notes", "")
                    ))

        # None files
        for item in data_files.get("none_files", []):
            if isinstance(item, dict):
                entries.append((item.get("path", ""), "None", None, item.get("notes", "")))
            else:
                entries.append((item, "None", None, ""))

        if not entries:
            self.lbl_save_status.setText("No files saved yet.")
            return

        self.table.blockSignals(True)
        self.table.setRowCount(0)

        active_scan_types = local_param.get("active_scan_types", []) if has_local else []

        for rel_path, scan_type, local_value, notes_text in entries:
            full_path = self.parent_window.base_dir / Path(rel_path)
            fname     = Path(rel_path).name
            row       = self.table.rowCount()
            self.table.insertRow(row)

            # Ensure items exist for all columns so background colors and layout work correctly
            for col_idx in range(self.table.columnCount()):
                self.table.setItem(row, col_idx, QTableWidgetItem(""))

            # 0: Filename
            item_name = QTableWidgetItem(fname)
            item_name.setFlags(item_name.flags() & ~Qt.ItemFlag.ItemIsEditable)
            if not full_path.exists():
                T = get_theme(self.parent_window.dark_mode)
                item_name.setForeground(QBrush(QColor(T.missing_file_fg)))
                item_name.setToolTip(f"File not found:\n{full_path}")
            self.table.setItem(row, 0, item_name)

            # 1: Scan Type (Widget)
            combo = self._make_scan_combo(cfg.get("scan_types", ["None"]), row)
            idx   = combo.findText(scan_type)
            if idx >= 0: combo.setCurrentIndex(idx)
            self.table.setCellWidget(row, 1, combo)

            # 2/3: Local / Notes / Path
            notes_col = 2
            if has_local:
                default_val = local_param.get("default", 0)
                spin = self._make_local_spin(local_param, value=local_value if local_value is not None else default_val)
                enabled = scan_type in active_scan_types
                if not enabled:
                    spin.setEnabled(False)
                    spin.setStyleSheet(self._disabled_spin_style())
                self.table.setCellWidget(row, 2, spin)
                notes_col = 3
            
            # Notes Widget
            notes_edit = self._make_notes_edit(notes_text)
            self.table.setCellWidget(row, notes_col, notes_edit)

            # Hidden Path Column
            path_item = QTableWidgetItem(str(full_path))
            self.table.setItem(row, self.table.columnCount()-1, path_item)

            self._update_row_color(row, combo.currentText())

        self.table.blockSignals(False)
        self.table.resizeRowsToContents()
        self.lbl_save_status.setText("Loaded from JSON.")

    # ------------------------------------------------------------------ ADD FILES
    def _add_files(self):
        if not self._current_technique:
            QMessageBox.warning(self, "No Experiment",
                "Select an experiment in the sidebar first.")
            return

        initial_dir = self._last_file_dir if self._last_file_dir else str(self.parent_window.base_dir)

        files, _ = QFileDialog.getOpenFileNames(
            self, "Select Data Files", initial_dir,
            "Data Files (*.xls *.txt *.csv *.dat *.asc *.sp);;All Files (*)"
        )
        if not files:
            return

        self._last_file_dir = str(Path(files[0]).parent)

        cfg         = TECHNIQUE_CONFIG[self._current_technique]
        scan_types  = cfg["scan_types"]
        local_param = cfg.get("local_param")
        has_local   = local_param is not None

        self.table.blockSignals(True)
        for fpath in files:
            fname = Path(fpath).name
            row   = self.table.rowCount()
            self.table.insertRow(row)

            # Ensure items exist for all columns
            for col_idx in range(self.table.columnCount()):
                self.table.setItem(row, col_idx, QTableWidgetItem(""))

            # 0: Filename
            item_name = QTableWidgetItem(fname)
            item_name.setFlags(item_name.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.table.setItem(row, 0, item_name)

            # 1: Scan Type
            combo = self._make_scan_combo(scan_types, row)
            combo.setCurrentText("None")
            self.table.setCellWidget(row, 1, combo)

            # Local / Notes / Path
            notes_col = 2
            if has_local:
                spin = self._make_local_spin(local_param, value=local_param.get("default", 0))
                spin.setEnabled(False)
                spin.setStyleSheet(self._disabled_spin_style())
                self.table.setCellWidget(row, 2, spin)
                notes_col = 3
            
            self.table.setCellWidget(row, notes_col, self._make_notes_edit(""))

            # Hidden Path
            self.table.setItem(row, self.table.columnCount()-1, QTableWidgetItem(fpath))

            self._update_row_color(row, "None")

        self.table.blockSignals(False)
        self.table.resizeRowsToContents()
        self._schedule_autosave()

    # ------------------------------------------------------------------ HELPERS
    def _make_scan_combo(self, scan_types, row):
        combo = QComboBox()
        combo.addItems(scan_types)
        T = get_theme(self.parent_window.dark_mode)
        combo.setStyleSheet(f"""
            QComboBox {{
                background-color: {T.combo_bg}; color: {T.combo_fg};
                border: 1px solid {T.combo_border}; border-radius: 3px; padding: 2px 6px;
                min-width: 100px;
            }}
            QComboBox::drop-down {{ border: none; }}
        """)
        combo.currentTextChanged.connect(
            lambda text, r=row: self._on_scan_type_changed(r, text)
        )
        return combo

    def _make_local_spin(self, local_param: dict, value=0):
        """Create a QDoubleSpinBox for the table's local-param column."""
        spin = QDoubleSpinBox()
        spin.setRange(local_param.get("min", -9999), local_param.get("max", 9999))
        spin.setSingleStep(local_param.get("step", 1))
        spin.setDecimals(local_param.get("decimals", 0))
        spin.setValue(value)
        spin.setStyleSheet(self._make_spin_style())
        spin.valueChanged.connect(self._schedule_autosave)
        return spin

    def _make_notes_edit(self, text):
        edit = QPlainTextEdit(text)
        edit.setPlaceholderText("Add notes...")
        edit.setTabChangesFocus(True)
        edit.setMaximumHeight(45)
        edit.setStyleSheet(self._get_widget_style(edit, self.parent_window.dark_mode))
        edit.textChanged.connect(self._schedule_autosave)
        return edit

    def _on_scan_type_changed(self, row, text):
        cfg         = TECHNIQUE_CONFIG.get(self._current_technique, {})
        key_map     = cfg.get("json_key_map", {})
        local_param = cfg.get("local_param")

        # Unique scan types (those in json_key_map, excluding none_files) can only
        # appear once — demote any previous row with the same type to "None"
        if text in key_map and key_map[text] != "none_files":
            for r in range(self.table.rowCount()):
                if r != row:
                    combo = self.table.cellWidget(r, 1)
                    if combo and combo.currentText() == text:
                        combo.setCurrentText("None")
                        self._update_row_color(r, "None")

        self._update_row_color(row, text)

        # Enable/disable local-param spinbox based on active_scan_types
        if local_param:
            spin = self.table.cellWidget(row, 2)
            if isinstance(spin, QDoubleSpinBox):
                active = local_param.get("active_scan_types", [])
                if text in active:
                    spin.setEnabled(True)
                    spin.setStyleSheet(self._make_spin_style())
                else:
                    spin.setEnabled(False)
                    spin.setValue(local_param.get("default", 0))
                    spin.setStyleSheet(self._disabled_spin_style())

        self._schedule_autosave()

    def _update_row_color(self, row, scan_type):
        is_dark = self.parent_window.dark_mode
        T = get_theme(is_dark)
        
        # Look up the color tuple. Default to a neutral if not found.
        colors = SCAN_TYPE_COLORS.get(scan_type, ("#2a2a2a", "#ffffff"))
        
        # Select the color based on theme
        color_hex = colors[0] if is_dark else colors[1]
        
        # Also adjust text color for contrast
        text_color = T.row_text_fg_dark if is_dark else T.row_text_fg_light
        path_color = T.path_text_fg
        
        brush = QBrush(QColor(color_hex))
        text_brush = QBrush(QColor(text_color))
        path_brush = QBrush(QColor(path_color))

        for col in range(self.table.columnCount()):
            item = self.table.item(row, col)
            if item:
                item.setBackground(brush)
                item.setForeground(text_brush)

    def _remove_selected(self):
        rows = sorted(
            set(idx.row() for idx in self.table.selectedIndexes()),
            reverse=True
        )
        for r in rows:
            self.table.removeRow(r)
        self._schedule_autosave()

    def _clear_all(self):
        if self.table.rowCount() == 0:
            return
        reply = QMessageBox.question(
            self, "Clear All", "Remove all rows from the table?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            self.table.blockSignals(True)
            self.table.setRowCount(0)
            self.table.blockSignals(False)
            self._schedule_autosave()

    # ------------------------------------------------------------------ AUTOSAVE
    def _schedule_autosave(self, *_):
        """Reset the debounce timer on any change."""
        if not self._current_json_path:
            return
        T = get_theme(self.parent_window.dark_mode)
        self.lbl_save_status.setText("Unsaved changes…")
        self.lbl_save_status.setStyleSheet(f"color: {T.save_pending_fg}; font-size: 10px; font-style: italic;")
        self._autosave_timer.start()

    def _write_json(self):
        """Actually write the JSON — called by the debounce timer."""
        if not self._current_json_path or not self._current_technique:
            return

        json_path   = self._current_json_path
        technique   = self._current_technique
        cfg         = TECHNIQUE_CONFIG.get(technique, {})
        local_param = cfg.get("local_param")
        has_local   = local_param is not None
        local_key   = local_param["key"] if has_local else None
        key_map     = cfg.get("json_key_map", {})

        try:
            with open(json_path, 'r') as f:
                data = json.load(f)
        except Exception:
            T = get_theme(self.parent_window.dark_mode)
            self.lbl_save_status.setText("Save failed — read error.")
            self.lbl_save_status.setStyleSheet(f"color: {T.save_error_fg}; font-size: 10px;")
            return

        # ── core + parameters ─────────────────────────────────────────────────
        data.setdefault("core", {})["technique"] = technique
        data.setdefault("parameters", {}).update({
            key: (widget.value() if isinstance(widget, QDoubleSpinBox) else widget.text())
            for key, widget in self._param_widgets.items()
        })

        # ── data_files ────────────────────────────────────────────────────────
        data["data_files"] = {}
        if has_local:
            data["data_files"][f"{local_key}_scans"] = []
        data["data_files"]["none_files"] = []

        active_scan_types = local_param.get("active_scan_types", []) if has_local else []
        path_col  = self.table.columnCount() - 1
        if has_local:
            local_col = 2
            notes_col = 3
        else:
            local_col = None
            notes_col = 2

        for row in range(self.table.rowCount()):
            path_item    = self.table.item(row, path_col)
            combo_widget = self.table.cellWidget(row, 1)
            notes_widget = self.table.cellWidget(row, notes_col)
            if not path_item or not combo_widget or not notes_widget:
                continue

            full_path = path_item.text()
            scan_type = combo_widget.currentText()
            notes_val = notes_widget.toPlainText()

            try:
                rel = Path(full_path).relative_to(self.parent_window.base_dir).as_posix()
            except ValueError:
                rel = full_path

            if has_local and scan_type in active_scan_types:
                spin      = self.table.cellWidget(row, local_col)
                local_val = spin.value() if isinstance(spin, QDoubleSpinBox) else 0.0
                data["data_files"][f"{local_key}_scans"].append({
                    "file":      rel,
                    "scan_type": scan_type,
                    local_key:   local_val,
                    "notes":     notes_val
                })
            elif scan_type == "None":
                data["data_files"]["none_files"].append({"path": rel, "notes": notes_val})
            elif scan_type in key_map:
                data["data_files"][key_map[scan_type]] = {"path": rel, "notes": notes_val}

        try:
            with open(json_path, 'w') as f:
                json.dump(data, f, indent=4)
            T = get_theme(self.parent_window.dark_mode)
            self.lbl_save_status.setText("✓  Saved")
            self.lbl_save_status.setStyleSheet(f"color: {T.save_success_fg}; font-size: 10px; font-style: italic;")
        except Exception:
            T = get_theme(self.parent_window.dark_mode)
            self.lbl_save_status.setText("Save failed — write error.")
            self.lbl_save_status.setStyleSheet(f"color: {T.save_error_fg}; font-size: 10px;")

    # ------------------------------------------------------------------ JSON UTILS
    def _read_technique_from_json(self, json_path):
        try:
            with open(json_path, 'r') as f:
                data = json.load(f)
            return data.get("core", {}).get("technique", None)
        except Exception:
            return None