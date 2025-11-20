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


def check_appointment_availability(driver):
    """Check for appointment availability after clicking the next button."""
    print("\n=== Waiting for modal to appear (if any) ===")
    time.sleep(6)  # Initial wait
    
    print("=== Checking for appointment availability ===")
    modal_found = False
    captcha_failure_detected = False
    email_verification_required = False
    blocked_ip = None
    
    try:
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
                alert_text = alert_element.text.lower()
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
        except Exception as e:
            print(f"  Error finding alert: {e}")
        
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
    
    except Exception as e:
        print(f"  Error checking for modal: {e}")
        import traceback
        traceback.print_exc()
    
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
        return (True, "captcha_required")  # (slots_available, special_case)
    elif email_verification_required:
        current_url = driver.current_url
        print("✅ SLOTS FOUND - EMAIL VERIFICATION REQUIRED!")
        print(f"   {current_url}")
        print("="*60)
        return (True, "email_verification")  # (slots_available, special_case)
    elif blocked_ip:
        print("❌ ACCESS BLOCKED BY IP RESTRICTION ❌")
        print(f"   Blocked IP: {blocked_ip}")
        print("   Logged to logs/blocked_ips.log")
        print("="*60)
        return (False, "ip_blocked")
    elif modal_found:
        print("⚠️  ALL SLOTS ARE BUSY ⚠️")
        print("="*60)
        return (False, None)  # No appointments available
    else:
        current_url = driver.current_url
        print("✅ THERE ARE FREE SLOTS!!! GO BY LINK:")
        print(f"   {current_url}")
        print("="*60)
        return (True, None)  # Appointments available, no special case


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


def detect_blocked_ip(driver):
    """Detect blocked IP message anywhere on the page and log it."""
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
        _log_blocked_ip(blocked_ip)
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


def _log_blocked_ip(ip_address):
    """Append a timestamped log entry for blocked IP notices."""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    _log_to_paths(IP_BLOCKED_LOG_PATHS, f"{timestamp} - {ip_address}\n", "blocked IP")


