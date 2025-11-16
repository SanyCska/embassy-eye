#!/usr/bin/env python3
"""
Main runner that delegates to country-specific scrapers.
"""

import sys
import os

# Import country-specific scrapers
from ..scrapers.hungary.runner import fill_booking_form as fill_hungary_form
from ..scrapers.italy.runner import fill_italy_login_form


def fill_booking_form(scraper="hungary"):
    """
    Fill the booking form using the specified scraper.
    
    Args:
        scraper: The scraper to use ('hungary' or 'italy'). Defaults to 'hungary'.
    """
    scraper = scraper.lower()
    
    if scraper == "hungary":
        fill_hungary_form()
    elif scraper == "italy":
        fill_italy_login_form()
    else:
        print(f"✗ Error: Unknown scraper '{scraper}'. Available scrapers: 'hungary', 'italy'")
        sys.stdout.flush()
        return


if __name__ == "__main__":
    # Allow scraper selection via command line argument or environment variable
    scraper = "hungary"  # Default
    
    if len(sys.argv) > 1:
        scraper = sys.argv[1]
    elif os.getenv("SCRAPER"):
        scraper = os.getenv("SCRAPER")
    
    fill_booking_form(scraper)
