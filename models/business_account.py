"""
BusinessAccount implementation.

Demonstrates:
  - INHERITANCE: Subclasses base Account class.
  - POLYMORPHISM: Implements business-specific transaction fees on withdrawals and
    tiered treasury interest yields based on balance brackets.
  - ENCAPSULATION: Encapsulates corporate credentials (tax_id, business_name, fee schedules).
"""
from typing import Optional
from datetime import datetime

from core.enums import AccountType, Currency
from core.exceptions import (
    InsufficientFundsError,
    InvalidAmountError,
)
from models.account import Account


class BusinessAccount(Account):
    """
    [OOP Pillar: INHERITANCE]
    Derived from Account, tailored for commercial enterprise needs with per-transaction fees
    and tiered enterprise interest calculation.
    """

    TRANSACTION_FEE = 1.50  # Fixed commercial fee per outgoing transaction

    def __init__(
        self,
        account_number: str,
        customer_id: str,
        company_name: str,
        tax_id: str,
        initial_balance: float = 1000.0,
        currency: Currency = Currency.USD,
        created_at: Optional[datetime] = None,
        is_active: bool = True,
    ):
        super().__init__(
            account_number=account_number,
            customer_id=customer_id,
            initial_balance=initial_balance,
            currency=currency,
            created_at=created_at,
            is_active=is_active,
        )

        self._company_name: str = company_name.strip()
        self._tax_id: str = tax_id.strip()

    # -------------------------------------------------------------------------
    # Encapsulated Properties
    # -------------------------------------------------------------------------
    @property
    def company_name(self) -> str:
        return self._company_name

    @property
    def tax_id(self) -> str:
        """Masked tax ID for privacy preservation."""
        if len(self._tax_id) > 4:
            return f"***-**-{self._tax_id[-4:]}"
        return self._tax_id

    @property
    def raw_tax_id(self) -> str:
        return self._tax_id

    # -------------------------------------------------------------------------
    # [OOP Pillar: POLYMORPHISM] Overridden Abstract Methods
    # -------------------------------------------------------------------------
    def withdraw(self, amount: float, description: str = "Business withdrawal") -> float:
        """
        Polymorphic withdrawal logic:
        Deducts transaction amount PLUS standard commercial processing fee.
        Requires full balance coverage (no overdraft).
        """
        if amount <= 0:
            raise InvalidAmountError("Withdrawal amount must be strictly greater than zero")

        with self._lock:
            self._ensure_active()

            total_required = amount + self.TRANSACTION_FEE
            if self._balance < total_required:
                raise InsufficientFundsError(
                    current_balance=self._balance,
                    requested_amount=total_required,
                )

            self._balance = round(self._balance - amount, 2)
            self._record_audit("WITHDRAWAL", amount, description)

            self._balance = round(self._balance - self.TRANSACTION_FEE, 2)
            self._record_audit("FEE", self.TRANSACTION_FEE, "Commercial transaction processing fee")

            return self._balance

    def calculate_interest(self) -> float:
        """
        Polymorphic tiered enterprise yield:
        - Balances > $100,000 earn 3.5% APY
        - Balances > $25,000 earn 2.0% APY
        - Below $25,000 earn 1.0% APY
        """
        with self._lock:
            if self._balance >= 100_000:
                annual_rate = 0.035
            elif self._balance >= 25_000:
                annual_rate = 0.020
            else:
                annual_rate = 0.010

            return round(self._balance * (annual_rate / 12.0), 2)

    def get_account_type(self) -> AccountType:
        return AccountType.BUSINESS

    def to_dict(self) -> dict:
        data = super().to_dict()
        data.update({
            "company_name": self._company_name,
            "tax_id": self.tax_id,
            "transaction_fee": self.TRANSACTION_FEE,
        })
        return data
