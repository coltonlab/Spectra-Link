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
from PyQt6.QtGui import QColor, QBrush
import platform
import re

from config.techniques import TECHNIQUE_CONFIG



# ──────────────────────────────────────────────────────────────────────────────
#  New Experiment dialog
# ──────────────────────────────────────────────────────────────────────────────
class NewExperimentDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent_window = parent
        self.setWindowTitle("New Experiment")
        self.setMinimumWidth(360)

        self.apply_theme(getattr(self.parent_window, 'dark_mode', True))

        layout = QVBoxLayout(self)
        layout.setSpacing(14)
        layout.setContentsMargins(20, 20, 20, 16)

        form = QFormLayout()
        form.setSpacing(10)
        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("e.g. EA_run1_300K")
        form.addRow("Experiment Name:", self.name_edit)

        self.combo_technique = QComboBox()
        self.combo_technique.addItems(list(TECHNIQUE_CONFIG.keys()))
        form.addRow("Technique:", self.combo_technique)

        layout.addLayout(form)
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok |
            QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        self.name_edit.setFocus()

        self.apply_theme(getattr(self.parent_window, 'dark_mode', True))

    def apply_theme(self, is_dark: bool):
        """Updates the dialog stylesheet based on the theme."""
        bg_col      = "#1a1a1a" if is_dark else "#ffffff"
        input_bg    = "#2a2a2a" if is_dark else "#eeeeee"
        text_col    = "#e0e0e0" if is_dark else "#222222"
        label_col   = "#888888" if is_dark else "#666666"
        border_col  = "#333333" if is_dark else "#cccccc"
        
        btn_primary_bg    = "#1a4a6a" if is_dark else "#005a9e"
        btn_primary_hover = "#245a80" if is_dark else "#0078d4"
        
        btn_cancel_bg     = "#3a3a3a" if is_dark else "#e0e0e0"
        btn_cancel_hover  = "#4a4a4a" if is_dark else "#d0d0d0"
        btn_cancel_text   = "#eeeeee" if is_dark else "#222222"

        self.setStyleSheet(f"""
            QDialog {{ background-color: {bg_col}; color: {text_col}; }}
            QLabel  {{ color: {label_col}; font-size: 12px; }}
            QLineEdit {{
                background-color: {input_bg}; color: {text_col};
                border: 1px solid {border_col}; border-radius: 3px;
                padding: 5px 8px; font-size: 12px;
            }}
            QLineEdit:focus {{ border-color: #5a8fbf; }}
            QComboBox {{
                background-color: {input_bg}; color: {text_col};
                border: 1px solid {border_col}; border-radius: 3px;
                padding: 4px 8px; font-size: 12px;
            }}
            QComboBox QAbstractItemView {{
                background-color: {input_bg};
                color: {text_col};
                selection-background-color: {btn_primary_bg};
            }}
            QComboBox::drop-down {{ border: none; width: 20px; }}
            QDialogButtonBox QPushButton {{
                background-color: {btn_primary_bg}; color: white;
                border: none; padding: 6px 18px;
                border-radius: 3px; font-size: 12px;
            }}
            QDialogButtonBox QPushButton:hover {{ background-color: {btn_primary_hover}; }}
            QDialogButtonBox QPushButton[text="Cancel"] {{ 
                background-color: {btn_cancel_bg}; 
                color: {btn_cancel_text};
            }}
            QDialogButtonBox QPushButton[text="Cancel"]:hover {{ 
                background-color: {btn_cancel_hover}; 
            }}
        """)

    def get_values(self):
        return self.name_edit.text(), self.combo_technique.currentText()
