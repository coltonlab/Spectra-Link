import os
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import numpy as np
import pyqtgraph as pg
from PyQt6.QtGui import QColor
from PyQt6.QtWidgets import QApplication

from modeling_engines.k_analysis.k_analysis_ui import build_k_analysis_ui
from modeling_engines.k_analysis.k_analysis_interactions import KAnalysisInteractionController
from modeling_engines.k_analysis.k_analysis_controller import KAnalysisAppController
from modeling_engines.k_analysis.k_analysis_fit import fit_power_law


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
        self.assertTrue(hasattr(widget, "chk_show_cooks"))

    def test_interaction_controller_can_be_created(self):
        dummy_dashboard = type("DummyDashboard", (), {})()
        controller = KAnalysisInteractionController(dummy_dashboard)

        self.assertIsNotNone(controller)

    def test_app_controller_can_be_created(self):
        dummy_dashboard = type("DummyDashboard", (), {})()
        controller = KAnalysisAppController(dummy_dashboard)

        self.assertIsNotNone(controller)
        self.assertIs(dummy_dashboard, controller.dashboard)

    def test_region_style_uses_transparent_fill_with_same_color(self):
        controller = KAnalysisInteractionController(None)
        region = pg.LinearRegionItem(values=(0.0, 1.0))
        color = QColor(255, 0, 0, 255)

        controller.set_region_style(region, color)

        self.assertEqual(region.brush.color().red(), 255)
        self.assertEqual(region.brush.color().green(), 0)
        self.assertEqual(region.brush.color().blue(), 0)
        self.assertEqual(region.brush.color().alpha(), 25)

    def test_power_law_fit_reports_exponent_and_uncertainty(self):
        voltages = np.array([100.0, 200.0, 300.0, 400.0])
        amplitudes = np.array([0.1, 0.4, 0.9, 1.6])

        result = fit_power_law(voltages, amplitudes)

        self.assertGreater(result["k"], 0.0)
        self.assertGreater(result["k_error"], 0.0)
        self.assertEqual(len(result["cooks_distance"]), len(voltages))


if __name__ == "__main__":
    unittest.main()
