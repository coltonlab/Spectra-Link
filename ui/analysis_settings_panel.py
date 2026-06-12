from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QLabel, QFrame, QCheckBox, QComboBox, QScrollArea,
    QSizePolicy, QGraphicsDropShadowEffect, QLineEdit, QDoubleSpinBox, QSlider
)
from PyQt6.QtCore import Qt, pyqtSignal, QPropertyAnimation, QEasingCurve, QRect, QSize, QTimer
from PyQt6.QtGui import QColor, QFont, QPalette, QIcon
from config.techniques import TECHNIQUE_CONFIG, ANALYSIS_OPTION_META
from ui.theme import get_theme


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


class _ComboRow(QWidget):
    """A labeled combo row with tight alignment."""

    def __init__(self, label_text: str, C: dict, parent=None):
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)

        lbl = QLabel(label_text)
        lbl.setStyleSheet(f"color: {C['text_label']}; font-size: 11px;")
        lbl.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)

        self.combo = QComboBox()
        self.combo.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)

        layout.addWidget(lbl)
        layout.addWidget(self.combo)

class _TextRow(QWidget):
    """A labeled text input row with tight alignment."""

    def __init__(self, label_text: str, C: dict, parent=None):
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)

        lbl = QLabel(label_text)
        lbl.setStyleSheet(f"color: {C['text_label']}; font-size: 11px;")
        lbl.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)

        self.edit = QLineEdit()
        self.edit.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

        layout.addWidget(lbl)
        layout.addWidget(self.edit)

class _SpinRow(QWidget):
    """A labeled numeric input row."""

    def __init__(self, label_text: str, C: dict, min_v=0.1, max_v=20.0, step=0.1, decimals=1, parent=None):
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)

        lbl = QLabel(label_text)
        lbl.setStyleSheet(f"color: {C['text_label']}; font-size: 11px;")
        lbl.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)

        self.spin = QDoubleSpinBox()
        self.spin.setRange(min_v, max_v)
        self.spin.setSingleStep(step)
        self.spin.setDecimals(decimals)
        self.spin.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)

        layout.addWidget(lbl)
        layout.addWidget(self.spin)

class _SliderSpinRow(QWidget):
    """A labeled slider + numeric input row."""
    valueChanged = pyqtSignal(float)

    def __init__(self, label_text: str, C: dict, min_v=0.0, max_v=10.0, step=0.01, decimals=2, parent=None):
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)

        lbl = QLabel(label_text)
        lbl.setStyleSheet(f"color: {C['text_label']}; font-size: 11px;")
        lbl.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        lbl.setFixedWidth(100)

        self.slider = QSlider(Qt.Orientation.Horizontal)
        self.res = 100 # Resolution for float->int conversion
        self.slider.setRange(int(min_v * self.res), int(max_v * self.res))

        self.spin = QDoubleSpinBox()
        self.spin.setRange(min_v, max_v)
        self.spin.setSingleStep(step)
        self.spin.setDecimals(decimals)
        self.spin.setFixedWidth(70)

        # Syncing
        self.spin.valueChanged.connect(self._sync_slider)
        self.slider.valueChanged.connect(self._sync_spin)

        layout.addWidget(lbl)
        layout.addWidget(self.slider)
        layout.addWidget(self.spin)

    def _sync_slider(self, val):
        self.slider.blockSignals(True)
        self.slider.setValue(int(val * self.res))
        self.slider.blockSignals(False)
        self.valueChanged.emit(val)

    def _sync_spin(self, val):
        float_val = val / self.res
        self.spin.blockSignals(True)
        self.spin.setValue(float_val)
        self.spin.blockSignals(False)
        self.valueChanged.emit(float_val)

    def setValue(self, val):
        self.spin.setValue(val)

class _VerticalLinesWidget(QWidget):
    """Dynamic list of X-value spinboxes and Label edits."""
    changed = pyqtSignal(list)

    def __init__(self, initial_data, C, parent=None):
        super().__init__(parent)
        self.C = C
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(6)
        
        self.rows_layout = QVBoxLayout()
        self.rows_layout.setSpacing(4)
        self.layout.addLayout(self.rows_layout)
        
        self.add_btn = QPushButton("+ Add Reference Line")
        self.add_btn.setStyleSheet(f"""
            QPushButton {{
                background: {C['bg_hover']};
                color: {C['accent']};
                border: 1px dashed {C['border']};
                border-radius: 4px;
                padding: 6px;
                font-size: 10px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background: {C['bg_header']};
                border-color: {C['accent']};
            }}
        """)
        self.add_btn.clicked.connect(lambda: self.add_row())
        self.layout.addWidget(self.add_btn)
        
        for item in (initial_data or []):
            self.add_row(item.get("x", 2.0), item.get("label", ""), item.get("show_legend", True))

    def add_row(self, x=2.0, label="", show_legend=True):
        row = QWidget()
        l = QHBoxLayout(row)
        l.setContentsMargins(0, 0, 0, 0)
        l.setSpacing(4)
        
        spin = QDoubleSpinBox()
        spin.setRange(0, 10)
        spin.setValue(x)
        spin.setDecimals(3)
        spin.setStyleSheet(self._style())
        spin.valueChanged.connect(self._emit_changed)
        
        edit = QLineEdit(label)
        edit.setPlaceholderText("Label")
        edit.setStyleSheet(self._style())
        edit.textChanged.connect(self._emit_changed)
        
        chk = QCheckBox()
        chk.setToolTip("Show in legend")
        chk.setChecked(show_legend)
        chk.toggled.connect(self._emit_changed)

        del_btn = QPushButton("✕")
        del_btn.setFixedSize(20, 20)
        del_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        del_btn.setStyleSheet(f"color: {self.C['text_secondary']}; border: none; background: transparent;")
        del_btn.clicked.connect(lambda: self.remove_row(row))
        
        l.addWidget(edit, 3)
        l.addWidget(spin, 2)
        l.addWidget(chk, 0)
        l.addWidget(del_btn, 0)
        
        self.rows_layout.addWidget(row)
        self._emit_changed()

    def remove_row(self, row):
        row.deleteLater()
        self.rows_layout.removeWidget(row)
        QTimer.singleShot(10, self._emit_changed)

    def _emit_changed(self):
        data = []
        for i in range(self.rows_layout.count()):
            w = self.rows_layout.itemAt(i).widget()
            if w:
                spin = w.findChild(QDoubleSpinBox)
                edit = w.findChild(QLineEdit)
                chk = w.findChild(QCheckBox)
                if spin and edit and chk:
                    data.append({"x": spin.value(), "label": edit.text(), "show_legend": chk.isChecked()})
        self.changed.emit(data)

    def _style(self):
        return f"""
            background: {self.C['bg_combo']};
            color: {self.C['text_primary']};
            border: 1px solid {self.C['border']};
            border-radius: 4px;
            padding: 2px 4px;
            font-size: 10px;
        """


class AnalysisSettingsPanel(QWidget):
    """Floating, non-modal window for experiment-specific analysis options."""

    settingChanged = pyqtSignal(str, object)  # key, value

    def __init__(self, parent_window):
        super().__init__(parent_window)  # Link to parent window lifecycle
        self.parent_window = parent_window
        self.setWindowTitle("Analysis Control Center")
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

        title_lbl = QLabel("Analysis Control Center")
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
    def rebuild(self, technique: str, saved_settings: dict):
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

        cfg = TECHNIQUE_CONFIG.get(technique, {})
        option_keys = cfg.get("analysis_options", [])

        if not option_keys:
            placeholder = QLabel("No options available for this technique.")
            placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
            placeholder.setStyleSheet(f"color: {C['text_secondary']}; padding: 24px; background: transparent;")
            self.container_layout.insertWidget(0, placeholder)
            return

        # Group by category
        categories: dict[str, list] = {}
        for key in option_keys:
            meta = ANALYSIS_OPTION_META.get(key, {})
            cat = meta.get("category", "General")
            categories.setdefault(cat, []).append(key)

        # Build sections
        for i, (cat_name, keys) in enumerate(categories.items()):
            section = CollapsibleSection(cat_name, is_dark)

            for key in keys:
                meta = ANALYSIS_OPTION_META.get(key, {})
                label_text = meta.get("label", key)
                w_type = meta.get("type", "checkbox")

                if w_type == "combo":
                    row = _ComboRow(label_text, C)
                    row.combo.addItems(meta.get("options", []))
                    row.combo.setCurrentText(str(saved_settings.get(key, "")))
                    row.combo.currentTextChanged.connect(
                        lambda val, k=key: self.settingChanged.emit(k, val)
                    )
                    section.content_layout.addWidget(row)
                elif w_type == "list_of_dicts":
                    v_widget = _VerticalLinesWidget(saved_settings.get(key, []), C)
                    v_widget.changed.connect(lambda val, k=key: self.settingChanged.emit(k, val))
                    section.content_layout.addWidget(v_widget)
                elif w_type == "numeric":
                    row = _SpinRow(label_text, C, 
                                   min_v=meta.get("min", 0.1), 
                                   max_v=meta.get("max", 10000.0),
                                   step=meta.get("step", 0.1),
                                   decimals=meta.get("decimals", 1))
                    
                    val = float(saved_settings.get(key, meta.get("default", 1.5)))
                    row.spin.setValue(val)

                    def on_num_val_changed(v, k=key):
                        # While typing, if it's even, don't emit yet. 
                        # This prevents the plot from crashing on even windows 
                        # and allows the user to finish typing (e.g., typing '6' then '5').
                        if k == "smooth_window" and int(v) % 2 == 0:
                            return
                        self.settingChanged.emit(k, v)

                    def on_num_editing_finished(k=key, spin_row=row):
                        v = spin_row.spin.value()
                        # Final check when user hits Enter or leaves the box: 
                        # if they stopped on an even number, force it to the next odd value.
                        if k == "smooth_window" and int(v) % 2 == 0:
                            v = float(int(v) + 1)
                            spin_row.spin.blockSignals(True)
                            spin_row.spin.setValue(v)
                            spin_row.spin.blockSignals(False)
                        self.settingChanged.emit(k, v)

                    row.spin.valueChanged.connect(on_num_val_changed)
                    row.spin.editingFinished.connect(on_num_editing_finished)
                    section.content_layout.addWidget(row)
                elif w_type == "slider_numeric":
                    row = _SliderSpinRow(label_text, C, 
                                       min_v=meta.get("min", 0.0), 
                                       max_v=meta.get("max", 10.0),
                                       step=meta.get("step", 0.01),
                                       decimals=meta.get("decimals", 2))
                    row.setValue(float(saved_settings.get(key, meta.get("default", 1.0))))
                    row.valueChanged.connect(
                        lambda val, k=key: self.settingChanged.emit(k, val)
                    )
                    section.content_layout.addWidget(row)
                elif w_type == "text":
                    row = _TextRow(label_text, C)
                    row.edit.setText(str(saved_settings.get(key, "")))
                    row.edit.editingFinished.connect(
                        lambda r=row, k=key: self.settingChanged.emit(k, r.edit.text())
                    )
                    section.content_layout.addWidget(row)
                else:
                    chk = QCheckBox(label_text)
                    chk.setChecked(saved_settings.get(key, False))
                    chk.toggled.connect(
                        lambda state, k=key: self.settingChanged.emit(k, state)
                    )
                    chk.setToolTip(meta.get("tooltip", ""))
                    section.content_layout.addWidget(chk)
                    
                    # Inject a "Reverse Color Order" checkbox right under the colorbar toggle
                    if key == "show_colorbar":
                        rev_chk = QCheckBox("Reverse Color Order")
                        rev_chk.setChecked(saved_settings.get("reverse_colormap", False))
                        rev_chk.toggled.connect(
                            lambda state: self.settingChanged.emit("reverse_colormap", state)
                        )
                        section.content_layout.addWidget(rev_chk)

            # Insert before the trailing stretch
            self.container_layout.insertWidget(
                self.container_layout.count() - 1, section
            )

    # ── Window lifecycle ──────────────────────────────────────────────────────
    def closeEvent(self, event):
        self.hide()
        event.accept()