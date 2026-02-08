"""
Functions for checking modal/appointment availability.
"""

import re
import time
from datetime import datetime
from pathlib import Path

from selenium.common.exceptions import TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from ..notifications.telegram import (
    send_healthcheck_ip_blocked,
    send_healthcheck_slot_busy,
    get_ip_and_country,
)

BASE_DIR = Path(__file__).resolve().parents[2]
LOG_DIR_CANDIDATES = [
    Path("logs"),
    Path("screenshots") / "logs",
    BASE_DIR / "logs",
    Path("/tmp/embassy-eye/logs"),
]
CAPTCHA_FAILURE_TEXT = "hcaptcha has to be checked"
EMAIL_VERIFICATION_TEXT = "to proceed with your booking, you need to enter the code that is sent to the provided email address"
CAPTCHA_LOG_PATHS = [log_dir / "captcha_failures.log" for log_dir in LOG_DIR_CANDIDATES]
IP_BLOCKED_LOG_PATHS = [log_dir / "blocked_ips.log" for log_dir in LOG_DIR_CANDIDATES]
IP_BLOCKED_REGEX = re.compile(
    r"your ip \((?P<ip>\d{1,3}(?:\.\d{1,3}){3})\) has been blocked", re.IGNORECASE
)


def check_appointment_availability(driver, location=None):
    """Check for appointment availability after clicking the next button.
    
    Args:
        driver: Selenium WebDriver instance
        location: Optional location string (e.g., "subotica", "belgrade") for notifications
    """
    print("\n=== Waiting for modal to appear (if any) ===")
    time.sleep(6)  # Initial wait
    
    print("=== Checking for appointment availability ===")
    modal_found = False
    captcha_failure_detected = False
    email_verification_required = False
    blocked_ip = None
    alert_found = False
    alert_text_snippet = None
    page_title = None
    diagnostic_info = {}
    
    try:
        # Get page title and URL for diagnostics
        try:
            page_title = driver.title
            current_url = driver.current_url
            diagnostic_info['url'] = current_url
            diagnostic_info['title'] = page_title
        except Exception:
            pass
        
        # Method 1: Check page source/text directly for the message
        page_text = driver.page_source.lower()
        body_text = driver.find_element(By.TAG_NAME, "body").text.lower()
        
        if any(phrase in page_text or phrase in body_text for phrase in 
               ["no appointments available", "currently no appointments"]):
            print("  Found 'no appointments' text in page")
        if CAPTCHA_FAILURE_TEXT in page_text or CAPTCHA_FAILURE_TEXT in body_text:
            captcha_failure_detected = True
            print("  ✓ hCaptcha modal detected - slots found but captcha required on site!")
        if EMAIL_VERIFICATION_TEXT in page_text or EMAIL_VERIFICATION_TEXT in body_text:
            email_verification_required = True
            print("  ✓ Email verification modal detected - slots found!")
        blocked_ip = _extract_blocked_ip(page_text) or _extract_blocked_ip(body_text)
        if blocked_ip:
            print(f"  ⚠️ Detected blocked IP message for {blocked_ip}")
        
        # Method 2: Wait for and find the specific alert element with role="alert"
        alert_element = None
        try:
            alert_element = WebDriverWait(driver, 6).until(
                EC.presence_of_element_located((By.XPATH, "//*[@role='alert']"))
            )
            if alert_element and alert_element.is_displayed():
                alert_found = True
                alert_text = alert_element.text.lower()
                alert_text_snippet = alert_element.text[:200] if alert_element.text else None
                diagnostic_info['alert_found'] = True
                diagnostic_info['alert_text'] = alert_text_snippet
                print(f"  Found alert element with role='alert', text: '{alert_text[:80]}'")
                if "no appointments" in alert_text:
                    modal_found = True
                    print("  ✓ Modal confirmed with 'no appointments' message")
                if CAPTCHA_FAILURE_TEXT in alert_text:
                    captcha_failure_detected = True
                    print("  ✓ hCaptcha modal detected via alert element - slots found but captcha required on site!")
                if EMAIL_VERIFICATION_TEXT in alert_text:
                    email_verification_required = True
                    print("  ✓ Email verification modal detected via alert element - slots found!")
        except TimeoutException:
            print("  No alert element with role='alert' found")
            diagnostic_info['alert_found'] = False
        except Exception as e:
            print(f"  Error finding alert: {e}")
            diagnostic_info['alert_found'] = False
            diagnostic_info['alert_error'] = str(e)
        
        # Method 3: Look for red text elements
        if not modal_found:
            modal_found = _check_red_text_elements(driver)
        
        # Method 4: Check modal-content/modal-body structure
        if not modal_found and not email_verification_required:
            modal_found = _check_modal_body_elements(driver)
        
        # Check for email verification in modal-body
        if not email_verification_required:
            email_verification_required = _check_email_verification_modal(driver)
        
        # Method 5: Simple text search in all visible text
        if not modal_found and ("no appointments" in body_text or "no appointments available" in body_text):
            print("  Found 'no appointments' text in page body")
            modal_found = _check_modal_divs(driver)
        
        # Collect more diagnostic info
        diagnostic_info['modal_found'] = modal_found
        diagnostic_info['page_contains_no_slots'] = any(phrase in body_text for phrase in 
                                                         ["no appointments", "no appointments available", "currently no appointments"])
        
        # Check if we're back at the initial form (false positive for slots)
        # If page contains "please select a consulate" or similar text, we're at the beginning
        form_reset_detected = any(phrase in body_text for phrase in 
                                  ["please select a consulate", "please select the location required", "select location"])
        diagnostic_info['form_reset_detected'] = form_reset_detected
        
        # Check if we're still on the form page (booking data step)
        diagnostic_info['on_booking_form'] = "booking data" in body_text.lower() or "foglalasi-adatok" in page_text
        diagnostic_info['on_date_selection'] = "select a date" in body_text.lower() or "idopontvalasztas" in page_text
        
        # Check "Select date" button state
        try:
            select_date_button = None
            # Try to find button by text "Select date" or "Dátum"
            try:
                select_date_button = driver.find_element(
                    By.XPATH,
                    "//button[contains(text(), 'Select date') or contains(text(), 'Dátum')]"
                )
            except:
                # Try to find by button text containing "date"
                try:
                    select_date_button = driver.find_element(
                        By.XPATH,
                        "//button[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'date')]"
                    )
                except:
                    pass
            
            if select_date_button:
                is_disabled = not select_date_button.is_enabled() or select_date_button.get_attribute("disabled") is not None
                button_text = select_date_button.text.strip()
                diagnostic_info['select_date_button_found'] = True
                diagnostic_info['select_date_button_disabled'] = is_disabled
                diagnostic_info['select_date_button_text'] = button_text
                print(f"  Found 'Select date' button: disabled={is_disabled}, text='{button_text}'")
            else:
                diagnostic_info['select_date_button_found'] = False
                print("  'Select date' button not found")
        except Exception as e:
            diagnostic_info['select_date_button_found'] = False
            diagnostic_info['select_date_button_error'] = str(e)
            print(f"  Error checking 'Select date' button: {e}")
        
        # Get a snippet of visible text for context
        try:
            visible_text_snippet = body_text[:300].replace('\n', ' ').strip()
            diagnostic_info['page_text_snippet'] = visible_text_snippet
        except Exception:
            pass
    
    except Exception as e:
        print(f"  Error checking for modal: {e}")
        import traceback
        traceback.print_exc()
        diagnostic_info['error'] = str(e)
    
    if captcha_failure_detected:
        _log_captcha_failure()
    if blocked_ip:
        _log_blocked_ip(blocked_ip)
    
    # Print result
    print("\n" + "="*60)
    if captcha_failure_detected:
        current_url = driver.current_url
        print("✅ SLOTS FOUND - CAPTCHA REQUIRED ON SITE!")
        print(f"   {current_url}")
        print("="*60)
        return (True, "captcha_required", diagnostic_info)  # (slots_available, special_case, diagnostic_info)
    elif email_verification_required:
        current_url = driver.current_url
        print("✅ SLOTS FOUND - EMAIL VERIFICATION REQUIRED!")
        print(f"   {current_url}")
        print("="*60)
        return (True, "email_verification", diagnostic_info)  # (slots_available, special_case, diagnostic_info)
    elif blocked_ip:
        print("❌ ACCESS BLOCKED BY IP RESTRICTION ❌")
        print(f"   Blocked IP: {blocked_ip}")
        print("   Logged to logs/blocked_ips.log")
        print("="*60)
        # Send healthcheck notification for IP blocked
        _, country = get_ip_and_country()
        send_healthcheck_ip_blocked(blocked_ip, country, location=location)
        return (False, "ip_blocked", diagnostic_info)
    elif modal_found:
        print("⚠️  ALL SLOTS ARE BUSY ⚠️")
        print("="*60)
        # Send healthcheck notification for slot busy
        _, country = get_ip_and_country()
        send_healthcheck_slot_busy(country, location=location)
        return (False, None, diagnostic_info)  # No appointments available
    elif diagnostic_info.get('form_reset_detected'):
        print("⚠️  FORM WAS RESET - NO SLOTS (False Positive Detected) ⚠️")
        print("  Page is back at initial form state")
        print("="*60)
        # Send healthcheck notification for slot busy
        _, country = get_ip_and_country()
        send_healthcheck_slot_busy(country, location=location)
        return (False, None, diagnostic_info)  # No appointments available - form reset
    else:
        current_url = driver.current_url
        print("✅ THERE ARE FREE SLOTS!!! GO BY LINK:")
        print(f"   {current_url}")
        print("="*60)
        return (True, None, diagnostic_info)  # Appointments available, no special case


def _check_red_text_elements(driver):
    """Check for red text elements indicating no appointments."""
    try:
        red_elements = driver.find_elements(
            By.XPATH,
            "//*[contains(@style, 'color:red') or contains(@style, 'color: red') or contains(@style, 'color:red;')]"
        )
        print(f"  Found {len(red_elements)} elements with red style")
        for elem in red_elements:
            try:
                if elem.is_displayed():
                    elem_text = elem.text.lower()
                    print(f"    Red element text: '{elem_text[:80]}'")
                    if any(phrase in elem_text for phrase in 
                          ["no appointments", "no appointments available", "currently no appointments"]):
                        print("  ✓ Found red text element with 'no appointments' message")
                        return True
            except:
                continue
    except Exception as e:
        print(f"  Error finding red text: {e}")
    
    return False


def _check_modal_body_elements(driver):
    """Check modal-body elements for no appointments message."""
    try:
        modal_bodies = driver.find_elements(By.XPATH, "//div[contains(@class, 'modal-body')]")
        print(f"  Found {len(modal_bodies)} modal-body elements")
        for modal_body in modal_bodies:
            try:
                if modal_body.is_displayed():
                    modal_text = modal_body.text.lower()
                    print(f"    Modal body text: '{modal_text[:80]}'")
                    if any(phrase in modal_text for phrase in 
                          ["no appointments", "no appointments available", "currently no appointments"]):
                        print("  ✓ Found modal-body with 'no appointments' message")
                        return True
                    if CAPTCHA_FAILURE_TEXT in modal_text:
                        print("  ✓ Found modal-body with hCaptcha message - slots found but captcha required!")
                        return True
            except:
                continue
    except Exception as e:
        print(f"  Error finding modal-body: {e}")
    
    return False


def _check_modal_divs(driver):
    """Check modal divs for no appointments message."""
    try:
        all_divs = driver.find_elements(By.TAG_NAME, "div")
        for div in all_divs:
            try:
                if div.is_displayed():
                    div_classes = div.get_attribute("class") or ""
                    if "modal" in div_classes:
                        div_text = div.text.lower()
                        if "no appointments" in div_text:
                            print("  ✓ Found modal div with 'no appointments' message")
                            return True
                        if CAPTCHA_FAILURE_TEXT in div_text:
                            print("  ✓ Found modal div with hCaptcha message - slots found but captcha required!")
                            return True
            except:
                continue
    except:
        pass
    
    return False


def _check_email_verification_modal(driver):
    """Check for email verification modal indicating slots are available."""
    try:
        modal_bodies = driver.find_elements(By.XPATH, "//div[contains(@class, 'modal-body')]")
        for modal_body in modal_bodies:
            try:
                if modal_body.is_displayed():
                    modal_text = modal_body.text.lower()
                    if EMAIL_VERIFICATION_TEXT in modal_text:
                        print("  ✓ Found email verification modal - slots available!")
                        return True
            except:
                continue
    except Exception as e:
        print(f"  Error checking email verification modal: {e}")
    
    return False


def detect_blocked_ip(driver, embassy=None):
    """Detect blocked IP message anywhere on the page and log it.
    
    Args:
        driver: Selenium WebDriver instance
        embassy: Optional embassy name (e.g., "hungary", "italy")
    """
    try:
        page_text = driver.page_source.lower()
    except Exception:
        page_text = ""
    try:
        body_text = driver.find_element(By.TAG_NAME, "body").text.lower()
    except Exception:
        body_text = ""

    blocked_ip = _extract_blocked_ip(body_text) or _extract_blocked_ip(page_text)
    if blocked_ip:
        print("❌ ACCESS BLOCKED BY IP RESTRICTION ❌")
        print(f"   Detected blocked IP: {blocked_ip}")
        # Get country info
        _, country = get_ip_and_country()
        # Log to database and file
        _log_blocked_ip(blocked_ip, country=country, embassy=embassy)
        # Send healthcheck notification for IP blocked
        send_healthcheck_ip_blocked(blocked_ip, country)
        return blocked_ip

    return None


def _log_to_paths(paths, message, log_name):
    """Attempt to write message to first writable path in list."""
    last_error = None
    for path in paths:
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            with path.open("a", encoding="utf-8") as log_file:
                log_file.write(message)
            print(f"  Logged {log_name} entry to {path}")
            return
        except Exception as log_error:
            last_error = log_error
            print(f"  Warning: Failed to write {log_name} log at {path}: {log_error}")
            continue
    if last_error:
        print(f"  Warning: Unable to write {log_name} log to any configured path.")


def _log_captcha_failure():
    """Append a timestamped log entry for captcha failures."""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    _log_to_paths(CAPTCHA_LOG_PATHS, f"{timestamp} - hCaptcha modal encountered\n", "captcha")


def _extract_blocked_ip(text):
    """Extract blocked IP from text if present."""
    if not text:
        return None
    match = IP_BLOCKED_REGEX.search(text)
    if match:
        return match.group("ip")
    return None


def _log_blocked_ip(ip_address, country=None, embassy=None):
    """Log blocked IP to database and file backup."""
    # Log to database
    try:
        from ..database import log_blocked_ip
        log_blocked_ip(ip_address, country=country, embassy=embassy)
        print(f"  ✓ Logged blocked IP to database: {ip_address}")
    except Exception as e:
        print(f"  Warning: Failed to log to database: {e}")
    
    # Also log to file as backup
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    country_info = f" ({country})" if country else ""
    embassy_info = f" [{embassy}]" if embassy else ""
    _log_to_paths(IP_BLOCKED_LOG_PATHS, f"{timestamp} - {ip_address}{country_info}{embassy_info}\n", "blocked IP")


