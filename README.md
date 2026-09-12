# SecureBank OOP Enterprise Server & Database

A professional, production-grade Python banking server project built from first principles to demonstrate and reflect all four core pillars of **Object-Oriented Programming (OOP)**: **Encapsulation**, **Abstraction**, **Inheritance**, and **Polymorphism**.

The system features:
- **Zero external dependencies**: Built purely with Python 3.13 standard libraries (`sqlite3`, `socketserver`, `threading`, `abc`, `dataclasses`, `hashlib`, `unittest`).
- **Full Database Persistence**: SQLite database engine (`bank_server.db`) storing customers, accounts, transactions, and audit trails.
- **Thread-safe Concurrency**: Per-account deterministic lock sequencing preventing race conditions and double-spending.
- **Multi-threaded Network Server**: JSON-RPC style TCP socket server supporting concurrent client connections.
- **Interactive Terminal Client & Automated Demo Runner**: Rich command-line banking interface.

---

## The Four OOP Pillars in This Project

```
                              +----------------------------+
                              |   Account (ABC)            | <--- [ABSTRACTION & ENCAPSULATION]
                              |   _balance: float          |      _balance & __audit_trail protected;
                              |   _lock: RLock             |      @property getters with boundary guards;
                              |   + deposit(): float       |      abstract contracts for withdraw & interest.
                              +----------------------------+
                                             ^
                                             | (Inheritance)
                  +--------------------------+--------------------------+
                  |                                                     |
+-----------------------------------+                 +-----------------------------------+
| SavingsAccount                    |                 | CheckingAccount                   |
| - _minimum_balance: float         |                 | - _overdraft_limit: float         |
| - _interest_rate: float           |                 | - _overdraft_fee: float           |
| + withdraw() [Enforces min bal]   |                 | + withdraw() [Permits overdraft]  |
| + calculate_interest() [5% APY]   |                 | + calculate_interest() [Nominal]  |
+-----------------------------------+                 +-----------------------------------+
                  |                                                     |
                  +--------------------------+--------------------------+
                                             |
                              +-----------------------------------+
                              | BusinessAccount                   |
                              | - _company_name, _tax_id          | <--- [POLYMORPHISM]
                              | + withdraw() [Commercial fee]     |      Subclasses implement unique
                              | + calculate_interest() [Tiered]   |      business rules for the same method.
                              +-----------------------------------+
```

### 1. Encapsulation (Data Hiding & Protected Invariants)
- **Data Hiding**: Sensitive fields such as `_balance`, `__pin_hash`, `__salt`, and `__audit_trail` are protected or private. They cannot be altered from outside the class (e.g. `account.balance = 1000000` raises `AttributeError`).
- **Controlled Access**: Public access is granted exclusively through read-only `@property` getters (`account.balance`, `customer.customer_id`, `account.is_active`).
- **Defensive State Invariants**: All modifications occur through domain methods with strict validation guards (e.g., rejecting negative deposit amounts, verifying that checking balances stay within approved overdraft limits).
- **Authentication Protection**: In [`models/customer.py`](file:///models/customer.py), customer PINs are never stored as plaintext. Each customer generates a unique random cryptographic salt and SHA-256 digest (`__pin_hash`). Verification is performed through `customer.verify_pin(pin)` without leaking the underlying credentials.

### 2. Abstraction (Hiding Complexity Behind Clean Contracts)
- **Abstract Base Classes (ABCs)**: Uses Python's `abc.ABC` and `@abstractmethod` decorators to define clear behavioral contracts that cannot be instantiated directly:
  - [`Account`](file:///models/account.py): Abstract base class defining `withdraw()`, `calculate_interest()`, and `get_account_type()`.
  - [`Transaction`](file:///models/transaction.py): Abstract base class defining `execute()`, `rollback()`, and `get_affected_accounts()`.
  - [`BaseNotifier`](file:///notifications/notifier.py): Abstract interface for alert notification dispatch.
  - [`BankRepository`](file:///database/repository.py): Abstract storage interface separating business logic from storage mechanics.
- **Simplification for Callers**: Consumers of `BankService` simply call `service.transfer(src, dest, amount)` or `service.withdraw(acc, amount)`. Intricate internal mechanisms—such as thread locking order, SQLite schema transactions, rollback compensation, and notification fan-out—are completely abstracted away.

### 3. Inheritance (Code Reuse & Extensibility)
- **Account Specialization**:
  - `SavingsAccount`, `CheckingAccount`, and `BusinessAccount` inherit from `Account`. They reuse identity, locking mechanisms, audit trail generation, and universal deposit behavior, while specializing only what differs.
- **Transaction Specialization**:
  - `DepositTransaction`, `WithdrawalTransaction`, and `TransferTransaction` inherit from `Transaction`.
- **Notifier Specialization**:
  - `ConsoleAuditNotifier`, `EmailNotifier`, and `SMSNotifier` inherit from `BaseNotifier`.
- **Exception Hierarchy**:
  - `BankException` roots a domain-specific error hierarchy (`AuthenticationError`, `EntityNotFoundError` -> `AccountNotFoundError`, `BankingRuleViolationError` -> `InsufficientFundsError`, `OverdraftLimitExceededError`).

### 4. Polymorphism (Dynamic Dispatch & Pluggability)
- **Polymorphic Account Operations**:
  - `account.withdraw(amount)` behaves differently depending on the runtime type:
    - **`SavingsAccount`**: Rejects withdrawals that would breach the `$500` minimum balance or exceed the monthly withdrawal quota.
    - **`CheckingAccount`**: Permits withdrawals below zero down to the approved overdraft credit limit, automatically assessing an overdraft penalty fee.
    - **`BusinessAccount`**: Deducts the amount plus an enterprise processing fee (`$1.50`) and verifies corporate limits.
  - `account.calculate_interest()` calculates compound APY yields for savings, tiered enterprise yields for business accounts, and nominal yields for checking accounts.
- **Polymorphic Transaction Execution**:
  - In [`services/bank_service.py`](file:///services/bank_service.py), `process_transaction(txn: Transaction)` executes and persists any transaction type polymorphically:
    ```python
    def process_transaction(self, transaction: Transaction) -> bool:
        success = transaction.execute()
        for acc in transaction.get_affected_accounts():
            self._repository.save_account(acc)
        self._repository.save_transaction(transaction)
    ```
- **Pluggable Architecture**:
  - Storage backends (`SQLiteBankRepository` vs `InMemoryBankRepository`) can be swapped seamlessly.
  - `CompositeNotifier` treats any collection of `BaseNotifier` instances polymorphically, broadcasting alerts across email, SMS, and console simultaneously.

---

## Project Structure

```
bank server data base/
├── core/
│   ├── enums.py             # AccountType, TransactionType, TransactionStatus, Currency
│   └── exceptions.py        # Object-oriented domain exception hierarchy
├── models/
│   ├── account.py           # [Abstraction & Encapsulation] Abstract Account base class
│   ├── savings_account.py   # [Inheritance & Polymorphism] SavingsAccount with APY & min balance
│   ├── checking_account.py  # [Inheritance & Polymorphism] CheckingAccount with overdraft & fees
│   ├── business_account.py  # [Inheritance & Polymorphism] BusinessAccount with commercial fee schedule
│   ├── customer.py          # [Encapsulation] Customer entity with salted SHA-256 PIN hashing
│   └── transaction.py       # [Polymorphism] Polymorphic Deposit, Withdrawal, Transfer transactions
├── notifications/
│   └── notifier.py          # Abstract Notifier, Email, SMS, and Composite notifier
├── database/
│   └── repository.py        # Abstract BankRepository & SQLite persistent implementation
├── services/
│   ├── auth_service.py      # Session token lifecycle and customer credential verification
│   └── bank_service.py      # Core banking engine, thread safety, polymorphic transaction processing
├── server/
│   ├── bank_server.py       # Multi-threaded ThreadingTCPServer network listener
│   └── request_handler.py   # JSON protocol parser, router, and response serializer
├── client/
│   └── cli_client.py        # TCP Socket client communicating over JSON protocol
├── tests/
│   ├── test_oop_pillars.py  # 100% focused unit tests validating all 4 OOP pillars
│   └── test_banking_ops.py  # Concurrency safety, persistence rehydration, authentication tests
├── server_main.py           # Bank TCP Server entry point
├── client_main.py           # Interactive Command-Line Client interface
├── demo_runner.py           # Automated End-to-End Showcase Runner
└── README.md                # Comprehensive system documentation
```

---

## How to Run

### Prerequisites
Python 3.10+ (tested with Python 3.13 on Windows). Zero third-party `pip` packages required.

### 1. Run Automated OOP Showcase Demo
To run the automated verification script that launches the background server, executes all four OOP scenarios (customer registration, account opening, minimum balance rejection, overdraft allowance, compound interest, atomic fund transfers), and shuts down cleanly:

```powershell
& "C:\Users\divya\AppData\Local\Programs\Python\Python313\python.exe" demo_runner.py
```

### 2. Run the Unit Test Suite
To run the comprehensive test suite covering each OOP pillar and database concurrency:

```powershell
& "C:\Users\divya\AppData\Local\Programs\Python\Python313\python.exe" -m unittest discover -s tests -p "test_*.py" -v
```

### 3. Run the Live Server and Interactive Client
To start the persistent bank server:
```powershell
& "C:\Users\divya\AppData\Local\Programs\Python\Python313\python.exe" server_main.py
```

In another terminal, connect with the interactive CLI client:
```powershell
& "C:\Users\divya\AppData\Local\Programs\Python\Python313\python.exe" client_main.py
```

Interactive Client Features:
- `1`: Register customer profile
- `2`: Login (obtains session token)
- `4`: Open Savings, Checking, or Business account
- `5`: View accounts and live balances
- `6`: Deposit funds
- `7`: Withdraw funds (observe different rules for Savings vs Checking vs Business)
- `8`: Transfer funds between accounts
- `9`: Apply periodic interest
- `10`: View full account statement and transaction audit log
- `11`: Run automated OOP showcase inside the interactive session
