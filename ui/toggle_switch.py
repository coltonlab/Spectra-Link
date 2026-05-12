"""
toggle_switch.py  —  iOS-style sliding pill toggle for PyQt6
=============================================================
Drop-in replacement for QCheckBox in theme-switching scenarios.

Usage
-----
    from toggle_switch import ToggleSwitch

    toggle = ToggleSwitch(label="Dark Mode", checked=True)
    toggle.toggled.connect(my_slot)          # emits bool
    toggle.setChecked(False)
    is_on = toggle.isChecked()
"""

from __future__ import annotations
from PyQt6.QtWidgets import QWidget, QHBoxLayout, QLabel, QSizePolicy
from PyQt6.QtCore    import Qt, QPropertyAnimation, QRect, QEasingCurve, pyqtSignal, QRectF
from PyQt6.QtGui     import QPainter, QColor, QPen, QBrush


# ──────────────────────────────────────────────────────────────────────────────
#  The pill track + thumb widget
# ──────────────────────────────────────────────────────────────────────────────
class _PillTrack(QWidget):
    """
    The actual toggle pill graphic.  Emits _clicked when the user clicks it.
    Animated thumb slides left / right.
    """
    _clicked = pyqtSignal()

    _TRACK_W = 44
    _TRACK_H = 24
    _THUMB_D = 18
    _MARGIN  = 3

    def __init__(self, checked: bool = False,
                 color_on: str = "#4a90b8",
                 color_off: str = "#3a3d42",
                 thumb_color: str = "#dce1e7"):
        super().__init__()
        self._checked     = checked
        self._color_on    = QColor(color_on)
        self._color_off   = QColor(color_off)
        self._thumb_color = QColor(thumb_color)

        self.setFixedSize(self._TRACK_W, self._TRACK_H)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)

        # Thumb x position (animated)
        self._thumb_x = self._thumb_x_for(checked)

        self._anim = QPropertyAnimation(self, b"_thumb_x_prop", self)
        self._anim.setDuration(160)
        self._anim.setEasingCurve(QEasingCurve.Type.InOutCubic)

    # ── Internal property for animation ──────────────────────────────────────
    def _get_thumb_x(self) -> float:
        return self._thumb_x

    def _set_thumb_x(self, x: float):
        self._thumb_x = x
        self.update()

    _thumb_x_prop = property(_get_thumb_x, _set_thumb_x)   # type: ignore[misc]
    # Make it a real Qt property via pyqtProperty workaround:
    from PyQt6.QtCore import pyqtProperty as _p
    _thumb_x_prop = _p(float, _get_thumb_x, _set_thumb_x)  # type: ignore[misc]

    # ── Geometry helpers ─────────────────────────────────────────────────────
    def _thumb_x_for(self, checked: bool) -> float:
        if checked:
            return self._TRACK_W - self._THUMB_D - self._MARGIN
        return float(self._MARGIN)

    # ── Public API ───────────────────────────────────────────────────────────
    def setChecked(self, checked: bool, animate: bool = True):
        self._checked = checked
        target = self._thumb_x_for(checked)
        if animate and not self._anim.state() == QPropertyAnimation.State.Running:
            self._anim.stop()
            self._anim.setStartValue(self._thumb_x)
            self._anim.setEndValue(target)
            self._anim.start()
        else:
            self._thumb_x = target
            self.update()

    def isChecked(self) -> bool:
        return self._checked

    def updateColors(self, color_on: str, color_off: str, thumb_color: str):
        self._color_on    = QColor(color_on)
        self._color_off   = QColor(color_off)
        self._thumb_color = QColor(thumb_color)
        self.update()

    # ── Paint ────────────────────────────────────────────────────────────────
    def paintEvent(self, _event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Track
        track_color = self._color_on if self._checked else self._color_off
        p.setBrush(QBrush(track_color))
        p.setPen(Qt.PenStyle.NoPen)
        radius = self._TRACK_H / 2
        p.drawRoundedRect(QRectF(0, 0, self._TRACK_W, self._TRACK_H), radius, radius)

        # Thumb shadow (subtle)
        shadow = QColor(0, 0, 0, 60)
        p.setBrush(QBrush(shadow))
        cx = self._thumb_x + self._THUMB_D / 2 + 0.5
        cy = self._TRACK_H / 2 + 0.8
        p.drawEllipse(QRectF(cx - self._THUMB_D / 2,
                             cy - self._THUMB_D / 2,
                             self._THUMB_D, self._THUMB_D))

        # Thumb
        p.setBrush(QBrush(self._thumb_color))
        p.drawEllipse(QRectF(self._thumb_x,
                             (self._TRACK_H - self._THUMB_D) / 2,
                             self._THUMB_D, self._THUMB_D))
        p.end()

    # ── Interaction ──────────────────────────────────────────────────────────
    def mousePressEvent(self, _event):
        self._clicked.emit()


# ──────────────────────────────────────────────────────────────────────────────
#  Public composite widget: pill + label
# ──────────────────────────────────────────────────────────────────────────────
class ToggleSwitch(QWidget):
    """
    Pill toggle with an optional text label to its right.
    Emits ``toggled(bool)`` when the state changes.
    """
    toggled = pyqtSignal(bool)

    def __init__(self, label: str = "", checked: bool = False,
                 color_on:    str = "#4a90b8",
                 color_off:   str = "#3a3d42",
                 thumb_color: str = "#dce1e7",
                 parent=None):
        super().__init__(parent)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        self._track = _PillTrack(checked, color_on, color_off, thumb_color)
        self._track._clicked.connect(self._on_click)
        layout.addWidget(self._track)

        self._label_text = label
        if label:
            self._lbl = QLabel(label)
            self._lbl.setCursor(Qt.CursorShape.PointingHandCursor)
            self._lbl.mousePressEvent = lambda _e: self._on_click()
            layout.addWidget(self._lbl)
        else:
            self._lbl = None

        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)

    # ── Public API ───────────────────────────────────────────────────────────
    def isChecked(self) -> bool:
        return self._track.isChecked()

    def setChecked(self, checked: bool):
        self._track.setChecked(checked, animate=True)

    def updateThemeColors(self, color_on: str, color_off: str, thumb_color: str,
                          label_color: str = ""):
        """Call this when the app theme itself changes so the pill stays consistent."""
        self._track.updateColors(color_on, color_off, thumb_color)
        if self._lbl and label_color:
            self._lbl.setStyleSheet(f"color: {label_color};")

    # ── Internal ─────────────────────────────────────────────────────────────
    def _on_click(self):
        new_state = not self._track.isChecked()
        self._track.setChecked(new_state)
        self.toggled.emit(new_state)