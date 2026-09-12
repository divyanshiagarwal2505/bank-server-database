"""
Transaction domain entities.

Demonstrates:
  - ABSTRACTION: Base abstract class Transaction defines execute(), rollback(), and audit interface.
  - INHERITANCE: DepositTransaction, WithdrawalTransaction, and TransferTransaction extend Transaction.
  - POLYMORPHISM: Each transaction class implements its own execution and compensation (rollback) logic.
  - ENCAPSULATION: Transaction state transitions (PENDING -> COMPLETED / FAILED) are strictly controlled.
"""
from abc import ABC, abstractmethod
from datetime import datetime
import uuid
from typing import Optional, Dict, Any, List

from core.enums import TransactionType, TransactionStatus
from core.exceptions import InvalidAmountError
from models.account import Account


class Transaction(ABC):
    """
    [OOP Pillar: ABSTRACTION]
    Abstract Base Class for all financial transactions.
    """

    def __init__(
        self,
        amount: float,
        description: str,
        transaction_id: Optional[str] = None,
        timestamp: Optional[datetime] = None,
        status: TransactionStatus = TransactionStatus.PENDING,
    ):
        if amount <= 0:
            raise InvalidAmountError("Transaction amount must be strictly greater than zero")

        self._transaction_id: str = transaction_id or f"TXN-{uuid.uuid4().hex[:10].upper()}"
        self._amount: float = round(float(amount), 2)
        self._description: str = description
        self._timestamp: datetime = timestamp or datetime.now()
        self._status: TransactionStatus = status
        self._error_message: Optional[str] = None

    # -------------------------------------------------------------------------
    # Encapsulated Property Getters
    # -------------------------------------------------------------------------
    @property
    def transaction_id(self) -> str:
        return self._transaction_id

    @property
    def amount(self) -> float:
        return self._amount

    @property
    def description(self) -> str:
        return self._description

    @property
    def timestamp(self) -> datetime:
        return self._timestamp

    @property
    def status(self) -> TransactionStatus:
        return self._status

    @property
    def error_message(self) -> Optional[str]:
        return self._error_message

    # -------------------------------------------------------------------------
    # State Transition Guards
    # -------------------------------------------------------------------------
    def _mark_completed(self) -> None:
        self._status = TransactionStatus.COMPLETED
        self._error_message = None

    def _mark_failed(self, error: str) -> None:
        self._status = TransactionStatus.FAILED
        self._error_message = error

    def _mark_rolled_back(self) -> None:
        self._status = TransactionStatus.ROLLED_BACK

    # -------------------------------------------------------------------------
    # [OOP Pillar: ABSTRACTION & POLYMORPHISM] Abstract Methods
    # -------------------------------------------------------------------------
    @abstractmethod
    def execute(self) -> bool:
        """Executes the financial transaction polymorphically."""
        pass

    @abstractmethod
    def rollback(self) -> bool:
        """Compensating action in case of downstream pipeline failures."""
        pass

    @abstractmethod
    def get_type(self) -> TransactionType:
        """Returns specific TransactionType enum."""
        pass

    @abstractmethod
    def get_source_account(self) -> Optional[str]:
        """Returns originating account number if applicable."""
        pass

    @abstractmethod
    def get_destination_account(self) -> Optional[str]:
        """Returns receiving account number if applicable."""
        pass

    @abstractmethod
    def get_affected_accounts(self) -> List[Account]:
        """Returns list of Account instances mutated by this transaction."""
        pass

    def to_dict(self) -> Dict[str, Any]:
        return {
            "transaction_id": self._transaction_id,
            "type": self.get_type().value,
            "amount": self._amount,
            "description": self._description,
            "timestamp": self._timestamp.isoformat(),
            "status": self._status.value,
            "source_account": self.get_source_account(),
            "destination_account": self.get_destination_account(),
            "error_message": self._error_message,
        }


class DepositTransaction(Transaction):
    """
    [OOP Pillar: INHERITANCE & POLYMORPHISM]
    Credits money to an account.
    """

    def __init__(
        self,
        account: Account,
        amount: float,
        description: str = "Deposit",
        transaction_id: Optional[str] = None,
        timestamp: Optional[datetime] = None,
        status: TransactionStatus = TransactionStatus.PENDING,
    ):
        super().__init__(
            amount=amount,
            description=description,
            transaction_id=transaction_id,
            timestamp=timestamp,
            status=status,
        )
        self._account: Account = account

    def execute(self) -> bool:
        try:
            self._account.deposit(self._amount, description=self._description)
            self._mark_completed()
            return True
        except Exception as ex:
            self._mark_failed(str(ex))
            raise

    def rollback(self) -> bool:
        if self._status != TransactionStatus.COMPLETED:
            return False
        # Debit back
        self._account.withdraw(self._amount, description=f"Rollback: {self._transaction_id}")
        self._mark_rolled_back()
        return True

    def get_type(self) -> TransactionType:
        return TransactionType.DEPOSIT

    def get_source_account(self) -> Optional[str]:
        return None

    def get_destination_account(self) -> Optional[str]:
        return self._account.account_number

    def get_affected_accounts(self) -> List[Account]:
        return [self._account]


class WithdrawalTransaction(Transaction):
    """
    [OOP Pillar: INHERITANCE & POLYMORPHISM]
    Debits funds from an account according to the account's polymorphic withdrawal rules.
    """

    def __init__(
        self,
        account: Account,
        amount: float,
        description: str = "Withdrawal",
        transaction_id: Optional[str] = None,
        timestamp: Optional[datetime] = None,
        status: TransactionStatus = TransactionStatus.PENDING,
    ):
        super().__init__(
            amount=amount,
            description=description,
            transaction_id=transaction_id,
            timestamp=timestamp,
            status=status,
        )
        self._account: Account = account

    def execute(self) -> bool:
        try:
            # Invokes polymorphic withdraw() on Account subclass
            self._account.withdraw(self._amount, description=self._description)
            self._mark_completed()
            return True
        except Exception as ex:
            self._mark_failed(str(ex))
            raise

    def rollback(self) -> bool:
        if self._status != TransactionStatus.COMPLETED:
            return False
        self._account.deposit(self._amount, description=f"Rollback: {self._transaction_id}")
        self._mark_rolled_back()
        return True

    def get_type(self) -> TransactionType:
        return TransactionType.WITHDRAWAL

    def get_source_account(self) -> Optional[str]:
        return self._account.account_number

    def get_destination_account(self) -> Optional[str]:
        return None

    def get_affected_accounts(self) -> List[Account]:
        return [self._account]


class TransferTransaction(Transaction):
    """
    [OOP Pillar: INHERITANCE & POLYMORPHISM]
    Atomic balance transfer between two accounts with rollback guarantee.
    """

    def __init__(
        self,
        source_account: Account,
        destination_account: Account,
        amount: float,
        description: str = "Transfer",
        transaction_id: Optional[str] = None,
        timestamp: Optional[datetime] = None,
        status: TransactionStatus = TransactionStatus.PENDING,
    ):
        super().__init__(
            amount=amount,
            description=description,
            transaction_id=transaction_id,
            timestamp=timestamp,
            status=status,
        )
        self._source: Account = source_account
        self._destination: Account = destination_account
        self._debited: bool = False

    def execute(self) -> bool:
        # Acquire locks in deterministic order to prevent deadlocks
        accounts = sorted([self._source, self._destination], key=lambda a: a.account_number)
        lock1, lock2 = accounts[0]._lock, accounts[1]._lock

        with lock1:
            with lock2:
                try:
                    # 1. Withdraw from source
                    self._source.withdraw(
                        self._amount,
                        description=f"Transfer out to {self._destination.account_number}",
                    )
                    self._debited = True

                    # 2. Deposit into destination
                    self._destination.deposit(
                        self._amount,
                        description=f"Transfer in from {self._source.account_number}",
                    )
                    self._mark_completed()
                    return True
                except Exception as ex:
                    # Compensate if partial execution occurred
                    if self._debited:
                        self._source.deposit(
                            self._amount,
                            description=f"Compensation: {self._transaction_id}",
                        )
                    self._mark_failed(str(ex))
                    raise

    def rollback(self) -> bool:
        if self._status != TransactionStatus.COMPLETED:
            return False

        accounts = sorted([self._source, self._destination], key=lambda a: a.account_number)
        with accounts[0]._lock:
            with accounts[1]._lock:
                self._destination.withdraw(self._amount, description=f"Rollback transfer {self._transaction_id}")
                self._source.deposit(self._amount, description=f"Rollback transfer {self._transaction_id}")
                self._mark_rolled_back()
                return True

    def get_type(self) -> TransactionType:
        return TransactionType.TRANSFER

    def get_source_account(self) -> Optional[str]:
        return self._source.account_number

    def get_destination_account(self) -> Optional[str]:
        return self._destination.account_number

    def get_affected_accounts(self) -> List[Account]:
        return [self._source, self._destination]
