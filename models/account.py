"""
Abstract base class representing a generic Bank Account.

Demonstrates:
  - ABSTRACTION: Defines the contract that all concrete account types must honor.
    Direct instantiation of Account is blocked by ABC.
  - ENCAPSULATION: Protects internal state (_balance, _account_number, __transaction_history)
    behind property getters and controlled domain mutation methods.
"""
from abc import ABC, abstractmethod
from datetime import datetime
import threading
from typing import List, Dict, Any, Optional

from core.enums import AccountType, Currency
from core.exceptions import InvalidAmountError, AccountLockedError


class Account(ABC):
    """
    [OOP Pillar: ABSTRACTION]
    Abstract base class establishing the blueprint for all bank account variations.
    Cannot be instantiated directly.
    """

    def __init__(
        self,
        account_number: str,
        customer_id: str,
        initial_balance: float = 0.0,
        currency: Currency = Currency.USD,
        created_at: Optional[datetime] = None,
        is_active: bool = True,
        allow_negative: bool = False,
    ):
        """
        [OOP Pillar: ENCAPSULATION]
        Protected attributes (prefixed with _) allow derived classes to access internal state
        responsibly while preventing external consumers from mutating values directly.
        """
        if initial_balance < 0 and not allow_negative:
            raise InvalidAmountError("Initial account balance cannot be negative")

        self._account_number: str = account_number
        self._customer_id: str = customer_id
        self._balance: float = round(float(initial_balance), 2)
        self._currency: Currency = currency
        self._created_at: datetime = created_at or datetime.now()
        self._is_active: bool = is_active

        # Private attribute (name-mangled): internal transaction audit log
        self.__audit_trail: List[Dict[str, Any]] = []

        # Thread synchronization primitive for concurrency control
        self._lock = threading.RLock()

    # -------------------------------------------------------------------------
    # Encapsulated Property Accessors (Getters - Read-only external visibility)
    # -------------------------------------------------------------------------
    @property
    def account_number(self) -> str:
        """Read-only access to account identifier."""
        return self._account_number

    @property
    def customer_id(self) -> str:
        """Read-only access to owning customer ID."""
        return self._customer_id

    @property
    def balance(self) -> float:
        """
        [OOP Pillar: ENCAPSULATION]
        Controlled read-only access to current monetary balance.
        Balance cannot be directly mutated via `account.balance = 500`.
        Must use deposit() or withdraw().
        """
        with self._lock:
            return round(self._balance, 2)

    @property
    def currency(self) -> Currency:
        return self._currency

    @property
    def is_active(self) -> bool:
        return self._is_active

    @property
    def created_at(self) -> datetime:
        return self._created_at

    # -------------------------------------------------------------------------
    # State Management & Validation
    # -------------------------------------------------------------------------
    def lock_account(self, reason: str = "Admin security hold") -> None:
        """Freezes account operations."""
        with self._lock:
            self._is_active = False
            self._record_audit("ACCOUNT_LOCKED", 0.0, reason)

    def unlock_account(self) -> None:
        """Restores account operations."""
        with self._lock:
            self._is_active = True
            self._record_audit("ACCOUNT_UNLOCKED", 0.0, "Account reinstated")

    def _ensure_active(self) -> None:
        """Internal guard ensuring operations are only performed on active accounts."""
        if not self._is_active:
            raise AccountLockedError(self._account_number)

    # -------------------------------------------------------------------------
    # Public Domain Methods
    # -------------------------------------------------------------------------
    def deposit(self, amount: float, description: str = "Standard deposit") -> float:
        """
        Universal deposit implementation.
        Validates amount invariants and atomically mutates balance.
        """
        if amount <= 0:
            raise InvalidAmountError(f"Deposit amount must be positive. Received: {amount}")

        with self._lock:
            self._ensure_active()
            self._balance = round(self._balance + amount, 2)
            self._record_audit("DEPOSIT", amount, description)
            return self._balance

    # -------------------------------------------------------------------------
    # [OOP Pillar: ABSTRACTION] Abstract Contract Methods
    # Every concrete subclass MUST implement these according to its business rules.
    # -------------------------------------------------------------------------
    @abstractmethod
    def withdraw(self, amount: float, description: str = "Standard withdrawal") -> float:
        """
        Subclasses must implement withdrawal according to their distinct rules
        (e.g., overdraft allowances, minimum balances, withdrawal limits).
        """
        pass

    @abstractmethod
    def calculate_interest(self) -> float:
        """
        Subclasses must calculate periodic interest based on account-type formulas.
        """
        pass

    @abstractmethod
    def get_account_type(self) -> AccountType:
        """Returns the specific AccountType enum."""
        pass

    # -------------------------------------------------------------------------
    # Internal Encapsulated Utilities
    # -------------------------------------------------------------------------
    def _record_audit(self, action: str, amount: float, note: str) -> None:
        """Protected helper to record in-memory audit logs."""
        self.__audit_trail.append({
            "timestamp": datetime.now().isoformat(),
            "action": action,
            "amount": amount,
            "resulting_balance": self._balance,
            "note": note,
        })

    def get_audit_trail(self) -> List[Dict[str, Any]]:
        """Returns a shallow copy of internal audit entries (defensive copy)."""
        with self._lock:
            return list(self.__audit_trail)

    def to_dict(self) -> Dict[str, Any]:
        """Serializes account state for persistence or network transport."""
        with self._lock:
            return {
                "account_number": self._account_number,
                "customer_id": self._customer_id,
                "balance": self._balance,
                "currency": self._currency.value if hasattr(self._currency, "value") else str(self._currency),
                "account_type": self.get_account_type().value,
                "is_active": self._is_active,
                "created_at": self._created_at.isoformat(),
            }

    def __repr__(self) -> str:
        return (
            f"<{self.__class__.__name__} "
            f"no={self._account_number} "
            f"bal={self.balance:.2f} {self._currency}>"
        )
