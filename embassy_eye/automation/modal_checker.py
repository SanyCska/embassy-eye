"""
Functions for checking modal/appointment availability.
"""

import time
from datetime import datetime
from pathlib import Path

from selenium.common.exceptions import TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

CAPTCHA_FAILURE_TEXT = "hcaptcha has to be checked"
CAPTCHA_LOG_PATH = Path("logs") / "captcha_failures.log"


def check_appointment_availability(driver):
    """Check for appointment availability after clicking the next button."""
    print("\n=== Waiting for modal to appear (if any) ===")
    time.sleep(3)  # Initial wait
    
    print("=== Checking for appointment availability ===")
    modal_found = False
    captcha_failure_detected = False
    
    try:
        # Method 1: Check page source/text directly for the message
        page_text = driver.page_source.lower()
        body_text = driver.find_element(By.TAG_NAME, "body").text.lower()
        
        if any(phrase in page_text or phrase in body_text for phrase in 
               ["no appointments available", "currently no appointments"]):
            print("  Found 'no appointments' text in page")
        if CAPTCHA_FAILURE_TEXT in page_text or CAPTCHA_FAILURE_TEXT in body_text:
            captcha_failure_detected = True
            modal_found = True
            print("  ⚠ hCaptcha modal detected in page text")
        
        # Method 2: Wait for and find the specific alert element with role="alert"
        alert_element = None
        try:
            alert_element = WebDriverWait(driver, 3).until(
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
                    modal_found = True
                    print("  ⚠ hCaptcha modal detected via alert element")
        except TimeoutException:
            print("  No alert element with role='alert' found")
        except Exception as e:
            print(f"  Error finding alert: {e}")
        
        # Method 3: Look for red text elements
        if not modal_found:
            modal_found = _check_red_text_elements(driver)
        
        # Method 4: Check modal-content/modal-body structure
        if not modal_found:
            modal_found = _check_modal_body_elements(driver)
        
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
    
    # Print result
    print("\n" + "="*60)
    if modal_found:
        if captcha_failure_detected:
            print("⚠️  CAPTCHA NOT SOLVED ⚠️")
            print("="*60)
            return False
        print("⚠️  ALL SLOTS ARE BUSY ⚠️")
        print("="*60)
        return False  # No appointments available
    else:
        current_url = driver.current_url
        print("✅ THERE ARE FREE SLOTS!!! GO BY LINK:")
        print(f"   {current_url}")
        print("="*60)
        return True  # Appointments available


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
                        print("  ⚠ Found modal-body with hCaptcha message")
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
                            print("  ⚠ Found modal div with hCaptcha message")
                            return True
            except:
                continue
    except:
        pass
    
    return False


def _log_captcha_failure():
    """Append a timestamped log entry for captcha failures."""
    try:
        CAPTCHA_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with CAPTCHA_LOG_PATH.open("a", encoding="utf-8") as log_file:
            log_file.write(f"{timestamp} - hCaptcha modal encountered\n")
    except Exception as log_error:
        print(f"  Warning: Failed to write captcha log: {log_error}")


