"""
Handlers for dropdown selection logic.
"""

import time

from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.common.by import By

from ..config import (
    CONSULATE_DROPDOWN_ID,
    CONSULATE_DROPDOWN_NAME,
    CONSULATE_OPTION_TEXT,
    VISA_TYPE_DROPDOWN_ID,
    VISA_TYPE_OPTION_TEXT,
)
from .webdriver_utils import scroll_to_element


def find_dropdown_element(driver, name=None, element_id=None, css_selector=None, text_hint=None):
    """Find a dropdown element using multiple search strategies."""
    dropdown = None
    
    # Try to find by name
    if name:
        try:
            dropdown = driver.find_element(By.NAME, name)
            print(f"  Found dropdown by name '{name}'")
            return dropdown
        except:
            pass
    
    # Try to find by id
    if element_id and not dropdown:
        try:
            dropdown = driver.find_element(By.ID, element_id)
            print(f"  Found dropdown by id '{element_id}'")
            return dropdown
        except:
            pass
    
    # Try partial match on name or id attributes
    if name and not dropdown:
        try:
            dropdown = driver.find_element(
                By.XPATH,
                f"//*[@name and contains(@name, '{name}')] | //*[@id and contains(@id, '{name}')]"
            )
            print(f"  Found dropdown by partial match on '{name}'")
            return dropdown
        except:
            pass
    
    if element_id and not dropdown:
        try:
            dropdown = driver.find_element(
                By.XPATH,
                f"//*[@id='{element_id}'] | //*[@id and contains(@id, '{element_id[:8]}')]"
            )
            print(f"  Found dropdown by id/partial id '{element_id}'")
            return dropdown
        except:
            pass
    
    # Try to find by CSS selector
    if css_selector and not dropdown:
        try:
            dropdown = driver.find_element(By.CSS_SELECTOR, css_selector)
            print(f"  Found dropdown by CSS selector")
            return dropdown
        except:
            pass
    
    # Try to find input or button that might trigger the dropdown
    if name and not dropdown:
        try:
            dropdown = driver.find_element(
                By.XPATH,
                f"//input[contains(@name, '{name}')] | //button[contains(@name, '{name}')] | //div[contains(@name, '{name}')]"
            )
            print(f"  Found dropdown element by XPATH")
            return dropdown
        except:
            pass
    
    if text_hint and not dropdown:
        try:
            dropdown = driver.find_element(
                By.XPATH,
                f"//*[contains(normalize-space(.), '{text_hint}')]/ancestor::*[self::div or self::button or self::span][1]"
            )
            print(f"  Found dropdown by text hint '{text_hint}'")
            return dropdown
        except:
            pass
    
    return None


def find_radio_option_by_text(driver, option_text):
    """Find a radio button option by its label text."""
    radio_option = None
    
    # Method 1: Find by label text
    try:
        radio_option = driver.find_element(
            By.XPATH,
            f"//label[contains(text(), '{option_text}')]/preceding-sibling::input[@type='radio'] | "
            f"//label[contains(text(), '{option_text}')]/following-sibling::input[@type='radio'] | "
            f"//input[@type='radio'][following-sibling::label[contains(text(), '{option_text}')]] | "
            f"//input[@type='radio'][preceding-sibling::label[contains(text(), '{option_text}')]]"
        )
        return radio_option
    except:
        pass
    
    # Method 2: Find all radios and check their associated labels
    if not radio_option:
        try:
            radios = driver.find_elements(By.XPATH, "//input[@type='radio']")
            for radio in radios:
                # Check if the radio has a label nearby
                try:
                    radio_id = radio.get_attribute("id")
                    if radio_id:
                        label = driver.find_element(By.XPATH, f"//label[@for='{radio_id}']")
                        if option_text in label.text:
                            radio_option = radio
                            return radio_option
                except:
                    pass
                
                # Check parent or sibling for label
                try:
                    parent = radio.find_element(By.XPATH, "./..")
                    if option_text in parent.text:
                        radio_option = radio
                        return radio_option
                except:
                    pass
        except:
            pass
    
    # Method 3: Find by text anywhere near the radio
    if not radio_option:
        try:
            radio_option = driver.find_element(
                By.XPATH,
                f"//*[contains(text(), '{option_text}')]/preceding::input[@type='radio'][1] | "
                f"//*[contains(text(), '{option_text}')]/following::input[@type='radio'][1]"
            )
            return radio_option
        except:
            pass
    
    return None


def select_consulate_option(driver):
    """Select 'Serbia - Subotica' option from the consulate dropdown."""
    print("Step 1: Opening dropdown and selecting 'Serbia - Subotica'...")
    
    try:
        dropdown = find_dropdown_element(
            driver,
            name=CONSULATE_DROPDOWN_NAME,
            element_id=CONSULATE_DROPDOWN_ID,
            css_selector="[name*='ugyfelszolgalat'], [name='ugyfelszolgalat']",
            text_hint=CONSULATE_OPTION_TEXT,
        )
        
        if dropdown:
            scroll_to_element(driver, dropdown)
            time.sleep(0.5)
            
            # Click to open the dropdown
            print("  Clicking dropdown to open it...")
            driver.execute_script("arguments[0].click();", dropdown)
            time.sleep(1)  # Wait for dropdown to open
            
            # Find and select the radio option
            radio_option = find_radio_option_by_text(driver, CONSULATE_OPTION_TEXT)
            
            if radio_option:
                scroll_to_element(driver, radio_option)
                time.sleep(0.3)
                
                print(f"  Found radio option '{CONSULATE_OPTION_TEXT}', clicking it...")
                driver.execute_script("arguments[0].click();", radio_option)
                time.sleep(0.5)
                print(f"  ✓ Selected '{CONSULATE_OPTION_TEXT}'")
            else:
                print(f"  ✗ Could not find radio option '{CONSULATE_OPTION_TEXT}'")
                _list_all_radio_buttons(driver)
        else:
            print("  ✗ Could not find dropdown element")
            _debug_dropdown_search(driver)
    except Exception as e:
        print(f"  ✗ Error selecting dropdown option: {e}")
        import traceback
        traceback.print_exc()


def _list_all_radio_buttons(driver):
    """List all radio buttons found on the page for debugging."""
    print("  Listing all radio buttons found:")
    radios = driver.find_elements(By.XPATH, "//input[@type='radio']")
    for i, radio in enumerate(radios):
        radio_id = radio.get_attribute("id")
        radio_name = radio.get_attribute("name")
        radio_value = radio.get_attribute("value")
        try:
            label_text = ""
            if radio_id:
                try:
                    label = driver.find_element(By.XPATH, f"//label[@for='{radio_id}']")
                    label_text = label.text
                except:
                    pass
            if not label_text:
                try:
                    parent = radio.find_element(By.XPATH, "./..")
                    label_text = parent.text[:50] if parent.text else ""
                except:
                    pass
            print(f"    Radio [{i}]: id='{radio_id}', name='{radio_name}', value='{radio_value}', label='{label_text}'")
        except:
            print(f"    Radio [{i}]: id='{radio_id}', name='{radio_name}', value='{radio_value}'")


def _debug_dropdown_search(driver):
    """Debug helper to search for dropdown elements."""
    print("  Searching for elements with name containing 'ugyfelszolgalat'...")
    elements = driver.find_elements(By.CSS_SELECTOR, "[name*='ugyfelszolgalat'], [id*='ugyfelszolgalat']")
    for elem in elements:
        print(f"    Found: tag='{elem.tag_name}', name='{elem.get_attribute('name')}', id='{elem.get_attribute('id')}'")


def find_dropdown_trigger_by_label(driver, target_id, label_text_pattern=None):
    """Find dropdown trigger by finding the label first, then working backwards."""
    label = None
    dropdown_trigger = None
    
    # Method 1: Find label by 'for' attribute
    try:
        label = driver.find_element(By.XPATH, f"//label[@for='{target_id}']")
        print(f"  Found label by 'for' attribute")
    except:
        pass
    
    # Method 2: Find label by text pattern
    if not label and label_text_pattern:
        try:
            label = driver.find_element(By.XPATH, f"//label[contains(text(), '{label_text_pattern}')]")
            print(f"  Found label by text")
        except:
            pass
    
    # Now find the dropdown container that contains this label
    if label:
        try:
            ancestors = label.find_elements(By.XPATH, "./ancestor::*")
            
            for ancestor in ancestors:
                ancestor_class = (ancestor.get_attribute("class") or "").lower()
                ancestor_id = ancestor.get_attribute("id") or ""
                ancestor_role = ancestor.get_attribute("role") or ""
                ancestor_aria_expanded = ancestor.get_attribute("aria-expanded")
                
                # Skip language selectors
                if "lang" in ancestor_id.lower() or "language" in ancestor_class:
                    continue
                
                # Look for dropdown indicators
                is_dropdown = (
                    "dropdown" in ancestor_class or
                    "select" in ancestor_class or
                    ancestor_role == "listbox" or
                    ancestor.get_attribute("aria-haspopup") == "true" or
                    ancestor_aria_expanded == "false"
                )
                
                if is_dropdown:
                    print(f"  Found dropdown container (class='{ancestor.get_attribute('class')[:50]}', id='{ancestor_id[:50]}')")
                    
                    # Try to find trigger elements in this container
                    try:
                        triggers = ancestor.find_elements(
                            By.XPATH,
                            ".//button | .//input[@type='button'] | .//div[contains(@role, 'button') or @tabindex] | .//*[@aria-haspopup='true']"
                        )
                        
                        for trigger in triggers:
                            trigger_id = trigger.get_attribute("id") or ""
                            trigger_class = trigger.get_attribute("class") or ""
                            
                            # Skip language selectors
                            if "lang" in trigger_id.lower() or "language" in trigger_class.lower():
                                continue
                            
                            # Skip triggers that are the checkbox itself
                            if trigger.get_attribute("type") in ["checkbox", "radio"]:
                                continue
                            
                            dropdown_trigger = trigger
                            print(f"  Found dropdown trigger: id='{trigger_id}', class='{trigger_class[:50]}'")
                            break
                        
                        if dropdown_trigger:
                            break
                    except:
                        pass
                    
                    # If no trigger found, try clicking the container itself
                    if not dropdown_trigger:
                        try:
                            if ancestor.tag_name in ["button", "div"] and ancestor.get_attribute("tabindex"):
                                dropdown_trigger = ancestor
                                print(f"  Using container itself as trigger")
                                break
                        except:
                            pass
        except Exception as e:
            print(f"  Error finding dropdown container: {e}")
    
    # Alternative method: find all dropdowns and pick the second one
    if not dropdown_trigger:
        try:
            print("  Trying alternative method: finding all potential dropdowns...")
            potential_triggers = driver.find_elements(
                By.XPATH,
                "//button | //input[@type='button'] | //div[contains(@class, 'dropdown') or contains(@role, 'button') or @aria-haspopup='true']"
            )
            
            form_triggers = []
            for trigger in potential_triggers:
                trigger_id = trigger.get_attribute("id") or ""
                trigger_class = trigger.get_attribute("class") or ""
                trigger_text = (trigger.text or "").lower()
                
                # Skip language selectors
                if "lang" in trigger_id.lower() or "language" in trigger_class.lower() or trigger_text in ["english", "magyar", "hungarian"]:
                    continue
                
                # Skip if it's in header/footer
                try:
                    parent = trigger.find_element(By.XPATH, "./ancestor::header | ./ancestor::footer | ./ancestor::*[contains(@class, 'header') or contains(@class, 'footer')]")
                    continue
                except:
                    pass
                
                form_triggers.append(trigger)
            
            # Pick the second one (first is the consulate dropdown)
            if len(form_triggers) > 1:
                dropdown_trigger = form_triggers[1]
                print(f"  Found second dropdown trigger: id='{dropdown_trigger.get_attribute('id')}', text='{dropdown_trigger.text[:50]}'")
            elif len(form_triggers) == 1:
                dropdown_trigger = form_triggers[0]
                print(f"  Found dropdown trigger: id='{dropdown_trigger.get_attribute('id')}', text='{dropdown_trigger.text[:50]}'")
        except Exception as e:
            print(f"  Error finding dropdown by alternative method: {e}")
    
    return dropdown_trigger, label


def find_input_by_id_or_label(driver, target_id, label=None):
    """Find an input element by ID or via its label."""
    input_element = None
    
    # Method 1: Find by id directly
    try:
        input_element = driver.find_element(By.ID, target_id)
        print(f"  Found input element by id '{target_id}'")
        return input_element
    except:
        pass
    
    # Method 2: Find via label's 'for' attribute
    if not input_element and label:
        try:
            label_for = label.get_attribute("for")
            if label_for:
                input_element = driver.find_element(By.ID, label_for)
                print(f"  Found input element via label's 'for' attribute")
                return input_element
        except:
            pass
    
    # Method 3: Find input near the label
    if not input_element and label:
        try:
            input_element = label.find_element(
                By.XPATH,
                f"./preceding-sibling::input | ./following-sibling::input | ../input[@id='{target_id}']"
            )
            print(f"  Found input element near label")
            return input_element
        except:
            pass
    
    # Method 4: Search for checkbox/radio with this id anywhere
    if not input_element:
        try:
            input_element = driver.find_element(
                By.XPATH,
                f"//input[@id='{target_id}'] | //input[@type='checkbox'][@id='{target_id}'] | //input[@type='radio'][@id='{target_id}']"
            )
            print(f"  Found input element by XPATH")
            return input_element
        except:
            pass
    
    return None


def find_save_button(driver, input_element=None):
    """Find the Save button in a dropdown/modal."""
    save_button = None
    
    # Method 1: Find button with text "Save"
    try:
        save_button = driver.find_element(By.XPATH, "//button[contains(text(), 'Save') or contains(text(), 'Mentés')]")
        print(f"  Found Save button by text: '{save_button.text}'")
        return save_button
    except:
        pass
    
    # Method 2: Find button in the same dropdown container as the checkbox
    if not save_button and input_element:
        try:
            checkbox_container = input_element.find_element(
                By.XPATH,
                "./ancestor::*[contains(@class, 'dropdown') or contains(@class, 'modal') or contains(@class, 'popup') or contains(@role, 'dialog')][1]"
            )
            save_button = checkbox_container.find_element(
                By.XPATH,
                ".//button[contains(text(), 'Save') or contains(text(), 'Mentés') or contains(@class, 'save')]"
            )
            print(f"  Found Save button in dropdown container")
            return save_button
        except:
            pass
    
    # Method 3: Find any visible button with "Save" text
    if not save_button:
        try:
            save_buttons = driver.find_elements(
                By.XPATH,
                "//button[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'save')]"
            )
            for btn in save_buttons:
                if btn.is_displayed():
                    save_button = btn
                    print(f"  Found visible Save button: '{btn.text}'")
                    return save_button
        except:
            pass
    
    return None


def select_visa_type_option(driver):
    """Select visa type option from the second dropdown."""
    print("\nStep 2: Opening second dropdown and selecting 'Visa application (Schengen visa- type 'C')'...")
    
    try:
        # Find the dropdown trigger and label
        dropdown_trigger, label = find_dropdown_trigger_by_label(
            driver,
            VISA_TYPE_DROPDOWN_ID,
            label_text_pattern="Visa application (Schengen visa"
        )
        
        # Open the dropdown if we found a trigger
        if dropdown_trigger:
            print("  Clicking dropdown trigger to open it...")
            scroll_to_element(driver, dropdown_trigger)
            time.sleep(0.3)
            driver.execute_script("arguments[0].click();", dropdown_trigger)
            time.sleep(1.5)  # Wait for dropdown to open
            print("  Dropdown opened")
        else:
            print("  Could not find dropdown trigger, will try to find input directly...")
        
        # Find the input element
        input_element = find_input_by_id_or_label(driver, VISA_TYPE_DROPDOWN_ID, label)
        
        if input_element:
            scroll_to_element(driver, input_element)
            time.sleep(0.3)
            
            # Check element type and click accordingly
            input_type = input_element.get_attribute("type")
            print(f"  Input element type: {input_type}")
            
            if input_type == "checkbox":
                if not input_element.is_selected():
                    driver.execute_script("arguments[0].click();", input_element)
                    print(f"  ✓ Checked checkbox: '{VISA_TYPE_OPTION_TEXT}'")
                else:
                    print(f"  ✓ Checkbox already selected")
            elif input_type == "radio":
                driver.execute_script("arguments[0].click();", input_element)
                print(f"  ✓ Selected radio: '{VISA_TYPE_OPTION_TEXT}'")
            else:
                driver.execute_script("arguments[0].click();", input_element)
                print(f"  ✓ Clicked element: '{VISA_TYPE_OPTION_TEXT}'")
            
            time.sleep(0.5)
            
            # Click the Save button
            print("  Looking for 'Save' button in dropdown...")
            save_button = find_save_button(driver, input_element)
            
            if save_button:
                print("  Clicking Save button...")
                scroll_to_element(driver, save_button)
                time.sleep(0.3)
                driver.execute_script("arguments[0].click();", save_button)
                time.sleep(1)  # Wait for dropdown to close
                print("  ✓ Save button clicked, dropdown should be closed")
            else:
                print("  ✗ Could not find Save button in dropdown")
                _list_all_buttons(driver)
        else:
            print("  ✗ Could not find input element for 'Visa application (Schengen visa- type 'C')'")
            _debug_visa_type_search(driver)
    except Exception as e:
        print(f"  ✗ Error selecting second dropdown option: {e}")
        import traceback
        traceback.print_exc()


def _list_all_buttons(driver):
    """List all visible buttons for debugging."""
    print("  Listing all visible buttons...")
    buttons = driver.find_elements(By.XPATH, "//button")
    for btn in buttons:
        if btn.is_displayed():
            print(f"    Button: text='{btn.text[:50]}', id='{btn.get_attribute('id')}', class='{btn.get_attribute('class')[:50]}'")


def _debug_visa_type_search(driver):
    """Debug helper for visa type search."""
    print("  Searching for elements with id '7c357940-1e4e-4b29-8e87-8b1d09b97d07'...")
    elements = driver.find_elements(
        By.XPATH,
        "//*[@id='7c357940-1e4e-4b29-8e87-8b1d09b97d07'] | //*[contains(@id, '7c357940-1e4e-4b29-8e87-8b1d09b97d07')]"
    )
    for elem in elements:
        print(f"    Found: tag='{elem.tag_name}', type='{elem.get_attribute('type')}', id='{elem.get_attribute('id')}'")
    
    print("  Searching for labels...")
    labels = driver.find_elements(By.XPATH, "//label[contains(text(), 'Visa application')]")
    for lbl in labels:
        lbl_for = lbl.get_attribute("for")
        lbl_text = lbl.text
        print(f"    Label: text='{lbl_text[:50]}', for='{lbl_for}'")


