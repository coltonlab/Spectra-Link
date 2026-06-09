import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path
import sys
import os

# Global logger instance for the SpectraLink application
logger = logging.getLogger("SpectraLink")

def setup_logging():
    """
    Configures the application-wide logger.
    Logs to a file (with rotation) and to the console.
    The log file is placed in a 'logs' directory next to the executable.
    """
    logger.setLevel(logging.INFO) # Default to INFO, can be changed later for DEBUG

    # Ensure logger doesn't add handlers multiple times if called more than once
    if not logger.handlers:
        # Determine the base path for logs (next to the executable)
        if getattr(sys, 'frozen', False): # Running in a PyInstaller bundle
            log_base_path = Path(sys.executable).parent
        else: # Running in development
            log_base_path = Path(__file__).parent.parent # Project root

        log_dir = log_base_path / "logs"
        log_dir.mkdir(parents=True, exist_ok=True)
        log_file_path = log_dir / "app.log"

        # File handler with rotation
        file_handler = RotatingFileHandler(
            log_file_path,
            maxBytes=10 * 1024 * 1024,  # 10 MB
            backupCount=5,              # Keep 5 backup logs
            encoding='utf-8'
        )
        file_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        file_handler.setFormatter(file_formatter)
        logger.addHandler(file_handler)

        # Console handler (for INFO and above, or all if debug)
        console_handler = logging.StreamHandler(sys.stdout)
        console_formatter = logging.Formatter('%(levelname)s: %(message)s')
        console_handler.setFormatter(console_formatter)
        logger.addHandler(console_handler)

        logger.info(f"Logging initialized. Log file: {log_file_path}")