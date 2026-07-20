from pathlib import Path
from PyQt6.QtWidgets import QTableWidgetItem, QDoubleSpinBox, QLineEdit, QPlainTextEdit, QComboBox
from PyQt6.QtGui import QBrush, QColor
from PyQt6.QtCore import Qt
from config.techniques import TECHNIQUE_CONFIG
from ui.theme import get_theme
from utils.project_manager import ProjectManager

class DiscoveryDataMapper:
    """
    Handles the bidirectional mapping between the ProjectManager session data (JSON)
    and the DiscoveryTab UI (Table rows and parameter widgets).
    """

    @staticmethod
    def load_session_to_ui(tab):
        """Populates the table and parameter widgets from the active session data."""
        data = ProjectManager.Session.get_data()
        if not data:
            return

        technique = data.get("core", {}).get("technique")
        if not technique or technique not in TECHNIQUE_CONFIG:
            return

        cfg = TECHNIQUE_CONFIG[technique]
        local_param = cfg.get("local_param")
        has_local = local_param is not None
        local_key = local_param["key"] if has_local else None
        key_map = cfg["json_key_map"]
        data_files = data.get("data_files", {})
        parameters = data.get("parameters", {})

        # 1. Populate Global Parameter Widgets
        for key, widget in tab._param_widgets.items():
            val = parameters.get(key)
            if val is None: continue
            if isinstance(widget, QDoubleSpinBox):
                try: widget.setValue(float(val))
                except (ValueError, TypeError): pass
            elif isinstance(widget, QComboBox):
                widget.setCurrentText(str(val))
            elif isinstance(widget, QLineEdit):
                widget.setText(str(val))

        # 2. Flatten JSON data into entry list
        entries = []
        rev_map = {v: k for k, v in key_map.items()}
        for json_key, scan_type in rev_map.items():
            if json_key == "none_files": continue
            val = data_files.get(json_key)
            if val:
                if isinstance(val, dict):
                    entries.append((val.get("path", ""), scan_type, None, val.get("notes", "")))
                else:
                    entries.append((val, scan_type, None, ""))

        if has_local:
            for item in data_files.get(f"{local_key}_scans", []):
                entries.append((
                    item.get("file", ""), item.get("scan_type", ""),
                    item.get(local_key, local_param.get("default", 0)),
                    item.get("notes", "")
                ))

        for item in data_files.get("none_files", []):
            entries.append((item.get("path", ""), "None", None, item.get("notes", "")))

        # 3. Rebuild Table Rows
        tab.table.blockSignals(True)
        tab.table.setRowCount(0)
        active_types = local_param.get("active_scan_types", []) if has_local else []

        for rel_path, scan_type, local_val, notes in entries:
            row = tab.table.rowCount()
            tab.table.insertRow(row)
            full_p = tab.parent_window.base_dir / rel_path

            for c in range(tab.table.columnCount()):
                tab.table.setItem(row, c, QTableWidgetItem(""))

            # Date
            date_item = QTableWidgetItem(Path(rel_path).parent.name)
            date_item.setFlags(date_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            tab.table.setItem(row, 0, date_item)

            # Filename
            f_item = QTableWidgetItem(Path(rel_path).stem)
            f_item.setFlags(f_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            if not full_p.exists():
                T = get_theme(tab.parent_window.dark_mode)
                f_item.setForeground(QBrush(QColor(T.missing_file_fg)))
            tab.table.setItem(row, 1, f_item)

            cb = tab._make_scan_combo(cfg.get("scan_types", ["None"]), row)
            cb.setCurrentText(scan_type)
            tab.table.setCellWidget(row, 2, cb)

            note_col = 3
            if has_local:
                spin = tab._make_local_spin(local_param, value=local_val if local_val is not None else local_param.get("default", 0))
                if scan_type not in active_types:
                    spin.setEnabled(False)
                    spin.setStyleSheet(tab._disabled_spin_style())
                tab.table.setCellWidget(row, 3, spin)
                note_col = 4
            
            tab.table.setCellWidget(row, note_col, tab._make_notes_edit(notes))
            tab.table.setItem(row, tab.table.columnCount()-1, QTableWidgetItem(str(full_p)))
            tab._update_row_color(row, scan_type)

        tab.table.blockSignals(False)
        tab.table.resizeRowsToContents()

    @staticmethod
    def sync_ui_to_session(tab):
        """Extracts data from UI and updates the in-memory session data dictionary."""
        data = ProjectManager.Session.get_data()
        if not data or not tab._current_technique: return

        cfg = TECHNIQUE_CONFIG.get(tab._current_technique, {})
        local_param = cfg.get("local_param")
        has_local = local_param is not None
        local_key = local_param["key"] if has_local else None
        key_map = cfg.get("json_key_map", {})

        # 1. Update Parameters
        params = data.setdefault("parameters", {})
        for k, w in tab._param_widgets.items():
            if isinstance(w, QDoubleSpinBox):
                params[k] = w.value()
            elif isinstance(w, QComboBox):
                params[k] = w.currentText()
            else:
                params[k] = w.text()

        # 2. Rebuild data_files structure
        df = {"none_files": []}
        if has_local: df[f"{local_key}_scans"] = []
        
        active_types = local_param.get("active_scan_types", []) if has_local else []
        path_col = tab.table.columnCount() - 1
        loc_col, note_col = (3, 4) if has_local else (None, 3)

        for r in range(tab.table.rowCount()):
            cb, nt, pi = tab.table.cellWidget(r, 2), tab.table.cellWidget(r, note_col), tab.table.item(r, path_col)
            if not cb or not nt or not pi: continue

            st, notes, full_p = cb.currentText(), nt.toPlainText(), pi.text()
            try: rel = Path(full_p).relative_to(tab.parent_window.base_dir).as_posix()
            except ValueError: rel = full_p

            if has_local and st in active_types:
                sp = tab.table.cellWidget(r, loc_col)
                df[f"{local_key}_scans"].append({
                    "file": rel, "scan_type": st, "notes": notes,
                    local_key: sp.value() if isinstance(sp, QDoubleSpinBox) else 0
                })
            elif st == "None":
                df["none_files"].append({"path": rel, "notes": notes})
            elif st in key_map:
                df[key_map[st]] = {"path": rel, "notes": notes}
        
        data["data_files"] = df
