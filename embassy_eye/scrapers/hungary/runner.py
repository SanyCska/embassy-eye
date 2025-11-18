#!/usr/bin/env python3
"""
Script to fill the booking form on konzinfobooking.mfa.gov.hu
"""

import sys
import datetime
from pathlib import Path

from ...automation import (
    check_appointment_availability,
    click_next_button,
    create_driver,
    detect_blocked_ip,
    fill_fields_by_map,
    fill_reenter_email_field,
    fill_remaining_fields,
    fill_select_dropdowns,
    fill_textareas,
    get_full_page_screenshot,
    inspect_form_fields,
    navigate_to_booking_page,
    select_consulate_option,
    select_visa_type_option,
)
from ...notifications import send_result_notification, send_telegram_message
from ...runner.cooldown import check_and_handle_cooldown, save_captcha_cooldown


def fill_booking_form():
    """Fill the booking form with acceptable values and click save (without submitting)"""
    
    print("=" * 60)
    print(f"Starting embassy-eye (Hungary) at {datetime.datetime.now()}")
    print("=" * 60)
    sys.stdout.flush()
    
    # Check for captcha cooldown
    should_skip, cooldown_message = check_and_handle_cooldown()
    if should_skip:
        print(f"\n⏸️  {cooldown_message}")
        print("=" * 60)
        sys.stdout.flush()
        return
    elif cooldown_message:
        print(f"\nℹ️  {cooldown_message}")
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

        # Immediately check if access is blocked by IP
        blocked_ip = detect_blocked_ip(driver)
        if blocked_ip:
            print("  Detected blocked IP right after page load. Aborting run.")
            return
        
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
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            html_path = Path("screenshots") / f"filled_0_fields_{timestamp}.html"
            try:
                html_path.parent.mkdir(parents=True, exist_ok=True)
                with html_path.open("w", encoding="utf-8") as f:
                    f.write(driver.page_source)
                print(f"Saved HTML to {html_path}")
                # Send success notification
                send_telegram_message(f"✅ HTML saved successfully\n\nFile: {html_path}\nReason: No fields were filled (0 fields)")
            except PermissionError as e:
                error_msg = f"❌ Failed to save HTML: Permission denied\n\nFile: {html_path}\nError: {e}\n\nThis is not critical, script continues..."
                print(f"  Warning: Permission denied saving HTML to {html_path}: {e}")
                print("  This is not critical, continuing...")
                send_telegram_message(error_msg)
            except Exception as e:
                error_msg = f"❌ Failed to save HTML\n\nFile: {html_path}\nError: {e}\n\nThis is not critical, script continues..."
                print(f"  Warning: Failed to save HTML: {e}")
                print("  This is not critical, continuing...")
                send_telegram_message(error_msg)
        
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
            result = check_appointment_availability(driver)
            
            # Handle tuple return (slots_available, special_case) or boolean for backward compatibility
            if isinstance(result, tuple):
                slots_available, special_case = result
            else:
                slots_available = result
                special_case = None
            
            # Only send notification if slots are found
            if special_case == "ip_blocked":
                print("  🚫 IP blocked detected. Please switch network.")
                print("  Details saved to logs/blocked_ips.log")
            elif slots_available:
                print("\n[8/8] Sending notification...")
                sys.stdout.flush()
                
                # Save HTML only if it's not a captcha case
                if special_case != "captcha_required":
                    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
                    html_path = Path("screenshots") / f"slots_found_{timestamp}.html"
                    try:
                        html_path.parent.mkdir(parents=True, exist_ok=True)
                        with html_path.open("w", encoding="utf-8") as f:
                            f.write(driver.page_source)
                        print(f"  Saved page HTML to {html_path}")
                        # Send success notification
                        send_telegram_message(f"✅ HTML saved successfully\n\nFile: {html_path}\nReason: Slots found!")
                    except PermissionError as html_err:
                        error_msg = f"❌ Failed to save HTML: Permission denied\n\nFile: {html_path}\nError: {html_err}\n\nThis is not critical, script continues..."
                        print(f"  Warning: Permission denied saving page HTML: {html_err}")
                        print("  This is not critical, continuing...")
                        send_telegram_message(error_msg)
                    except Exception as html_err:
                        error_msg = f"❌ Failed to save HTML\n\nFile: {html_path}\nError: {html_err}\n\nThis is not critical, script continues..."
                        print(f"  Warning: Failed to save page HTML: {html_err}")
                        print("  This is not critical, continuing...")
                        send_telegram_message(error_msg)
                else:
                    print("  Skipping HTML save (captcha case)")
                
                if special_case in ("captcha_required", "email_verification"):
                    # Send notification without screenshot for special cases
                    send_result_notification(slots_available, None, special_case=special_case)
                    case_name = "captcha required" if special_case == "captcha_required" else "email verification"
                    print(f"✓ Notification sent (no screenshot - {case_name} required)")
                    
                    # Save cooldown if captcha is required
                    if special_case == "captcha_required":
                        save_captcha_cooldown()
                else:
                    print("  Capturing full page screenshot...")
                    sys.stdout.flush()
                    screenshot_bytes = get_full_page_screenshot(driver)
                    send_result_notification(slots_available, screenshot_bytes, special_case=None)
                    print("✓ Notification sent")
            else:
                print("  No slots available")
            sys.stdout.flush()
        else:
            print("  Next button not found or not clickable")
            sys.stdout.flush()
            blocked_ip = detect_blocked_ip(driver)
            if blocked_ip:
                print("  🚫 IP blocked detected after failing to find next button.")
                print("  Details saved to logs/blocked_ips.log")
        
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

