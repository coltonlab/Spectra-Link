from .base_engine import BaseModelingEngine
from .fk_engine import FKModelingEngine
from .k_analysis_engine import KAnalysisEngine

def get_available_models(technique: str) -> dict[str, type[BaseModelingEngine]]:
    """
    Returns a dictionary of available modeling engines (name -> class)
    for a given experiment technique.
    """
    engines = {
        "EA Voltage Series": {
            "K-Analysis": KAnalysisEngine,
            "Franz-Keldysh": FKModelingEngine, # Example: FK could also apply here
        },
        "EA Temp Series": {
            "K-Analysis": KAnalysisEngine,
        },
        "Electro-Absorption": {
            "Franz-Keldysh": FKModelingEngine,
        },
    }
    return engines.get(technique, {})

def create_modeling_engine(model_name: str, technique: str, parent_tab) -> BaseModelingEngine | None:
    """
    Instantiates a specific modeling engine by its name and technique.
    """
    available_models = get_available_models(technique)
    engine_class = available_models.get(model_name)
    if engine_class:
        return engine_class(parent_tab)
    return None