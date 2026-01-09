import httpx
import socket
import uvicorn
from multiprocessing import Process
import time

def find_free_port():
    """Find a free port to use for testing"""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("", 0))
        return s.getsockname()[1]


class ServerManager:
    """Helper to manage test server lifecycle"""

    def __init__(self, app, port=None):
        self.app = app
        self.port = port or find_free_port()
        self.process = None
        self.base_url = f"http://127.0.0.1:{self.port}"

    def start(self):
        """Start server in background"""

        def run():
            uvicorn.run(
                app=self.app,
                host="127.0.0.1",
                port=self.port,
                log_level="error",
                access_log=False,
            )

        self.process = Process(target=run)
        self.process.start()
        self._wait_for_server()

    def _wait_for_server(self, timeout=10):
        """Wait for server to be ready"""
        start = time.time()
        while time.time() - start < timeout:
            try:
                httpx.get(f"{self.base_url}/", timeout=0.5)
                return
            except (httpx.RequestError, ConnectionError):
                time.sleep(0.1)
        raise TimeoutError(f"Server didn't start in {timeout} seconds")

    def stop(self):
        """Stop server"""
        if self.process:
            self.process.terminate()
            self.process.join(timeout=5)
            