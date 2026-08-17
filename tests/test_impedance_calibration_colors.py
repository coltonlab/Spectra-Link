import pytest
import matplotlib.pyplot as plt
import numpy as np
from types import SimpleNamespace
from unittest.mock import patch

from processors.impedance_calibration_processor import ImpedanceCalibrationProcessor


def test_default_trace_color_and_alpha():
    c_open, a_open = ImpedanceCalibrationProcessor._get_trace_color_and_alpha("Open", {})
    assert c_open == "black"
    assert a_open == 0.7

    c_short, a_short = ImpedanceCalibrationProcessor._get_trace_color_and_alpha("Short", {})
    assert c_short == "black"
    assert a_short == 0.7

    c_load, a_load = ImpedanceCalibrationProcessor._get_trace_color_and_alpha("Load", {})
    assert c_load == "green"
    assert a_load == 0.7

    c_kl, a_kl = ImpedanceCalibrationProcessor._get_trace_color_and_alpha("Known Load", {})
    assert c_kl == "red"
    assert a_kl == 0.7

    c_sample, a_sample = ImpedanceCalibrationProcessor._get_trace_color_and_alpha("Sample", None)
    assert c_sample == "blue"
    assert a_sample == 0.7

    c_s2, a_s2 = ImpedanceCalibrationProcessor._get_trace_color_and_alpha("Sample 2", None)
    assert c_s2 == "brown"
    assert a_s2 == 0.7


def test_custom_trace_color_and_alpha_by_scan_key():
    settings = {
        "open_color": "red",
        "open_alpha": 0.5,
        "short_color": "#00ff00",
        "short_alpha": 0.8,
        "load_color": "blue",
        "load_alpha": 1.0,
        "known_load_color": "purple",
        "known_load_alpha": 0.9,
        "sample_color": "yellow",
        "sample_alpha": 0.3,
        "sample_2_color": "orange",
        "sample_2_alpha": 0.7,
        "calibrated_sample_color": "magenta",
        "calibrated_sample_alpha": 0.6,
    }

    c_open, a_open = ImpedanceCalibrationProcessor._get_trace_color_and_alpha("Open", settings)
    assert c_open == "red"
    assert a_open == 0.5

    c_short, a_short = ImpedanceCalibrationProcessor._get_trace_color_and_alpha("Short", settings)
    assert c_short == "#00ff00"
    assert a_short == 0.8

    c_cal, a_cal = ImpedanceCalibrationProcessor._get_trace_color_and_alpha("Calibrated Sample", settings)
    assert c_cal == "magenta"
    assert a_cal == 0.6


def test_custom_trace_color_and_alpha_by_dict():
    settings = {
        "scan_colors": {
            "Open": "cyan",
            "Sample": "lime",
        },
        "scan_alphas": {
            "Open": 0.4,
            "Sample": 0.85,
        }
    }

    c_open, a_open = ImpedanceCalibrationProcessor._get_trace_color_and_alpha("Open", settings)
    assert c_open == "cyan"
    assert a_open == 0.4

    c_sample, a_sample = ImpedanceCalibrationProcessor._get_trace_color_and_alpha("Sample", settings)
    assert c_sample == "lime"
    assert a_sample == 0.85

    # Fallback for Load should be default green with alpha 0.7
    c_load, a_load = ImpedanceCalibrationProcessor._get_trace_color_and_alpha("Load", settings)
    assert c_load == "green"
    assert a_load == 0.7


def test_generate_plot_applies_custom_color_and_alpha(tmp_path):
    processor = ImpedanceCalibrationProcessor.__new__(ImpedanceCalibrationProcessor)
    processor.parent_window = SimpleNamespace(base_dir=str(tmp_path))
    processor.data_path = None

    (tmp_path / "open.csv").write_text("dummy")

    def fake_read_data(path):
        return {
            "F (Hz)": [100.0, 200.0],
            "R": [10.0, 20.0],
            "X": [1.0, 2.0],
        }

    json_data = {
        "data_files": {
            "open_file": "open.csv",
        },
        "analysis_settings": {
            "show_open_scan": True,
            "open_color": "green",
            "open_alpha": 0.75,
        }
    }

    with patch.object(processor, "get_json_data", return_value=json_data), \
         patch("processors.public.read_colton_files.read_data_simple", side_effect=fake_read_data):
        fig = plt.figure()
        success = processor.generate_plot(fig)
        assert success is True

        ax = fig.gca()
        lines = ax.get_lines()
        assert len(lines) == 1
        line = lines[0]
        assert line.get_alpha() == 0.75
        plt.close(fig)
