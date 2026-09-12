"""
BankService coordinating all domain operations.

Demonstrates:
  - ABSTRACTION: Clean facade over persistence, thread synchronization, account rules, and alerts.
  - POLYMORPHISM:
      1. process_transaction(txn: Transaction) executes any transaction polymorphically.
      2. account.withdraw() and account.calculate_interest() dispatch to specific derived types.
      3. notifier.send_notification() dispatches polymorphically.
  - ENCAPSULATION: Enforces validation invariants and atomic lock management.
"""
import uuid
import threading
import logging
from typing import List, Dict, Any, Optional

from core.enums import AccountType, Currency, TransactionStatus
from core.exceptions import (
    AccountNotFoundError,
    CustomerNotFoundError,
    DuplicateEntityError,
    InvalidAmountError,
    BankException,
)
from database.repository import BankRepository
from models.account import Account
from models.savings_account import SavingsAccount
from models.checking_account import CheckingAccount
from models.business_account import BusinessAccount
from models.customer import Customer
from models.transaction import (
    Transaction,
    DepositTransaction,
    WithdrawalTransaction,
    TransferTransaction,
)
from notifications.notifier import BaseNotifier, ConsoleAuditNotifier

logger = logging.getLogger("BankService")


class BankService:
    """
    [OOP Pillar: ABSTRACTION & POLYMORPHISM]
    Central service handling bank workflows, concurrency safety, and transaction audits.
    """

    def __init__(
        self,
        repository: BankRepository,
        notifier: Optional[BaseNotifier] = None,
    ):
        self._repository = repository
        self._notifier: BaseNotifier = notifier or ConsoleAuditNotifier()
        # Per-account memory locks cache
        self._locks: Dict[str, threading.RLock] = {}
        self._global_lock = threading.RLock()

    def _get_account_lock(self, account_number: str) -> threading.RLock:
        """Encapsulated synchronization lock per account number."""
        with self._global_lock:
            if account_number not in self._locks:
                self._locks[account_number] = threading.RLock()
            return self._locks[account_number]

    # -------------------------------------------------------------------------
    # Customer Operations
    # -------------------------------------------------------------------------
    def register_customer(
        self,
        name: str,
        email: str,
        phone: str,
        pin: str,
    ) -> Customer:
        """Registers a new bank customer profile."""
        if not name or not email or not phone:
            raise BankException("Name, email, and phone are required fields")
        if len(pin) < 4 or not pin.isdigit():
            raise InvalidAmountError("PIN must be at least 4 numeric digits")

        existing = self._repository.get_customer_by_email(email)
        if existing:
            raise DuplicateEntityError("Customer", email)

        customer_id = f"CUST-{uuid.uuid4().hex[:8].upper()}"
        customer = Customer(
            customer_id=customer_id,
            name=name,
            email=email,
            phone=phone,
            pin=pin,
        )
        self._repository.save_customer(customer)
        logger.info(f"Registered customer: {customer_id} ({email})")

        self._notifier.send_notification(
            recipient=email,
            subject="Welcome to SecureBank",
            message=f"Hello {name}, your profile has been created successfully (ID: {customer_id}).",
        )
        return customer

    def get_customer(self, customer_id: str) -> Customer:
        cust = self._repository.get_customer(customer_id)
        if not cust:
            raise CustomerNotFoundError(customer_id)
        return cust

    # -------------------------------------------------------------------------
    # Account Factory (Polymorphic Instantiation)
    # -------------------------------------------------------------------------
    def open_account(
        self,
        customer_id: str,
        account_type: AccountType,
        initial_deposit: float = 0.0,
        currency: Currency = Currency.USD,
        **kwargs: Any,
    ) -> Account:
        """
        [OOP Pillar: POLYMORPHISM]
        Factory method generating specialized Account subtypes based on requested type.
        """
        customer = self.get_customer(customer_id)
        account_number = f"ACC-{uuid.uuid4().hex[:8].upper()}"

        # Merge any nested extra_params dictionary into options
        options = dict(kwargs)
        if "extra_params" in options and isinstance(options["extra_params"], dict):
            options.update(options.pop("extra_params"))

        account: Account
        if account_type == AccountType.SAVINGS:
            min_bal = options.get("minimum_balance", SavingsAccount.DEFAULT_MINIMUM_BALANCE)
            interest_rate = options.get("interest_rate", SavingsAccount.DEFAULT_INTEREST_RATE)
            if initial_deposit < min_bal:
                raise InvalidAmountError(
                    f"Initial deposit for Savings account must be at least {min_bal:.2f}"
                )
            account = SavingsAccount(
                account_number=account_number,
                customer_id=customer_id,
                initial_balance=initial_deposit,
                interest_rate=interest_rate,
                minimum_balance=min_bal,
                currency=currency,
            )
        elif account_type == AccountType.CHECKING:
            overdraft_limit = options.get("overdraft_limit", CheckingAccount.DEFAULT_OVERDRAFT_LIMIT)
            overdraft_fee = options.get("overdraft_fee", CheckingAccount.DEFAULT_OVERDRAFT_FEE)
            account = CheckingAccount(
                account_number=account_number,
                customer_id=customer_id,
                initial_balance=initial_deposit,
                overdraft_limit=overdraft_limit,
                overdraft_fee=overdraft_fee,
                currency=currency,
            )
        elif account_type == AccountType.BUSINESS:
            company_name = options.get("company_name", customer.name)
            tax_id = options.get("tax_id", "00-0000000")
            account = BusinessAccount(
                account_number=account_number,
                customer_id=customer_id,
                company_name=company_name,
                tax_id=tax_id,
                initial_balance=initial_deposit,
                currency=currency,
            )
        else:
            raise BankException(f"Unsupported account type: {account_type}")

        # Persist account and link to customer
        self._repository.save_account(account)
        customer.link_account(account_number)
        self._repository.save_customer(customer)

        self._notifier.send_notification(
            recipient=customer.email,
            subject="New Account Activated",
            message=(
                f"Your new {account.get_account_type().value} account {account_number} "
                f"is active with balance {account.balance:.2f} {account.currency.value}."
            ),
        )
        return account

    def get_account(self, account_number: str) -> Account:
        acc = self._repository.get_account(account_number)
        if not acc:
            raise AccountNotFoundError(account_number)
        return acc

    def get_customer_accounts(self, customer_id: str) -> List[Account]:
        self.get_customer(customer_id)
        return self._repository.get_accounts_by_customer(customer_id)

    # -------------------------------------------------------------------------
    # [OOP Pillar: POLYMORPHISM] Polymorphic Transaction Processing
    # -------------------------------------------------------------------------
    def process_transaction(self, transaction: Transaction) -> bool:
        """
        [OOP Pillar: POLYMORPHISM]
        Executes any Transaction instance polymorphically without knowing its specific subtype!
        """
        try:
            success = transaction.execute()
            if success:
                # Synchronize updated account(s) to repository
                for acc in transaction.get_affected_accounts():
                    self._repository.save_account(acc)

                self._repository.save_transaction(transaction)
                return True
            return False
        except Exception as ex:
            self._repository.save_transaction(transaction)
            logger.error(f"Transaction {transaction.transaction_id} failed: {ex}")
            raise

    # -------------------------------------------------------------------------
    # High-Level Banking Operations
    # -------------------------------------------------------------------------
    def deposit(self, account_number: str, amount: float, description: str = "Deposit") -> Dict[str, Any]:
        """Deposits funds by constructing and polymorphically executing a DepositTransaction."""
        lock = self._get_account_lock(account_number)
        with lock:
            account = self.get_account(account_number)
            txn = DepositTransaction(account=account, amount=amount, description=description)
            self.process_transaction(txn)
            # Re-fetch updated account
            account = self.get_account(account_number)
            return {
                "transaction_id": txn.transaction_id,
                "status": txn.status.value,
                "account_number": account_number,
                "amount": amount,
                "new_balance": account.balance,
            }

    def withdraw(self, account_number: str, amount: float, description: str = "Withdrawal") -> Dict[str, Any]:
        """Withdraws funds using polymorphic WithdrawalTransaction."""
        lock = self._get_account_lock(account_number)
        with lock:
            account = self.get_account(account_number)
            txn = WithdrawalTransaction(account=account, amount=amount, description=description)
            self.process_transaction(txn)
            account = self.get_account(account_number)
            return {
                "transaction_id": txn.transaction_id,
                "status": txn.status.value,
                "account_number": account_number,
                "amount": amount,
                "new_balance": account.balance,
            }

    def transfer(
        self,
        source_account_number: str,
        dest_account_number: str,
        amount: float,
        description: str = "Funds transfer",
    ) -> Dict[str, Any]:
        """Transfers funds between accounts atomically using TransferTransaction."""
        if source_account_number == dest_account_number:
            raise BankException("Source and destination accounts must be distinct")

        # Deterministic locking order
        src_lock = self._get_account_lock(source_account_number)
        dest_lock = self._get_account_lock(dest_account_number)

        ordered_locks = sorted(
            [(source_account_number, src_lock), (dest_account_number, dest_lock)],
            key=lambda item: item[0],
        )

        with ordered_locks[0][1]:
            with ordered_locks[1][1]:
                src_acc = self.get_account(source_account_number)
                dest_acc = self.get_account(dest_account_number)

                txn = TransferTransaction(
                    source_account=src_acc,
                    destination_account=dest_acc,
                    amount=amount,
                    description=description,
                )
                self.process_transaction(txn)

                src_acc = self.get_account(source_account_number)
                dest_acc = self.get_account(dest_account_number)

                # Send notifications
                src_cust = self._repository.get_customer(src_acc.customer_id)
                dest_cust = self._repository.get_customer(dest_acc.customer_id)
                if src_cust:
                    self._notifier.send_notification(
                        src_cust.email,
                        "Debit Alert: Transfer Sent",
                        f"Sent {amount:.2f} {src_acc.currency.value} to account {dest_acc.account_number}. Balance: {src_acc.balance:.2f}",
                    )
                if dest_cust:
                    self._notifier.send_notification(
                        dest_cust.email,
                        "Credit Alert: Transfer Received",
                        f"Received {amount:.2f} from account {src_acc.account_number}. Balance: {dest_acc.balance:.2f}",
                    )

                return {
                    "transaction_id": txn.transaction_id,
                    "status": txn.status.value,
                    "source_account": source_account_number,
                    "source_balance": src_acc.balance,
                    "destination_account": dest_account_number,
                    "destination_balance": dest_acc.balance,
                    "amount": amount,
                }

    def apply_monthly_interest(self, account_number: str) -> Dict[str, Any]:
        """
        [OOP Pillar: POLYMORPHISM]
        Calls calculate_interest() on the account, which executes the polymorphic interest logic
        specific to SavingsAccount, CheckingAccount, or BusinessAccount.
        """
        lock = self._get_account_lock(account_number)
        with lock:
            account = self.get_account(account_number)
            interest_earned = account.calculate_interest()
            if interest_earned > 0:
                account.deposit(interest_earned, description="Monthly Interest Accrual")
                self._repository.save_account(account)

            return {
                "account_number": account_number,
                "account_type": account.get_account_type().value,
                "interest_earned": interest_earned,
                "new_balance": account.balance,
            }

    def get_statement(self, account_number: str, limit: int = 20) -> Dict[str, Any]:
        """Retrieves current account status and transaction statement."""
        account = self.get_account(account_number)
        transactions = self._repository.get_transactions_for_account(account_number, limit=limit)
        return {
            "account": account.to_dict(),
            "transactions": transactions,
        }
