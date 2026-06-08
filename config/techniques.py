# ──────────────────────────────────────────────────────────────────────────────
#  Technique definitions
# ──────────────────────────────────────────────────────────────────────────────

TECHNIQUE_CONFIG = {

    # ── Absorption ────────────────────────────────────────────────────────────
    "Absorption": {
        "badge_color":      "#1a4a6a",
        "badge_text_color": "#7ec8e3",
        "scan_types": ["Blank", "Transmission", "None"],
        "json_key_map": {
            "Blank":        "blank_file",
            "Transmission": "sample_file",
            "None":         "none_files",
        },
        "global_params": [
            {
                "key": "author", "label": "Author", "type": "text", "default": "",
            },
            {
                "key": "temperature", "label": "Temperature (K)",
                "min": 0, "max": 450, "default": 295, "step": 1, "decimals": 0,
            },
        ],
        "local_param": None,
        "analysis_options": [
            "show_title",
            "plot_title",
            "line_width",
            "scaling_factor",
            "trace_color",
            "smooth_data",
            "smooth_window",
            "smooth_poly",
            "convert_to_ev",
            "vertical_lines",
            "min_wavelength",
            "max_wavelength",
            "normalize_to_peak",
            "show_legend",
        ],
    },

    # ── Absorption — Temperature Series ───────────────────────────────────────
    "ABS Temp Series": {
        "badge_color":      "#1a4a6a",
        "badge_text_color": "#7ec8e3",
        "scan_types": ["Blank", "Transmission", "None"],
        "json_key_map": {
            "Blank":        "blank_file",
            "Transmission": "sample_file",
            "None":         "none_files",
        },
        "global_params": [
            {
                "key": "author", "label": "Author", "type": "text", "default": "",
            },
        ],
        "local_param": {
            "key": "temperature", "label": "Temperature (K)",
            "min": 0, "max": 9999, "default": 295, "step": 1, "decimals": 0,
            "active_scan_types": ["Transmission"],
        },
        "analysis_options": [
            "show_title",
            "plot_title",
            "line_width",
            "scaling_factor",
            "smooth_data",
            "smooth_window",
            "smooth_poly",
            "convert_to_ev",
            "normalize_to_peak",
            "min_wavelength",
            "max_wavelength",
            "show_colorbar",
            "colormap_name",
            "show_zero_line",
            "vertical_lines",
            "show_legend",
        ],
    },

    # ── Electro-Absorption — Voltage Series ───────────────────────────────────
    "EA Voltage Series": {
        "badge_color":      "#4a2a1a",
        "badge_text_color": "#e3a87e",
        "scan_types": ["Blank", "Transmission", "Voltage", "None"],
        "json_key_map": {
            "Blank":        "blank_file",
            "Transmission": "transmission_file",
            "None":         "none_files",
        },
        "global_params": [
            {
                "key": "author", "label": "Author", "type": "text", "default": "",
            },
            {
                "key": "temperature", "label": "Temperature (K)",
                "min": 0, "max": 9999, "default": 295, "step": 1, "decimals": 0,
            },
        ],
        "local_param": {
            "key": "voltage", "label": "Voltage (V)",
            "min": -9999, "max": 9999, "default": 0, "step": 1, "decimals": 0,
            "active_scan_types": ["Voltage"],
        },
        "analysis_options": [
            "show_title",
            "plot_title",
            "line_width",
            "scaling_factor",
            "smooth_data",
            "smooth_window",
            "smooth_poly",
            "flip_sign",
            "convert_to_ev",
            "min_wavelength",
            "max_wavelength",
            "show_colorbar",
            "colormap_name",
            "show_zero_line",
            "vertical_lines",
            "show_legend",
        ],
    },

    # ── Electro-Absorption — Temperature Series ───────────────────────────────
    "EA Temp Series": {
        "badge_color":      "#4a2a1a",
        "badge_text_color": "#e3a87e",
        "scan_types": ["Blank", "Transmission", "Voltage", "None"],
        "json_key_map": {
            "Blank":        "blank_file",
            "Transmission": "transmission_file",
            "None":         "none_files",
        },
        "global_params": [
            {
                "key": "author", "label": "Author", "type": "text", "default": "",
            },
            {
                "key": "voltage", "label": "Voltage (V)",
                "min": -9999, "max": 9999, "default": 0, "step": 1, "decimals": 0,
            }
        ],
        "local_param": {
            "key": "temperature", "label": "Temperature (K)",
            "min": 0, "max": 9999, "default": 295, "step": 1, "decimals": 0,
            "active_scan_types": ["Voltage", "Transmission"],
        },
        "analysis_options": [
            "smooth_data",
            "smooth_window",
            "smooth_poly",
            "line_width",
            "scaling_factor",
            "flip_sign",
            "convert_to_ev",
            "min_wavelength",
            "max_wavelength",
            "normalize_to_peak",
            "show_legend",
            "show_colorbar",
            "colormap_name",
            "show_zero_line",
            "vertical_lines",
            "overlay_absorption",
        ],
    },

    # ── Circular Dichroism (CD) ───────────────────────────────────────────────
    "Circular Dichroism (CD)": {
        "badge_color":      "#1a4a2a",
        "badge_text_color": "#7ee3a8",
        "scan_types": ["Background", "Sample", "None"],
        "json_key_map": {
            "Background": "background_file",
            "Sample":     "sample_file",
            "None":       "none_files",
        },
        "global_params": [
            {
                "key": "author", "label": "Author", "type": "text", "default": "",
            },
            {
                "key": "temperature", "label": "Temperature (K)",
                "min": 0, "max": 9999, "default": 295, "step": 1, "decimals": 0,
            },
            {
                "key": "pem_retardation", "label": "PEM Retardation",
                "min": 0.0, "max": 5.0, "default": 0.25, "step": 0.01, "decimals": 2,
            },
        ],
        "local_param": {
            "key": "rotation", "label": "Sample Rotation (°)",
            "min": 0, "max": 360, "default": 0, "step": 1, "decimals": 0,
            "active_scan_types": ["Sample"],
        },
        "analysis_options": [
            "smooth_data",
            "convert_to_ev",
            "normalize_to_peak",
            "show_legend",
            "trace_color",
            "vertical_lines",
        ],
    },

    # ── Photoluminescence ─────────────────────────────────────────────────────
    "Photoluminescence (PL)": {
        "badge_color":      "#2a1a4a",
        "badge_text_color": "#b87ee3",
        "scan_types": ["Background", "Sample", "Reference", "None"],
        "json_key_map": {
            "Background": "background_file",
            "Sample":     "sample_file",
            "Reference":  "reference_file",
            "None":       "none_files",
        },
        "global_params": [
            {
                "key": "author", "label": "Author", "type": "text", "default": "",
            },
            {
                "key": "temperature", "label": "Temperature (K)",
                "min": 0, "max": 9999, "default": 295, "step": 1, "decimals": 0,
            },
        ],
        "local_param": None,
        "analysis_options": [
            "smooth_data",
            "convert_to_ev",
            "normalize_to_peak",
            "offset_traces",
            "show_legend",
        ],
    },
}

# ──────────────────────────────────────────────────────────────────────────────
# Format: "Type": (Dark_Hex, Light_Hex)
SCAN_TYPE_COLORS = {
    "Blank":        ("#2d4a3e", "#d5e8df"),  # Soft Green
    "Transmission": ("#2b3d5c", "#d5e1f0"),  # Soft Blue
    "Reference":    ("#3d2b4a", "#e8d5f0"),  # Soft Purple
    "Voltage":      ("#4a3a1e", "#f0e6d5"),  # Soft Gold/Tan
    "Background":   ("#1e3a4a", "#d5e4f0"),  # Soft Deep Blue
    "Sample":       ("#2b3d5c", "#d5e1f0"),  # Soft Blue
    "None":         ("#2a2a2a", "#f3f2f2"),  # Dark Gray / Light Gray
}

# ──────────────────────────────────────────────────────────────────────────────
# Predefined single colors for plotting
# ──────────────────────────────────────────────────────────────────────────────
TRACE_COLORS = [
    "black",
    "red",
    "blue",
    "green",
    "orange",
    "purple",
    "brown",
    "pink",
    "gray",
]

# ──────────────────────────────────────────────────────────────────────────────
# Predefined color gradients for plotting
# These correspond to common colormaps in libraries like Matplotlib
# ──────────────────────────────────────────────────────────────────────────────
COLOR_GRADIENTS = [
    "viridis",
    "plasma",
    "inferno",
    "magma",
    "cividis",
    "Greys",
    "Purples",
    "Blues",
    "Greens",
    "Oranges",
    "Reds",
    "YlOrBr",
    "YlGnBu",
    "PuBuGn",
    "BuGn",
    "GnBu",
    "YlOrRd",
    "PuRd",
    "RdPu",
    "BuPu",
    "OrRd",
]

# ──────────────────────────────────────────────────────────────────────────────
# Human-readable labels and tooltips for every possible analysis option key.
# analysis_tab.py reads this dict to build the dynamic options toolbar so you
# never have to hard-code labels in two places.
# ──────────────────────────────────────────────────────────────────────────────
ANALYSIS_OPTION_META: dict[str, dict] = {
    "smooth_data": {
        "label":   "Smooth Data",
        "tooltip": "Apply Savitzky-Golay smoothing to reduce noise",
        "category": "Preprocessing",
    },
    "flip_y": {
        "label":   "Flip Y-axis",
        "tooltip": "Invert the y-axis — multiply all y values by −1",
        "category": "Data Correction",
    },
    "flip_sign": {
        "label":   "Flip Sign",
        "tooltip": "Flip the sign of the differential signal (EA-specific)",
        "category": "Preprocessing",
    },
    "smooth_window": {
        "label":   "Smooth Window",
        "tooltip": "Number of points for Savitzky-Golay (must be odd)",
        "type":    "numeric",
        "min":     3,
        "max":     999,
        "default": 11,
        "step":    2,
        "decimals": 0,
        "category": "Preprocessing",
    },
    "smooth_poly": {
        "label":   "Smooth Poly",
        "tooltip": "Polynomial order for Savitzky-Golay",
        "type":    "numeric",
        "min":     1,
        "max":     39,
        "default": 3,
        "step":    1,
        "decimals": 0,
        "category": "Preprocessing",
    },
    "convert_to_ev": {
        "label":   "nm → eV",
        "tooltip": "Convert the wavelength axis to photon energy using E = 1240 / λ (nm)",
        "category": "Axes",
    },
    "normalize_to_peak": {
        "label":   "Normalize to Peak",
        "tooltip": "Scale each trace so its absolute maximum equals 1",
        "category": "Preprocessing",
    },
    "offset_traces": {
        "label":   "Offset Traces",
        "tooltip": "Add an incremental vertical offset between overlaid traces for clarity",
        "category": "Axes",
    },
    "show_legend": {
        "label":   "Legend",
        "tooltip": "Display a legend labelling each trace",
        "category": "Visualization",
    },
    "show_title": {
        "label":   "Show Title",
        "tooltip": "Toggle the plot title on or off",
        "category": "Visualization",
    },
    "plot_title": {
        "label":   "Edit Title",
        "tooltip": "Custom text for the plot title",
        "type":    "text",
        "category": "Visualization",
    },
    "line_width": {
        "label":   "Line Width",
        "tooltip": "Set the thickness of the plot lines",
        "type":    "numeric",
        "min":     0.1,
        "max":     10.0,
        "default": 1.5,
        "category": "Visualization",
    },
    "scaling_factor": {
        "label":   "Scaling Factor",
        "tooltip": "Multiply the absorbance values by this factor",
        "type":    "slider_numeric",
        "min":     0.0,
        "max":     10.0,
        "default": 1.0,
        "step":    0.01,
        "category": "Preprocessing",
    },
    "min_wavelength": {
        "label":   "Min Wavelength (nm)",
        "tooltip": "Exclude data points below this wavelength value",
        "type":    "numeric",
        "min":     0.0,
        "max":     10000.0,
        "default": 0.0,
        "category": "Preprocessing",
    },
    "max_wavelength": {
        "label":   "Max Wavelength (nm)",
        "tooltip": "Exclude data points above this wavelength value",
        "type":    "numeric",
        "min":     0.0,
        "max":     10000.0,
        "default": 5000.0,
        "category": "Preprocessing",
    },
    "trace_color": {
        "label":   "Trace Color",
        "tooltip": "Select the color for the plot line",
        "type":    "combo",
        "options": TRACE_COLORS,
        "category": "Visualization",
    },
    "show_colorbar": {
        "label":   "Colorbar",
        "tooltip": "Toggle the intensity/temperature colorbar on the right",
        "category": "Visualization",
    },
    "colormap_name": {
        "label":   "Color",
        "tooltip": "Select a color gradient for plotting multiple traces in a series.",
        "type":    "combo",
        "options": COLOR_GRADIENTS,
        "category": "Visualization",
    },
    "show_zero_line": {
        "label":   "Show Zero Line",
        "tooltip": "Draw a horizontal reference line at Y=0",
        "category": "Visualization",
    },
    "vertical_lines": {
        "label":   "Reference Lines",
        "tooltip": "Add vertical markers at specific energy values (eV)",
        "type":    "list_of_dicts",
        "category": "Visualization",
    },
    "overlay_absorption": {
        "label":   "Overlay Absorption",
        "tooltip": "Calculate ground-state absorbance from Blank/Transmission and plot on a secondary axis behind EA",
        "category": "Visualization",
    },
}