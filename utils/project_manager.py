import os
import json
from pathlib import Path
from utils.app_logger import logger # Import the global logger

class ProjectManager:
    """Handles all file system operations and JSON data integrity."""

    class Session:
        """In-memory state for the currently active experiment."""
        _current_path: Path | None = None
        _cached_data: dict = {}

        @classmethod
        def load_experiment(cls, json_path: Path) -> dict:
            """Loads a new experiment into the active session."""
            cls._current_path = json_path
            cls._cached_data = ProjectManager.read_json(json_path)
            return cls._cached_data

        @classmethod
        def clear(cls):
            """Resets the active session."""
            cls._current_path = None
            cls._cached_data = {}

        @classmethod
        def get_data(cls) -> dict:
            """Retrieves the current session data."""
            return cls._cached_data

        @classmethod
        def get_path(cls) -> Path | None:
            """Retrieves the current session file path."""
            return cls._current_path

        @classmethod
        def save(cls) -> bool:
            """Persists the current in-memory data to disk."""
            if cls._current_path:
                return ProjectManager.write_json(cls._current_path, cls._cached_data)
            return False

    @staticmethod
    def list_folders(path: Path) -> list[str]:
        """Returns sorted directory names, excluding hidden ones."""
        if not path.exists():
            return []
        try:
            return sorted([e.name for e in os.scandir(path) 
                           if e.is_dir() and not e.name.startswith('.')])
        except Exception as e:
            logger.error(f"Error listing folders in {path}: {e}")
            return []

    @staticmethod
    def list_experiments(json_dir: Path) -> list[str]:
        """Returns stems of all .json files in a directory."""
        if not json_dir.exists():
            return []
        return sorted([f.stem for f in json_dir.glob("*.json")])

    @staticmethod
    def read_json(path: Path) -> dict:
        """Safely reads a JSON file; returns empty dict on failure."""
        if not path or not path.exists():
            return {}
        try:
            with open(path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Error reading JSON from {path}: {e}")
            return {}

    @staticmethod
    def write_json(path: Path, data: dict) -> bool:
        """Writes a dictionary to a JSON file with standard indentation."""
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            with open(path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=4)
            logger.debug(f"JSON written to {path}")
            return True
        except Exception as e:
            logger.error(f"Error writing JSON to {path}: {e}")
            return False

    @staticmethod
    def create_experiment_template(path: Path, name: str, technique: str) -> bool:
        """Initializes a new experiment JSON file if it doesn't already exist."""
        if path.exists():
            return False
        template = {
            "core": {
                "experiment_name": name,
                "technique": technique,
                "schema_version": "1.0.0"
            },
            "data_files": {},
            "parameters": {"temperature": 295.0},
            "modeling": {"saved_results": {}}
        }
        return ProjectManager.write_json(path, template)

    @staticmethod
    def rename_path(old_path: Path, new_name: str) -> Path:
        """Renames a file or folder and returns the new Path object."""
        new_path = old_path.parent / new_name.strip()
        old_path.rename(new_path)
        logger.info(f"Renamed '{old_path}' to '{new_path}'")
        return new_path


    @staticmethod
    def create_folder(path: Path, parents: bool = True, exist_ok: bool = True) -> bool:
        """Creates a directory and its parents if they don't exist."""
        try:
            path.mkdir(parents=parents, exist_ok=exist_ok)
            logger.debug(f"Folder created: {path}")
            return True
        except Exception as e:
            logger.error(f"Error creating folder {path}: {e}")
            return False

    @staticmethod
    def delete_file(path: Path) -> bool:
        """Deletes a file if it exists."""
        try:
            path.unlink(missing_ok=True)
            logger.info(f"File deleted: {path}")
            return True
        except Exception as e:
            logger.error(f"Error deleting file {path}: {e}")
            return False

    @staticmethod
    def delete_folder(path: Path) -> bool:
        """Deletes an empty folder."""
        # For now, only delete if empty. Recursive deletion is dangerous.
        # Consider adding a check for emptiness or a more robust shutil.rmtree wrapper.
        try:
            path.rmdir()
            logger.info(f"Folder deleted: {path}")
            return True
        except OSError as e: # Directory not empty or doesn't exist
            logger.error(f"Error deleting folder {path}: {e}")
            return False