#!/usr/bin/env python3
"""
Script to fill the booking form on konzinfobooking.mfa.gov.hu
"""

import sys
import datetime
from pathlib import Path

from webdriver_utils import create_driver, navigate_to_booking_page, inspect_form_fields
from dropdown_handlers import select_consulate_option, select_visa_type_option
from form_helpers import (
    fill_select_dropdowns,
    fill_reenter_email_field,
    fill_fields_by_map,
    fill_remaining_fields,
    fill_textareas
)
from button_handlers import click_next_button
from modal_checker import check_appointment_availability
from telegram_notifier import send_result_notification


def fill_booking_form():
    """Fill the booking form with acceptable values and click save (without submitting)"""
    
    print("=" * 60)
    print(f"Starting embassy-eye at {datetime.datetime.now()}")
    print("=" * 60)
    sys.stdout.flush()
    
    # Initialize Chrome driver
    print("\n[1/8] Initializing Chrome driver...")
    sys.stdout.flush()  # Force output to appear immediately
    
    try:
        driver = create_driver(headless=True)
        print("✓ Chrome driver initialized successfully")
        sys.stdout.flush()
    except Exception as e:
        print(f"✗ Failed to initialize Chrome driver: {e}")
        import traceback
        traceback.print_exc()
        sys.stdout.flush()
        return
    
    try:
        # Navigate to the booking page
        print("\n[2/8] Navigating to booking page...")
        sys.stdout.flush()
        wait = navigate_to_booking_page(driver)
        print("✓ Page loaded")
        sys.stdout.flush()
        
        # Inspect form fields
        print("\n[3/8] Inspecting form fields...")
        sys.stdout.flush()
        inputs, selects, textareas = inspect_form_fields(driver)
        print("✓ Form fields inspected")
        sys.stdout.flush()

        print("\n[4/8] Starting form filling...")
        sys.stdout.flush()
        
        # Step 1: Select consulate option (Serbia - Subotica)
        print("  → Selecting consulate...")
        sys.stdout.flush()
        select_consulate_option(driver)
        
        # Step 2: Select visa type option
        print("  → Selecting visa type...")
        sys.stdout.flush()
        select_visa_type_option(driver)
        
        # Fill standard HTML select dropdowns
        print("  → Filling select dropdowns...")
        sys.stdout.flush()
        fill_select_dropdowns(driver, selects)
        
        # Fill form fields with default data
        filled_count = 0
        
        # Fill re-enter email field (special handling)
        print("  → Filling email field...")
        sys.stdout.flush()
        filled_count += fill_reenter_email_field(driver)
        
        # Fill fields by field map
        print("  → Filling mapped fields...")
        sys.stdout.flush()
        filled_count += fill_fields_by_map(driver)
        
        # Fill any remaining fields
        print("  → Filling remaining fields...")
        sys.stdout.flush()
        filled_count += fill_remaining_fields(driver, inputs)
        
        # Fill textareas
        print("  → Filling textareas...")
        sys.stdout.flush()
        filled_count += fill_textareas(driver, textareas, wait)
        
        print(f"\n[5/8] Summary: Filled {filled_count} field(s)")
        sys.stdout.flush()
        
        # If nothing was filled, persist the current page HTML once for offline inspection
        if filled_count == 0:
            html_path = Path("screenshots/filled_0_fields.html")
            try:
                if not html_path.exists():
                    html_path.parent.mkdir(parents=True, exist_ok=True)
                    with html_path.open("w", encoding="utf-8") as f:
                        f.write(driver.page_source)
                    print(f"Saved HTML to {html_path}")
                else:
                    print(f"HTML already exists at {html_path}, skipping download")
            except Exception as e:
                print(f"Failed to save HTML: {e}")
        
        # Click the next button
        print("\n[6/8] Clicking next button...")
        sys.stdout.flush()
        slots_available = None
        if click_next_button(driver):
            print("✓ Next button clicked")
            sys.stdout.flush()
            # Check for appointment availability
            print("\n[7/8] Checking appointment availability...")
            sys.stdout.flush()
            slots_available = check_appointment_availability(driver)
            
            # Only send notification if slots are found
            if slots_available:
                print("\n[8/8] Sending notification...")
                sys.stdout.flush()
                screenshot_bytes = driver.get_screenshot_as_png()
                send_result_notification(slots_available, screenshot_bytes)
                print("✓ Notification sent")
            else:
                print("  No slots available")
            sys.stdout.flush()
        else:
            print("  Next button not found or not clickable")
            sys.stdout.flush()
        
        # Keep browser open for inspection (only if not headless)
        # Since we're in headless mode, skip the inspection delay
        
    except Exception as e:
        print(f"\n✗ Error occurred: {e}")
        import traceback
        traceback.print_exc()
        sys.stdout.flush()
    finally:
        print("\n[Cleanup] Closing browser...")
        sys.stdout.flush()
        try:
            driver.quit()
            print("✓ Browser closed")
        except Exception as e:
            print(f"  Warning: Error closing browser: {e}")
        sys.stdout.flush()
        print("=" * 60)
        print(f"Finished at {datetime.datetime.now()}")
        print("=" * 60)
        sys.stdout.flush()


if __name__ == "__main__":
    fill_booking_form()
