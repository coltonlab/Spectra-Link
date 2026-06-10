from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QLabel, QFrame, QScrollArea, QSizePolicy, QCheckBox
)
from PyQt6.QtCore import Qt, pyqtSignal, QPropertyAnimation, QEasingCurve, QRect, QSize, QTimer
from PyQt6.QtGui import QColor, QFont, QPalette, QIcon
from ui.theme import get_theme

# Re-using palette and stylesheet functions from analysis_settings_panel.py
# In a real project, these might be refactored into a shared ui/styles.py
# For now, copying them to keep this file self-contained and functional.

# ── Palette constants ────────────────────────────────────────────────────────
_DARK = {
    "bg_panel":      "#141418",
    "bg_section":    "#1c1c22",
    "bg_header":     "#22222a",
    "bg_hover":      "#2a2a34",
    "bg_content":    "#18181f",
    "bg_combo":      "#222230",
    "bg_combo_drop": "#1c1c28",
    "accent":        "#5c9aff",
    "accent_dim":    "#3a6acc",
    "border":        "#2e2e3a",
    "border_accent": "#3a4a7a",
    "text_primary":  "#e8e8f0",
    "text_secondary":"#8888aa",
    "text_label":    "#c4c4d8",
    "check_bg":      "#1e1e2c",
    "check_active":  "#5c9aff",
    "scrollbar":     "#2e2e3a",
    "scrollbar_h":   "#5c9aff",
}

_LIGHT = {
    "bg_panel":      "#f4f4f8",
    "bg_section":    "#ffffff",
    "bg_header":     "#ebebf0",
    "bg_hover":      "#dddde8",
    "bg_content":    "#f9f9fc",
    "bg_combo":      "#ffffff",
    "bg_combo_drop": "#f4f4f8",
    "accent":        "#3a6acc",
    "accent_dim":    "#5c9aff",
    "border":        "#d4d4e0",
    "border_accent": "#aabcee",
    "text_primary":  "#1a1a2e",
    "text_secondary":"#5b6275",
    "text_label":    "#303050",
    "check_bg":      "#e8e8f4",
    "check_active":  "#3a6acc",
    "scrollbar":     "#d0d0dc",
    "scrollbar_h":   "#3a6acc",
}


def _palette(is_dark: bool) -> dict:
    return _DARK if is_dark else _LIGHT


def _global_stylesheet(C: dict) -> str:
    """Application-wide stylesheet applied to the panel."""
    return f"""
        /* ── Panel base ── */
        QWidget {{
            background-color: {C['bg_panel']};
            color: {C['text_primary']};
            font-family: "Segoe UI Variable", "Segoe UI", "Inter", "Helvetica Neue", sans-serif;
            font-size: 12px;
        }}

        /* ── Scroll area ── */
        QScrollArea {{
            background-color: transparent;
            border: none;
        }}
        QScrollBar:vertical {{
            background: transparent;
            width: 6px;
            margin: 4px 2px;
            border-radius: 3px;
        }}
        QScrollBar::handle:vertical {{
            background: {C['scrollbar']};
            border-radius: 3px;
            min-height: 24px;
        }}
        QScrollBar::handle:vertical:hover {{
            background: {C['scrollbar_h']};
        }}
        QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
            height: 0px;
        }}
        QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{
            background: transparent;
        }}

        /* ── Checkboxes ── */
        QCheckBox {{
            color: {C['text_label']};
            spacing: 8px;
            padding: 3px 2px;
        }}
        QCheckBox::indicator {{
            width: 16px;
            height: 16px;
            border-radius: 4px;
            border: 1.5px solid {C['border']};
            background: {C['check_bg']};
        }}
        QCheckBox::indicator:hover {{
            border-color: {C['accent']};
        }}
        QCheckBox::indicator:checked {{
            background: {C['check_active']};
            border-color: {C['check_active']};
            image: url(none);
        }}
        QCheckBox:hover {{
            color: {C['text_primary']};
        }}

        /* ── ComboBox ── */
        QComboBox {{
            background: {C['bg_combo']};
            color: {C['text_primary']};
            border: 1.5px solid {C['border']};
            border-radius: 6px;
            padding: 4px 8px;
            font-size: 11px;
            min-width: 90px;
        }}
        QComboBox:hover {{
            border-color: {C['accent']};
        }}
        QComboBox::drop-down {{
            border: none;
            width: 20px;
        }}
        QComboBox::down-arrow {{
            width: 8px;
            height: 8px;
        }}
        QComboBox QAbstractItemView {{
            background: {C['bg_combo_drop']};
            color: {C['text_primary']};
            border: 1px solid {C['border_accent']};
            border-radius: 6px;
            padding: 4px;
            selection-background-color: {C['accent_dim']};
        }}

        /* ── Labels inside combo rows ── */
        QLabel {{
            color: {C['text_label']};
            background: transparent;
        }}

        /* ── SpinBox ── */
        QDoubleSpinBox {{
            background: {C['bg_combo']};
            color: {C['text_primary']};
            border: 1.5px solid {C['border']};
            border-radius: 6px;
            padding: 2px 6px;
            font-size: 11px;
            min-width: 80px;
        }}

        /* ── Slider ── */
        QSlider::groove:horizontal {{
            border: 1px solid {C['border']};
            height: 4px;
            background: {C['bg_combo']};
            margin: 2px 0;
            border-radius: 2px;
        }}
        QSlider::handle:horizontal {{
            background: {C['accent']};
            border: 1px solid {C['accent']};
            width: 14px;
            height: 14px;
            margin: -5px 0;
            border-radius: 7px;
        }}
    """


class _AccentDivider(QFrame):
    """1px horizontal rule with a leading accent pip."""
    def __init__(self, C: dict):
        super().__init__()
        self.setFixedHeight(1)
        self.setStyleSheet(f"background: {C['border']};")


class CollapsibleSection(QWidget):
    """Accordion-style section with animated toggle and polished header."""

    def __init__(self, title: str, is_dark: bool = True):
        super().__init__()
        self.title = title
        self.is_dark = is_dark
        self.C = _palette(is_dark)
        self._expanded = True

        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(0, 0, 0, 0)
        self._layout.setSpacing(0)

        # ── Header ──────────────────────────────────────────────────────────
        self.header = QPushButton()
        self.header.setCheckable(True)
        self.header.setChecked(True)
        self.header.setCursor(Qt.CursorShape.PointingHandCursor)
        self.header.setFixedHeight(36)
        self.header.clicked.connect(self.toggle)
        self._update_header_text()

        # ── Content frame ────────────────────────────────────────────────────
        self.content = QFrame()
        self.content.setObjectName("sectionContent")
        self.content_layout = QVBoxLayout(self.content)
        self.content_layout.setContentsMargins(16, 10, 16, 14)
        self.content_layout.setSpacing(8)

        # ── Bottom separator ─────────────────────────────────────────────────
        self._sep = _AccentDivider(self.C)

        self._layout.addWidget(self.header)
        self._layout.addWidget(self.content)
        self._layout.addWidget(self._sep)

        self._apply_style()

    def _update_header_text(self):
        arrow = "▾" if self._expanded else "▸"
        self.header.setText(f"  {arrow}   {self.title.upper()}")

    def _apply_style(self):
        C = self.C
        self.header.setStyleSheet(f"""
            QPushButton {{
                background-color: {C['bg_header']};
                color: {C['text_secondary']};
                border: none;
                text-align: left;
                padding: 0 14px;
                font-size: 10px;
                font-weight: 600;
                letter-spacing: 1.2px;
                border-left: 3px solid {C['accent']};
            }}
            QPushButton:hover {{
                background-color: {C['bg_hover']};
                color: {C['text_primary']};
                border-left: 3px solid {C['accent_dim']};
            }}
            QPushButton:checked {{
                color: {C['accent']};
            }}
        """)
        self.content.setStyleSheet(f"""
            QFrame#sectionContent {{
                background-color: {C['bg_content']};
                border: none;
            }}
        """)

    def toggle(self):
        self._expanded = self.header.isChecked()
        self.content.setVisible(self._expanded)
        self._update_header_text()


class ModelingSettingsPanel(QWidget):
    """Floating, non-modal window for experiment-specific modeling options."""

    settingChanged = pyqtSignal(str, object)  # key, value

    def __init__(self, parent_window):
        super().__init__(parent_window)  # Link to parent window lifecycle
        self.parent_window = parent_window
        self.setWindowTitle("Modeling Control Center")
        self.setWindowFlags(
            Qt.WindowType.Window |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.FramelessWindowHint   # custom chrome feel
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, False)
        self.setMinimumWidth(300)
        self.resize(320, 540)

        self._drag_pos = None
        self._init_ui()

    # ── Drag support for frameless window ────────────────────────────────────
    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()

    def mouseMoveEvent(self, event):
        if self._drag_pos and event.buttons() == Qt.MouseButton.LeftButton:
            self.move(event.globalPosition().toPoint() - self._drag_pos)

    def mouseReleaseEvent(self, event):
        self._drag_pos = None

    # ── UI Construction ───────────────────────────────────────────────────────
    def _init_ui(self):
        is_dark = getattr(self.parent_window, "dark_mode", True)
        C = _palette(is_dark)
        self.setStyleSheet(_global_stylesheet(C))

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        # ── Title bar ────────────────────────────────────────────────────────
        title_bar = self._build_title_bar(C)
        outer.addWidget(title_bar)

        # ── Scroll area ──────────────────────────────────────────────────────
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        self.container = QWidget()
        self.container.setStyleSheet(f"background: {C['bg_panel']};")
        self.container_layout = QVBoxLayout(self.container)
        self.container_layout.setContentsMargins(0, 4, 0, 12)
        self.container_layout.setSpacing(0)
        self.container_layout.addStretch()

        scroll.setWidget(self.container)
        outer.addWidget(scroll)

        self.main_layout = outer

    def _build_title_bar(self, C: dict) -> QWidget:
        bar = QWidget()
        bar.setFixedHeight(44)
        bar.setStyleSheet(f"""
            QWidget {{
                background: {C['bg_section']};
                border-bottom: 1px solid {C['border']};
            }}
        """)

        h = QHBoxLayout(bar)
        h.setContentsMargins(14, 0, 10, 0)
        h.setSpacing(8)

        # Accent pip
        pip = QFrame()
        pip.setFixedSize(4, 20)
        pip.setStyleSheet(f"background: {C['accent']}; border-radius: 2px;")

        title_lbl = QLabel("Modeling Control Center")
        title_lbl.setStyleSheet(f"""
            color: {C['text_primary']};
            font-size: 12px;
            font-weight: 600;
            background: transparent;
            border: none;
        """)

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

        h.addWidget(pip)
        h.addWidget(title_lbl)
        h.addStretch()
        h.addWidget(close_btn)

        return bar

    # ── Dynamic rebuild ───────────────────────────────────────────────────────
    def rebuild(self, technique: str, saved_settings: dict, engine=None):
        """Dynamically build collapsible sections based on technique metadata."""
        is_dark = getattr(self.parent_window, "dark_mode", True)
        C = _palette(is_dark)

        # Re-apply stylesheet in case dark mode changed
        self.setStyleSheet(_global_stylesheet(C))
        self.container.setStyleSheet(f"background: {C['bg_panel']};")

        # Clear existing widgets (keep the trailing stretch)
        while self.container_layout.count() > 1:
            item = self.container_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        if engine:
            # Delegate the UI construction to the specialized engine
            engine.build_ui(self.container_layout)
        else:
            # Placeholder for actual modeling options
            placeholder = QLabel(f"No specialized modeling engine found for '{technique}'.")
            placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
            placeholder.setWordWrap(True)
            placeholder.setStyleSheet(f"color: {C['text_secondary']}; padding: 24px; background: transparent;")
            self.container_layout.insertWidget(0, placeholder)
            
            # Show a generic empty section
            section = CollapsibleSection("Generic Modeling Settings", is_dark)
            section.content_layout.addWidget(QLabel("Please select an experiment with a supported technique."))
            self.container_layout.insertWidget(self.container_layout.count() - 1, section)

    def apply_theme(self, is_dark: bool):
        """Updates the panel's theme."""
        C = _palette(is_dark)
        self.setStyleSheet(_global_stylesheet(C))
        self.container.setStyleSheet(f"background: {C['bg_panel']};")
        # Rebuild content to apply theme to internal widgets
        # We attempt to find the active engine to keep the UI state consistent
        engine = None
        if hasattr(self.parent_window, "modeling_tab"):
            engine = getattr(self.parent_window.modeling_tab, "active_engine", None)

        self.rebuild("None", {}, engine) 

    # ── Window lifecycle ──────────────────────────────────────────────────────
    def closeEvent(self, event):
        self.hide()
        event.accept()