"""
Interactive Command-Line Banking Client.
Allows manual user interaction or running an automated end-to-end OOP showcase scenario.
"""
import sys
import os
import json
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from client.cli_client import BankClient


def format_header(title: str):
    print("\n" + "=" * 60)
    print(f"  {title.center(56)}")
    print("=" * 60)


def print_response(resp: dict):
    status = resp.get("status")
    if status == "SUCCESS":
        print("[+] SUCCESS")
        print(json.dumps(resp.get("data", {}), indent=2))
    else:
        code = resp.get("code", "ERROR")
        msg = resp.get("message", "Unknown error")
        details = resp.get("details", "")
        print(f"[-] ERROR [{code}]: {msg}")
        if details:
            print(f"    Details: {details}")


def run_automated_demo(client: BankClient):
    """
    Automated walkthrough showcasing all 4 OOP Pillars through live server calls.
    """
    format_header("RUNNING AUTOMATED OOP SHOWCASE DEMO")
    print("This demo demonstrates:")
    print("  1. Encapsulation: Hashed credentials, private balance, protected state.")
    print("  2. Abstraction: Clean client commands executing complex server workflows.")
    print("  3. Inheritance: Savings, Checking, Business accounts deriving from Account.")
    print("  4. Polymorphism: Different withdrawal behaviors (overdraft vs fee) and interest rates.\n")

    time_str = str(int(time.time()))[-4:]
    email1 = f"alice_{time_str}@techcorp.com"
    email2 = f"bob_{time_str}@startup.io"

    # 1. Register Customers
    print(f"[*] Registering Alice ({email1})...")
    r1 = client.register("Alice Morgan", email1, "+1-555-0100", "1234")
    print_response(r1)

    print(f"\n[*] Registering Bob ({email2})...")
    r2 = client.register("Bob Chen", email2, "+1-555-0200", "5678")
    print_response(r2)

    # 2. Login as Alice
    print("\n[*] Logging in as Alice...")
    client.login(email1, "1234")
    print(f"[+] Authenticated! Token: {client.token[:12]}...")

    # 3. Open Savings Account for Alice (Inheritance & Polymorphism)
    print("\n[*] Opening Savings Account for Alice (min bal: $500, initial: $1,000)...")
    resp_sav = client.open_account(
        account_type="SAVINGS",
        initial_deposit=1000.0,
        extra_params={"interest_rate": 0.05, "minimum_balance": 500.0},
    )
    print_response(resp_sav)
    alice_savings = resp_sav["data"]["account"]["account_number"]

    # 4. Open Checking Account for Alice (Inheritance & Polymorphism)
    print("\n[*] Opening Checking Account for Alice with Overdraft Protection...")
    resp_chk = client.open_account(
        account_type="CHECKING",
        initial_deposit=200.0,
        extra_params={"overdraft_limit": 300.0, "overdraft_fee": 20.0},
    )
    print_response(resp_chk)
    alice_checking = resp_chk["data"]["account"]["account_number"]

    # 5. Demonstrate Polymorphic Withdrawal (Savings vs Checking)
    print("\n--- [POLYMORPHISM IN ACTION: WITHDRAWAL RULES] ---")
    print(f"[*] Attempting to withdraw $600 from Savings {alice_savings} (Balance: $1000, Min: $500)...")
    print("    Expected result: REJECTED by SavingsAccount (would violate $500 minimum balance)")
    r_fail = client.withdraw(alice_savings, 600.0, "Vacation trip")
    print_response(r_fail)

    print(f"\n[*] Withdrawing $300 from Checking {alice_checking} (Balance: $200, Overdraft limit: $300)...")
    print("    Expected result: ALLOWED by CheckingAccount via overdraft, assesses $20 fee")
    r_chk_wd = client.withdraw(alice_checking, 300.0, "Laptop purchase")
    print_response(r_chk_wd)

    # 6. Demonstrate Polymorphic Interest Accrual
    print("\n--- [POLYMORPHISM IN ACTION: INTEREST CALCULATION] ---")
    print(f"[*] Applying interest to Alice's Savings {alice_savings} (5% APY compound)...")
    r_int_sav = client.apply_interest(alice_savings)
    print_response(r_int_sav)

    print(f"\n[*] Applying interest to Alice's Checking {alice_checking} (Nominal yield)...")
    r_int_chk = client.apply_interest(alice_checking)
    print_response(r_int_chk)

    # 7. Open Business Account for Bob
    client.logout()
    print("\n[*] Logging in as Bob...")
    client.login(email2, "5678")

    print("\n[*] Opening Business Account for Bob's Company...")
    resp_biz = client.open_account(
        account_type="BUSINESS",
        initial_deposit=5000.0,
        extra_params={"company_name": "Bob Innovations LLC", "tax_id": "12-3456789"},
    )
    print_response(resp_biz)
    bob_biz = resp_biz["data"]["account"]["account_number"]

    # 8. Transfer funds between Bob and Alice (Polymorphic TransferTransaction with rollback guarantee)
    print("\n--- [POLYMORPHIC TRANSACTION: FUNDS TRANSFER] ---")
    print(f"[*] Bob transferring $1,500 from {bob_biz} to Alice's Savings {alice_savings}...")
    r_xfer = client.transfer(bob_biz, alice_savings, 1500.0, "Consulting Invoice #104")
    print_response(r_xfer)

    # 9. View Statement
    print(f"\n[*] Viewing Bob's account statement for {bob_biz}...")
    stmt = client.get_statement(bob_biz)
    print_response(stmt)

    format_header("AUTOMATED DEMO COMPLETED SUCCESSFULLY")


def interactive_menu(client: BankClient):
    """Interactive loop for human testing."""
    while True:
        format_header("SECURE BANK CLIENT MENU")
        curr = client.current_user
        if curr:
            print(f"  Logged in as: {curr['name']} ({curr['email']})")
        else:
            print("  Status: Not logged in")
        print("-" * 60)
        print("  1. Register Customer")
        print("  2. Login")
        print("  3. Logout")
        print("  4. Open New Account (Savings / Checking / Business)")
        print("  5. View My Accounts & Balances")
        print("  6. Deposit Funds")
        print("  7. Withdraw Funds")
        print("  8. Transfer Funds")
        print("  9. Apply Monthly Interest")
        print(" 10. View Account Statement")
        print(" 11. Run Full Automated OOP Showcase Demo")
        print("  0. Exit")
        print("-" * 60)

        choice = input("Select option [0-11]: ").strip()

        if choice == "0":
            print("Exiting. Goodbye!")
            client.disconnect()
            break

        elif choice == "1":
            name = input("Enter full name: ").strip()
            email = input("Enter email: ").strip()
            phone = input("Enter phone number: ").strip()
            pin = input("Enter 4-digit PIN: ").strip()
            resp = client.register(name, email, phone, pin)
            print_response(resp)

        elif choice == "2":
            email = input("Enter email: ").strip()
            pin = input("Enter 4-digit PIN: ").strip()
            resp = client.login(email, pin)
            print_response(resp)

        elif choice == "3":
            resp = client.logout()
            print_response(resp)

        elif choice == "4":
            print("\nAccount Types: SAVINGS, CHECKING, BUSINESS")
            acc_type = input("Choose account type: ").strip().upper()
            init_dep = float(input("Initial deposit amount ($): ") or "0")
            extra = {}
            if acc_type == "BUSINESS":
                extra["company_name"] = input("Company name: ").strip()
                extra["tax_id"] = input("Tax ID: ").strip()
            resp = client.open_account(acc_type, init_dep, extra_params=extra)
            print_response(resp)

        elif choice == "5":
            resp = client.get_accounts()
            print_response(resp)

        elif choice == "6":
            acc_no = input("Enter account number: ").strip()
            amt = float(input("Enter deposit amount: ").strip())
            desc = input("Description [Deposit]: ").strip() or "Deposit"
            resp = client.deposit(acc_no, amt, desc)
            print_response(resp)

        elif choice == "7":
            acc_no = input("Enter account number: ").strip()
            amt = float(input("Enter withdrawal amount: ").strip())
            desc = input("Description [Withdrawal]: ").strip() or "Withdrawal"
            resp = client.withdraw(acc_no, amt, desc)
            print_response(resp)

        elif choice == "8":
            src = input("Source account number: ").strip()
            dest = input("Destination account number: ").strip()
            amt = float(input("Transfer amount: ").strip())
            desc = input("Description [Transfer]: ").strip() or "Transfer"
            resp = client.transfer(src, dest, amt, desc)
            print_response(resp)

        elif choice == "9":
            acc_no = input("Enter account number: ").strip()
            resp = client.apply_interest(acc_no)
            print_response(resp)

        elif choice == "10":
            acc_no = input("Enter account number: ").strip()
            resp = client.get_statement(acc_no)
            print_response(resp)

        elif choice == "11":
            run_automated_demo(client)

        else:
            print("Invalid selection. Try again.")


def main():
    host = "127.0.0.1"
    port = 9999
    client = BankClient(host=host, port=port)

    print(f"Connecting to SecureBank Server at {host}:{port}...")
    try:
        client.connect()
        ping_res = client.ping()
        print(f"[+] Connected! Server says: {ping_res.get('data', {}).get('server')}")
    except Exception as ex:
        print(f"[-] Could not connect to bank server: {ex}")
        print("    Make sure 'server_main.py' is running!")
        sys.exit(1)

    interactive_menu(client)


if __name__ == "__main__":
    main()
