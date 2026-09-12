"""
Integration, Persistence, Concurrency, and Authentication tests.
"""
import unittest
import os
import tempfile
import threading

from core.enums import AccountType, Currency
from core.exceptions import AuthenticationError, InsufficientFundsError
from database.repository import SQLiteBankRepository
from models.savings_account import SavingsAccount
from models.checking_account import CheckingAccount
from models.business_account import BusinessAccount
from services.bank_service import BankService
from services.auth_service import AuthService
from notifications.notifier import ConsoleAuditNotifier


class TestBankingOperations(unittest.TestCase):

    def setUp(self):
        # Create temporary database file for isolation
        self.temp_db = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        self.temp_db.close()
        self.repo = SQLiteBankRepository(db_path=self.temp_db.name)
        self.bank_service = BankService(repository=self.repo, notifier=ConsoleAuditNotifier())
        self.auth_service = AuthService(repository=self.repo)

    def tearDown(self):
        try:
            os.remove(self.temp_db.name)
        except Exception:
            pass

    def test_customer_registration_and_authentication(self):
        """Test customer registration, password salting/hashing, and session token issuance."""
        cust = self.bank_service.register_customer(
            name="John Doe",
            email="john@example.com",
            phone="+1-555-1234",
            pin="9876",
        )
        self.assertIsNotNone(cust.customer_id)

        # Successful login
        token, auth_cust = self.auth_service.authenticate("john@example.com", "9876")
        self.assertTrue(token.startswith("AUTH-"))
        self.assertEqual(auth_cust.customer_id, cust.customer_id)

        # Session validation
        validated_cust = self.auth_service.validate_session(token)
        self.assertEqual(validated_cust.customer_id, cust.customer_id)

        # Failed login with wrong PIN
        with self.assertRaises(AuthenticationError):
            self.auth_service.authenticate("john@example.com", "0000")

    def test_sqlite_persistence_and_rehydration(self):
        """Verify accounts of various polymorphic subtypes persist and rehydrate properly from SQLite."""
        cust = self.bank_service.register_customer("Jane Smith", "jane@corp.com", "+1-555-4321", "1122")

        # Open Savings, Checking, and Business accounts
        sav = self.bank_service.open_account(
            customer_id=cust.customer_id,
            account_type=AccountType.SAVINGS,
            initial_deposit=1500.0,
            extra_params={"interest_rate": 0.05, "minimum_balance": 500.0},
        )
        chk = self.bank_service.open_account(
            customer_id=cust.customer_id,
            account_type=AccountType.CHECKING,
            initial_deposit=500.0,
            extra_params={"overdraft_limit": 400.0, "overdraft_fee": 15.0},
        )
        biz = self.bank_service.open_account(
            customer_id=cust.customer_id,
            account_type=AccountType.BUSINESS,
            initial_deposit=3000.0,
            extra_params={"company_name": "Smith Enterprise", "tax_id": "44-5556667"},
        )

        # Re-fetch from repository (tests database rehydration into proper subclasses)
        rehydrated_sav = self.repo.get_account(sav.account_number)
        rehydrated_chk = self.repo.get_account(chk.account_number)
        rehydrated_biz = self.repo.get_account(biz.account_number)

        self.assertIsInstance(rehydrated_sav, SavingsAccount)
        self.assertIsInstance(rehydrated_chk, CheckingAccount)
        self.assertIsInstance(rehydrated_biz, BusinessAccount)

        self.assertEqual(rehydrated_sav.balance, 1500.0)
        self.assertEqual(rehydrated_chk.overdraft_limit, 400.0)
        self.assertEqual(rehydrated_biz.company_name, "Smith Enterprise")

    def test_concurrent_transfers_thread_safety(self):
        """
        Verify that multiple concurrent threads transferring money between accounts
        maintain absolute fund balance integrity (no lost updates or race conditions).
        """
        cust1 = self.bank_service.register_customer("User 1", "u1@test.com", "111", "1234")
        cust2 = self.bank_service.register_customer("User 2", "u2@test.com", "222", "1234")

        acc1 = self.bank_service.open_account(cust1.customer_id, AccountType.CHECKING, initial_deposit=10_000.0)
        acc2 = self.bank_service.open_account(cust2.customer_id, AccountType.CHECKING, initial_deposit=10_000.0)

        initial_total = acc1.balance + acc2.balance  # $20,000

        # Run 50 concurrent transfers in both directions
        threads = []
        errors = []

        def worker_1_to_2():
            try:
                for _ in range(25):
                    self.bank_service.transfer(acc1.account_number, acc2.account_number, 50.0)
            except Exception as e:
                errors.append(e)

        def worker_2_to_1():
            try:
                for _ in range(25):
                    self.bank_service.transfer(acc2.account_number, acc1.account_number, 50.0)
            except Exception as e:
                errors.append(e)

        t1 = threading.Thread(target=worker_1_to_2)
        t2 = threading.Thread(target=worker_2_to_1)
        t1.start()
        t2.start()
        t1.join()
        t2.join()

        self.assertEqual(len(errors), 0, f"Encountered concurrency errors: {errors}")

        # Total funds must be completely conserved
        updated_acc1 = self.repo.get_account(acc1.account_number)
        updated_acc2 = self.repo.get_account(acc2.account_number)
        final_total = updated_acc1.balance + updated_acc2.balance
        self.assertEqual(initial_total, final_total)


if __name__ == "__main__":
    unittest.main()
