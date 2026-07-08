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


def perform_k_analysis(traces, metadata, parent_window, regions, range_list_widget, results_log, current_view, plot, update_view_callback, save_ranges_callback, k_results, show_fits_checkbox, fit_gaussian_fn=fit_gaussian):
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

        for i, raw_trace in enumerate(traces):
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
                else:
                    peaks.append(np.max(np.abs(y_slice)))

        v_arr = np.array(voltages)
        p_arr = np.array(peaks)

        mask = (v_arr > 0) & (p_arr > 0)
        if np.sum(mask) >= 2:
            log_v = np.log10(v_arr[mask])
            log_p = np.log10(p_arr[mask])
            k, intercept = np.polyfit(log_v, log_p, 1)
            k_results.append(
                {
                    "id": idx,
                    "min_x": min_x,
                    "max_x": max_x,
                    "k": k,
                    "intercept": intercept,
                    "voltages": v_arr[mask],
                    "peaks": p_arr[mask],
                }
            )

            item = range_list_widget.item(idx)
            if item:
                item.setText(f"Range {idx + 1}: {min_x:.2f}-{max_x:.2f} eV (k={k:.3f})")
            else:
                range_list_widget.addItem(f"Range {idx + 1}: {min_x:.2f}-{max_x:.2f} eV (k={k:.3f})")
            results_log.append(f"Range {idx + 1} ({min_x:.2f}-{max_x:.2f} eV): <b>k = {k:.3f}</b>")
        else:
            results_log.append(f"Range {idx + 1} ({min_x:.2f}-{max_x:.2f} eV): Not enough data points for fit.")
        results_log.append("-" * 20)

    if current_view == "k-plot" and k_results:
        plot.clear()
        for result in k_results:
            color_idx = result["id"] % 10
            plot_color = pg.intColor(color_idx, 10)
            plot.plot(result["voltages"], result["peaks"], pen=None, symbol="o", symbolBrush=plot_color, name=f"Data R{result['id'] + 1}")
            fit_v = np.linspace(min(result["voltages"]), max(result["voltages"]), 100)
            fit_p = 10 ** (result["k"] * np.log10(fit_v) + result["intercept"])
            plot.plot(fit_v, fit_p, pen=pg.mkPen(plot_color, width=2), name=f"Fit R{result['id'] + 1} (k={result['k']:.2f})")
    elif current_view == "spectrum":
        update_view_callback()

    save_ranges_callback()
    return k_results
