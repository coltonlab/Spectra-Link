from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QLabel, QFrame, QCheckBox, QComboBox, QScrollArea,
    QSizePolicy, QDoubleSpinBox
)
from PyQt6.QtCore import Qt, pyqtSignal
from ui.analysis_settings_panel import CollapsibleSection, _palette, _global_stylesheet

class ComparisonSettingsPanel(QWidget):
    """
    Floating panel for global grid overrides: Units, Layout, Legends, and Styling.
    """
    settingChanged = pyqtSignal()

    def __init__(self, parent_window):
        super().__init__(parent_window)
        self.parent_window = parent_window
        self.setWindowTitle("Comparison Settings")
        self.setWindowFlags(
            Qt.WindowType.Window |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.FramelessWindowHint
        )
        self.setMinimumWidth(300)
        self.resize(320, 500)

        # Default Settings State
        self.settings = {
            "sync_y": False,
            "hspace": 0.1,                    # Options 2
            "wspace": 0.1,
            "label_outer": True,
            "legend_mode": "Individual",       # Options 3
            "line_width": 1.5,                 # Options 4
            "color_palette": "tab10"
        }

        self._drag_pos = None
        self._init_ui()

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()

    def mouseMoveEvent(self, event):
        if self._drag_pos and event.buttons() == Qt.MouseButton.LeftButton:
            self.move(event.globalPosition().toPoint() - self._drag_pos)

    def _init_ui(self):
        is_dark = getattr(self.parent_window, "dark_mode", True)
        C = _palette(is_dark)
        self.setStyleSheet(_global_stylesheet(C))

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Header
        header = QWidget()
        header.setFixedHeight(44)
        header.setStyleSheet(f"background: {C['bg_section']}; border-bottom: 1px solid {C['border']};")
        h_lay = QHBoxLayout(header)
        title = QLabel("Comparison Visual Settings")
        title.setStyleSheet(f"font-weight: 600; color: {C['text_primary']};")
        close_btn = QPushButton("✕")
        close_btn.setFixedSize(30, 30)
        close_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        close_btn.setStyleSheet(f"""
            QPushButton {{
                background: transparent;
                color: {C['text_primary']};
                border: none;
                border-radius: 15px;
                font-size: 18px;
                font-weight: bold;
                padding: 0;
            }}
            QPushButton:hover {{
                background: {C['bg_hover']};
                color: {C['accent']};
            }}
        """)
        close_btn.clicked.connect(self.hide)
        h_lay.addWidget(title)
        h_lay.addStretch()
        h_lay.addWidget(close_btn)
        layout.addWidget(header)

        # Scrollable Content
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        self.container = QWidget()
        self.cont_layout = QVBoxLayout(self.container)
        
        # 1. Axis & Units
        s1 = CollapsibleSection("Global Axis Control", is_dark)
        self.chk_sync_y = QCheckBox("Sync Y-Axis Scale")
        self.chk_sync_y.toggled.connect(lambda v: self._upd("sync_y", v))
        s1.content_layout.addWidget(self.chk_sync_y)
        self.cont_layout.addWidget(s1)

        # 2. Layout
        s2 = CollapsibleSection("Layout & Geometry", is_dark)
        self.spin_h = QDoubleSpinBox()
        self.spin_h.setRange(0, 1.0); self.spin_h.setSingleStep(0.05); self.spin_h.setValue(0.1)
        self.spin_h.valueChanged.connect(lambda v: self._upd("hspace", v))
        s2.content_layout.addWidget(QLabel("Vertical Padding:"))
        s2.content_layout.addWidget(self.spin_h)

        self.chk_outer = QCheckBox("Clean Outer Labels Only")
        self.chk_outer.setChecked(True)
        self.chk_outer.toggled.connect(lambda v: self._upd("label_outer", v))
        s2.content_layout.addWidget(self.chk_outer)
        self.cont_layout.addWidget(s2)

        # 3. Legends
        s3 = CollapsibleSection("Legend Management", is_dark)
        self.leg_combo = QComboBox()
        self.leg_combo.addItems(["Individual", "Global Figure Legend", "All Off"])
        self.leg_combo.currentTextChanged.connect(lambda v: self._upd("legend_mode", v))
        s3.content_layout.addWidget(QLabel("Mode:"))
        s3.content_layout.addWidget(self.leg_combo)
        self.cont_layout.addWidget(s3)

        # 4. Visual Overrides
        s4 = CollapsibleSection("Visual Styling", is_dark)
        self.spin_lw = QDoubleSpinBox()
        self.spin_lw.setRange(0.5, 5.0); self.spin_lw.setValue(1.5)
        self.spin_lw.valueChanged.connect(lambda v: self._upd("line_width", v))
        s4.content_layout.addWidget(QLabel("Global Line Weight:"))
        s4.content_layout.addWidget(self.spin_lw)
        self.cont_layout.addWidget(s4)

        self.cont_layout.addStretch()
        scroll.setWidget(self.container)
        layout.addWidget(scroll)

    def _upd(self, key, val):
        self.settings[key] = val
        self.settingChanged.emit()

    def get_settings(self):
        return self.settings

    def set_settings(self, new_settings: dict):
        """
        Applies new settings to the panel widgets and updates the internal settings dictionary.
        This is used when loading a comparison configuration.
        """
        self.settings.update(new_settings)
        
        # Update UI widgets without emitting signals immediately
        self.chk_sync_y.setChecked(self.settings.get("sync_y", False))
        self.spin_h.setValue(self.settings.get("hspace", 0.1))
        self.chk_outer.setChecked(self.settings.get("label_outer", True))
        self.leg_combo.setCurrentText(self.settings.get("legend_mode", "Individual"))
        self.spin_lw.setValue(self.settings.get("line_width", 1.5))
        
        # Emit signal once after all settings are applied
        self.settingChanged.emit()