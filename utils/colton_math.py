import numpy as np


def calculate_true_z(real_raw, imag_raw, is_series_mode):
    """
    Convert raw impedance/admittance components into the true impedance magnitude,
    phase, and real/imaginary parts.

    In series mode, the inputs are treated as series impedance components: Z = R + jX.
    In parallel mode, the inputs are treated as admittance components: Y = G + jB,
    and the equivalent impedance is recovered as Z = 1 / Y using the complex conjugate.
    """
    real_vals = np.array(real_raw, dtype=float)
    imag_vals = np.array(imag_raw, dtype=float)

    z_complex = np.zeros(real_vals.shape, dtype=np.complex128)
    valid = (~np.isnan(real_vals)) & (~np.isnan(imag_vals))

    if is_series_mode:
        z_complex[valid] = real_vals[valid] + 1j * imag_vals[valid]
    else:
        denom = real_vals**2 + imag_vals**2
        parallel_valid = valid & (denom != 0)
        if np.any(parallel_valid):
            z_complex[parallel_valid] = (real_vals[parallel_valid] - 1j * imag_vals[parallel_valid]) / denom[parallel_valid]

    z_true_mag = np.abs(z_complex)
    z_true_phi = np.degrees(np.angle(z_complex))
    z_true_real = np.real(z_complex)
    z_true_imag = np.imag(z_complex)

    return z_true_mag, z_true_phi, z_true_real, z_true_imag
