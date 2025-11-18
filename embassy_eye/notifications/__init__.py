"""
Notification utilities for embassy-eye.
"""

from .telegram import (
    send_result_notification,
    send_telegram_message,
    send_telegram_document,
)

__all__ = ["send_result_notification", "send_telegram_message", "send_telegram_document"]

