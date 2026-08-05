from types import SimpleNamespace
from unittest.mock import patch

import numpy as np

from processors.impedance_calibration_processor import ImpedanceCalibrationProcessor
from utils.colton_math import calculate_true_z


def test_calculate_true_z_uses_series_r_and_x():
    r = np.array([3.0, 0.0])
    x = np.array([4.0, 0.0])

    mag, phase, real_part, imag_part = calculate_true_z(r, x, is_series_mode=True)

    assert np.allclose(mag, np.array([5.0, 0.0]))
    assert np.allclose(phase, np.array([53.13010235, 0.0]))
    assert np.allclose(real_part, np.array([3.0, 0.0]))
    assert np.allclose(imag_part, np.array([4.0, 0.0]))


def test_calculate_true_z_uses_parallel_g_and_b_conjugate():
    g = np.array([3.0, 0.0])
    b = np.array([4.0, 0.0])

    mag, phase, real_part, imag_part = calculate_true_z(g, b, is_series_mode=False)

    assert np.allclose(mag, np.array([0.2, 0.0]))
    assert np.allclose(phase, np.array([-53.13010235, 0.0]))
    assert np.allclose(real_part, np.array([0.12, 0.0]))
    assert np.allclose(imag_part, np.array([-0.16, 0.0]))


def test_calculate_calibrated_sample_uses_complex_values():
    processor = ImpedanceCalibrationProcessor.__new__(ImpedanceCalibrationProcessor)

    z_known_load = np.array([10.0 + 0.0j])
    z_short = np.array([2.0 + 1.0j])
    z_sample = np.array([4.0 + 2.0j])
    z_load = np.array([8.0 + 0.0j])
    z_open = np.array([1.0 + 0.0j])

    calibrated = processor._calculate_calibrated_sample(
        z_known_load, z_short, z_sample, z_load, z_open
    )

    assert np.allclose(calibrated, np.array([7.13097713 + 0.29106029j]))


def test_calibrated_sample_can_use_hidden_scans(tmp_path):
    processor = ImpedanceCalibrationProcessor.__new__(ImpedanceCalibrationProcessor)
    processor.parent_window = SimpleNamespace(base_dir=str(tmp_path))

    for filename in ["open.csv", "short.csv", "load.csv", "known_load.csv", "sample.csv"]:
        (tmp_path / filename).write_text("dummy")

    def fake_read_data_simple(path):
        return {
            "F (Hz)": [1.0, 2.0],
            "R": [10.0, 20.0],
            "X": [3.0, 4.0],
        }

    json_data = {
        "data_files": {
            "open_file": "open.csv",
            "short_file": "short.csv",
            "load_file": "load.csv",
            "known_load_file": "known_load.csv",
            "sample_file": "sample.csv",
        },
        "global_settings": {"circuit_model": "Series"},
    }
    settings = {
        "show_open_scan": False,
        "show_short_scan": False,
        "show_load_scan": False,
        "show_known_load_scan": False,
        "show_sample_scan": False,
        "show_calibrated_sample_scan": True,
    }

    with patch("processors.public.read_colton_files.read_data_simple", side_effect=fake_read_data_simple):
        traces = processor._load_traces_custom(json_data, settings)

    assert any(trace["type"] == "Calibrated Sample" for trace in traces)
