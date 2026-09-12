"""
Customer domain entity.

Demonstrates:
  - ENCAPSULATION: Sensitive credentials (PIN hash and cryptographic salt) are strictly private
    (__pin_hash, __salt) and never exposed. Verification happens via internal hashing logic.
  - Controlled aggregation: Manages customer's portfolio of account numbers.
"""
import hashlib
import os
from datetime import datetime
from typing import List, Optional, Dict, Any


class Customer:
    """
    [OOP Pillar: ENCAPSULATION]
    Represents a bank client. Enforces data hiding for security-critical authentication secrets.
    """

    def __init__(
        self,
        customer_id: str,
        name: str,
        email: str,
        phone: str,
        pin: Optional[str] = None,
        pin_hash: Optional[str] = None,
        salt: Optional[str] = None,
        created_at: Optional[datetime] = None,
        account_ids: Optional[List[str]] = None,
    ):
        self._customer_id: str = customer_id
        self._name: str = name.strip()
        self._email: str = email.strip().lower()
        self._phone: str = phone.strip()
        self._created_at: datetime = created_at or datetime.now()
        self._account_ids: List[str] = list(account_ids or [])

        # [OOP Pillar: ENCAPSULATION] Private attributes (double underscore)
        if pin is not None:
            # Generate new salt and hash for fresh customer registration
            self.__salt: str = os.urandom(16).hex()
            self.__pin_hash: str = self._hash_pin(pin, self.__salt)
        elif pin_hash is not None and salt is not None:
            # Rehydrate from database storage
            self.__salt = salt
            self.__pin_hash = pin_hash
        else:
            raise ValueError("Either plaintext 'pin' or ('pin_hash' and 'salt') must be provided")

    # -------------------------------------------------------------------------
    # Encapsulated Hash Generator & Validator
    # -------------------------------------------------------------------------
    @staticmethod
    def _hash_pin(pin: str, salt: str) -> str:
        """Internal helper computing salted SHA-256 digest."""
        payload = f"{salt}:{pin}".encode("utf-8")
        return hashlib.sha256(payload).hexdigest()

    def verify_pin(self, candidate_pin: str) -> bool:
        """
        Safely validates PIN without ever exposing the stored hash or salt to callers.
        """
        computed = self._hash_pin(candidate_pin, self.__salt)
        return computed == self.__pin_hash

    def change_pin(self, old_pin: str, new_pin: str) -> bool:
        """Controlled mutation of authentication secret."""
        if not self.verify_pin(old_pin):
            return False
        if len(new_pin) < 4 or not new_pin.isdigit():
            raise ValueError("PIN must be at least 4 digits")
        self.__salt = os.urandom(16).hex()
        self.__pin_hash = self._hash_pin(new_pin, self.__salt)
        return True

    # -------------------------------------------------------------------------
    # Public Read-Only Properties
    # -------------------------------------------------------------------------
    @property
    def customer_id(self) -> str:
        return self._customer_id

    @property
    def name(self) -> str:
        return self._name

    @property
    def email(self) -> str:
        return self._email

    @property
    def phone(self) -> str:
        return self._phone

    @property
    def created_at(self) -> datetime:
        return self._created_at

    @property
    def account_ids(self) -> List[str]:
        """Returns a defensive copy of linked account numbers."""
        return list(self._account_ids)

    # -------------------------------------------------------------------------
    # Account Management
    # -------------------------------------------------------------------------
    def link_account(self, account_number: str) -> None:
        """Associates an account with this customer profile."""
        if account_number not in self._account_ids:
            self._account_ids.append(account_number)

    def unlink_account(self, account_number: str) -> None:
        if account_number in self._account_ids:
            self._account_ids.remove(account_number)

    # -------------------------------------------------------------------------
    # Serialization / Persistence Helpers
    # -------------------------------------------------------------------------
    def export_credentials(self) -> Dict[str, str]:
        """Protected export helper for database persistence layer only."""
        return {
            "pin_hash": self.__pin_hash,
            "salt": self.__salt,
        }

    def to_dict(self, include_sensitive: bool = False) -> Dict[str, Any]:
        """Clean dictionary representation excluding sensitive secrets by default."""
        data = {
            "customer_id": self._customer_id,
            "name": self._name,
            "email": self._email,
            "phone": self._phone,
            "created_at": self._created_at.isoformat(),
            "accounts_count": len(self._account_ids),
            "account_ids": list(self._account_ids),
        }
        if include_sensitive:
            data.update(self.export_credentials())
        return data

    def __repr__(self) -> str:
        return f"<Customer id={self._customer_id} name={self._name} email={self._email}>"
