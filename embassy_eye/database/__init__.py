"""
Database package for embassy-eye.
"""

from .connection import get_db_session, init_db
from .models import BlockedVPN, SlotStatistic, RunStatistic
from .operations import (
    log_blocked_ip,
    log_slot_found,
    log_run_statistic,
    is_ip_already_blocked,
    get_recent_blocked_ips,
    get_slot_statistics,
    get_run_statistics,
    get_run_statistics_summary,
)

__all__ = [
    "get_db_session",
    "init_db",
    "BlockedVPN",
    "SlotStatistic",
    "RunStatistic",
    "log_blocked_ip",
    "log_slot_found",
    "log_run_statistic",
    "is_ip_already_blocked",
    "get_recent_blocked_ips",
    "get_slot_statistics",
    "get_run_statistics",
    "get_run_statistics_summary",
]
