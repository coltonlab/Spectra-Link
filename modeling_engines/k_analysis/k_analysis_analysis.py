from __future__ import annotations

import os
import sys

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

import numpy as np
import pyqtgraph as pg
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor

from modeling_engines.k_analysis.k_analysis_fit import fit_power_law, power_law

def fit_gaussian(x_slice, y_slice):
    if len(x_slice) < 4:
        return None

    idx_max = np.argmax(np.abs(y_slice))
    x0_guess = x_slice[idx_max]
    A_guess = y_slice[idx_max]
    sigma_guess = (x_slice.max() - x_slice.min()) / 4.0
    if sigma_guess <= 0:
        sigma_guess = 0.01
    C_guess = np.mean(y_slice)

    p0 = [A_guess, x0_guess, sigma_guess, C_guess]

    def gauss(x, A, x0, sigma, C):
        return A * np.exp(-((x - x0) ** 2) / (2 * sigma ** 2)) + C

    try:
        from scipy.optimize import curve_fit

        popt, _ = curve_fit(gauss, x_slice, y_slice, p0=p0, maxfev=2000)
        popt[2] = abs(popt[2])
        return popt
    except Exception:
        return None


def _format_k_value(k, k_error=None):
    if k_error is None or not np.isfinite(k_error):
        return f"{k:.3f}"
    return f"{k:.3f} ± {k_error:.3f}"


def perform_k_analysis(traces, metadata, parent_window, regions, range_list_widget, results_log, current_view, plot, update_view_callback, save_ranges_callback, k_results, show_fits_checkbox, region_curve_filters=None, fit_gaussian_fn=fit_gaussian, show_studentized_res=False):
    k_results.clear()
    results_log.clear()

    if not traces:
        return k_results

    try:
        from processors.factory import get_processor
    except (ImportError, ModuleNotFoundError):
        from processors.factory import get_processor

    processor = get_processor(metadata.get("core", {}).get("technique"), parent_window)
    settings = metadata.get("analysis_settings", {})

    for idx, region in enumerate(regions):
        min_x, max_x = region.getRegion()
        voltages = []
        peaks = []
        peak_errors = []

        if region_curve_filters is not None and idx < len(region_curve_filters):
            allowed_indices = region_curve_filters[idx]
        else:
            allowed_indices = None

        for i, raw_trace in enumerate(traces):
            if allowed_indices is not None and i not in allowed_indices:
                continue
            x, y = processor._process_trace(raw_trace["wavelengths"], raw_trace["ea"], settings, i)
            mask = (x >= min_x) & (x <= max_x)
            if np.any(mask):
                voltages.append(raw_trace.get("value", 0))
                x_slice = x[mask]
                y_slice = y[mask]
                popt = fit_gaussian_fn(x_slice, y_slice)
                if popt is not None:
                    A, x0, sigma, C = popt
                    fit_y = A * np.exp(-((x_slice - x0) ** 2) / (2 * sigma ** 2)) + C
                    peaks.append(np.max(np.abs(fit_y)))
                    peak_errors.append(max(float(sigma), 1e-6))
                else:
                    peaks.append(np.max(np.abs(y_slice)))
                    peak_errors.append(1e-3)

        v_arr = np.array(voltages)
        p_arr = np.array(peaks)

        mask = (v_arr > 0) & (p_arr > 0)
        if np.sum(mask) >= 2:
            try:
                fit_result = fit_power_law(v_arr[mask], p_arr[mask])
            except Exception:
                fit_result = {
                    "a": np.nan,
                    "k": np.nan,
                    "k_error": np.nan,
                    "fitted_amplitudes": np.array([]),
                    "studentized_res": np.array([]),
                }

            k = fit_result.get("k", np.nan)
            k_error = fit_result.get("k_error", np.nan)
            k_results.append(
                {
                    "id": idx,
                    "min_x": min_x,
                    "max_x": max_x,
                    "k": k,
                    "k_error": k_error,
                    "intercept": np.nan,
                    "voltages": v_arr[mask],
                    "peaks": p_arr[mask],
                    "fitted_amplitudes": fit_result.get("fitted_amplitudes", np.array([])),
                    "studentized_res": fit_result.get("studentized_res", np.array([])),
                    "a": fit_result.get("a", np.nan),
                }
            )

            k_label = _format_k_value(k, k_error)
            item = range_list_widget.item(idx)
            if item:
                item.setText(f"Range {idx + 1}: {min_x:.2f}-{max_x:.2f} eV (k={k_label})")
            else:
                range_list_widget.addItem(f"Range {idx + 1}: {min_x:.2f}-{max_x:.2f} eV (k={k_label})")
            results_log.append(f"Range {idx + 1} ({min_x:.2f}-{max_x:.2f} eV): <b>k = {k_label}</b>, intercept = {fit_result.get('a', np.nan)}")
        else:
            results_log.append(f"Range {idx + 1} ({min_x:.2f}-{max_x:.2f} eV): Not enough data points for fit.")
        results_log.append("-" * 20)

    if current_view == "k-plot" and k_results:
        plot.clear()
        for result in k_results:
            color_idx = result["id"] % 10
            plot_color = pg.intColor(color_idx, 10)
            plot.plot(result["voltages"], result["peaks"], pen=None, symbol="o", symbolBrush=plot_color, name=f"Data R{result['id'] + 1}")
            
            if show_studentized_res:
                for x_val, y_val, d_val in zip(result["voltages"], result["peaks"], result["studentized_res"]):
                    if not np.isfinite(d_val):
                        continue
                    label = pg.TextItem(text=f"D={d_val:.2f}", color=plot_color, anchor=(0.5, 1.0))
                    label = pg.TextItem(text=f"D={d_val:.2f}", color=plot_color, anchor=(0.5, 1.0))
                    
                    # Mandatorily apply log10 to coordinates for log-log scale mapping
                    log_x = np.log10(float(x_val))
                    log_y = np.log10(float(y_val))
                    
                    label.setPos(log_x, log_y)
                    plot.addItem(label)

            fit_v = np.linspace(min(result["voltages"]), max(result["voltages"]), 100)
            fit_p = power_law(fit_v, result.get("a", np.nan), result.get("k", np.nan))
            plot.plot(fit_v, fit_p, pen=pg.mkPen(plot_color, width=2), name=f"Fit R{result['id'] + 1} (k={_format_k_value(result['k'], result.get('k_error'))})")
    elif current_view == "spectrum":
        update_view_callback()

    save_ranges_callback()
    return k_results
