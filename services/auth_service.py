"""
Authentication and session management service.

Demonstrates:
  - ENCAPSULATION: Session state and token lifecycle are maintained internally.
"""
import uuid
from datetime import datetime, timedelta
from typing import Dict, Optional, Tuple

from core.exceptions import AuthenticationError
from database.repository import BankRepository
from models.customer import Customer


class AuthService:
    """
    [OOP Pillar: ENCAPSULATION]
    Provides credential authentication and token-based session management.
    """

    DEFAULT_SESSION_DURATION = timedelta(hours=2)

    def __init__(self, repository: BankRepository):
        self._repository = repository
        # In-memory session store: token -> (customer_id, expires_at)
        self._sessions: Dict[str, Tuple[str, datetime]] = {}

    def authenticate(self, email: str, pin: str) -> Tuple[str, Customer]:
        """
        Validates customer credentials and produces an authenticated session token.
        """
        customer = self._repository.get_customer_by_email(email)
        if not customer:
            raise AuthenticationError("Invalid email or PIN")

        if not customer.verify_pin(pin):
            raise AuthenticationError("Invalid email or PIN")

        token = f"AUTH-{uuid.uuid4().hex}"
        expires_at = datetime.now() + self.DEFAULT_SESSION_DURATION
        self._sessions[token] = (customer.customer_id, expires_at)
        return token, customer

    def validate_session(self, token: str) -> Customer:
        """
        Ensures the provided session token is valid and active.
        """
        if not token or token not in self._sessions:
            raise AuthenticationError("Session token missing or invalid. Please log in.")

        customer_id, expires_at = self._sessions[token]
        if datetime.now() > expires_at:
            del self._sessions[token]
            raise AuthenticationError("Session expired. Please log in again.")

        customer = self._repository.get_customer(customer_id)
        if not customer:
            raise AuthenticationError("Authenticated customer not found")

        return customer

    def revoke_session(self, token: str) -> bool:
        """Logs the user out by deleting active session."""
        if token in self._sessions:
            del self._sessions[token]
            return True
        return False
