import os 
import time
import signal
import subprocess
from typing import Optional, List

class ServerManager:
    def __init__(self) -> None:
        self.process = None
        self.config = {}
    
    def start(
        self,
        dsn_or_db_path: str,
        agent_name: str,
        config_path: Optional[str] = None,
        env_path: Optional[str] = None,
        include_tables: Optional[List[str]] = None,
        exclude_tables: Optional[List[str]] = None, 
        host: str = "127.0.0.1",
        port: str = 8500
    ):
        if self.process:
            print("Server is already running. Stop it first.")
            return
        
        # TODO: Need to change this command as a CLI command
        command = [
            "python3",
            "premsql/_inference_server/main.py",
            "--dsn_or_db_path", dsn_or_db_path,
            "--agent_name", agent_name,
            "--host", host,
            "--port", str(port)
        ]

        if config_path:
            command.extend(["--config_path", config_path])
        if env_path:
            command.extend(["--env_path", env_path])
        if include_tables:
            command.extend(["--include_tables"] + include_tables)
        if exclude_tables:
            command.extend(["--exclude_tables"] + exclude_tables)
        
        self.config = {
            "dsn_or_db_path": dsn_or_db_path,
            "agent_name": agent_name,
            "config_path": config_path,
            "env_path": env_path,
            "include_tables": include_tables,
            "exclude_tables": exclude_tables,
            "host": host,
            "port": port
        }

        self.process = subprocess.Popen(command)
        print(f"Server started with PID {self.process.pid}")
        time.sleep(2)

    def stop(self, port: Optional[int] = None):
        if port is None and not self.process:
            print("No server is running")
            return
        
        if port:
            try:
                # Use lsof to find the process using the specified port
                result = subprocess.run(['lsof', '-ti', f':{port}'], capture_output=True, text=True)
                if result.returncode == 0:
                    pid = int(result.stdout.strip())
                    os.kill(pid, signal.SIGTERM)
                    print(f"Server running on port {port} (PID {pid}) stopped.")
                else:
                    print(f"No server found running on port {port}")
            except subprocess.CalledProcessError:
                print(f"No server found running on port {port}")
        else:
            os.kill(self.process.pid, signal.SIGTERM)
            self.process.wait()
            print(f"Server with PID {self.process.pid} stopped.")
            self.process = None
    
    def restart(self):
        self.stop()
        self.start(**self.config)

    def is_running(self, port: Optional[int] = None):
        if port is not None:
            try:
                result = subprocess.run(['lsof', '-ti', f':{port}'], capture_output=True, text=True)
                return result.returncode == 0
            except subprocess.CalledProcessError:
                return False
        else:
            return self.process is not None and self.process.poll() is None
    