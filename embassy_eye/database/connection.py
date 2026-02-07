"""
Database connection management.
"""

import os
from contextlib import contextmanager
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session
from sqlalchemy.pool import NullPool

from .models import Base

# Get database URL from environment variable
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://embassy_user:embassy_pass@localhost:5432/embassy_eye"
)

# Create engine
# Use NullPool for serverless/short-lived connections
engine = create_engine(
    DATABASE_URL,
    poolclass=NullPool,
    echo=os.getenv("DB_ECHO", "false").lower() == "true"
)

# Create session factory
SessionLocal = scoped_session(sessionmaker(autocommit=False, autoflush=False, bind=engine))


def init_db():
    """Initialize database tables."""
    Base.metadata.create_all(bind=engine)
    print("✓ Database tables initialized")


@contextmanager
def get_db_session():
    """
    Context manager for database sessions.
    
    Usage:
        with get_db_session() as session:
            # Use session here
            session.add(obj)
            session.commit()
    """
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def get_db():
    """
    Get a database session (alternative to context manager).
    Remember to close the session when done.
    
    Usage:
        session = get_db()
        try:
            # Use session
            session.add(obj)
            session.commit()
        finally:
            session.close()
    """
    return SessionLocal()
