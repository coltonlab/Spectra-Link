"""
Registry for Spectra-Link Modeling Dashboards.
This file maps experimental techniques to available modeling engines.
"""

from modeling_engines.dummy_dashboard import DummyDashboard
# Import future engines here as they are created
from modeling_engines.fk_modeling_dashboard import FKModelingDashboard
from modeling_engines.k_analysis.k_analysis_dashboard import KAnalysisDashboard
from modeling_engines.absorption_fitter_dashboard import AbsorptionFitterDashboard
from modeling_engines.ea_absorption_fitter_dashboard import EAAbsorptionFitterDashboard
from modeling_engines.abs_temp_fitter_dashboard import AbsorptionTempFitterDashboard
from modeling_engines.impedance_calibration_dashboard import ImpedanceCalibrationDashboard


# Mapping of techniques to a list of available dashboard classes.
# The ModelingTab UI will automatically prepend a "None" option to this list.
MODELING_REGISTRY = {
    "EA Voltage Series": [KAnalysisDashboard, FKModelingDashboard, EAAbsorptionFitterDashboard, DummyDashboard],
    "EA Temp Series": [FKModelingDashboard, EAAbsorptionFitterDashboard, DummyDashboard],
    "Absorption": [AbsorptionFitterDashboard, DummyDashboard],
    "ABS Temp Series": [AbsorptionTempFitterDashboard, DummyDashboard],
    "Impedance Calibration": [ImpedanceCalibrationDashboard, DummyDashboard],
    "Circular Dichroism (CD)": [],
    "Photoluminescence (PL)": []
}