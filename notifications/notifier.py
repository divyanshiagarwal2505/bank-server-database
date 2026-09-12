"""
Notification system showcasing ABSTRACTION, INHERITANCE, and POLYMORPHISM.

Hierarchy:
BaseNotifier (Abstract Base Class)
  ├── ConsoleAuditNotifier (Default server logger)
  ├── EmailNotifier
  ├── SMSNotifier
  └── CompositeNotifier (Broadcasts to multiple polymorphic notifiers)
"""
from abc import ABC, abstractmethod
import logging
from typing import List

logger = logging.getLogger("BankNotification")


class BaseNotifier(ABC):
    """
    [OOP Pillar: ABSTRACTION]
    Defines the contract for all alert dispatch mechanisms.
    """

    @abstractmethod
    def send_notification(self, recipient: str, subject: str, message: str) -> bool:
        """Sends an alert to a recipient."""
        pass


class ConsoleAuditNotifier(BaseNotifier):
    """
    [OOP Pillar: INHERITANCE & POLYMORPHISM]
    Logs notifications directly to standard logging system.
    """

    def send_notification(self, recipient: str, subject: str, message: str) -> bool:
        logger.info(f"[AUDIT ALERT] To: {recipient} | Subject: {subject} | Body: {message}")
        return True


class EmailNotifier(BaseNotifier):
    """
    [OOP Pillar: INHERITANCE & POLYMORPHISM]
    Simulates email dispatch with templating and delivery tracking.
    """

    def __init__(self, smtp_host: str = "smtp.securebank.com"):
        self._smtp_host = smtp_host
        self.sent_count = 0

    def send_notification(self, recipient: str, subject: str, message: str) -> bool:
        if "@" not in recipient:
            return False
        logger.info(f"[EMAIL via {self._smtp_host}] To: <{recipient}> | {subject}: {message}")
        self.sent_count += 1
        return True


class SMSNotifier(BaseNotifier):
    """
    [OOP Pillar: INHERITANCE & POLYMORPHISM]
    Simulates SMS telecommunication gateway dispatch.
    """

    def __init__(self, sender_id: str = "SECURE_BANK"):
        self._sender_id = sender_id
        self.sent_count = 0

    def send_notification(self, recipient: str, subject: str, message: str) -> bool:
        # Standard SMS formatting
        sms_text = f"[{self._sender_id}] {subject}: {message}"
        logger.info(f"[SMS] To: {recipient} | Text: {sms_text}")
        self.sent_count += 1
        return True


class CompositeNotifier(BaseNotifier):
    """
    [OOP Pillar: POLYMORPHISM]
    Demonstrates the Composite Design Pattern.
    Holds a collection of polymorphic BaseNotifier instances and broadcasts to each.
    """

    def __init__(self, notifiers: List[BaseNotifier] = None):
        self._notifiers: List[BaseNotifier] = list(notifiers or [])

    def add_notifier(self, notifier: BaseNotifier) -> None:
        if not isinstance(notifier, BaseNotifier):
            raise TypeError("Notifier must inherit from BaseNotifier")
        self._notifiers.append(notifier)

    def send_notification(self, recipient: str, subject: str, message: str) -> bool:
        """Polymorphically calls send_notification on every registered channel."""
        success = True
        for notifier in self._notifiers:
            try:
                ok = notifier.send_notification(recipient, subject, message)
                if not ok:
                    success = False
            except Exception as ex:
                logger.error(f"Failed to dispatch alert via {notifier.__class__.__name__}: {ex}")
                success = False
        return success
