"""
Automated end-to-end verification script.
Spawns the BankTCPServer in background, executes the full client banking workflow,
verifies all OOP pillars in action, and shuts down gracefully.
"""
import sys
import os
import time
import logging

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from database.repository import SQLiteBankRepository
from notifications.notifier import CompositeNotifier, ConsoleAuditNotifier, EmailNotifier, SMSNotifier
from services.bank_service import BankService
from services.auth_service import AuthService
from server.request_handler import BankRequestHandler
from server.bank_server import BankTCPServer
from client.cli_client import BankClient
from client_main import run_automated_demo


def main():
    logging.basicConfig(level=logging.WARNING)
    print("=" * 65)
    print("     STARTING SECURE BANK LIVE SERVER & CLIENT TEST")
    print("=" * 65)

    test_db = os.path.join(os.path.dirname(os.path.abspath(__file__)), "bank_server.db")
    host = "127.0.0.1"
    port = 9998  # Isolated port for automated test run

    # Wire up server components
    repo = SQLiteBankRepository(db_path=test_db)
    notifier = CompositeNotifier([ConsoleAuditNotifier(), EmailNotifier(), SMSNotifier()])
    bank_service = BankService(repository=repo, notifier=notifier)
    auth_service = AuthService(repository=repo)
    handler = BankRequestHandler(bank_service=bank_service, auth_service=auth_service)
    server = BankTCPServer(host=host, port=port, request_handler=handler)

    print(f"[*] Starting server on {host}:{port} in background...")
    server.start_background()
    time.sleep(0.5)

    client = BankClient(host=host, port=port)
    try:
        print("[*] Connecting client to server...")
        client.connect()
        ping_res = client.ping()
        print(f"[+] Server responded: {ping_res}")

        # Run full automated OOP showcase
        run_automated_demo(client)

        print("\n" + "=" * 65)
        print("  ALL LIVE SERVER CALLS AND OOP DEMOS COMPLETED SUCCESSFULLY!")
        print("=" * 65)

    finally:
        client.disconnect()
        print("[*] Stopping server...")
        server.stop()


if __name__ == "__main__":
    main()
