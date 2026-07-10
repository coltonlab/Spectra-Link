import numpy as np
from scipy.optimize import curve_fit


def power_law(voltages, a, b):
    return a * np.power(voltages, b)

def _compute_weighted_studentized_residuals(voltages, amplitudes):
    """Calculates internally studentized residuals, weighted slope (k), 

    intercept, and the standard error of the slope for a log-log fit.
    Weights are based on squared linear amplitudes (w = Amp^2).
    """
    # 1. Transform coordinates to the log domain
    x = np.log10(voltages)
    y = np.log10(amplitudes)
    n = len(x)
    p = 2  # Number of parameters (slope and intercept)
    
    # 2. Define weights based on the square of the raw linear amplitudes
    weights = amplitudes ** 2
    
    # 3. Perform Weighted Linear Regression in the log-log domain
    slope, intercept = np.polyfit(x, y, 1, w=np.sqrt(weights))
    y_pred = slope * x + intercept
    raw_residuals = y - y_pred
    
    # 4. Calculate Weighted Design Matrix components for Error and Leverage
    W = np.diag(weights)
    X = np.column_stack((np.ones(n), x))  # Design matrix
    
    try:
        # Covariance matrix calculation: (X^T * W * X)^-1
        xt_w_x_inv = np.linalg.inv(np.dot(np.dot(X.T, W), X))
        
        # Calculate Weighted Mean Squared Error (MSE)
        weighted_rss = np.sum(weights * (raw_residuals ** 2))
        mse_weighted = weighted_rss / (n - p)
        
        # Parameter variances are the diagonal of (MSE * Covariance Matrix)
        param_cov = mse_weighted * xt_w_x_inv
        intercept_err = np.sqrt(param_cov[0, 0])
        slope_err = np.sqrt(param_cov[1, 1])  # Standard error of the slope (k)
        
        # Leverage extraction for studentized residuals
        hat_matrix = np.dot(np.dot(np.dot(X, xt_w_x_inv), X.T), W)
        leverage = np.diag(hat_matrix)
        
    except np.linalg.LinAlgError:
        # Fallback if matrix math becomes unstable with small datasets
        x_mean = np.mean(x)
        leverage = (1 / n) + ((x - x_mean) ** 2) / np.sum((x - x_mean) ** 2)
        # Standard unweighted slope error calculation fallback
        rss = np.sum(raw_residuals ** 2)
        mse = rss / (n - p)
        slope_err = np.sqrt(mse / np.sum((x - x_mean) ** 2))

    # 5. Compute Weighted Studentized Residuals
    denom = np.sqrt(mse_weighted * (1.0 - leverage) / weights)
    denom = np.where(denom == 0, 1e-10, denom)
    studentized_res = raw_residuals / denom
    
    # Returns EVERYTHING you need for your UI text and plots
    return studentized_res, slope, intercept, slope_err

def fit_power_law(voltages, amplitudes, p0=None):
    voltages = np.asarray(voltages, dtype=float)
    amplitudes = np.asarray(amplitudes, dtype=float)

    mask = np.isfinite(voltages) & np.isfinite(amplitudes) & (voltages > 0) & (amplitudes > 0)
    voltages = voltages[mask]
    amplitudes = amplitudes[mask]

    if len(voltages) < 3:
        raise ValueError("At least three positive data points are required for a stable power-law fit.")

    if p0 is None:
        a_guess = max(amplitudes) / max(voltages) ** 2
        p0 = [a_guess, 1.0]

    try:
        studentized_res, slope, intercept, slope_err = _compute_weighted_studentized_residuals(voltages, amplitudes)
        return {
            "a": float(10**intercept),
            "k": float(slope),
            "k_error": float(slope_err),
            "fitted_amplitudes": 10**(intercept + slope * np.log10(voltages)),
            "studentized_res": studentized_res,
            "covariance": None,
        }
    except Exception:
        return {
            "a": np.nan,
            "k": np.nan,
            "k_error": np.nan,
            "fitted_amplitudes": np.array([]),
            "studentized_res": np.array([]),
            "covariance": None,
        }