"""
Database models for embassy-eye.
"""

from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, Text
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()


class SlotStatistic(Base):
    """Table for tracking when slots were found."""
    
    __tablename__ = "slot_statistics"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    embassy = Column(String(100), nullable=False, index=True)
    location = Column(String(100), nullable=True, index=True)  # e.g., "subotica", "belgrade"
    service = Column(String(200), nullable=True)  # e.g., booking service ID
    detected_at = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)
    notes = Column(Text, nullable=True)  # Any additional information
    
    def __repr__(self):
        return f"<SlotStatistic(id={self.id}, embassy='{self.embassy}', location='{self.location}', detected_at='{self.detected_at}')>"


class BlockedVPN(Base):
    """Table for tracking blocked VPN IPs."""
    
    __tablename__ = "blocked_vpns"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    ip_address = Column(String(45), nullable=False, index=True)  # Supports IPv4 and IPv6
    country = Column(String(100), nullable=True, index=True)
    blocked_at = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)
    embassy = Column(String(100), nullable=True, index=True)  # Which embassy blocked it
    notes = Column(Text, nullable=True)  # Any additional context
    
    def __repr__(self):
        return f"<BlockedVPN(id={self.id}, ip='{self.ip_address}', country='{self.country}', blocked_at='{self.blocked_at}')>"


class RunStatistic(Base):
    """Table for tracking every scraper run and its outcome."""
    
    __tablename__ = "run_statistics"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    embassy = Column(String(100), nullable=False, index=True)  # "hungary" or "italy"
    location = Column(String(100), nullable=True, index=True)  # e.g., "subotica", "belgrade"
    service = Column(String(200), nullable=True)  # e.g., booking service ID for Italy
    run_at = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)
    
    # Outcome of the run (one of these):
    # - "slots_found" - slots available (no modal or positive indicators)
    # - "slots_found_captcha" - slots found but captcha required
    # - "slots_found_email_verification" - slots found but email verification required
    # - "no_slots_modal" - modal detected with "no appointments" message
    # - "ip_blocked" - IP was blocked
    # - "no_slots_other" - no slots but no modal detected (ambiguous)
    outcome = Column(String(50), nullable=False, index=True)
    
    ip_address = Column(String(45), nullable=True)  # IP used for this run
    country = Column(String(100), nullable=True)  # VPN country if available
    notes = Column(Text, nullable=True)  # Additional diagnostic information
    
    def __repr__(self):
        return f"<RunStatistic(id={self.id}, embassy='{self.embassy}', location='{self.location}', outcome='{self.outcome}', run_at='{self.run_at}')>"
