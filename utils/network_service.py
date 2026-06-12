import socket
import platform
import sys
import os
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
            # Robustly extract hostname regardless of slash direction (\ or /)
            normalized = host.replace('\\', '/')
            host_ip = normalized.strip('/').split('/')[0]
            try:
                # Revert to standard timeout
                with socket.create_connection((host_ip, 445), timeout=0.2):
                    valid_hosts.append(host)
            except (socket.timeout, ConnectionRefusedError, OSError):
                logger.debug(f"Host {host_ip} not reachable on port 445.")
        return valid_hosts

    @staticmethod
    def resolve_base_dir(raw_path: str, is_remote: bool) -> Path:
        """Resolves the 'Data' folder path based on OS and connection mode."""
        if not is_remote or not raw_path:
            # Match the logic in main.py for local resolution
            if sys.platform == "win32":
                lab_root = Path("C:/Data")
                if lab_root.exists():
                    return lab_root

            # Portable check
            exe_dir = Path(os.path.abspath(os.path.dirname(sys.argv[0])))
            if (exe_dir / "Data").exists():
                return exe_dir / "Data"

            # Fallback to a standard location in Documents
            # Note: We use a hardcoded string here because importing QStandardPaths 
            # into this service would add a heavy dependency on PyQt.
            user_docs = Path(os.path.expanduser("~")) / "Documents"
            return user_docs / "SpectraLink_Data"
            
        if platform.system() == "Darwin":
            # On Mac, UNC paths are typically mounted as volumes
            normalized = raw_path.replace('\\', '/')
            share_name = normalized.split('/')[-1]
            return Path("/Volumes") / share_name / "Data"
        
        return Path(raw_path) / "Data"