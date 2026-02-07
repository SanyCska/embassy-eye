"""
Database operations for embassy-eye.
"""

from datetime import datetime
from typing import Optional

from .connection import get_db_session
from .models import BlockedVPN, SlotStatistic


def log_blocked_ip(
    ip_address: str,
    country: Optional[str] = None,
    embassy: Optional[str] = None,
    notes: Optional[str] = None
) -> BlockedVPN:
    """
    Log a blocked VPN IP to the database.
    
    Args:
        ip_address: The blocked IP address
        country: Country of the VPN server
        embassy: Which embassy blocked it (e.g., "hungary", "italy")
        notes: Additional context or information
    
    Returns:
        The created BlockedVPN record
    """
    try:
        with get_db_session() as session:
            blocked_vpn = BlockedVPN(
                ip_address=ip_address,
                country=country,
                embassy=embassy,
                blocked_at=datetime.utcnow(),
                notes=notes
            )
            session.add(blocked_vpn)
            session.commit()
            session.refresh(blocked_vpn)
            return blocked_vpn
    except Exception as e:
        print(f"  Warning: Failed to log blocked IP to database: {e}")
        # Don't raise - we don't want to break the main flow
        return None


def log_slot_found(
    embassy: str,
    location: Optional[str] = None,
    service: Optional[str] = None,
    notes: Optional[str] = None
) -> SlotStatistic:
    """
    Log when a slot was found.
    
    Args:
        embassy: The embassy name (e.g., "hungary", "italy")
        location: Specific location (e.g., "subotica", "belgrade")
        service: Service identifier (e.g., booking service ID)
        notes: Additional information
    
    Returns:
        The created SlotStatistic record
    """
    try:
        with get_db_session() as session:
            slot_stat = SlotStatistic(
                embassy=embassy,
                location=location,
                service=service,
                detected_at=datetime.utcnow(),
                notes=notes
            )
            session.add(slot_stat)
            session.commit()
            session.refresh(slot_stat)
            return slot_stat
    except Exception as e:
        print(f"  Warning: Failed to log slot statistic to database: {e}")
        # Don't raise - we don't want to break the main flow
        return None


def is_ip_already_blocked(ip_address: str, hours: int = 24) -> bool:
    """
    Check if an IP was already blocked recently.
    
    Args:
        ip_address: The IP to check
        hours: How many hours to look back (default: 24)
    
    Returns:
        True if the IP was blocked in the last N hours, False otherwise
    """
    try:
        from datetime import timedelta
        
        with get_db_session() as session:
            cutoff = datetime.utcnow() - timedelta(hours=hours)
            result = session.query(BlockedVPN).filter(
                BlockedVPN.ip_address == ip_address,
                BlockedVPN.blocked_at >= cutoff
            ).first()
            return result is not None
    except Exception as e:
        print(f"  Warning: Failed to check if IP is blocked: {e}")
        return False


def get_recent_blocked_ips(hours: int = 24, limit: int = 100):
    """
    Get recently blocked IPs.
    
    Args:
        hours: How many hours to look back (default: 24)
        limit: Maximum number of records to return
    
    Returns:
        List of BlockedVPN records
    """
    try:
        from datetime import timedelta
        
        with get_db_session() as session:
            cutoff = datetime.utcnow() - timedelta(hours=hours)
            results = session.query(BlockedVPN).filter(
                BlockedVPN.blocked_at >= cutoff
            ).order_by(BlockedVPN.blocked_at.desc()).limit(limit).all()
            
            # Detach from session for safe return
            return [
                {
                    'id': r.id,
                    'ip_address': r.ip_address,
                    'country': r.country,
                    'blocked_at': r.blocked_at,
                    'embassy': r.embassy,
                    'notes': r.notes
                }
                for r in results
            ]
    except Exception as e:
        print(f"  Warning: Failed to fetch recent blocked IPs: {e}")
        return []


def get_slot_statistics(days: int = 7, limit: int = 100):
    """
    Get recent slot statistics.
    
    Args:
        days: How many days to look back (default: 7)
        limit: Maximum number of records to return
    
    Returns:
        List of SlotStatistic records
    """
    try:
        from datetime import timedelta
        
        with get_db_session() as session:
            cutoff = datetime.utcnow() - timedelta(days=days)
            results = session.query(SlotStatistic).filter(
                SlotStatistic.detected_at >= cutoff
            ).order_by(SlotStatistic.detected_at.desc()).limit(limit).all()
            
            # Detach from session for safe return
            return [
                {
                    'id': r.id,
                    'embassy': r.embassy,
                    'location': r.location,
                    'service': r.service,
                    'detected_at': r.detected_at,
                    'notes': r.notes
                }
                for r in results
            ]
    except Exception as e:
        print(f"  Warning: Failed to fetch slot statistics: {e}")
        return []
