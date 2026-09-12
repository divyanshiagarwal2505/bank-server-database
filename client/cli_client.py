"""
Network client for interacting with the SecureBank TCP server.
Provides programmatic client interface and formatted command-line interaction.
"""
import socket
import json
from typing import Dict, Any, Optional


class BankClient:
    """
    Client helper connecting to the SecureBank TCP server over socket.
    Encapsulates connection state and active auth token.
    """

    def __init__(self, host: str = "127.0.0.1", port: int = 9999):
        self._host = host
        self._port = port
        self._socket: Optional[socket.socket] = None
        self._token: Optional[str] = None
        self._customer_data: Optional[Dict[str, Any]] = None

    @property
    def token(self) -> Optional[str]:
        return self._token

    @property
    def current_user(self) -> Optional[Dict[str, Any]]:
        return self._customer_data

    def connect(self) -> None:
        """Establishes TCP connection to the bank server."""
        self._socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._socket.connect((self._host, self._port))

    def disconnect(self) -> None:
        """Closes TCP socket connection."""
        if self._socket:
            try:
                self._socket.close()
            except Exception:
                pass
            self._socket = None

    def send_command(self, action: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Sends formatted JSON request and returns parsed JSON response.
        Automatically reconnects if socket was closed.
        """
        if not self._socket:
            self.connect()

        payload = {
            "action": action,
            "params": params or {},
            "token": self._token,
        }

        raw_req = json.dumps(payload) + "\n"
        self._socket.sendall(raw_req.encode("utf-8"))

        # Read response line
        buffer = ""
        while "\n" not in buffer:
            chunk = self._socket.recv(4096)
            if not chunk:
                raise ConnectionError("Connection terminated by bank server")
            buffer += chunk.decode("utf-8")

        resp_line, _ = buffer.split("\n", 1)
        return json.loads(resp_line.strip())

    # -------------------------------------------------------------------------
    # High-level Client Actions
    # -------------------------------------------------------------------------
    def ping(self) -> Dict[str, Any]:
        return self.send_command("PING")

    def register(self, name: str, email: str, phone: str, pin: str) -> Dict[str, Any]:
        return self.send_command("REGISTER", {
            "name": name,
            "email": email,
            "phone": phone,
            "pin": pin,
        })

    def login(self, email: str, pin: str) -> Dict[str, Any]:
        resp = self.send_command("LOGIN", {"email": email, "pin": pin})
        if resp.get("status") == "SUCCESS":
            self._token = resp["data"]["token"]
            self._customer_data = resp["data"]["customer"]
        return resp

    def logout(self) -> Dict[str, Any]:
        resp = self.send_command("LOGOUT")
        self._token = None
        self._customer_data = None
        return resp

    def open_account(
        self,
        account_type: str,
        initial_deposit: float = 0.0,
        currency: str = "USD",
        extra_params: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        return self.send_command("OPEN_ACCOUNT", {
            "account_type": account_type,
            "initial_deposit": initial_deposit,
            "currency": currency,
            "extra_params": extra_params or {},
        })

    def get_accounts(self) -> Dict[str, Any]:
        return self.send_command("GET_ACCOUNTS")

    def deposit(self, account_number: str, amount: float, description: str = "Deposit") -> Dict[str, Any]:
        return self.send_command("DEPOSIT", {
            "account_number": account_number,
            "amount": amount,
            "description": description,
        })

    def withdraw(self, account_number: str, amount: float, description: str = "Withdrawal") -> Dict[str, Any]:
        return self.send_command("WITHDRAW", {
            "account_number": account_number,
            "amount": amount,
            "description": description,
        })

    def transfer(
        self,
        source_account: str,
        destination_account: str,
        amount: float,
        description: str = "Transfer",
    ) -> Dict[str, Any]:
        return self.send_command("TRANSFER", {
            "source_account": source_account,
            "destination_account": destination_account,
            "amount": amount,
            "description": description,
        })

    def apply_interest(self, account_number: str) -> Dict[str, Any]:
        return self.send_command("APPLY_INTEREST", {"account_number": account_number})

    def get_statement(self, account_number: str, limit: int = 10) -> Dict[str, Any]:
        return self.send_command("GET_STATEMENT", {
            "account_number": account_number,
            "limit": limit,
        })
