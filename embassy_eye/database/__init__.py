"""
Database package for embassy-eye.
"""

from .connection import get_db_session, init_db
from .models import BlockedVPN, SlotStatistic
from .operations import (
    log_blocked_ip,
    log_slot_found,
    is_ip_already_blocked,
    get_recent_blocked_ips,
    get_slot_statistics,
)

__all__ = [
    "get_db_session",
    "init_db",
    "BlockedVPN",
    "SlotStatistic",
    "log_blocked_ip",
    "log_slot_found",
    "is_ip_already_blocked",
    "get_recent_blocked_ips",
    "get_slot_statistics",
]
