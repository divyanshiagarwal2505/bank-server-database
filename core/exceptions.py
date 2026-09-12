"""
Custom exception hierarchy demonstrating the INHERITANCE pillar in error handling.

Hierarchy:
Exception
  └── BankException (Base abstract application exception)
        ├── AuthenticationError
        ├── EntityNotFoundError
        │     ├── AccountNotFoundError
        │     └── CustomerNotFoundError
        ├── ValidationException
        │     ├── InvalidAmountError
        │     └── DuplicateEntityError
        └── BankingRuleViolationError
              ├── InsufficientFundsError
              ├── OverdraftLimitExceededError
              ├── TransactionLimitExceededError
              └── AccountLockedError
"""
from typing import Optional


class BankException(Exception):
    """
    [OOP Pillar: INHERITANCE - Root of domain exception hierarchy]
    Base exception for all banking operations.
    Encapsulates error code and human-readable message.
    """
    def __init__(self, message: str, code: str = "BANK_ERROR", details: Optional[dict] = None):
        super().__init__(message)
        self.message = message
        self.code = code
        self.details = details or {}

    def to_dict(self) -> dict:
        return {
            "error_type": self.__class__.__name__,
            "code": self.code,
            "message": self.message,
            "details": self.details,
        }


class AuthenticationError(BankException):
    """Raised when authentication fails (invalid credentials or expired session)."""
    def __init__(self, message: str = "Authentication failed", details: Optional[dict] = None):
        super().__init__(message=message, code="AUTH_FAILED", details=details)


class EntityNotFoundError(BankException):
    """Base class for missing resource lookup errors."""
    def __init__(self, message: str, entity_type: str, entity_id: str):
        super().__init__(
            message=message,
            code="ENTITY_NOT_FOUND",
            details={"entity_type": entity_type, "entity_id": entity_id},
        )


class AccountNotFoundError(EntityNotFoundError):
    """Raised when an account number does not exist."""
    def __init__(self, account_number: str):
        super().__init__(
            message=f"Account '{account_number}' not found",
            entity_type="Account",
            entity_id=account_number,
        )


class CustomerNotFoundError(EntityNotFoundError):
    """Raised when a customer identifier does not exist."""
    def __init__(self, customer_id: str):
        super().__init__(
            message=f"Customer '{customer_id}' not found",
            entity_type="Customer",
            entity_id=customer_id,
        )


class ValidationException(BankException):
    """Base class for invalid business input parameters."""
    def __init__(self, message: str, field_name: str, code: str = "VALIDATION_ERROR"):
        super().__init__(message=message, code=code, details={"field": field_name})


class InvalidAmountError(ValidationException):
    """Raised when monetary amount is negative, zero, or non-numeric."""
    def __init__(self, message: str = "Transaction amount must be strictly greater than zero"):
        super().__init__(message=message, field_name="amount", code="INVALID_AMOUNT")


class DuplicateEntityError(ValidationException):
    """Raised when an entity with unique constraint already exists."""
    def __init__(self, entity: str, identifier: str):
        super().__init__(
            message=f"{entity} with identifier '{identifier}' already exists",
            field_name="identifier",
            code="DUPLICATE_ENTITY",
        )


class BankingRuleViolationError(BankException):
    """Base class for violations of banking domain rules."""
    pass


class InsufficientFundsError(BankingRuleViolationError):
    """Raised when account balance cannot cover the requested transaction."""
    def __init__(self, current_balance: float, requested_amount: float):
        super().__init__(
            message=(
                f"Insufficient funds: available {current_balance:.2f}, "
                f"attempted debit {requested_amount:.2f}"
            ),
            code="INSUFFICIENT_FUNDS",
            details={"current_balance": current_balance, "requested_amount": requested_amount},
        )


class OverdraftLimitExceededError(BankingRuleViolationError):
    """Raised when checking account overdraft limit would be breached."""
    def __init__(self, current_balance: float, overdraft_limit: float, requested_amount: float):
        super().__init__(
            message=(
                f"Overdraft limit exceeded: balance={current_balance:.2f}, "
                f"limit={overdraft_limit:.2f}, requested={requested_amount:.2f}"
            ),
            code="OVERDRAFT_LIMIT_EXCEEDED",
            details={
                "current_balance": current_balance,
                "overdraft_limit": overdraft_limit,
                "requested_amount": requested_amount,
            },
        )


class TransactionLimitExceededError(BankingRuleViolationError):
    """Raised when transaction amount exceeds per-transaction or daily quota."""
    def __init__(self, limit: float, attempted: float):
        super().__init__(
            message=f"Transaction limit exceeded: limit is {limit:.2f}, attempted {attempted:.2f}",
            code="TRANSACTION_LIMIT_EXCEEDED",
            details={"limit": limit, "attempted": attempted},
        )


class AccountLockedError(BankingRuleViolationError):
    """Raised when operations are attempted on a frozen/inactive account."""
    def __init__(self, account_number: str, reason: str = "Account is inactive or locked"):
        super().__init__(
            message=f"Account '{account_number}' is locked: {reason}",
            code="ACCOUNT_LOCKED",
            details={"account_number": account_number, "reason": reason},
        )
