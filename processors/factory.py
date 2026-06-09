from typing import Optional
from utils.app_logger import logger # Import the global logger

def get_processor(tech: str, parent_window):
    """Factory to instantiate the correct processor based on the technique name."""
    if not tech:
        # Fallback for empty selections or folders
        from processors.abs_processor import ABSProcessor
        return ABSProcessor(parent_window)

    tech_lower = tech.lower()
    
    # Mapping tech keywords to specific processor classes
    mapping = {
        "ea voltage series": ("processors.ea_processor", "EAProcessor"),
        "absorption": ("processors.abs_processor", "ABSProcessor"),
        "abs temp series": ("processors.abs_temp_processor", "ABSTempProcessor"),
        "ea temp series": ("processors.ea_temp_processor", "EATempProcessor"),
    }

    for key, (module_path, class_name) in mapping.items():
        if key in tech_lower:
            try:
                module = __import__(module_path, fromlist=[class_name])
                processor_class = getattr(module, class_name)
                return processor_class(parent_window)
            except (ImportError, AttributeError) as e:
                logger.error(f"Error loading processor '{class_name}' for technique '{tech}': {e}")
                break
    
    # Default fallback
    from processors.abs_processor import ABSProcessor
    return ABSProcessor(parent_window)