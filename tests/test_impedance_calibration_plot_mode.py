import numpy as np

from processors.impedance_calibration_processor import ImpedanceCalibrationProcessor


def test_plot_mode_capacitance_uses_imaginary_impedance():
    processor = ImpedanceCalibrationProcessor.__new__(ImpedanceCalibrationProcessor)
    trace = {
        "f": np.array([1e3, 2e3]),
        "z_real": np.array([10.0, 20.0]),
        "z_imag": np.array([-1.0, -2.0]),
    }

    values = processor._get_plot_values(trace, {"impedance_display_mode": "Capacitance"})

    expected = 1.0 / (2.0 * np.pi * np.array([1e3, 2e3]) * np.array([-1.0, -2.0]))
    np.testing.assert_allclose(values, expected)
