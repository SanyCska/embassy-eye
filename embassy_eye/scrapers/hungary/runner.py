#!/usr/bin/env python3
"""
Script to fill the booking form on konzinfobooking.mfa.gov.hu
"""

import sys
import time
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
from ...notifications import send_result_notification, send_telegram_message, send_healthcheck_reloaded_page
from ...runner.cooldown import check_and_handle_cooldown, save_captcha_cooldown
from .config import BOOKING_URL, PAGE_LOAD_WAIT


def fill_and_submit_form(driver, wait, location="subotica"):
    """Fill the booking form and submit it. Returns (slots_available, special_case, diagnostic_info)."""
    # Inspect form fields
    print("\n[3/8] Inspecting form fields...")
    sys.stdout.flush()
    inputs, selects, textareas = inspect_form_fields(driver)
    print("✓ Form fields inspected")
    sys.stdout.flush()

    print("\n[4/8] Starting form filling...")
    sys.stdout.flush()
    
    # Step 1: Select consulate option (Serbia - Subotica or Serbia - Belgrade)
    location_display = location.capitalize()
    print(f"  → Selecting consulate ({location_display})...")
    sys.stdout.flush()
    select_consulate_option(driver, location=location)
    
    # Step 2: Select visa type option
    print("  → Selecting visa type...")
    sys.stdout.flush()
    select_visa_type_option(driver, location=location)
    
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
    
    # If nothing was filled, return early with special case
    if filled_count == 0:
        print("  ⚠️  No fields were filled - will trigger retry")
        sys.stdout.flush()
        return None, "no_fields_filled", {"filled_count": 0}
    
    # Click the next button
    print("\n[6/8] Clicking next button...")
    sys.stdout.flush()
    slots_available = None
    special_case = None
    diagnostic_info = {}
    
    if click_next_button(driver):
        print("✓ Next button clicked")
        sys.stdout.flush()
        # Check for appointment availability
        print("\n[7/8] Checking appointment availability...")
        sys.stdout.flush()
        result = check_appointment_availability(driver, location=location)
        
        # Handle tuple return (slots_available, special_case, diagnostic_info) or boolean for backward compatibility
        if isinstance(result, tuple):
            if len(result) == 3:
                slots_available, special_case, diagnostic_info = result
            elif len(result) == 2:
                slots_available, special_case = result
                diagnostic_info = {}
            else:
                slots_available = result[0]
                special_case = None
                diagnostic_info = {}
        else:
            slots_available = result
            special_case = None
            diagnostic_info = {}
    else:
        print("  Next button not found or not clickable")
        sys.stdout.flush()
        blocked_ip = detect_blocked_ip(driver)
        if blocked_ip:
            print("  🚫 IP blocked detected after failing to find next button.")
            print("  Details saved to logs/blocked_ips.log")
            special_case = "ip_blocked"
    
    return slots_available, special_case, diagnostic_info


def fill_booking_form(location="subotica"):
    """Fill the booking form with acceptable values and click save (without submitting)
    
    Args:
        location: Either 'subotica' or 'belgrade' to select the appropriate consulate
    """
    location_display = location.capitalize()
    print("=" * 60)
    print(f"Starting embassy-eye (Hungary - {location_display}) at {datetime.datetime.now()}")
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
            print("  Exit code 2 will trigger VPN IP rotation and retry.")
            sys.exit(2)  # Special exit code for IP blocked - triggers VPN rotation
        
        # Try form filling and submission (with retry logic)
        attempt = 1
        max_attempts = 2
        slots_available = None
        special_case = None
        diagnostic_info = {}
        
        while attempt <= max_attempts:
            if attempt > 1:
                print(f"\n{'='*60}")
                print(f"Retry attempt {attempt}/{max_attempts}: Reloading page and filling form again...")
                print(f"{'='*60}")
                sys.stdout.flush()
                
                # Reload the page
                print("\n[Retry] Reloading page...")
                sys.stdout.flush()
                driver.refresh()
                time.sleep(3)  # Wait for page to reload
                
                # Send healthcheck notification for reloaded page
                reason = None
                if special_case == "no_fields_filled":
                    reason = "No fields were filled"
                elif slots_available and special_case is None and not diagnostic_info.get('modal_found', False):
                    reason = "Slots detected but no modal found"
                send_healthcheck_reloaded_page(reason, location=location)
                
                # Re-initialize wait after reload
                from selenium.webdriver.support.ui import WebDriverWait
                wait = WebDriverWait(driver, PAGE_LOAD_WAIT)
                
                # Check if IP is blocked after reload
                blocked_ip = detect_blocked_ip(driver)
                if blocked_ip:
                    print("  Detected blocked IP after page reload. Aborting run.")
                    print("  Exit code 2 will trigger VPN IP rotation and retry.")
                    sys.exit(2)  # Special exit code for IP blocked - triggers VPN rotation
            
            # Fill and submit the form
            slots_available, special_case, diagnostic_info = fill_and_submit_form(driver, wait, location=location)
            
            # Check if IP was blocked during form submission
            if special_case == "ip_blocked":
                print("  🚫 IP blocked detected during form submission.")
                print("  Exit code 2 will trigger VPN IP rotation and retry.")
                sys.exit(2)  # Special exit code for IP blocked - triggers VPN rotation
            
            # Check if we should retry
            # Retry if: 0 fields filled OR (slots detected but no modal found)
            should_retry = False
            if attempt < max_attempts:
                if special_case == "no_fields_filled":
                    should_retry = True
                    print(f"\n⚠️  No fields were filled. Will retry once by reloading page...")
                elif slots_available and special_case is None and not diagnostic_info.get('modal_found', False):
                    should_retry = True
                    print(f"\n⚠️  Slots detected but no modal found. Will retry once by reloading page...")
            
            if should_retry:
                sys.stdout.flush()
                attempt += 1
                continue
            else:
                # No retry needed, break out of loop
                break
        
        # Process the result
        if special_case == "ip_blocked":
            print("  🚫 IP blocked detected. Please switch network.")
            print("  Details saved to logs/blocked_ips.log")
        elif special_case == "no_fields_filled":
            print("  ⚠️  No fields were filled after retry. Ending Hungary scraping for this run.")
            sys.stdout.flush()
        elif slots_available:
            print("\n[8/8] Sending notification...")
            sys.stdout.flush()
            
            # Save HTML only if it's not a captcha or email verification case
            if special_case not in ("captcha_required", "email_verification"):
                timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
                html_path = Path("screenshots") / f"slots_found_{timestamp}.html"
                try:
                    html_path.parent.mkdir(parents=True, exist_ok=True)
                    with html_path.open("w", encoding="utf-8") as f:
                        f.write(driver.page_source)
                    print(f"  Saved page HTML to {html_path}")
                    
                    # Build diagnostic message
                    diag_msg_parts = [
                        f"✅ HTML saved successfully",
                        f"",
                        f"File: {html_path}",
                        f"Reason: Slots found!",
                        f""
                    ]
                    
                    # Add diagnostic information
                    if diagnostic_info:
                        diag_msg_parts.append("📊 Diagnostic Info:")
                        if diagnostic_info.get('url'):
                            diag_msg_parts.append(f"URL: {diagnostic_info['url']}")
                        if diagnostic_info.get('title'):
                            diag_msg_parts.append(f"Page Title: {diagnostic_info['title']}")
                        if 'alert_found' in diagnostic_info:
                            diag_msg_parts.append(f"Alert Element: {'Found' if diagnostic_info['alert_found'] else 'Not Found'}")
                            if diagnostic_info.get('alert_text'):
                                alert_snippet = diagnostic_info['alert_text'][:150]
                                diag_msg_parts.append(f"Alert Text: {alert_snippet}...")
                        if 'modal_found' in diagnostic_info:
                            diag_msg_parts.append(f"No-Slots Modal: {'Found' if diagnostic_info['modal_found'] else 'Not Found'}")
                        if 'on_booking_form' in diagnostic_info:
                            diag_msg_parts.append(f"On Booking Form: {diagnostic_info['on_booking_form']}")
                        if 'on_date_selection' in diagnostic_info:
                            diag_msg_parts.append(f"On Date Selection: {diagnostic_info['on_date_selection']}")
                        if 'select_date_button_found' in diagnostic_info:
                            if diagnostic_info['select_date_button_found']:
                                button_status = "Disabled" if diagnostic_info.get('select_date_button_disabled') else "Enabled"
                                button_text = diagnostic_info.get('select_date_button_text', 'N/A')
                                diag_msg_parts.append(f"Select Date Button: {button_status} (text: '{button_text}')")
                            else:
                                diag_msg_parts.append(f"Select Date Button: Not Found")
                        if 'page_contains_no_slots' in diagnostic_info:
                            diag_msg_parts.append(f"Page Contains 'No Slots': {diagnostic_info['page_contains_no_slots']}")
                        if diagnostic_info.get('page_text_snippet'):
                            text_snippet = diagnostic_info['page_text_snippet'][:200]
                            diag_msg_parts.append(f"Page Text Snippet: {text_snippet}...")
                    
                    diag_message = "\n".join(diag_msg_parts)
                    send_telegram_message(diag_message)
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
                case_name = "captcha" if special_case == "captcha_required" else "email verification"
                print(f"  Skipping HTML save ({case_name} case)")
            
            if special_case in ("captcha_required", "email_verification"):
                # Send notification without screenshot for special cases
                send_result_notification(slots_available, None, special_case=special_case, booking_url=BOOKING_URL, location=location)
                case_name = "captcha required" if special_case == "captcha_required" else "email verification"
                print(f"✓ Notification sent (no screenshot - {case_name} required)")
                
                # Save cooldown if captcha is required
                if special_case == "captcha_required":
                    save_captcha_cooldown()
            else:
                print("  Capturing full page screenshot...")
                sys.stdout.flush()
                screenshot_bytes = get_full_page_screenshot(driver)
                send_result_notification(slots_available, screenshot_bytes, special_case=None, booking_url=BOOKING_URL, location=location)
                print("✓ Notification sent")
        else:
            print("  No slots available")
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


def fill_booking_form_both_locations():
    """Fill booking forms for both Subotica and Belgrade in sequence, reloading browser between."""
    print("=" * 60)
    print(f"Starting embassy-eye (Hungary - Both Locations) at {datetime.datetime.now()}")
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
    sys.stdout.flush()
    
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
        # Run Subotica first
        print("\n" + "=" * 60)
        print("CHECKING SUBOTICA")
        print("=" * 60)
        _run_location_check(driver, "subotica")
        
        # Reload browser for Belgrade check
        print("\n" + "=" * 60)
        print("Reloading browser for Belgrade check...")
        print("=" * 60)
        driver.quit()
        time.sleep(2)
        
        # Reinitialize driver for Belgrade
        print("\n[1/8] Reinitializing Chrome driver for Belgrade...")
        sys.stdout.flush()
        driver = create_driver(headless=True)
        print("✓ Chrome driver reinitialized successfully")
        sys.stdout.flush()
        
        # Run Belgrade
        print("\n" + "=" * 60)
        print("CHECKING BELGRADE")
        print("=" * 60)
        _run_location_check(driver, "belgrade")
        
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
        print(f"Finished checking both locations at {datetime.datetime.now()}")
        print("=" * 60)
        sys.stdout.flush()


def _run_location_check(driver, location):
    """Helper function to run a single location check."""
    location_display = location.capitalize()
    
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
            print("  Exit code 2 will trigger VPN IP rotation and retry.")
            sys.exit(2)  # Special exit code for IP blocked - triggers VPN rotation
        
        # Try form filling and submission (with retry logic)
        attempt = 1
        max_attempts = 2
        slots_available = None
        special_case = None
        diagnostic_info = {}
        
        while attempt <= max_attempts:
            if attempt > 1:
                print(f"\n{'='*60}")
                print(f"Retry attempt {attempt}/{max_attempts}: Reloading page and filling form again...")
                print(f"{'='*60}")
                sys.stdout.flush()
                
                # Reload the page
                print("\n[Retry] Reloading page...")
                sys.stdout.flush()
                driver.refresh()
                time.sleep(3)  # Wait for page to reload
                
                # Send healthcheck notification for reloaded page
                reason = None
                if special_case == "no_fields_filled":
                    reason = "No fields were filled"
                elif slots_available and special_case is None and not diagnostic_info.get('modal_found', False):
                    reason = "Slots detected but no modal found"
                send_healthcheck_reloaded_page(reason, location=location)
                
                # Re-initialize wait after reload
                from selenium.webdriver.support.ui import WebDriverWait
                wait = WebDriverWait(driver, PAGE_LOAD_WAIT)
                
                # Check if IP is blocked after reload
                blocked_ip = detect_blocked_ip(driver)
                if blocked_ip:
                    print("  Detected blocked IP after page reload. Aborting run.")
                    print("  Exit code 2 will trigger VPN IP rotation and retry.")
                    sys.exit(2)  # Special exit code for IP blocked - triggers VPN rotation
            
            # Fill and submit the form
            slots_available, special_case, diagnostic_info = fill_and_submit_form(driver, wait, location=location)
            
            # Check if IP was blocked during form submission
            if special_case == "ip_blocked":
                print("  🚫 IP blocked detected during form submission.")
                print("  Exit code 2 will trigger VPN IP rotation and retry.")
                sys.exit(2)  # Special exit code for IP blocked - triggers VPN rotation
            
            # Check if we should retry
            # Retry if: 0 fields filled OR (slots detected but no modal found)
            should_retry = False
            if attempt < max_attempts:
                if special_case == "no_fields_filled":
                    should_retry = True
                    print(f"\n⚠️  No fields were filled. Will retry once by reloading page...")
                elif slots_available and special_case is None and not diagnostic_info.get('modal_found', False):
                    should_retry = True
                    print(f"\n⚠️  Slots detected but no modal found. Will retry once by reloading page...")
            
            if should_retry:
                sys.stdout.flush()
                attempt += 1
                continue
            else:
                # No retry needed, break out of loop
                break
        
        # Process the result
        if special_case == "ip_blocked":
            print("  🚫 IP blocked detected. Please switch network.")
            print("  Details saved to logs/blocked_ips.log")
        elif special_case == "no_fields_filled":
            print(f"  ⚠️  No fields were filled after retry. Ending {location_display} scraping for this run.")
            sys.stdout.flush()
        elif slots_available:
            print("\n[8/8] Sending notification...")
            sys.stdout.flush()
            
            # Save HTML only if it's not a captcha or email verification case
            if special_case not in ("captcha_required", "email_verification"):
                timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
                html_path = Path("screenshots") / f"slots_found_{location}_{timestamp}.html"
                try:
                    html_path.parent.mkdir(parents=True, exist_ok=True)
                    with html_path.open("w", encoding="utf-8") as f:
                        f.write(driver.page_source)
                    print(f"  Saved page HTML to {html_path}")
                    
                    # Build diagnostic message
                    diag_msg_parts = [
                        f"✅ HTML saved successfully",
                        f"",
                        f"File: {html_path}",
                        f"Location: {location_display}",
                        f"Reason: Slots found!",
                        f""
                    ]
                    
                    # Add diagnostic information
                    if diagnostic_info:
                        diag_msg_parts.append("📊 Diagnostic Info:")
                        if diagnostic_info.get('url'):
                            diag_msg_parts.append(f"URL: {diagnostic_info['url']}")
                        if diagnostic_info.get('title'):
                            diag_msg_parts.append(f"Page Title: {diagnostic_info['title']}")
                        if 'alert_found' in diagnostic_info:
                            diag_msg_parts.append(f"Alert Element: {'Found' if diagnostic_info['alert_found'] else 'Not Found'}")
                            if diagnostic_info.get('alert_text'):
                                alert_snippet = diagnostic_info['alert_text'][:150]
                                diag_msg_parts.append(f"Alert Text: {alert_snippet}...")
                        if 'modal_found' in diagnostic_info:
                            diag_msg_parts.append(f"No-Slots Modal: {'Found' if diagnostic_info['modal_found'] else 'Not Found'}")
                        if 'on_booking_form' in diagnostic_info:
                            diag_msg_parts.append(f"On Booking Form: {diagnostic_info['on_booking_form']}")
                        if 'on_date_selection' in diagnostic_info:
                            diag_msg_parts.append(f"On Date Selection: {diagnostic_info['on_date_selection']}")
                        if 'select_date_button_found' in diagnostic_info:
                            if diagnostic_info['select_date_button_found']:
                                button_status = "Disabled" if diagnostic_info.get('select_date_button_disabled') else "Enabled"
                                button_text = diagnostic_info.get('select_date_button_text', 'N/A')
                                diag_msg_parts.append(f"Select Date Button: {button_status} (text: '{button_text}')")
                            else:
                                diag_msg_parts.append(f"Select Date Button: Not Found")
                        if 'page_contains_no_slots' in diagnostic_info:
                            diag_msg_parts.append(f"Page Contains 'No Slots': {diagnostic_info['page_contains_no_slots']}")
                        if diagnostic_info.get('page_text_snippet'):
                            text_snippet = diagnostic_info['page_text_snippet'][:200]
                            diag_msg_parts.append(f"Page Text Snippet: {text_snippet}...")
                    
                    diag_message = "\n".join(diag_msg_parts)
                    send_telegram_message(diag_message)
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
                case_name = "captcha" if special_case == "captcha_required" else "email verification"
                print(f"  Skipping HTML save ({case_name} case)")
            
            if special_case in ("captcha_required", "email_verification"):
                # Send notification without screenshot for special cases
                send_result_notification(slots_available, None, special_case=special_case, booking_url=BOOKING_URL, location=location)
                case_name = "captcha required" if special_case == "captcha_required" else "email verification"
                print(f"✓ Notification sent (no screenshot - {case_name} required)")
                
                # Save cooldown if captcha is required
                if special_case == "captcha_required":
                    save_captcha_cooldown()
            else:
                print("  Capturing full page screenshot...")
                sys.stdout.flush()
                screenshot_bytes = get_full_page_screenshot(driver)
                send_result_notification(slots_available, screenshot_bytes, special_case=None, booking_url=BOOKING_URL, location=location)
                print("✓ Notification sent")
        else:
            print("  No slots available")
        sys.stdout.flush()
    except Exception as e:
        print(f"\n✗ Error occurred during {location_display} check: {e}")
        import traceback
        traceback.print_exc()
        sys.stdout.flush()


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Hungary embassy booking form filler")
    parser.add_argument(
        "--location",
        choices=["subotica", "belgrade", "both"],
        default="subotica",
        help="Location to check slots for: 'subotica', 'belgrade', or 'both' (default: subotica)"
    )
    args = parser.parse_args()
    
    if args.location == "both":
        fill_booking_form_both_locations()
    else:
        fill_booking_form(location=args.location)

