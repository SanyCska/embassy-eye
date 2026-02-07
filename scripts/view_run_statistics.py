#!/usr/bin/env python3
"""
View run statistics from the database.

This script provides various views of the run statistics:
- Recent runs
- Summary by outcome
- Success rate analysis
"""

import argparse
import sys
from datetime import datetime, timedelta
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from embassy_eye.database import (
    get_run_statistics,
    get_run_statistics_summary,
    get_db_session
)
from embassy_eye.database.models import RunStatistic
from sqlalchemy import func


def print_recent_runs(days=7, limit=50, embassy=None, location=None):
    """Print recent run statistics."""
    print("=" * 80)
    print(f"RECENT RUNS (Last {days} days)")
    print("=" * 80)
    
    runs = get_run_statistics(days=days, limit=limit, embassy=embassy, location=location)
    
    if not runs:
        print("No runs found.")
        return
    
    print(f"\nTotal runs: {len(runs)}")
    print()
    
    # Print header
    print(f"{'Date/Time':<20} {'Embassy':<10} {'Location':<12} {'Outcome':<30} {'Country':<10}")
    print("-" * 80)
    
    # Print runs
    for run in runs:
        date_str = run['run_at'].strftime('%Y-%m-%d %H:%M:%S')
        embassy = run['embassy'] or '-'
        location = run['location'] or '-'
        outcome = run['outcome']
        country = run['country'] or '-'
        
        print(f"{date_str:<20} {embassy:<10} {location:<12} {outcome:<30} {country:<10}")
    
    print()


def print_summary(days=7, embassy=None):
    """Print summary statistics."""
    print("=" * 80)
    print(f"RUN STATISTICS SUMMARY (Last {days} days)")
    print("=" * 80)
    
    summary = get_run_statistics_summary(days=days, embassy=embassy)
    
    if not summary:
        print("No statistics found.")
        return
    
    # Group by location
    locations = set()
    for key in summary.keys():
        location = key.split('_')[0]
        locations.add(location)
    
    for location in sorted(locations):
        print(f"\nLocation: {location.upper()}")
        print("-" * 40)
        
        total = 0
        for key, count in summary.items():
            if key.startswith(f"{location}_"):
                outcome = key.replace(f"{location}_", "")
                print(f"  {outcome:<30} {count:>5}")
                total += count
        
        print(f"  {'TOTAL':<30} {total:>5}")
    
    print()


def print_detailed_stats(days=7, embassy=None):
    """Print detailed statistics with percentages."""
    print("=" * 80)
    print(f"DETAILED STATISTICS (Last {days} days)")
    print("=" * 80)
    
    try:
        from sqlalchemy import func
        
        with get_db_session() as session:
            cutoff = datetime.utcnow() - timedelta(days=days)
            query = session.query(
                RunStatistic.location,
                RunStatistic.outcome,
                func.count(RunStatistic.id).label('count')
            ).filter(
                RunStatistic.run_at >= cutoff
            )
            
            if embassy:
                query = query.filter(RunStatistic.embassy == embassy)
            
            results = query.group_by(
                RunStatistic.location,
                RunStatistic.outcome
            ).all()
            
            # Calculate totals per location
            location_totals = {}
            location_stats = {}
            
            for location, outcome, count in results:
                loc = location or 'unknown'
                if loc not in location_totals:
                    location_totals[loc] = 0
                    location_stats[loc] = {}
                location_totals[loc] += count
                location_stats[loc][outcome] = count
            
            # Print statistics
            for location in sorted(location_stats.keys()):
                total = location_totals[location]
                stats = location_stats[location]
                
                print(f"\n{location.upper()}")
                print("-" * 80)
                print(f"Total runs: {total}")
                print()
                
                # Categorize outcomes
                slots_found = (
                    stats.get('slots_found', 0) +
                    stats.get('slots_found_captcha', 0) +
                    stats.get('slots_found_email_verification', 0)
                )
                no_slots_modal = stats.get('no_slots_modal', 0)
                ip_blocked = stats.get('ip_blocked', 0)
                no_slots_other = stats.get('no_slots_other', 0)
                
                print("Outcome Categories:")
                print(f"  ✅ Slots Found:          {slots_found:>5} ({slots_found/total*100:>5.1f}%)")
                if stats.get('slots_found'):
                    print(f"     - Available:          {stats['slots_found']:>5}")
                if stats.get('slots_found_captcha'):
                    print(f"     - Captcha required:   {stats['slots_found_captcha']:>5}")
                if stats.get('slots_found_email_verification'):
                    print(f"     - Email verification: {stats['slots_found_email_verification']:>5}")
                
                print(f"  ❌ No Slots (Modal):      {no_slots_modal:>5} ({no_slots_modal/total*100:>5.1f}%)")
                print(f"  🚫 IP Blocked:            {ip_blocked:>5} ({ip_blocked/total*100:>5.1f}%)")
                print(f"  ⚠️  No Slots (Other):     {no_slots_other:>5} ({no_slots_other/total*100:>5.1f}%)")
                print()
                
                # Calculate success rate (slots found / (slots found + no slots modal))
                relevant_runs = slots_found + no_slots_modal
                if relevant_runs > 0:
                    success_rate = slots_found / relevant_runs * 100
                    print(f"Success Rate (excluding IP blocks & ambiguous): {success_rate:.1f}%")
                    print(f"  (Based on {relevant_runs} runs with clear outcomes)")
                
                print()
            
    except Exception as e:
        print(f"Error getting detailed statistics: {e}")
        import traceback
        traceback.print_exc()


def main():
    parser = argparse.ArgumentParser(
        description="View run statistics from the database",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # View recent runs
  python scripts/view_run_statistics.py --recent

  # View summary for last 7 days
  python scripts/view_run_statistics.py --summary

  # View detailed statistics for last 30 days
  python scripts/view_run_statistics.py --detailed --days 30

  # View statistics for specific location
  python scripts/view_run_statistics.py --detailed --location subotica

  # View statistics for Hungary only
  python scripts/view_run_statistics.py --detailed --embassy hungary
        """
    )
    
    parser.add_argument(
        '--recent',
        action='store_true',
        help='Show recent runs'
    )
    parser.add_argument(
        '--summary',
        action='store_true',
        help='Show summary statistics'
    )
    parser.add_argument(
        '--detailed',
        action='store_true',
        help='Show detailed statistics with percentages'
    )
    parser.add_argument(
        '--days',
        type=int,
        default=7,
        help='Number of days to look back (default: 7)'
    )
    parser.add_argument(
        '--limit',
        type=int,
        default=50,
        help='Limit number of recent runs to show (default: 50)'
    )
    parser.add_argument(
        '--embassy',
        choices=['hungary', 'italy'],
        help='Filter by embassy'
    )
    parser.add_argument(
        '--location',
        help='Filter by location (e.g., subotica, belgrade)'
    )
    
    args = parser.parse_args()
    
    # If no flags provided, show everything
    if not (args.recent or args.summary or args.detailed):
        args.detailed = True
        args.summary = True
    
    try:
        if args.detailed:
            print_detailed_stats(days=args.days, embassy=args.embassy)
        
        if args.summary:
            print_summary(days=args.days, embassy=args.embassy)
        
        if args.recent:
            print_recent_runs(
                days=args.days,
                limit=args.limit,
                embassy=args.embassy,
                location=args.location
            )
            
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
