"""
SavingsAccount implementation.

Demonstrates:
  - INHERITANCE: Extends base Account class, inheriting identity, balances, locking, and audit mechanics.
  - POLYMORPHISM: Overrides withdraw() with minimum balance constraints and calculate_interest() with APY formula.
  - ENCAPSULATION: Protects interest rate and minimum balance thresholds behind getters/setters with boundary checks.
"""
from typing import Optional
from datetime import datetime

from core.enums import AccountType, Currency
from core.exceptions import (
    InsufficientFundsError,
    InvalidAmountError,
    TransactionLimitExceededError,
)
from models.account import Account


class SavingsAccount(Account):
    """
    [OOP Pillar: INHERITANCE]
    Derived from Account, specializing behavior for interest-earning retail savings.
    """

    DEFAULT_INTEREST_RATE = 0.045  # 4.5% annual interest
    DEFAULT_MINIMUM_BALANCE = 500.0
    MAX_MONTHLY_WITHDRAWALS = 6

    def __init__(
        self,
        account_number: str,
        customer_id: str,
        initial_balance: float = DEFAULT_MINIMUM_BALANCE,
        interest_rate: float = DEFAULT_INTEREST_RATE,
        minimum_balance: float = DEFAULT_MINIMUM_BALANCE,
        currency: Currency = Currency.USD,
        created_at: Optional[datetime] = None,
        is_active: bool = True,
    ):
        # Delegate shared initialization to superclass constructor
        super().__init__(
            account_number=account_number,
            customer_id=customer_id,
            initial_balance=initial_balance,
            currency=currency,
            created_at=created_at,
            is_active=is_active,
        )

        if interest_rate < 0:
            raise InvalidAmountError("Interest rate cannot be negative")
        if minimum_balance < 0:
            raise InvalidAmountError("Minimum balance cannot be negative")

        self._interest_rate: float = interest_rate
        self._minimum_balance: float = minimum_balance
        self._withdrawal_count: int = 0

    # -------------------------------------------------------------------------
    # Encapsulated Properties
    # -------------------------------------------------------------------------
    @property
    def interest_rate(self) -> float:
        return self._interest_rate

    @interest_rate.setter
    def interest_rate(self, new_rate: float) -> None:
        if new_rate < 0 or new_rate > 0.50:
            raise InvalidAmountError("Interest rate must be between 0.0% and 50.0%")
        with self._lock:
            self._interest_rate = new_rate

    @property
    def minimum_balance(self) -> float:
        return self._minimum_balance

    @property
    def withdrawal_count(self) -> int:
        return self._withdrawal_count

    # -------------------------------------------------------------------------
    # [OOP Pillar: POLYMORPHISM] Overridden Abstract Methods
    # -------------------------------------------------------------------------
    def withdraw(self, amount: float, description: str = "Savings withdrawal") -> float:
        """
        Polymorphic withdrawal logic:
        Enforces monthly transaction count quota and prevents breaching minimum balance.
        """
        if amount <= 0:
            raise InvalidAmountError("Withdrawal amount must be strictly greater than zero")

        with self._lock:
            self._ensure_active()

            if self._withdrawal_count >= self.MAX_MONTHLY_WITHDRAWALS:
                raise TransactionLimitExceededError(
                    limit=self.MAX_MONTHLY_WITHDRAWALS,
                    attempted=self._withdrawal_count + 1,
                )

            projected_balance = self._balance - amount
            if projected_balance < self._minimum_balance:
                raise InsufficientFundsError(
                    current_balance=self._balance - self._minimum_balance,
                    requested_amount=amount,
                )

            self._balance = round(projected_balance, 2)
            self._withdrawal_count += 1
            self._record_audit("WITHDRAWAL", amount, f"{description} [Count: {self._withdrawal_count}]")
            return self._balance

    def calculate_interest(self) -> float:
        """
        Polymorphic interest formula:
        Calculates monthly compound interest accrual: Balance * (APY / 12).
        """
        with self._lock:
            monthly_interest = round(self._balance * (self._interest_rate / 12.0), 2)
            return monthly_interest

    def get_account_type(self) -> AccountType:
        return AccountType.SAVINGS

    def reset_monthly_counter(self) -> None:
        """Resets periodic withdrawal counter at billing cycle."""
        with self._lock:
            self._withdrawal_count = 0

    def to_dict(self) -> dict:
        data = super().to_dict()
        data.update({
            "interest_rate": self._interest_rate,
            "minimum_balance": self._minimum_balance,
            "withdrawal_count": self._withdrawal_count,
        })
        return data
