import numpy as np

def calculate_true_z(z_raw, phi_deg, is_series_mode):
    """
    Applies math conversions to get the true Z value (Impedance).
    In series mode, Z is actually Y (Admittance).
    Y = Y_mag * exp(j * Phi)
    Z_true = 1 / Y.
    Returns: True Z magnitude and True Phi in degrees.
    """
    # z_raw could be a pandas Series or numpy array
    z_raw = np.array(z_raw, dtype=float)
    phi_deg = np.array(phi_deg, dtype=float)

    if not is_series_mode:
        return z_raw, phi_deg
    
    # In series mode, z_raw is actually Y magnitude, and phi_deg is Y phase.
    # Z_true = 1 / Y
    # Magnitude of Z = 1 / Magnitude of Y
    # Phase of Z = - Phase of Y
    
    # Avoid division by zero
    z_true_mag = np.zeros_like(z_raw)
    valid = (z_raw != 0) & (~np.isnan(z_raw))
    z_true_mag[valid] = 1.0 / z_raw[valid]
    
    z_true_phi = -phi_deg
    
    return z_true_mag, z_true_phi
