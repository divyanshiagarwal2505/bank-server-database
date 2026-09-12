"""
Multi-threaded TCP Banking Server.
"""
import socketserver
import threading
import logging
from typing import Optional

from server.request_handler import BankRequestHandler

logger = logging.getLogger("BankTCPServer")


class _ThreadedTCPRequestHandler(socketserver.BaseRequestHandler):
    """Handles individual client socket connections in a separate thread."""

    def handle(self):
        handler: BankRequestHandler = self.server.request_handler  # type: ignore
        client_address = self.client_address
        logger.info(f"Client connected from {client_address[0]}:{client_address[1]}")

        # Buffer for incoming socket data stream
        buffer = ""
        while True:
            try:
                chunk = self.request.recv(4096)
                if not chunk:
                    break

                buffer += chunk.decode("utf-8")
                while "\n" in buffer:
                    line, buffer = buffer.split("\n", 1)
                    line = line.strip()
                    if not line:
                        continue

                    response = handler.handle_request(line)
                    self.request.sendall((response + "\n").encode("utf-8"))

            except ConnectionResetError:
                break
            except Exception as ex:
                logger.error(f"Error handling connection {client_address}: {ex}")
                break

        logger.info(f"Client {client_address} disconnected.")


class BankTCPServer(socketserver.ThreadingTCPServer):
    """
    Production-grade threaded TCP server.
    """
    allow_reuse_address = True
    daemon_threads = True

    def __init__(self, host: str, port: int, request_handler: BankRequestHandler):
        self.request_handler = request_handler
        super().__init__((host, port), _ThreadedTCPRequestHandler)
        self._is_running = False
        self._server_thread: Optional[threading.Thread] = None

    def start_background(self) -> None:
        """Starts server listening in background thread."""
        self._is_running = True
        self._server_thread = threading.Thread(target=self.serve_forever, daemon=True)
        self._server_thread.start()
        logger.info(f"SecureBank Server active on {self.server_address[0]}:{self.server_address[1]}")

    def stop(self) -> None:
        """Gracefully shuts down the server."""
        if self._is_running:
            logger.info("Shutting down SecureBank Server...")
            self.shutdown()
            self.server_close()
            self._is_running = False
            logger.info("Server stopped.")
