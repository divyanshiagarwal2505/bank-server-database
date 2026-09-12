"""
Main server launcher for SecureBank OOP Server.
Initializes SQLite database, dependency injection wiring, and starts multi-threaded TCP listener.
"""
import sys
import os
import signal
import logging
import time

# Ensure project root is in sys.path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from database.repository import SQLiteBankRepository
from notifications.notifier import (
    CompositeNotifier,
    ConsoleAuditNotifier,
    EmailNotifier,
    SMSNotifier,
)
from services.bank_service import BankService
from services.auth_service import AuthService
from server.request_handler import BankRequestHandler
from server.bank_server import BankTCPServer


def setup_logging():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] [%(name)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )


def print_banner(host: str, port: int, db_path: str):
    banner = f"""
========================================================================
                  SECURE BANK - OOP ENTERPRISE SERVER                  
========================================================================
  Host:            {host}
  Port:            {port}
  Database:        {db_path} (SQLite)
  OOP Principles:
    - Encapsulation:  Private hashes, property getters, balance guards
    - Abstraction:    Abstract base Account, Transaction, Repository
    - Inheritance:    Specialized Savings, Checking, Business accounts
    - Polymorphism:   Overdraft & fee policies, polymorphic transactions
========================================================================
 Server is listening for TCP connections... Press Ctrl+C to terminate.
========================================================================
"""
    print(banner)


def main():
    setup_logging()
    logger = logging.getLogger("Main")

    host = "127.0.0.1"
    port = 9999
    db_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "bank_server.db")

    logger.info("Initializing persistence layer (SQLite)...")
    repository = SQLiteBankRepository(db_path=db_file)

    logger.info("Configuring polymorphic notification composite...")
    notifier = CompositeNotifier([
        ConsoleAuditNotifier(),
        EmailNotifier(smtp_host="smtp.securebank.com"),
        SMSNotifier(sender_id="BANK_ALERT"),
    ])

    logger.info("Wired business services (BankService & AuthService)...")
    bank_service = BankService(repository=repository, notifier=notifier)
    auth_service = AuthService(repository=repository)

    logger.info("Initializing request router...")
    request_handler = BankRequestHandler(bank_service=bank_service, auth_service=auth_service)

    server = BankTCPServer(host=host, port=port, request_handler=request_handler)
    print_banner(host, port, db_file)

    def shutdown_handler(signum, frame):
        logger.info("Shutdown signal received. Stopping server...")
        server.stop()
        sys.exit(0)

    signal.signal(signal.SIGINT, shutdown_handler)
    signal.signal(signal.SIGTERM, shutdown_handler)

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        logger.info("Server received keyboard interrupt.")
    finally:
        server.stop()


if __name__ == "__main__":
    main()
