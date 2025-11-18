"""
Automation subpackage containing Selenium utilities and form helpers.
"""

from .button_handlers import click_next_button, find_next_button
from .dropdown_handlers import select_consulate_option, select_visa_type_option
from .form_helpers import (
    fill_fields_by_map,
    fill_reenter_email_field,
    fill_remaining_fields,
    fill_select_dropdowns,
    fill_textareas,
)
from .modal_checker import check_appointment_availability, detect_blocked_ip
from .webdriver_utils import (
    create_driver,
    get_full_page_screenshot,
    inspect_form_fields,
    navigate_to_booking_page,
    scroll_to_element,
)

__all__ = [
    "check_appointment_availability",
    "click_next_button",
    "create_driver",
    "detect_blocked_ip",
    "fill_fields_by_map",
    "fill_reenter_email_field",
    "fill_remaining_fields",
    "fill_select_dropdowns",
    "fill_textareas",
    "find_next_button",
    "get_full_page_screenshot",
    "inspect_form_fields",
    "navigate_to_booking_page",
    "scroll_to_element",
    "select_consulate_option",
    "select_visa_type_option",
]

