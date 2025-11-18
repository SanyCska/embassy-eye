"""
Telegram notification module for sending results and screenshots.
"""

import os
import requests
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_USER_ID = os.getenv("TELEGRAM_USER_ID")


def _ensure_telegram_config() -> bool:
    """Verify that the Telegram bot credentials are configured."""
    if not TELEGRAM_BOT_TOKEN:
        print("Warning: TELEGRAM_BOT_TOKEN not set in .env file")
        return False
    if not TELEGRAM_USER_ID:
        print("Warning: TELEGRAM_USER_ID not set in .env file")
        return False
    return True


def send_telegram_message(message: str, screenshot_bytes: bytes = None):
    """
    Send a message to the user via Telegram bot.
    
    Args:
        message: Text message to send
        screenshot_bytes: Optional screenshot bytes to attach
    
    Returns:
        bool: True if message was sent successfully, False otherwise
    """
    if not _ensure_telegram_config():
        return False
    
    try:
        if screenshot_bytes:
            # Send message with photo from memory
            url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendPhoto"
            
            files = {'photo': ('screenshot.png', screenshot_bytes, 'image/png')}
            data = {
                'chat_id': TELEGRAM_USER_ID,
                'caption': message
            }
            response = requests.post(url, files=files, data=data)
        else:
            # Send text message only
            url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
            data = {
                'chat_id': TELEGRAM_USER_ID,
                'text': message
            }
            response = requests.post(url, json=data)
        
        response.raise_for_status()
        print(f"✓ Telegram message sent successfully")
        return True
        
    except requests.exceptions.RequestException as e:
        print(f"Error sending Telegram message: {e}")
        return False
    except Exception as e:
        print(f"Unexpected error sending Telegram message: {e}")
        return False


def send_telegram_document(filename: str, caption: str, file_bytes: bytes) -> bool:
    """
    Send a document (e.g., HTML dump) to the user via Telegram bot.
    
    Args:
        filename: Name of the document (shown in Telegram)
        caption: Optional caption (max 1024 characters)
        file_bytes: File content in bytes
    
    Returns:
        bool: True if document was sent successfully, False otherwise
    """
    if not _ensure_telegram_config():
        return False
    
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendDocument"
        files = {'document': (filename, file_bytes, 'text/html')}
        data = {
            'chat_id': TELEGRAM_USER_ID,
            'caption': caption[:1024] if caption else ""
        }
        response = requests.post(url, files=files, data=data)
        response.raise_for_status()
        print("✓ Telegram document sent successfully")
        return True
    except requests.exceptions.RequestException as e:
        print(f"Error sending Telegram document: {e}")
        return False
    except Exception as e:
        print(f"Unexpected error sending Telegram document: {e}")
        return False


def send_result_notification(slots_available: bool, screenshot_bytes: bytes = None, special_case: str = None):
    """
    Send appointment availability result notification.
    Only sends notification when slots are found.
    
    Args:
        slots_available: True if slots are available, False otherwise
        screenshot_bytes: Optional screenshot bytes to attach (None for special cases)
        special_case: String indicating special case: "captcha_required", "email_verification", or None
    """
    if not slots_available:
        # Don't send notification if no slots found
        return
    
    if special_case == "captcha_required":
        message = "✅ SLOTS FOUND!\n\nThere are available appointment slots!\n\n⚠️ Site requests captcha check on site"
        # Send without screenshot for captcha case
        send_telegram_message(message, None)
    elif special_case == "email_verification":
        message = "✅ SLOTS FOUND!\n\nThere are available appointment slots!\n\n⚠️ Site requested email verification (captcha was sent on email)"
        # Send without screenshot for email verification case
        send_telegram_message(message, None)
    else:
        message = "✅ SLOTS FOUND!\n\nThere are available appointment slots!"
        send_telegram_message(message, screenshot_bytes)

