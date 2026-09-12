"""
Network request handler decoding JSON-RPC style payloads and routing to domain services.
"""
import json
import logging
from typing import Dict, Any

from core.enums import AccountType, Currency
from core.exceptions import BankException, AuthenticationError
from services.bank_service import BankService
from services.auth_service import AuthService

logger = logging.getLogger("BankRequestHandler")


class BankRequestHandler:
    """
    Decodes requests, authenticates sessions where required, and formats standardized responses.
    """

    def __init__(self, bank_service: BankService, auth_service: AuthService):
        self._bank_service = bank_service
        self._auth_service = auth_service

    def handle_request(self, raw_data: str) -> str:
        """Processes a single raw JSON message string and returns formatted JSON response."""
        try:
            if not raw_data or not raw_data.strip():
                return self._format_error("INVALID_JSON", "Empty payload received")

            payload = json.loads(raw_data)
            action = payload.get("action", "").upper()
            params = payload.get("params", {})
            token = payload.get("token")

            logger.info(f"Incoming action: {action}")

            # Routing table
            routes = {
                "PING": self._handle_ping,
                "REGISTER": self._handle_register,
                "LOGIN": self._handle_login,
                "LOGOUT": self._handle_logout,
                "OPEN_ACCOUNT": self._handle_open_account,
                "GET_ACCOUNTS": self._handle_get_accounts,
                "GET_STATEMENT": self._handle_get_statement,
                "DEPOSIT": self._handle_deposit,
                "WITHDRAW": self._handle_withdraw,
                "TRANSFER": self._handle_transfer,
                "APPLY_INTEREST": self._handle_apply_interest,
            }

            handler = routes.get(action)
            if not handler:
                return self._format_error("UNKNOWN_ACTION", f"Action '{action}' is not supported")

            result = handler(params, token)
            return self._format_success(result)

        except BankException as be:
            logger.warning(f"Bank rule exception: {be.message}")
            return json.dumps({
                "status": "ERROR",
                "code": be.code,
                "message": be.message,
                "details": be.details,
            })
        except json.JSONDecodeError:
            return self._format_error("INVALID_JSON", "Failed to parse JSON string")
        except Exception as ex:
            logger.exception(f"Unhandled server error: {ex}")
            return self._format_error("INTERNAL_SERVER_ERROR", str(ex))

    # -------------------------------------------------------------------------
    # Route Handlers
    # -------------------------------------------------------------------------
    def _handle_ping(self, params: dict, token: str) -> dict:
        return {"message": "pong", "server": "SecureBank OOP Server v1.0"}

    def _handle_register(self, params: dict, token: str) -> dict:
        cust = self._bank_service.register_customer(
            name=params.get("name", ""),
            email=params.get("email", ""),
            phone=params.get("phone", ""),
            pin=params.get("pin", ""),
        )
        return {"customer": cust.to_dict()}

    def _handle_login(self, params: dict, token: str) -> dict:
        email = params.get("email", "")
        pin = params.get("pin", "")
        auth_token, customer = self._auth_service.authenticate(email, pin)
        return {
            "token": auth_token,
            "customer": customer.to_dict(),
        }

    def _handle_logout(self, params: dict, token: str) -> dict:
        ok = self._auth_service.revoke_session(token)
        return {"logged_out": ok}

    def _handle_open_account(self, params: dict, token: str) -> dict:
        customer = self._auth_service.validate_session(token)
        acc_type_str = params.get("account_type", "SAVINGS").upper()
        try:
            acc_type = AccountType(acc_type_str)
        except ValueError:
            raise BankException(f"Invalid account type: {acc_type_str}")

        initial_deposit = float(params.get("initial_deposit", 0.0))
        currency = Currency(params.get("currency", "USD"))

        account = self._bank_service.open_account(
            customer_id=customer.customer_id,
            account_type=acc_type,
            initial_deposit=initial_deposit,
            currency=currency,
            **params.get("extra_params", {}),
        )
        return {"account": account.to_dict()}

    def _handle_get_accounts(self, params: dict, token: str) -> dict:
        customer = self._auth_service.validate_session(token)
        accounts = self._bank_service.get_customer_accounts(customer.customer_id)
        return {"accounts": [acc.to_dict() for acc in accounts]}

    def _handle_get_statement(self, params: dict, token: str) -> dict:
        customer = self._auth_service.validate_session(token)
        account_number = params.get("account_number", "")
        account = self._bank_service.get_account(account_number)

        # Authorization check: customer must own this account
        if account.customer_id != customer.customer_id:
            raise AuthenticationError("You are not authorized to view this account statement")

        limit = int(params.get("limit", 20))
        return self._bank_service.get_statement(account_number, limit=limit)

    def _handle_deposit(self, params: dict, token: str) -> dict:
        # Deposits can be done by authenticated user
        self._auth_service.validate_session(token)
        account_number = params.get("account_number", "")
        amount = float(params.get("amount", 0.0))
        desc = params.get("description", "Deposit")
        return self._bank_service.deposit(account_number, amount, desc)

    def _handle_withdraw(self, params: dict, token: str) -> dict:
        customer = self._auth_service.validate_session(token)
        account_number = params.get("account_number", "")
        account = self._bank_service.get_account(account_number)

        if account.customer_id != customer.customer_id:
            raise AuthenticationError("Unauthorized to withdraw from this account")

        amount = float(params.get("amount", 0.0))
        desc = params.get("description", "ATM Withdrawal")
        return self._bank_service.withdraw(account_number, amount, desc)

    def _handle_transfer(self, params: dict, token: str) -> dict:
        customer = self._auth_service.validate_session(token)
        src_no = params.get("source_account", "")
        src_acc = self._bank_service.get_account(src_no)

        if src_acc.customer_id != customer.customer_id:
            raise AuthenticationError("Unauthorized to transfer from source account")

        dest_no = params.get("destination_account", "")
        amount = float(params.get("amount", 0.0))
        desc = params.get("description", "Funds Transfer")
        return self._bank_service.transfer(src_no, dest_no, amount, desc)

    def _handle_apply_interest(self, params: dict, token: str) -> dict:
        self._auth_service.validate_session(token)
        account_number = params.get("account_number", "")
        return self._bank_service.apply_monthly_interest(account_number)

    # -------------------------------------------------------------------------
    # Response Formatters
    # -------------------------------------------------------------------------
    def _format_success(self, data: Any) -> str:
        return json.dumps({"status": "SUCCESS", "data": data})

    def _format_error(self, code: str, message: str) -> str:
        return json.dumps({"status": "ERROR", "code": code, "message": message})
