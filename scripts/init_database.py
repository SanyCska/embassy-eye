#!/usr/bin/env python3
"""
Script to initialize the database and run migrations.

This script will:
1. Check database connection
2. Create tables if they don't exist
3. Display current database status

Usage:
    python scripts/init_database.py
"""

import sys
from pathlib import Path

# Add parent directory to path to import embassy_eye
sys.path.insert(0, str(Path(__file__).parent.parent))

from embassy_eye.database import init_db, get_db_session
from embassy_eye.database.models import BlockedVPN, SlotStatistic


def check_connection():
    """Check if we can connect to the database."""
    try:
        with get_db_session() as session:
            result = session.execute("SELECT version();")
            version = result.fetchone()[0]
            print(f"✓ Database connection successful")
            print(f"  PostgreSQL version: {version}")
            return True
    except Exception as e:
        print(f"✗ Database connection failed: {e}")
        return False


def check_tables():
    """Check which tables exist."""
    try:
        with get_db_session() as session:
            # Check for slot_statistics table
            result = session.execute(
                "SELECT EXISTS (SELECT FROM information_schema.tables "
                "WHERE table_schema = 'public' AND table_name = 'slot_statistics');"
            )
            slot_stats_exists = result.fetchone()[0]
            
            # Check for blocked_vpns table
            result = session.execute(
                "SELECT EXISTS (SELECT FROM information_schema.tables "
                "WHERE table_schema = 'public' AND table_name = 'blocked_vpns');"
            )
            blocked_vpns_exists = result.fetchone()[0]
            
            print("\nTable status:")
            print(f"  slot_statistics: {'✓ exists' if slot_stats_exists else '✗ missing'}")
            print(f"  blocked_vpns: {'✓ exists' if blocked_vpns_exists else '✗ missing'}")
            
            return slot_stats_exists and blocked_vpns_exists
    except Exception as e:
        print(f"✗ Failed to check tables: {e}")
        return False


def show_counts():
    """Show record counts."""
    try:
        with get_db_session() as session:
            slot_count = session.query(SlotStatistic).count()
            blocked_count = session.query(BlockedVPN).count()
            
            print("\nRecord counts:")
            print(f"  Slot statistics: {slot_count}")
            print(f"  Blocked VPNs: {blocked_count}")
    except Exception as e:
        print(f"Warning: Could not get record counts: {e}")


def main():
    """Main function."""
    print("=" * 60)
    print("Embassy-Eye Database Initialization")
    print("=" * 60)
    print()
    
    # Check connection
    if not check_connection():
        print("\n❌ Cannot connect to database. Please check:")
        print("  1. PostgreSQL is running")
        print("  2. DATABASE_URL is set correctly in .env")
        print("  3. Database user and password are correct")
        sys.exit(1)
    
    # Check if tables exist
    tables_exist = check_tables()
    
    if not tables_exist:
        print("\n📦 Initializing database tables...")
        try:
            init_db()
            print("✓ Database tables created successfully")
        except Exception as e:
            print(f"✗ Failed to create tables: {e}")
            sys.exit(1)
        
        # Check again
        check_tables()
    else:
        print("\n✓ All required tables exist")
    
    # Show counts
    show_counts()
    
    print("\n" + "=" * 60)
    print("✓ Database initialization complete!")
    print("=" * 60)
    print("\nYou can now use the database with your scrapers.")
    print("\nUseful commands:")
    print("  - View blocked IPs: psql -h localhost -U embassy_user -d embassy_eye -c 'SELECT * FROM blocked_vpns ORDER BY blocked_at DESC LIMIT 10;'")
    print("  - View slot stats: psql -h localhost -U embassy_user -d embassy_eye -c 'SELECT * FROM slot_statistics ORDER BY detected_at DESC LIMIT 10;'")
    print()


if __name__ == "__main__":
    main()
