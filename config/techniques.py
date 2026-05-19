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
            "smooth_data",
            "convert_to_ev",
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
            "smooth_data",
            "convert_to_ev",
            "normalize_to_peak",
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
            "smooth_data",
            "flip_sign",
            "convert_to_ev",
            "show_colorbar",
            "colormap_name",
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
            "active_scan_types": ["Voltage"],
        },
        "analysis_options": [
            "smooth_data",
            "flip_sign",
            "convert_to_ev",
            "normalize_to_peak",
            "show_legend",
            "show_colorbar",
            "colormap_name",
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
        "tooltip": "Apply Savitzky-Golay smoothing (window 11, poly 3) to reduce noise",
    },
    "flip_y": {
        "label":   "Flip Y-axis",
        "tooltip": "Invert the y-axis — multiply all y values by −1",
    },
    "flip_sign": {
        "label":   "Flip Sign",
        "tooltip": "Flip the sign of the differential signal (EA-specific)",
    },
    "convert_to_ev": {
        "label":   "nm → eV",
        "tooltip": "Convert the wavelength axis to photon energy using E = 1240 / λ (nm)",
    },
    "normalize_to_peak": {
        "label":   "Normalize to Peak",
        "tooltip": "Scale each trace so its absolute maximum equals 1",
    },
    "offset_traces": {
        "label":   "Offset Traces",
        "tooltip": "Add an incremental vertical offset between overlaid traces for clarity",
    },
    "show_legend": {
        "label":   "Legend",
        "tooltip": "Display a legend labelling each trace",
    },
    "show_colorbar": {
        "label":   "Colorbar",
        "tooltip": "Toggle the intensity/temperature colorbar on the right",
    },
    "colormap_name": {
        "label":   "Color",
        "tooltip": "Select a color gradient for plotting multiple traces in a series.",
        "type":    "combo",
        "options": COLOR_GRADIENTS,
    },
}