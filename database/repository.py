"""
Persistence repository implementing ABSTRACTION and POLYMORPHISM.

Hierarchy:
BankRepository (Abstract Base Class)
  ├── InMemoryBankRepository (Fast volatile test double)
  └── SQLiteBankRepository (Production-grade persistent SQL storage)
"""
from abc import ABC, abstractmethod
import sqlite3
import threading
import contextlib
from datetime import datetime
from typing import Optional, List, Dict, Any, Generator

from core.enums import AccountType, Currency, TransactionStatus
from models.account import Account
from models.savings_account import SavingsAccount
from models.checking_account import CheckingAccount
from models.business_account import BusinessAccount
from models.customer import Customer
from models.transaction import Transaction


class BankRepository(ABC):
    """
    [OOP Pillar: ABSTRACTION]
    Defines the persistence contract for banking storage engines.
    """

    @abstractmethod
    def save_customer(self, customer: Customer) -> None:
        pass

    @abstractmethod
    def get_customer(self, customer_id: str) -> Optional[Customer]:
        pass

    @abstractmethod
    def get_customer_by_email(self, email: str) -> Optional[Customer]:
        pass

    @abstractmethod
    def save_account(self, account: Account) -> None:
        pass

    @abstractmethod
    def get_account(self, account_number: str) -> Optional[Account]:
        pass

    @abstractmethod
    def get_accounts_by_customer(self, customer_id: str) -> List[Account]:
        pass

    @abstractmethod
    def save_transaction(self, transaction: Transaction) -> None:
        pass

    @abstractmethod
    def get_transactions_for_account(self, account_number: str, limit: int = 50) -> List[Dict[str, Any]]:
        pass


class InMemoryBankRepository(BankRepository):
    """
    [OOP Pillar: INHERITANCE & POLYMORPHISM]
    Volatile in-memory dictionary-backed repository for rapid unit testing.
    """

    def __init__(self):
        self._customers: Dict[str, Customer] = {}
        self._accounts: Dict[str, Account] = {}
        self._transactions: List[Dict[str, Any]] = []
        self._lock = threading.RLock()

    def save_customer(self, customer: Customer) -> None:
        with self._lock:
            self._customers[customer.customer_id] = customer

    def get_customer(self, customer_id: str) -> Optional[Customer]:
        with self._lock:
            return self._customers.get(customer_id)

    def get_customer_by_email(self, email: str) -> Optional[Customer]:
        with self._lock:
            for cust in self._customers.values():
                if cust.email.lower() == email.lower():
                    return cust
            return None

    def save_account(self, account: Account) -> None:
        with self._lock:
            self._accounts[account.account_number] = account

    def get_account(self, account_number: str) -> Optional[Account]:
        with self._lock:
            return self._accounts.get(account_number)

    def get_accounts_by_customer(self, customer_id: str) -> List[Account]:
        with self._lock:
            return [acc for acc in self._accounts.values() if acc.customer_id == customer_id]

    def save_transaction(self, transaction: Transaction) -> None:
        with self._lock:
            self._transactions.append(transaction.to_dict())

    def get_transactions_for_account(self, account_number: str, limit: int = 50) -> List[Dict[str, Any]]:
        with self._lock:
            matches = [
                tx for tx in self._transactions
                if tx["source_account"] == account_number or tx["destination_account"] == account_number
            ]
            return matches[-limit:]


class SQLiteBankRepository(BankRepository):
    """
    [OOP Pillar: INHERITANCE & POLYMORPHISM]
    Thread-safe SQLite persistent database repository.
    """

    def __init__(self, db_path: str = "bank_server.db"):
        self._db_path = db_path
        self._lock = threading.RLock()
        self._init_db()

    @contextlib.contextmanager
    def _get_connection(self) -> Generator[sqlite3.Connection, None, None]:
        conn = sqlite3.connect(self._db_path, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
        finally:
            conn.close()

    def _init_db(self) -> None:
        """Initializes database schema if not already created."""
        with self._lock, self._get_connection() as conn:
            cursor = conn.cursor()

            # Customers table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS customers (
                    customer_id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    email TEXT UNIQUE NOT NULL,
                    phone TEXT NOT NULL,
                    pin_hash TEXT NOT NULL,
                    salt TEXT NOT NULL,
                    created_at TEXT NOT NULL
                )
            """)

            # Accounts table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS accounts (
                    account_number TEXT PRIMARY KEY,
                    customer_id TEXT NOT NULL,
                    account_type TEXT NOT NULL,
                    balance REAL NOT NULL,
                    currency TEXT NOT NULL,
                    is_active INTEGER NOT NULL,
                    created_at TEXT NOT NULL,
                    extra_data TEXT,
                    FOREIGN KEY(customer_id) REFERENCES customers(customer_id)
                )
            """)

            # Transactions table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS transactions (
                    transaction_id TEXT PRIMARY KEY,
                    transaction_type TEXT NOT NULL,
                    amount REAL NOT NULL,
                    description TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    status TEXT NOT NULL,
                    source_account TEXT,
                    destination_account TEXT,
                    error_message TEXT
                )
            """)

            # Audit logs table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS audit_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    event_type TEXT NOT NULL,
                    entity_id TEXT NOT NULL,
                    details TEXT NOT NULL
                )
            """)

            conn.commit()

    def save_customer(self, customer: Customer) -> None:
        creds = customer.export_credentials()
        with self._lock, self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO customers (customer_id, name, email, phone, pin_hash, salt, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(customer_id) DO UPDATE SET
                    name=excluded.name,
                    email=excluded.email,
                    phone=excluded.phone,
                    pin_hash=excluded.pin_hash,
                    salt=excluded.salt
            """, (
                customer.customer_id,
                customer.name,
                customer.email,
                customer.phone,
                creds["pin_hash"],
                creds["salt"],
                customer.created_at.isoformat(),
            ))
            conn.commit()

    def get_customer(self, customer_id: str) -> Optional[Customer]:
        with self._lock, self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM customers WHERE customer_id = ?", (customer_id,))
            row = cursor.fetchone()
            if not row:
                return None
            return self._row_to_customer(row, conn)

    def get_customer_by_email(self, email: str) -> Optional[Customer]:
        with self._lock, self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM customers WHERE LOWER(email) = LOWER(?)", (email,))
            row = cursor.fetchone()
            if not row:
                return None
            return self._row_to_customer(row, conn)

    def _row_to_customer(self, row: sqlite3.Row, conn: sqlite3.Connection) -> Customer:
        cursor = conn.cursor()
        cursor.execute("SELECT account_number FROM accounts WHERE customer_id = ?", (row["customer_id"],))
        acc_rows = cursor.fetchall()
        account_ids = [r["account_number"] for r in acc_rows]

        return Customer(
            customer_id=row["customer_id"],
            name=row["name"],
            email=row["email"],
            phone=row["phone"],
            pin_hash=row["pin_hash"],
            salt=row["salt"],
            created_at=datetime.fromisoformat(row["created_at"]),
            account_ids=account_ids,
        )

    def save_account(self, account: Account) -> None:
        import json
        extra: Dict[str, Any] = {}
        if isinstance(account, SavingsAccount):
            extra["interest_rate"] = account.interest_rate
            extra["minimum_balance"] = account.minimum_balance
        elif isinstance(account, CheckingAccount):
            extra["overdraft_limit"] = account.overdraft_limit
            extra["overdraft_fee"] = account.overdraft_fee
        elif isinstance(account, BusinessAccount):
            extra["company_name"] = account.company_name
            extra["tax_id"] = account.raw_tax_id

        with self._lock, self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO accounts (account_number, customer_id, account_type, balance, currency, is_active, created_at, extra_data)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(account_number) DO UPDATE SET
                    balance=excluded.balance,
                    is_active=excluded.is_active,
                    extra_data=excluded.extra_data
            """, (
                account.account_number,
                account.customer_id,
                account.get_account_type().value,
                account.balance,
                account.currency.value,
                1 if account.is_active else 0,
                account.created_at.isoformat(),
                json.dumps(extra),
            ))
            conn.commit()

    def get_account(self, account_number: str) -> Optional[Account]:
        with self._lock, self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM accounts WHERE account_number = ?", (account_number,))
            row = cursor.fetchone()
            if not row:
                return None
            return self._row_to_account(row)

    def get_accounts_by_customer(self, customer_id: str) -> List[Account]:
        with self._lock, self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM accounts WHERE customer_id = ?", (customer_id,))
            rows = cursor.fetchall()
            return [self._row_to_account(r) for r in rows]

    def _row_to_account(self, row: sqlite3.Row) -> Account:
        """Polymorphic factory instantiating the right concrete Account subclass."""
        import json
        acc_type = row["account_type"]
        extra = json.loads(row["extra_data"] or "{}")
        created_at = datetime.fromisoformat(row["created_at"])
        is_active = bool(row["is_active"])

        if acc_type == AccountType.SAVINGS.value:
            return SavingsAccount(
                account_number=row["account_number"],
                customer_id=row["customer_id"],
                initial_balance=row["balance"],
                interest_rate=extra.get("interest_rate", SavingsAccount.DEFAULT_INTEREST_RATE),
                minimum_balance=extra.get("minimum_balance", SavingsAccount.DEFAULT_MINIMUM_BALANCE),
                currency=Currency(row["currency"]),
                created_at=created_at,
                is_active=is_active,
            )
        elif acc_type == AccountType.CHECKING.value:
            return CheckingAccount(
                account_number=row["account_number"],
                customer_id=row["customer_id"],
                initial_balance=row["balance"],
                overdraft_limit=extra.get("overdraft_limit", CheckingAccount.DEFAULT_OVERDRAFT_LIMIT),
                overdraft_fee=extra.get("overdraft_fee", CheckingAccount.DEFAULT_OVERDRAFT_FEE),
                currency=Currency(row["currency"]),
                created_at=created_at,
                is_active=is_active,
            )
        elif acc_type == AccountType.BUSINESS.value:
            return BusinessAccount(
                account_number=row["account_number"],
                customer_id=row["customer_id"],
                company_name=extra.get("company_name", "Enterprise Client"),
                tax_id=extra.get("tax_id", "00-0000000"),
                initial_balance=row["balance"],
                currency=Currency(row["currency"]),
                created_at=created_at,
                is_active=is_active,
            )
        else:
            raise ValueError(f"Unknown account type stored in database: {acc_type}")

    def save_transaction(self, transaction: Transaction) -> None:
        data = transaction.to_dict()
        with self._lock, self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO transactions (
                    transaction_id, transaction_type, amount, description,
                    timestamp, status, source_account, destination_account, error_message
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                data["transaction_id"],
                data["type"],
                data["amount"],
                data["description"],
                data["timestamp"],
                data["status"],
                data["source_account"],
                data["destination_account"],
                data["error_message"],
            ))
            conn.commit()

    def get_transactions_for_account(self, account_number: str, limit: int = 50) -> List[Dict[str, Any]]:
        with self._lock, self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM transactions
                WHERE source_account = ? OR destination_account = ?
                ORDER BY timestamp DESC
                LIMIT ?
            """, (account_number, account_number, limit))
            rows = cursor.fetchall()
            return [dict(r) for r in rows]
