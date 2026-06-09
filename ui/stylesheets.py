
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
    font-family: "Segoe UI Variable", "Segoe UI", "Inter", "Helvetica Neue", sans-serif;
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
