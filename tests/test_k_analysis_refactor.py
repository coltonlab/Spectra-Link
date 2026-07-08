import os
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt6.QtWidgets import QApplication

from modeling_engines.k_analysis.k_analysis_ui import build_k_analysis_ui


class KAnalysisUiRefactorTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_build_k_analysis_ui_creates_core_widgets(self):
        widget = build_k_analysis_ui()

        self.assertIsNotNone(widget)
        self.assertTrue(hasattr(widget, "plot"))
        self.assertTrue(hasattr(widget, "results_log"))
        self.assertTrue(hasattr(widget, "btn_add_range"))
        self.assertTrue(hasattr(widget, "range_list_widget"))
        self.assertTrue(hasattr(widget, "btn_toggle_view"))
        self.assertTrue(hasattr(widget, "chk_show_fits"))


if __name__ == "__main__":
    unittest.main()
