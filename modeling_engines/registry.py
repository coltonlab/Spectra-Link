"""
Registry for Spectra-Link Modeling Dashboards.
This file maps experimental techniques to available modeling engines.
"""

from modeling_engines.dummy_dashboard import DummyDashboard
# Import future engines here as they are created
from modeling_engines.fk_modeling_dashboard import FKModelingDashboard
from modeling_engines.k_analysis.k_analysis_dashboard import KAnalysisDashboard


# Mapping of techniques to a list of available dashboard classes.
# The ModelingTab UI will automatically prepend a "None" option to this list.
MODELING_REGISTRY = {
    "EA Voltage Series": [KAnalysisDashboard, FKModelingDashboard, DummyDashboard],
    "EA Temp Series": [FKModelingDashboard, DummyDashboard],
    "Absorption": [DummyDashboard],
    "ABS Temp Series": [DummyDashboard],
    "Circular Dichroism (CD)": [],
    "Photoluminescence (PL)": []
}