import socket
import platform
from pathlib import Path
from utils.app_logger import logger # Import the global logger

class NetworkService:
    """Handles scanning for lab computers and resolving network mount points."""
    
    LAB_HOSTS = [
        r"\\1.coltonlab.byu.edu\C$", 
        r"\\2.coltonlab.byu.edu\C$", 
        r"\\3.coltonlab.byu.edu\C$"
    ]

    @staticmethod
    def get_available_hosts() -> list[str]:
        """Pings the lab computers via SMB port 445 to see if they are online."""
        valid_hosts = []
        for host in NetworkService.LAB_HOSTS:
            host_ip = host.strip('\\').split('\\')[0]
            try:
                # Quick socket check to avoid UI hang
                with socket.create_connection((host_ip, 445), timeout=0.2):
                    valid_hosts.append(host)
            except (socket.timeout, ConnectionRefusedError, OSError):
                logger.debug(f"Host {host_ip} not reachable on port 445.")
        return valid_hosts

    @staticmethod
    def resolve_base_dir(raw_path: str, is_remote: bool) -> Path:
        """Resolves the 'Data' folder path based on OS and connection mode."""
        if not is_remote or not raw_path:
            # Import here to avoid circular dependency
            import sys
            import os
            try:
                base_path = sys._MEIPASS
            except AttributeError:
                base_path = os.path.dirname(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
            return Path(base_path) / "Data"
            
        if platform.system() == "Darwin":
            share_name = raw_path.split('\\')[-1]
            return Path("/Volumes") / share_name / "Data"
        
        return Path(raw_path) / "Data"