import logging
import os
import signal
import subprocess

from premsql.logger import setup_console_logger

logger = setup_console_logger("[BACKEND-UTILS]")


def stop_server_on_port(port: int):
    try:
        result = subprocess.run(
            ["lsof", "-ti", f":{port}"], capture_output=True, text=True
        )
        if result.returncode == 0:
            pid = int(result.stdout.strip())
            os.kill(pid, signal.SIGTERM)
            logger.info(f"Server running on port {port} (PID {pid}) stopped.")
        else:
            logger.info(f"No server found running on port {port}")
    except subprocess.CalledProcessError:
        logger.info(f"No server found running on port {port}")
    except ProcessLookupError:
        logger.info(f"Process on port {port} no longer exists")
