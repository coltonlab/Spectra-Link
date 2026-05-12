"""
theme.py  —  SpectraLink centralized theme system
==================================================
Single source of truth for every color used in the application.

Dark mode  : deep charcoal backgrounds, steel-blue accents
Light mode : cool light-gray backgrounds, same steel-blue accents

Usage
-----
    from theme import get_theme, apply_palette_to_app

    T = get_theme(is_dark=True)   # returns a ThemeColors instance
    T.bg_main                     # "#1e2022"
    T.accent                      # "#4a90b8"
"""

from __future__ import annotations
from dataclasses import dataclass
from PyQt6.QtGui import QPalette, QColor
from PyQt6.QtCore import Qt


# ──────────────────────────────────────────────────────────────────────────────
#  Color token dataclass
# ──────────────────────────────────────────────────────────────────────────────
@dataclass(frozen=True)
class ThemeColors:
    # ── Backgrounds ──────────────────────────────────────────────────────────
    bg_main:        str   # main window / widget background
    bg_secondary:   str   # sidebar, panels, frames
    bg_input:       str   # text inputs, combo boxes, spin boxes
    bg_table:       str   # table background
    bg_table_alt:   str   # alternating table row
    bg_header:      str   # table / section headers
    bg_btn:         str   # generic button background
    bg_btn_hover:   str   # generic button hover
    bg_tooltip:     str   # tooltip background

    # ── Foregrounds ──────────────────────────────────────────────────────────
    text_primary:   str   # main body text
    text_secondary: str   # labels, captions, dim text
    text_disabled:  str   # disabled widget text
    text_btn:       str   # button label text

    # ── Borders & separators ─────────────────────────────────────────────────
    border:         str   # standard widget border
    border_focus:   str   # focused input border (accent)
    separator:      str   # HR / frame line color

    # ── Accent / interactive ─────────────────────────────────────────────────
    accent:         str   # steel-blue highlight
    accent_hover:   str   # accent on hover
    accent_text:    str   # text on top of accent bg (always white)

    # ── Semantic ─────────────────────────────────────────────────────────────
    success:        str   # saved / OK
    warning:        str   # unsaved / pending
    error:          str   # failed / missing file

    # ── Action buttons ───────────────────────────────────────────────────────
    btn_add:        str   # "Add Files" button
    btn_add_hover:  str
    btn_remove:     str   # "Remove Selected" button
    btn_remove_hover: str
    btn_clear:      str   # "Clear All" button
    btn_clear_hover: str

    # ── Badge fallback ───────────────────────────────────────────────────────
    badge_none_bg:  str   # "No experiment selected" badge bg
    badge_none_fg:  str   # "No experiment selected" badge text

    # ── Toggle switch ────────────────────────────────────────────────────────
    toggle_track_on:  str
    toggle_track_off: str
    toggle_thumb:     str

    # ── Discovery tab specific ───────────────────────────────────────────────
    table_selected_bg_dark: str   # table selected row bg (dark mode)
    table_selected_bg_light: str  # table selected row bg (light mode)
    table_header_bg: str          # table header background
    table_header_fg: str          # table header text
    spin_bg: str                  # spinbox background
    spin_fg: str                  # spinbox text
    spin_border: str              # spinbox border
    spin_disabled_bg: str         # disabled spinbox background
    spin_disabled_fg: str         # disabled spinbox text
    combo_bg: str                 # combo box background
    combo_fg: str                 # combo box text
    combo_border: str             # combo box border
    target_no_exp_fg: str         # target label when no experiment
    target_exp_fg: str            # target label when experiment selected
    save_pending_fg: str          # save status pending color
    save_success_fg: str          # save status success color
    save_error_fg: str            # save status error color
    row_text_fg_dark: str         # table row text color (dark mode)
    row_text_fg_light: str        # table row text color (light mode)
    path_text_fg: str             # full path text color in table
    missing_file_fg: str          # color for missing file names


# ──────────────────────────────────────────────────────────────────────────────
#  Palette definitions
# ──────────────────────────────────────────────────────────────────────────────
_DARK = ThemeColors(
    # Backgrounds
    bg_main        = "#1e2022",
    bg_secondary   = "#2b2d30",
    bg_input       = "#2a2d30",
    bg_table       = "#1e2022",
    bg_table_alt   = "#252729",
    bg_header      = "#252729",
    bg_btn         = "#3a3d42",
    bg_btn_hover   = "#474b52",
    bg_tooltip     = "#1a1c1e",

    # Foregrounds
    text_primary   = "#dce1e7",
    text_secondary = "#8a9099",
    text_disabled  = "#555a60",
    text_btn       = "#dce1e7",

    # Borders
    border         = "#3a3d42",
    border_focus   = "#4a90b8",
    separator      = "#333638",

    # Accent
    accent         = "#4a90b8",
    accent_hover   = "#5aaad4",
    accent_text    = "#ffffff",

    # Semantic
    success        = "#5aab6e",
    warning        = "#c8a84b",
    error          = "#c05858",

    # Action buttons
    btn_add          = "#2a5a3a",
    btn_add_hover    = "#3a7a50",
    btn_remove       = "#6a2a2a",
    btn_remove_hover = "#8a3a3a",
    btn_clear        = "#3a3a2a",
    btn_clear_hover  = "#505038",

    # Badge fallback
    badge_none_bg  = "#2b2d30",
    badge_none_fg  = "#555a60",

    # Toggle
    toggle_track_on  = "#4a90b8",
    toggle_track_off = "#3a3d42",
    toggle_thumb     = "#dce1e7",

    # Discovery tab specific
    table_selected_bg_dark  = "#2a4a6a",
    table_selected_bg_light = "#bcdffc",
    table_header_bg         = "#2a2a2a",
    table_header_fg         = "#8a9099",
    spin_bg                 = "#2a2a2a",
    spin_fg                 = "#ddd",
    spin_border             = "#444",
    spin_disabled_bg        = "#252525",
    spin_disabled_fg        = "#777",
    combo_bg                = "#2a2a2a",
    combo_fg                = "#ddd",
    combo_border            = "#444",
    target_no_exp_fg        = "#c0784a",
    target_exp_fg           = "#6abf69",
    save_pending_fg         = "#c0a030",
    save_success_fg         = "#6abf69",
    save_error_fg           = "#c05050",
    row_text_fg_dark        = "#eeeeee",
    row_text_fg_light       = "#222222",
    path_text_fg            = "#777",
    missing_file_fg         = "#c05050",
)

_LIGHT = ThemeColors(
    # Backgrounds
    bg_main        = "#e8eaed",
    bg_secondary   = "#d8dce2",
    bg_input       = "#f0f2f5",
    bg_table       = "#f5f6f8",
    bg_table_alt   = "#eceef2",
    bg_header      = "#d0d4da",
    bg_btn         = "#d0d4da",
    bg_btn_hover   = "#bec3cc",
    bg_tooltip     = "#ffffff",

    # Foregrounds
    text_primary   = "#1a1d21",
    text_secondary = "#5a6270",
    text_disabled  = "#9aa0ac",
    text_btn       = "#1a1d21",

    # Borders
    border         = "#c0c5ce",
    border_focus   = "#4a90b8",
    separator      = "#c8ccd4",

    # Accent
    accent         = "#2e78a8",
    accent_hover   = "#3a90c8",
    accent_text    = "#ffffff",

    # Semantic
    success        = "#2e7d3a",
    warning        = "#8a6a10",
    error          = "#b03030",

    # Action buttons
    btn_add          = "#1e5c30",
    btn_add_hover    = "#2a7a42",
    btn_remove       = "#7a2020",
    btn_remove_hover = "#982828",
    btn_clear        = "#5a5a30",
    btn_clear_hover  = "#6e6e3c",

    # Badge fallback
    badge_none_bg  = "#d0d4da",
    badge_none_fg  = "#8a9099",

    # Toggle
    toggle_track_on  = "#2e78a8",
    toggle_track_off = "#b0b8c4",
    toggle_thumb     = "#ffffff",

    # Discovery tab specific
    table_selected_bg_dark  = "#2a4a6a",
    table_selected_bg_light = "#bcdffc",
    table_header_bg         = "#e8e8e8",
    table_header_fg         = "#5a6270",
    spin_bg                 = "#eeeeee",
    spin_fg                 = "#222",
    spin_border             = "#ccc",
    spin_disabled_bg        = "#f5f5f5",
    spin_disabled_fg        = "#999",
    combo_bg                = "#fdfdfd",
    combo_fg                = "#222",
    combo_border            = "#ccc",
    target_no_exp_fg        = "#a0582a",
    target_exp_fg           = "#2e7d32",
    save_pending_fg         = "#8a6a10",
    save_success_fg         = "#2e7d3a",
    save_error_fg           = "#b03030",
    row_text_fg_dark        = "#eeeeee",
    row_text_fg_light       = "#222222",
    path_text_fg            = "#777",
    missing_file_fg         = "#b03030",
)


# ──────────────────────────────────────────────────────────────────────────────
#  Public accessor
# ──────────────────────────────────────────────────────────────────────────────
def get_theme(is_dark: bool) -> ThemeColors:
    """Return the correct ThemeColors for the requested mode."""
    return _DARK if is_dark else _LIGHT


# ──────────────────────────────────────────────────────────────────────────────
#  QPalette helper  (apply to QApplication for native widget fallback coverage)
# ──────────────────────────────────────────────────────────────────────────────
def build_palette(is_dark: bool) -> QPalette:
    """
    Build a QPalette that covers all native Qt roles.
    Apply this to QApplication so that QMessageBox, QInputDialog,
    QFileDialog and any other native dialogs inherit the correct colors.
    """
    T = get_theme(is_dark)
    p = QPalette()

    bg   = QColor(T.bg_main)
    bg2  = QColor(T.bg_secondary)
    inp  = QColor(T.bg_input)
    txt  = QColor(T.text_primary)
    dim  = QColor(T.text_secondary)
    btn  = QColor(T.bg_btn)
    btxt = QColor(T.text_btn)
    high = QColor(T.accent)
    htxt = QColor(T.accent_text)
    dis  = QColor(T.text_disabled)
    bord = QColor(T.border)

    p.setColor(QPalette.ColorRole.Window,          bg)
    p.setColor(QPalette.ColorRole.WindowText,      txt)
    p.setColor(QPalette.ColorRole.Base,            inp)
    p.setColor(QPalette.ColorRole.AlternateBase,   bg2)
    p.setColor(QPalette.ColorRole.Text,            txt)
    p.setColor(QPalette.ColorRole.BrightText,      QColor("#ffffff"))
    p.setColor(QPalette.ColorRole.Button,          btn)
    p.setColor(QPalette.ColorRole.ButtonText,      btxt)
    p.setColor(QPalette.ColorRole.Highlight,       high)
    p.setColor(QPalette.ColorRole.HighlightedText, QColor(htxt))
    p.setColor(QPalette.ColorRole.ToolTipBase,     QColor(T.bg_tooltip))
    p.setColor(QPalette.ColorRole.ToolTipText,     txt)
    p.setColor(QPalette.ColorRole.PlaceholderText, dim)
    p.setColor(QPalette.ColorRole.Mid,             bg2)
    p.setColor(QPalette.ColorRole.Dark,            QColor(T.separator))
    p.setColor(QPalette.ColorRole.Shadow,          QColor("#000000"))
    p.setColor(QPalette.ColorRole.Link,            high)
    p.setColor(QPalette.ColorRole.LinkVisited,     QColor(T.accent_hover))

    # Disabled state
    p.setColor(QPalette.ColorGroup.Disabled, QPalette.ColorRole.WindowText, dis)
    p.setColor(QPalette.ColorGroup.Disabled, QPalette.ColorRole.Text,       dis)
    p.setColor(QPalette.ColorGroup.Disabled, QPalette.ColorRole.ButtonText, dis)
    p.setColor(QPalette.ColorGroup.Disabled, QPalette.ColorRole.Base,       bg)

    return p


def apply_palette_to_app(app, is_dark: bool):
    """Apply the full palette to a QApplication instance."""
    app.setPalette(build_palette(is_dark))