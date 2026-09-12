"""
CheckingAccount implementation.

Demonstrates:
  - INHERITANCE: Subclasses base Account class.
  - POLYMORPHISM: Overrides withdraw() to permit overdraft coverage with penalty fees;
    overrides calculate_interest() with flat transaction rebate or nominal yields.
  - ENCAPSULATION: Protects overdraft threshold and fee parameters with validation bounds.
"""
from typing import Optional
from datetime import datetime

from core.enums import AccountType, Currency
from core.exceptions import (
    OverdraftLimitExceededError,
    InvalidAmountError,
)
from models.account import Account


class CheckingAccount(Account):
    """
    [OOP Pillar: INHERITANCE]
    Derived from Account, specializing behavior for daily transactional use with overdraft protection.
    """

    DEFAULT_OVERDRAFT_LIMIT = 500.0
    DEFAULT_OVERDRAFT_FEE = 25.0
    CHECKING_INTEREST_RATE = 0.005  # Nominal 0.5% APY

    def __init__(
        self,
        account_number: str,
        customer_id: str,
        initial_balance: float = 0.0,
        overdraft_limit: float = DEFAULT_OVERDRAFT_LIMIT,
        overdraft_fee: float = DEFAULT_OVERDRAFT_FEE,
        currency: Currency = Currency.USD,
        created_at: Optional[datetime] = None,
        is_active: bool = True,
    ):
        if overdraft_limit < 0:
            raise InvalidAmountError("Overdraft limit cannot be negative")
        if overdraft_fee < 0:
            raise InvalidAmountError("Overdraft fee cannot be negative")

        super().__init__(
            account_number=account_number,
            customer_id=customer_id,
            initial_balance=initial_balance,
            currency=currency,
            created_at=created_at,
            is_active=is_active,
            allow_negative=(initial_balance >= -overdraft_limit),
        )

        self._overdraft_limit: float = overdraft_limit
        self._overdraft_fee: float = overdraft_fee

    # -------------------------------------------------------------------------
    # Encapsulated Properties
    # -------------------------------------------------------------------------
    @property
    def overdraft_limit(self) -> float:
        return self._overdraft_limit

    @overdraft_limit.setter
    def overdraft_limit(self, new_limit: float) -> None:
        if new_limit < 0:
            raise InvalidAmountError("Overdraft limit cannot be negative")
        with self._lock:
            self._overdraft_limit = new_limit

    @property
    def overdraft_fee(self) -> float:
        return self._overdraft_fee

    @property
    def is_in_overdraft(self) -> bool:
        """Helper to check if current balance is negative."""
        with self._lock:
            return self._balance < 0.0

    # -------------------------------------------------------------------------
    # [OOP Pillar: POLYMORPHISM] Overridden Abstract Methods
    # -------------------------------------------------------------------------
    def withdraw(self, amount: float, description: str = "Checking withdrawal") -> float:
        """
        Polymorphic withdrawal logic:
        Allows debiting into negative balance up to the overdraft limit.
        If overdraft is utilized, assesses an overdraft penalty fee.
        """
        if amount <= 0:
            raise InvalidAmountError("Withdrawal amount must be strictly greater than zero")

        with self._lock:
            self._ensure_active()

            available_funds = self._balance + self._overdraft_limit
            fee_to_apply = 0.0

            # If this withdrawal pushes balance below zero or account is already overdrawn
            projected_balance = self._balance - amount
            if projected_balance < 0:
                fee_to_apply = self._overdraft_fee

            total_required = amount + fee_to_apply
            if total_required > available_funds:
                raise OverdraftLimitExceededError(
                    current_balance=self._balance,
                    overdraft_limit=self._overdraft_limit,
                    requested_amount=total_required,
                )

            self._balance = round(self._balance - amount, 2)
            self._record_audit("WITHDRAWAL", amount, description)

            if fee_to_apply > 0:
                self._balance = round(self._balance - fee_to_apply, 2)
                self._record_audit("FEE", fee_to_apply, f"Overdraft penalty assessed for {description}")

            return self._balance

    def calculate_interest(self) -> float:
        """
        Polymorphic interest logic:
        Checking accounts yield modest returns on positive balances only.
        """
        with self._lock:
            if self._balance <= 0:
                return 0.0
            return round(self._balance * (self.CHECKING_INTEREST_RATE / 12.0), 2)

    def get_account_type(self) -> AccountType:
        return AccountType.CHECKING

    def to_dict(self) -> dict:
        data = super().to_dict()
        data.update({
            "overdraft_limit": self._overdraft_limit,
            "overdraft_fee": self._overdraft_fee,
            "is_in_overdraft": self.is_in_overdraft,
        })
        return data
