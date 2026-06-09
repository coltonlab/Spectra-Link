import sys
import platform
import requests
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QLabel, QLineEdit, 
    QTextEdit, QPushButton, QHBoxLayout, QMessageBox
)
from PyQt6.QtCore import Qt
from utils.app_logger import logger # Import the global logger

class BugReportDialog(QDialog):
    """
    A 'headless' bug reporting dialog that submits directly to a Google Form.
    Aggregates application state and system metadata automatically.
    """
    def __init__(self, parent_window):
        super().__init__(parent_window)
        self.parent_window = parent_window
        self.setWindowTitle("Report a Bug / Feedback")
        self.setFixedWidth(450)
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(10)

        layout.addWidget(QLabel("<b>Your Name</b>"))
        self.edit_name = QLineEdit()
        self.edit_name.setPlaceholderText("Enter your name")
        layout.addWidget(self.edit_name)

        layout.addWidget(QLabel("<b>Summary</b> (Short description of the problem)"))
        self.edit_title = QLineEdit()
        self.edit_title.setPlaceholderText("e.g., Analysis tab fails to plot Absorption data")
        layout.addWidget(self.edit_title)

        layout.addWidget(QLabel("<b>Steps to Reproduce / Details</b>"))
        self.edit_desc = QTextEdit()
        self.edit_desc.setPlaceholderText("What were you doing when the issue occurred?")
        layout.addWidget(self.edit_desc)

        info_lbl = QLabel("<i>Technical metadata (OS, Technique, and Path) will be attached to help with debugging.</i>")
        info_lbl.setWordWrap(True)
        info_lbl.setStyleSheet("color: gray; font-size: 11px;")
        layout.addWidget(info_lbl)

        # Buttons
        btn_layout = QHBoxLayout()
        self.btn_cancel = QPushButton("Cancel")
        self.btn_submit = QPushButton("Submit Report")
        self.btn_submit.setToolTip("Submit this report to the developer via Google Forms")
        self.btn_submit.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_submit.setStyleSheet("font-weight: bold; padding: 6px 16px;")
        
        self.btn_cancel.clicked.connect(self.reject)
        self.btn_submit.clicked.connect(self.submit_report)

        btn_layout.addStretch()
        btn_layout.addWidget(self.btn_cancel)
        btn_layout.addWidget(self.btn_submit)
        layout.addLayout(btn_layout)

    def _get_metadata(self) -> str:
        """Gathers diagnostic info from the current session and environment."""
        tech = "Unknown"
        path = "No file open"
        
        # Attempt to pull state from the Discovery Tab
        if hasattr(self.parent_window, 'discovery_tab'):
            dt = self.parent_window.discovery_tab
            tech = getattr(dt, "_current_technique", "None") or "None"
            path = str(getattr(dt, "_current_json_path", "None")) or "None"

        metadata = [
            f"--- ENVIRONMENT ---",
            f"OS: {platform.system()} {platform.release()} ({platform.machine()})",
            f"Python: {sys.version.split()[0]}",
            f"--- SPECTRA-LINK STATE ---",
            f"Active Technique: {tech}",
            f"Current JSON: {path}",
            f"Base Dir: {getattr(self.parent_window, 'base_dir', 'Unknown')}",
            f"Remote Mode: {getattr(self.parent_window.sidebar.check_remote, 'isChecked', lambda: False)()}"
        ]
        return "\n".join(metadata)

    def submit_report(self):
        user_name = self.edit_name.text().strip()
        title = self.edit_title.text().strip()
        desc = self.edit_desc.toPlainText().strip()

        if not title:
            QMessageBox.warning(self, "Required Field", "Please provide a summary for the bug report.")
            return

        self.btn_submit.setEnabled(False)
        self.btn_submit.setText("Sending...")

        form_url = "https://docs.google.com/forms/d/e/1FAIpQLSfJUl8rIidPxycUJ0R_K-BgKiWs8vPxmSrDrAVJtjufXXN6sw/formResponse"
        payload = {
            "entry.1755151959": user_name,
            "entry.152593343": title,
            "entry.1436956166": desc,
            "entry.516745869": self._get_metadata()
        }

        try:
            response = requests.post(form_url, data=payload, timeout=10)
            if response.status_code == 200:
                logger.info("Bug report submitted successfully.")
                QMessageBox.information(self, "Report Submitted", "Thank you! Your feedback has been received.")
                self.accept()
            else:
                logger.error(f"Bug report submission failed with status code {response.status_code}")
                raise Exception(f"Server responded with code {response.status_code}")
        except Exception as e:
            QMessageBox.critical(self, "Submission Failed", f"Could not submit report.\nError: {str(e)}")
            self.btn_submit.setEnabled(True)
            self.btn_submit.setText("Submit Report")