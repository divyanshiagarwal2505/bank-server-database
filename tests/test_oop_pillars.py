"""
Dedicated Unit Tests validating the Four OOP Pillars:
  1. ENCAPSULATION
  2. ABSTRACTION
  3. INHERITANCE
  4. POLYMORPHISM
"""
import unittest
from datetime import datetime

from core.enums import AccountType, Currency
from core.exceptions import (
    InsufficientFundsError,
    OverdraftLimitExceededError,
    InvalidAmountError,
    AccountLockedError,
)
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
from notifications.notifier import BaseNotifier, EmailNotifier, SMSNotifier, CompositeNotifier


class TestOOPPillars(unittest.TestCase):

    # =========================================================================
    # 1. ENCAPSULATION TESTS
    # =========================================================================
    def test_encapsulation_balance_cannot_be_mutated_directly(self):
        """Verify that account balance cannot be overwritten directly from the outside."""
        acc = SavingsAccount(account_number="ACC-101", customer_id="CUST-1", initial_balance=1000.0)

        # Attempting to assign `acc.balance = 5000` must raise AttributeError
        with self.assertRaises(AttributeError):
            acc.balance = 5000.0  # type: ignore

        # Balance remains protected at initial value
        self.assertEqual(acc.balance, 1000.0)

    def test_encapsulation_customer_pin_is_hidden_and_hashed(self):
        """Verify that customer PIN is never stored plaintext and is strictly encapsulated."""
        cust = Customer(
            customer_id="CUST-1",
            name="Alice",
            email="alice@test.com",
            phone="123456",
            pin="4321",
        )

        # Private attributes are name-mangled and cannot be accessed via public `cust.pin` or `cust.pin_hash`
        self.assertFalse(hasattr(cust, "pin"))
        self.assertFalse(hasattr(cust, "pin_hash"))

        # State is safely queried via encapsulated verification method
        self.assertTrue(cust.verify_pin("4321"))
        self.assertFalse(cust.verify_pin("0000"))

        # Serialized export dictionary for public consumption hides credentials
        public_dict = cust.to_dict()
        self.assertNotIn("pin", public_dict)
        self.assertNotIn("pin_hash", public_dict)
        self.assertNotIn("salt", public_dict)

    def test_encapsulation_invariants_and_validation(self):
        """Verify that invalid modifications violate domain guards."""
        acc = SavingsAccount(account_number="ACC-102", customer_id="CUST-1", initial_balance=600.0)

        # Negative deposits rejected
        with self.assertRaises(InvalidAmountError):
            acc.deposit(-50.0)

        # Negative withdrawals rejected
        with self.assertRaises(InvalidAmountError):
            acc.withdraw(-100.0)

        # Locked account rejects operations
        acc.lock_account("Suspicious activity")
        with self.assertRaises(AccountLockedError):
            acc.deposit(100.0)

    # =========================================================================
    # 2. ABSTRACTION TESTS
    # =========================================================================
    def test_abstraction_abstract_classes_cannot_be_instantiated(self):
        """Verify that ABC classes cannot be instantiated directly without implementation."""
        with self.assertRaises(TypeError):
            # Account is abstract (has abstract methods: withdraw, calculate_interest, get_account_type)
            Account("ACC-ABSTRACT", "CUST-1", 100.0)  # type: ignore

        with self.assertRaises(TypeError):
            # Transaction is abstract
            Transaction(100.0, "Abstract Txn")  # type: ignore

        with self.assertRaises(TypeError):
            # BaseNotifier is abstract
            BaseNotifier()  # type: ignore

    # =========================================================================
    # 3. INHERITANCE TESTS
    # =========================================================================
    def test_inheritance_subclasses_inherit_base_attributes_and_methods(self):
        """Verify that specialized accounts inherit identity, lock, audit, and deposit logic."""
        savings = SavingsAccount("SAV-1", "C-1", initial_balance=500.0)
        checking = CheckingAccount("CHK-1", "C-1", initial_balance=200.0)
        business = BusinessAccount("BIZ-1", "C-1", "Corp Inc", "99-1234567", initial_balance=1000.0)

        # isinstance checks verifying class hierarchy
        self.assertIsInstance(savings, Account)
        self.assertIsInstance(checking, Account)
        self.assertIsInstance(business, Account)

        # Shared base method `deposit` is inherited seamlessly by all subclasses
        savings.deposit(100.0)
        checking.deposit(100.0)
        business.deposit(100.0)

        self.assertEqual(savings.balance, 600.0)
        self.assertEqual(checking.balance, 300.0)
        self.assertEqual(business.balance, 1100.0)

        # Base properties inherited
        self.assertEqual(savings.currency, Currency.USD)
        self.assertTrue(savings.is_active)

    # =========================================================================
    # 4. POLYMORPHISM TESTS
    # =========================================================================
    def test_polymorphism_different_withdrawal_behaviors(self):
        """
        Verify that calling `withdraw()` on different Account types dispatches dynamically
        to unique business rules.
        """
        # 1. SavingsAccount: strictly enforces $500 minimum balance
        savings = SavingsAccount("SAV-P", "C-1", initial_balance=600.0, minimum_balance=500.0)
        # Attempting to withdraw $200 would reduce balance to $400 (< $500 min)
        with self.assertRaises(InsufficientFundsError):
            savings.withdraw(200.0)
        # Withdrawing $100 leaves exactly $500 (allowed)
        savings.withdraw(100.0)
        self.assertEqual(savings.balance, 500.0)

        # 2. CheckingAccount: allows overdraft with penalty fee
        checking = CheckingAccount(
            "CHK-P", "C-1",
            initial_balance=100.0,
            overdraft_limit=200.0,
            overdraft_fee=25.0,
        )
        # Withdrawing $150 dips into overdraft ($100 - $150 - $25 fee = -$75)
        checking.withdraw(150.0)
        self.assertEqual(checking.balance, -75.0)
        self.assertTrue(checking.is_in_overdraft)

        # Attempting to exceed overdraft limit: remaining credit is $200 - $75 = $125
        with self.assertRaises(OverdraftLimitExceededError):
            checking.withdraw(150.0)

        # 3. BusinessAccount: applies standard $1.50 commercial fee on every withdrawal
        business = BusinessAccount(
            "BIZ-P", "C-1",
            company_name="Acme",
            tax_id="01-12345",
            initial_balance=1000.0,
        )
        business.withdraw(200.0)
        # Balance = 1000 - 200 - 1.50 fee = 798.50
        self.assertEqual(business.balance, 798.50)

    def test_polymorphism_interest_calculation(self):
        """Verify polymorphic interest yields across different account types."""
        savings = SavingsAccount("SAV-I", "C-1", initial_balance=12_000.0, interest_rate=0.06)
        # 6% of $12,000 / 12 months = $60.00
        self.assertEqual(savings.calculate_interest(), 60.0)

        checking = CheckingAccount("CHK-I", "C-1", initial_balance=12_000.0)
        # Checking interest is nominal (0.5% APY): 0.005 * 12000 / 12 = $5.00
        self.assertEqual(checking.calculate_interest(), 5.0)

        biz = BusinessAccount("BIZ-I", "C-1", "Enterprise", "00-111", initial_balance=120_000.0)
        # High balance (> $100,000) earns 3.5% tier: 0.035 * 120000 / 12 = $350.00
        self.assertEqual(biz.calculate_interest(), 350.0)

    def test_polymorphism_transaction_execution(self):
        """
        Verify polymorphic execution of Transaction subtypes:
        DepositTransaction, WithdrawalTransaction, TransferTransaction.
        """
        acc1 = SavingsAccount("ACC-TXN-1", "C-1", initial_balance=1000.0, minimum_balance=200.0)
        acc2 = CheckingAccount("ACC-TXN-2", "C-2", initial_balance=500.0)

        transactions = [
            DepositTransaction(account=acc1, amount=500.0, description="Bonus"),
            WithdrawalTransaction(account=acc2, amount=100.0, description="ATM"),
            TransferTransaction(source_account=acc1, destination_account=acc2, amount=300.0),
        ]

        # Polymorphic execution loop
        for txn in transactions:
            self.assertIsInstance(txn, Transaction)
            success = txn.execute()
            self.assertTrue(success)

        # Assert balances after all polymorphic transactions execute
        # acc1: 1000 + 500 (deposit) - 300 (transfer) = 1200.0
        self.assertEqual(acc1.balance, 1200.0)
        # acc2: 500 - 100 (withdrawal) + 300 (transfer) = 700.0
        self.assertEqual(acc2.balance, 700.0)

    def test_polymorphism_notification_dispatch(self):
        """Verify polymorphic dispatch with CompositeNotifier holding different notification channels."""
        email_notifier = EmailNotifier()
        sms_notifier = SMSNotifier()
        composite = CompositeNotifier([email_notifier, sms_notifier])

        result = composite.send_notification("test@bank.com", "Security Alert", "Suspicious login")
        self.assertTrue(result)
        self.assertEqual(email_notifier.sent_count, 1)
        self.assertEqual(sms_notifier.sent_count, 1)


if __name__ == "__main__":
    unittest.main()
