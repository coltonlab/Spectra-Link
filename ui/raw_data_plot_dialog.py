from pathlib import Path
import numpy as np
import matplotlib.pyplot as plt
from PyQt6.QtWidgets import QDialog, QVBoxLayout, QPushButton, QHBoxLayout, QLabel
from PyQt6.QtCore import Qt
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qtagg import NavigationToolbar2QT as NavigationToolbar
from matplotlib.figure import Figure

from processors.public.read_colton_files import read_data_simple
from ui.theme import get_theme

class RawDataPlotDialog(QDialog):
    """
    A standalone dialog that displays the raw content of a data file.
    Plots all detected signals against the primary X-axis (usually wavelength).
    """
    def __init__(self, file_path: str, is_dark: bool = True, parent=None):
        super().__init__(parent)
        self.file_path = file_path
        self.is_dark = is_dark
        self.setWindowTitle(f"Raw Data Inspection — {Path(file_path).name}")
        
        # Make window non-modal and ensure it stays separate from the main workspace
        self.setWindowFlags(self.windowFlags() | Qt.WindowType.Window)
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
        self.setMinimumSize(900, 650)
        
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(10)

        # Header: File Path Information
        self.header = QLabel(f"<b>File Source:</b> {self.file_path}")
        self.header.setWordWrap(True)
        self.header.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        layout.addWidget(self.header)

        # Matplotlib Plot Components
        self.figure = Figure(layout='constrained')
        self.canvas = FigureCanvas(self.figure)
        self.toolbar = NavigationToolbar(self.canvas, self)
        
        layout.addWidget(self.toolbar)
        layout.addWidget(self.canvas, stretch=1)

        # Footer Actions
        footer = QHBoxLayout()
        footer.addStretch()
        self.close_btn = QPushButton("Close View")
        self.close_btn.setMinimumWidth(100)
        self.close_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.close_btn.clicked.connect(self.accept)
        footer.addWidget(self.close_btn)
        layout.addLayout(footer)

        # Apply initial theme and plot
        self.apply_theme(self.is_dark)

    def apply_theme(self, is_dark: bool):
        """Updates the dialog and plot colors dynamically."""
        self.is_dark = is_dark
        T = get_theme(is_dark)
        
        self.setStyleSheet(f"background-color: {T.bg_main}; color: {T.text_primary};")
        self.header.setStyleSheet(f"color: {T.text_secondary}; font-size: 11px;")
        
        self.toolbar.setStyleSheet(f"""
            QToolBar {{ background: {T.bg_secondary}; border: none; padding: 4px; }}
            QToolButton {{ color: {T.text_primary}; }}
        """)
        
        self.close_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {T.bg_btn};
                color: {T.text_btn};
                border: 1px solid {T.border};
                border-radius: 4px;
                padding: 7px 16px;
                font-weight: bold;
            }}
            QPushButton:hover {{ background-color: {T.bg_btn_hover}; }}
        """)

        # Re-plot raw data to update axes and backgrounds
        self.figure.set_facecolor(T.bg_main)
        self.figure.clear()
        self._plot_raw()
        self.canvas.draw()

    def _plot_raw(self):
        T = get_theme(self.is_dark)
        data = read_data_simple(self.file_path)
        
        ax = self.figure.add_subplot(111)
        
        # Configure axes look based on theme
        ax.set_facecolor(T.bg_table if self.is_dark else T.bg_main)
        for spine in ax.spines.values():
            spine.set_color(T.border)
        ax.tick_params(colors=T.text_secondary, labelsize=9)
        ax.grid(True, linestyle=':', alpha=0.3, color=T.text_secondary)

        if not data:
            ax.text(0.5, 0.5, "Failed to load or parse file.\nCheck logs for details.",
                    ha='center', va='center', color=T.error, transform=ax.transAxes, fontsize=12)
            self.canvas.draw()
            return

        cols = list(data.keys())
        x_key = cols[0]
        x_values = data[x_key]
        
        # Plot all columns except the first one (X)
        y_keys = cols[1:]
        cmap = plt.get_cmap("tab10")
        
        for i, y_key in enumerate(y_keys):
            y_values = data[y_key]
            if len(y_values) == len(x_values):
                ax.plot(x_values, y_values, label=y_key, 
                        color=cmap(i % 10), linewidth=1.2)

        ax.set_xlabel(x_key, color=T.text_primary, fontsize=10)
        ax.set_ylabel("Signal Amplitude (V / Counts)", color=T.text_primary, fontsize=10)
        ax.set_title(f"Data Trace: {Path(self.file_path).name}", color=T.text_primary, fontweight='bold')
        
        legend = ax.legend(frameon=False, fontsize=9, loc='best')
        if legend:
            for text in legend.get_texts():
                text.set_color(T.text_secondary)

        self.canvas.draw()