"""
Helper functions for filling form fields.
"""

import random
import time

from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import Select

from ..scrapers.hungary.config import (
    CHAR_TYPE_DELAY,
    DEFAULT_TEXTAREA_VALUE,
    DEFAULT_VALUES,
    FIELD_MAP,
)
from .webdriver_utils import scroll_to_element


def fill_select_dropdowns(driver, selects):
    """Fill standard HTML select dropdowns."""
    if not selects:
        return
    
    for select in selects:
        try:
            select_id = select.get_attribute("id")
            select_name = select.get_attribute("name")
            select_obj = Select(select)
            options = select_obj.options
            if len(options) > 1:
                # Select the second option (skip first if it's placeholder)
                select_obj.select_by_index(1)
                selected_option = options[1].text
                print(f"Filled select {select_id or select_name}: {selected_option}")
            elif len(options) == 1:
                select_obj.select_by_index(0)
                print(f"Filled select {select_id or select_name}: {options[0].text}")
            # Random delay between fills
            time.sleep(random.uniform(0.2, 0.5))
        except Exception as e:
            pass


def fill_reenter_email_field(driver):
    """Fill the re-enter email field with special handling."""
    filled_count = 0
    
    try:
        # Find the re-enter email field by its label
        reenter_email_label = driver.find_element(
            By.XPATH,
            "//label[contains(text(), 'Re-enter') or contains(text(), 're-enter') or contains(text(), 'Reenter')]"
        )
        reenter_email_id = reenter_email_label.get_attribute("for")
        
        if reenter_email_id:
            reenter_email_field = driver.find_element(By.ID, reenter_email_id)
            
            if reenter_email_field.is_displayed():
                scroll_to_element(driver, reenter_email_field)
                time.sleep(0.2)
                
                # Remove the onpaste restriction first
                driver.execute_script("arguments[0].removeAttribute('onpaste')", reenter_email_field)
                time.sleep(0.1)
                
                # Clear the field
                driver.execute_script("arguments[0].value = '';", reenter_email_field)
                time.sleep(0.1)
                
                # Focus the field
                reenter_email_field.click()
                driver.execute_script("arguments[0].focus();", reenter_email_field)
                time.sleep(0.2)
                
                # Type character by character using send_keys()
                for char in DEFAULT_VALUES["email"]:
                    reenter_email_field.send_keys(char)
                    time.sleep(CHAR_TYPE_DELAY)
                
                time.sleep(0.3)  # Wait for field to process all characters
                
                # Verify the value was set
                actual_value = reenter_email_field.get_attribute("value")
                if actual_value == DEFAULT_VALUES["email"]:
                    print("Filled re-enter email field")
                    filled_count += 1
                else:
                    # Attempt to fix by typing remaining characters
                    
                    # Try to fix by typing remaining characters
                    if len(actual_value) < len(DEFAULT_VALUES["email"]):
                        missing_chars = DEFAULT_VALUES["email"][len(actual_value):]
                        for char in missing_chars:
                            reenter_email_field.send_keys(char)
                            time.sleep(CHAR_TYPE_DELAY)
                        
                        time.sleep(0.3)
                        actual_value = reenter_email_field.get_attribute("value")
                        if actual_value == DEFAULT_VALUES["email"]:
                            print("Filled re-enter email field")
                            filled_count += 1
            
            
    except NoSuchElementException:
        pass
    except Exception as e:
        pass
    
    return filled_count


def fill_date_of_birth_field(driver):
    """Fill the date of birth field with special date picker handling."""
    filled_count = 0
    
    try:
        # Find the date picker input
        date_input = driver.find_element(By.ID, "birthDate")
        scroll_to_element(driver, date_input)
        time.sleep(0.3)
        
        # Clear and fill the date input
        date_input.clear()
        time.sleep(0.1)
        date_input.send_keys(DEFAULT_VALUES["date_of_birth"])
        time.sleep(0.3)
        
        # Also try to set the value via the date picker component
        try:
            date_picker = driver.find_element(By.ID, "birthDateComponent")
            driver.execute_script("arguments[0].value = arguments[1];", date_picker, DEFAULT_VALUES["date_of_birth_iso"])
            # Trigger change event
            driver.execute_script("arguments[0].dispatchEvent(new Event('change', { bubbles: true }));", date_picker)
        except:
            pass
        
        print(f"Filled birthDate: {DEFAULT_VALUES['date_of_birth']}")
        filled_count += 1
    except Exception as e:
        pass
    
    return filled_count


def fill_checkbox_field(driver, field_id):
    """Fill a checkbox field."""
    filled_count = 0
    
    try:
        checkbox = driver.find_element(By.ID, field_id)
        if checkbox.is_displayed() and not checkbox.is_selected():
            scroll_to_element(driver, checkbox)
            time.sleep(0.2)
            checkbox.click()
            print(f"Filled checkbox {field_id}")
            filled_count += 1
    except NoSuchElementException:
        pass
    except Exception as e:
        pass
    
    return filled_count


def fill_text_field(driver, field_id, value):
    """Fill a regular text input field."""
    filled_count = 0
    
    try:
        input_field = driver.find_element(By.ID, field_id)
        if input_field.is_displayed():
            scroll_to_element(driver, input_field)
            time.sleep(0.2)
            
            # Skip fields with onpaste attribute (re-enter email already handled separately)
            try:
                onpaste_attr = input_field.get_attribute("onpaste")
                if onpaste_attr:
                    return filled_count
            except:
                pass
            
            # Skip if this is a re-enter email field (already handled separately)
            try:
                label = driver.find_element(By.XPATH, f"//label[@for='{field_id}']")
                label_text = label.text.lower() if label else ""
                if "re-enter" in label_text or "reenter" in label_text:
                    return filled_count
            except:
                pass
            
            # Clear field
            try:
                input_field.clear()
            except:
                try:
                    input_field.send_keys(Keys.CONTROL + "a")
                    input_field.send_keys(Keys.DELETE)
                except:
                    # Use JavaScript to clear
                    driver.execute_script("arguments[0].value = '';", input_field)
            
            time.sleep(0.1)
            
            # Fill field
            try:
                input_field.send_keys(value)
                print(f"Filled {field_id}: {value}")
            except:
                # Fallback: JavaScript
                driver.execute_script("arguments[0].value = arguments[1];", input_field, value)
                driver.execute_script("arguments[0].dispatchEvent(new Event('input', { bubbles: true }));", input_field)
                driver.execute_script("arguments[0].dispatchEvent(new Event('change', { bubbles: true }));", input_field)
                print(f"Filled {field_id}: {value}")
            
            # Random delay between field fills to simulate human typing
            time.sleep(random.uniform(0.3, 0.7))
            filled_count += 1
    except NoSuchElementException:
        pass
    except Exception as e:
        pass
    
    return filled_count


def fill_fields_by_map(driver):
    """Fill all fields defined in FIELD_MAP."""
    filled_count = 0
    
    for field_id, (field_type, value) in FIELD_MAP.items():
        try:
            if field_type == "checkbox":
                filled_count += fill_checkbox_field(driver, field_id)
            elif field_id == "birthDate":
                filled_count += fill_date_of_birth_field(driver)
            else:
                filled_count += fill_text_field(driver, field_id, value)
        except Exception as e:
            pass
    
    return filled_count


def fill_remaining_fields(driver, inputs):
    """Fill any remaining fields that might have been missed."""
    filled_count = 0
    filled_ids = set(FIELD_MAP.keys())
    
    for input_field in inputs:
        input_type = input_field.get_attribute("type") or "text"
        input_id = input_field.get_attribute("id") or ""
        input_name = input_field.get_attribute("name") or ""
        
        # Skip fields already handled by field_map
        if input_id in filled_ids:
            continue
        
        # Skip hidden, submit, button types
        if input_type in ["hidden", "submit", "button", "image"]:
            continue
        
        # Skip if already has a value
        try:
            current_value = input_field.get_attribute("value") or ""
            if current_value and input_type not in ["checkbox", "radio"] and len(current_value.strip()) > 0:
                continue
        except:
            pass
        
        try:
            # Only handle checkboxes if visible
            if input_type == "checkbox":
                if input_field.is_displayed() and not input_field.is_selected():
                    scroll_to_element(driver, input_field)
                    time.sleep(0.2)
                    input_field.click()
                    print(f"Filled checkbox {input_id or input_name or 'unknown'}")
                    filled_count += 1
                continue
            
            elif input_type == "radio":
                # Radio buttons - skip (already handled in dropdowns)
                continue
            
            # Skip other fields as they should already be handled by field_map
            else:
                continue
        except Exception as e:
            pass
    
    return filled_count


def fill_textareas(driver, textareas, wait):
    """Fill all textarea fields."""
    from selenium.webdriver.support import expected_conditions as EC
    
    filled_count = 0
    
    for textarea in textareas:
        try:
            wait.until(EC.element_to_be_clickable(textarea))
            scroll_to_element(driver, textarea)
            time.sleep(0.3)
            textarea.clear()
            textarea.send_keys(DEFAULT_TEXTAREA_VALUE)
            print(f"Filled textarea {textarea.get_attribute('id') or textarea.get_attribute('name')}")
            filled_count += 1
        except Exception as e:
            pass
    
    return filled_count


