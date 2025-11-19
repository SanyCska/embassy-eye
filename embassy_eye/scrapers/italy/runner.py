#!/usr/bin/env python3
"""
Production-ready Playwright script for handling reCAPTCHA Enterprise login
on prenotami.esteri.it using real Google Chrome via CDP.

Launches real Google Chrome (not Playwright Chromium) and connects via
Chrome DevTools Protocol to ensure:
- Real Chrome Client Hints (Sec-CH-UA*, Platform, Architecture)
- Google Integrity tokens
- Full Enterprise reCAPTCHA API bindings
- Correct Trusted Types support
- CSP script loading

Uses minimal stealth (only webdriver override) - no fingerprint spoofing.
"""

import sys
import os
import time
import random
import math
import datetime
import subprocess
import tempfile
import signal
from typing import Optional, Dict, Any, Tuple, List
from dotenv import load_dotenv
from playwright.sync_api import (
    sync_playwright,
    Page,
    BrowserContext,
    TimeoutError as PlaywrightTimeoutError,
    Response,
    Request,
)
from ...notifications import send_telegram_message

# Load environment variables
load_dotenv()

# Configuration
LOGIN_URL = os.getenv("ITALY_LOGIN_URL", "https://prenotami.esteri.it/")
EMAIL = os.getenv("LOGIN_EMAIL") or os.getenv("ITALY_EMAIL", "")
PASSWORD = os.getenv("LOGIN_PASSWORD") or os.getenv("ITALY_PASSWORD", "")

# Headless mode configuration (for Docker/server environments)
# Set ITALY_HEADLESS=true or ITALY_INTERACTIVE=false to run in headless mode
HEADLESS_MODE = os.getenv("ITALY_HEADLESS", "").lower() in ("true", "1", "yes") or \
                os.getenv("ITALY_INTERACTIVE", "").lower() in ("false", "0", "no")

# Proxy configuration (optional)
PROXY_SERVER = os.getenv("PROXY_SERVER", "")  # e.g., "http://proxy.example.com:8080"
PROXY_USERNAME = os.getenv("PROXY_USERNAME", "")
PROXY_PASSWORD = os.getenv("PROXY_PASSWORD", "")

# Selectors
EMAIL_SELECTOR = "#login-email"
PASSWORD_SELECTOR = "#login-password"
CAPTCHA_TRIGGER_SELECTOR = "#captcha-trigger"
LOGIN_FORM_SELECTOR = "#login-form"
SERVICES_TAB_SELECTOR = "nav.app-menu a[href='/Services']"
BOOKING_TARGET_URLS = [
    "/Services/Booking/1151",
    "/Services/Booking/1258",
]
NO_SLOT_MESSAGES = [
    "Sorry, all appointments for this service are currently booked. Please check again tomorrow for cancellations or new appointments.",
    "Stante l'elevata richiesta i posti disponibili per il servizio scelto sono esauriti."
]
APPOINTMENT_PORTAL_URL = "https://prenotami.esteri.it/"

# Timeouts (in milliseconds)
PAGE_LOAD_TIMEOUT = 45000
NETWORK_IDLE_TIMEOUT = 30000
ELEMENT_WAIT_TIMEOUT = 15000
CAPTCHA_COMPLETE_TIMEOUT = 90000
LOGIN_COMPLETE_TIMEOUT = 60000


class LoginError(Exception):
    """Custom exception for login-related errors."""
    pass


class CaptchaError(Exception):
    """Custom exception for captcha-related errors."""
    pass


class Logger:
    """Centralized logging utility."""
    
    @staticmethod
    def log(message: str, level: str = "INFO"):
        """Log a message with timestamp."""
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"[{timestamp}] [{level}] {message}")
        sys.stdout.flush()


class StealthPatcher:
    """Minimal stealth mode - only removes webdriver property."""
    
    @staticmethod
    def get_stealth_script() -> str:
        """Return minimal stealth JavaScript - only webdriver override."""
        return """
        (function() {
            'use strict';
            
            // Only safe override: remove webdriver property
            // All other fingerprint spoofing is removed to allow reCAPTCHA Enterprise
            // to work properly with natural browser fingerprint
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined
            });
        })();
        """


class MouseSimulator:
    """Human-like mouse movement simulation."""
    
    def __init__(self, page: Page):
        self.page = page
        self.current_x = 0
        self.current_y = 0
    
    def move_to(self, target_x: int, target_y: int, steps: Optional[int] = None) -> None:
        """
        Move mouse to target coordinates with human-like trajectory.
    
    Args:
            target_x: Target X coordinate
            target_y: Target Y coordinate
            steps: Number of steps (auto-calculated if None)
        """
        if steps is None:
            distance = math.sqrt((target_x - self.current_x)**2 + (target_y - self.current_y)**2)
            steps = max(10, min(50, int(distance / 10)))
        
        # Generate Bezier curve control points for natural movement
        control_x1 = self.current_x + (target_x - self.current_x) * 0.25 + random.randint(-20, 20)
        control_y1 = self.current_y + (target_y - self.current_y) * 0.25 + random.randint(-20, 20)
        control_x2 = self.current_x + (target_x - self.current_x) * 0.75 + random.randint(-20, 20)
        control_y2 = self.current_y + (target_y - self.current_y) * 0.75 + random.randint(-20, 20)
        
        for i in range(steps + 1):
            t = i / steps
            # Bezier curve interpolation
            x = (1-t)**3 * self.current_x + 3*(1-t)**2*t * control_x1 + 3*(1-t)*t**2 * control_x2 + t**3 * target_x
            y = (1-t)**3 * self.current_y + 3*(1-t)**2*t * control_y1 + 3*(1-t)*t**2 * control_y2 + t**3 * target_y
            
            # Add small random jitter
            x += random.uniform(-1, 1)
            y += random.uniform(-1, 1)
            
            self.page.mouse.move(int(x), int(y))
            
            # Variable delay between steps
            time.sleep(random.uniform(0.005, 0.015))
        
        self.current_x = target_x
        self.current_y = target_y
    
    def random_movement(self, center_x: int, center_y: int, radius: int = 50) -> None:
        """
        Perform random jitter movement around a center point.
        
        Args:
            center_x: Center X coordinate
            center_y: Center Y coordinate
            radius: Movement radius
        """
        for _ in range(random.randint(2, 5)):
            jitter_x = center_x + random.randint(-radius, radius)
            jitter_y = center_y + random.randint(-radius, radius)
            self.move_to(jitter_x, jitter_y, steps=random.randint(5, 15))
            time.sleep(random.uniform(0.2, 0.6))
    
    def move_to_element(self, element, offset_x: int = 0, offset_y: int = 0) -> None:
        """
        Move mouse to an element with human-like movement.
        
        Args:
            element: Playwright locator or element
            offset_x: X offset from element center
            offset_y: Y offset from element center
        """
        box = element.bounding_box()
        if box:
            target_x = int(box['x'] + box['width'] / 2 + offset_x)
            target_y = int(box['y'] + box['height'] / 2 + offset_y)
            
            # Small random movement before moving to element
            if self.current_x > 0 or self.current_y > 0:
                self.random_movement(self.current_x, self.current_y, radius=30)
            
            self.move_to(target_x, target_y)
            time.sleep(random.uniform(0.3, 0.9))


class TypingSimulator:
    """Human-like typing simulation."""
    
    @staticmethod
    def type_human_like(page: Page, selector: str, text: str) -> None:
        """
        Type text with human-like delays and event triggering.
    
    Args:
        page: Playwright page object
            selector: CSS selector for the input field
            text: Text to type
        """
        field = page.locator(selector)
        field.click()
        time.sleep(random.uniform(0.2, 0.4))
        
        # Clear field
        field.fill("")
        time.sleep(random.uniform(0.1, 0.2))
        
        # Type character by character with variable delays
        for char in text:
            field.type(char, delay=random.uniform(80, 160))
            
            # Occasional longer pauses (like thinking)
            if random.random() < 0.1:
                time.sleep(random.uniform(0.2, 0.5))
        
        # Trigger all necessary events
        page.evaluate(f"""
            (value) => {{
                const field = document.querySelector('{selector}');
                if (field) {{
                    field.value = value;
                    field.dispatchEvent(new Event('input', {{ bubbles: true, cancelable: true }}));
                    field.dispatchEvent(new Event('change', {{ bubbles: true, cancelable: true }}));
                    field.dispatchEvent(new Event('keyup', {{ bubbles: true, cancelable: true }}));
                    field.dispatchEvent(new Event('blur', {{ bubbles: true, cancelable: true }}));
                    
                    // jQuery events if available
                    if (typeof jQuery !== 'undefined') {{
                        jQuery(field).trigger('input');
                        jQuery(field).trigger('change');
                        jQuery(field).trigger('blur');
                    }}
                }}
            }}
        """, text)
        
        time.sleep(random.uniform(0.3, 0.6))


class ScrollSimulator:
    """Human-like scrolling simulation."""
    
    @staticmethod
    def scroll_realistic(page: Page, direction: str = "down", amount: int = 300) -> None:
        """
        Perform realistic scrolling with incremental steps.
    
    Args:
        page: Playwright page object
            direction: 'up' or 'down'
            amount: Total scroll amount in pixels
        """
        steps = random.randint(5, 12)
        step_size = amount // steps
        
        for i in range(steps):
            scroll_amount = step_size + random.randint(-10, 10)
            if direction == "down":
                page.mouse.wheel(0, scroll_amount)
            else:
                page.mouse.wheel(0, -scroll_amount)
            
            time.sleep(random.uniform(0.05, 0.15))
        
        # Small pause after scrolling
        time.sleep(random.uniform(0.2, 0.4))
    
    @staticmethod
    def scroll_to_element(page: Page, element) -> None:
        """
        Scroll to element with realistic behavior.
        
        Args:
            page: Playwright page object
            element: Playwright locator
        """
        element.scroll_into_view_if_needed()
        time.sleep(random.uniform(0.3, 0.7))
        
        # Small additional scroll for natural positioning
        page.mouse.wheel(0, random.randint(-50, 50))
        time.sleep(random.uniform(0.2, 0.4))
        

class HumanBehavior:
    """Human behavior simulation utilities."""
    
    @staticmethod
    def random_delay(min_ms: float = 300, max_ms: float = 900) -> None:
        """
        Random delay to simulate human thinking/reading time.
        
        Args:
            min_ms: Minimum delay in milliseconds
            max_ms: Maximum delay in milliseconds
        """
        time.sleep(random.uniform(min_ms / 1000, max_ms / 1000))
    
    @staticmethod
    def simulate_reading(page: Page) -> None:
        """Simulate reading the page."""
        HumanBehavior.random_delay(800, 1800)
        
        # Small random mouse movements while "reading"
        mouse = MouseSimulator(page)
        viewport = page.viewport_size
        if viewport:
            for _ in range(random.randint(1, 3)):
                x = random.randint(100, viewport['width'] - 100)
                y = random.randint(100, viewport['height'] - 100)
                mouse.move_to(x, y, steps=random.randint(5, 15))
                HumanBehavior.random_delay(200, 600)
    
    @staticmethod
    def simulate_tab_switch(page: Page) -> None:
        """Simulate tab switching by blurring and focusing."""
        page.evaluate("window.blur()")
        HumanBehavior.random_delay(500, 1500)
        page.evaluate("window.focus()")
        HumanBehavior.random_delay(200, 400)


class BrowserFingerprint:
    """Generate realistic browser fingerprint."""
    
    @staticmethod
    def get_fingerprint_config() -> Dict[str, Any]:
        """Get realistic browser fingerprint configuration."""
        # Realistic viewport sizes (common resolutions)
        viewports = [
            {'width': 1920, 'height': 1080},
            {'width': 1366, 'height': 768},
            {'width': 1536, 'height': 864},
            {'width': 1440, 'height': 900},
        ]
        viewport = random.choice(viewports)
        
        # Realistic user agents (Chrome on macOS)
        user_agents = [
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/132.0.0.0 Safari/537.36',
        ]
                
        return {
            'viewport': viewport,
            'user_agent': random.choice(user_agents),
            'locale': 'it-IT',
            'timezone_id': 'Europe/Rome',
            'device_scale_factor': 1.0,
            'color_scheme': 'light',
            'geolocation': {'latitude': 41.9028, 'longitude': 12.4964},
            'permissions': ['geolocation'],
            'extra_http_headers': {
                'Accept-Language': 'it-IT,it;q=0.9,en-US;q=0.8,en;q=0.7',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
                'Accept-Encoding': 'gzip, deflate, br',
                'DNT': '1',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1',
                'Sec-Fetch-Dest': 'document',
                'Sec-Fetch-Mode': 'navigate',
                'Sec-Fetch-Site': 'none',
                'Sec-Fetch-User': '?1',
                'Cache-Control': 'max-age=0',
            }
        }


class ProxyConfig:
    """Proxy configuration handler."""
    
    @staticmethod
    def get_proxy_config() -> Optional[Dict[str, str]]:
        """
        Get proxy configuration from environment variables.
        
        Returns:
            Proxy config dict or None if not configured
        """
        if not PROXY_SERVER:
            return None
        
        config = {'server': PROXY_SERVER}
        
        if PROXY_USERNAME and PROXY_PASSWORD:
            config['username'] = PROXY_USERNAME
            config['password'] = PROXY_PASSWORD
        
        return config


class ItalyLoginBot:
    """Main bot class for Italy login with anti-detection."""
    
    def __init__(self):
        self.playwright_instance = None
        self.browser = None
        self.context = None
        self.page = None
        self.mouse = None
        self.chrome_process = None
        self.xvfb_process = None
        self.user_data_dir = None
        self.slots_notified = False
    
    def setup_browser(self) -> None:
        """Setup browser by launching real Google Chrome and connecting via CDP."""
        Logger.log("Setting up real Google Chrome with CDP connection...")
        
        # Try to use Xvfb virtual display for headless mode (avoids detection)
        # This is better than --headless flag because it's harder to detect
        self.xvfb_process = None
        xvfb_started = False
        
        if HEADLESS_MODE:
            Logger.log("Attempting to use Xvfb virtual display (better than --headless for anti-detection)...")
            try:
                self.xvfb_process = subprocess.Popen(
                    ['Xvfb', ':99', '-screen', '0', '1920x1080x24', '-ac', '+extension', 'RANDR'],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL
                )
                time.sleep(2)  # Give Xvfb time to start
                
                # Check if Xvfb is running
                if self.xvfb_process.poll() is None:
                    os.environ['DISPLAY'] = ':99'
                    Logger.log("✓ Xvfb virtual display started (DISPLAY=:99)")
                    xvfb_started = True
                else:
                    Logger.log("⚠ Xvfb failed to start, will fall back to --headless mode", "WARN")
                    self.xvfb_process = None
            except FileNotFoundError:
                Logger.log("⚠ Xvfb not found (install with: apt-get install xvfb or brew install xquartz)", "WARN")
                Logger.log("⚠ Falling back to --headless mode (may be detected by website)", "WARN")
            except Exception as e:
                Logger.log(f"⚠ Failed to start Xvfb: {e}, falling back to --headless mode", "WARN")
                self.xvfb_process = None
        
        # Create temporary user data directory for Chrome
        self.user_data_dir = tempfile.mkdtemp(prefix="chrome_user_data_")
        Logger.log(f"Using Chrome user data directory: {self.user_data_dir}")
        
        proxy_config = ProxyConfig.get_proxy_config()
        
        # Build Chrome launch command
        chrome_args = [
            'google-chrome',  # or 'chromium' or 'chrome' depending on system
            '--remote-debugging-port=9222',
            f'--user-data-dir={self.user_data_dir}',
            '--disable-dev-shm-usage',
            '--no-sandbox',
            '--disable-blink-features=AutomationControlled',
        ]
        
        # Add headless mode flags if running in Docker/server environment
        if HEADLESS_MODE:
            if xvfb_started:
                # Use Xvfb virtual display instead of --headless (harder to detect)
                chrome_args.extend([
                    '--display=:99',
                    '--window-size=1920,1080',
                ])
                Logger.log("Running Chrome with Xvfb virtual display (avoids headless detection)")
            else:
                # Fallback to --headless if Xvfb not available
                chrome_args.extend([
                    '--headless=new',
                    '--disable-gpu',
                    '--disable-software-rasterizer',
                    '--disable-extensions',
                ])
                Logger.log("Running Chrome in headless mode (may be detected by website)", "WARN")
        else:
            Logger.log("Running Chrome in interactive mode")
        
        # Add proxy if configured
        if proxy_config:
            proxy_server = proxy_config['server']
            chrome_args.append(f'--proxy-server={proxy_server}')
            Logger.log(f"Using proxy: {proxy_server}")
        
        # Launch real Google Chrome
        Logger.log("Launching real Google Chrome...")
        try:
            self.chrome_process = subprocess.Popen(
                chrome_args,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                preexec_fn=os.setsid if hasattr(os, 'setsid') else None
            )
            Logger.log("✓ Chrome launched")
        except FileNotFoundError:
            # Try alternative Chrome executable names
            for chrome_name in ['chromium', 'chrome', 'chromium-browser', '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome']:
                try:
                    chrome_args[0] = chrome_name
                    self.chrome_process = subprocess.Popen(
                        chrome_args,
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                        preexec_fn=os.setsid if hasattr(os, 'setsid') else None
                    )
                    Logger.log(f"✓ Chrome launched using: {chrome_name}")
                    break
                except FileNotFoundError:
                    continue
            else:
                raise LoginError("Could not find Google Chrome executable. Please install Chrome or set PATH correctly.")
        
        # Wait for Chrome to start and CDP to be available
        Logger.log("Waiting for Chrome CDP to be ready...")
        import urllib.request
        max_retries = 30  # Increased timeout for Docker environments
        for i in range(max_retries):
            try:
                with urllib.request.urlopen("http://localhost:9222/json/version", timeout=2) as response:
                    if response.status == 200:
                        Logger.log("✓ Chrome CDP is ready")
                        break
            except Exception as e:
                if i < max_retries - 1:
                    if (i + 1) % 5 == 0:  # Log every 5 seconds
                        Logger.log(f"  → Still waiting for CDP... ({i + 1}s elapsed)")
                    time.sleep(1)
                else:
                    # Check if Chrome process is still running
                    if self.chrome_process and self.chrome_process.poll() is None:
                        Logger.log(f"✗ Chrome CDP did not become available after {max_retries} seconds", "ERROR")
                        Logger.log(f"  Chrome process is running but CDP not accessible. Last error: {e}", "ERROR")
                        Logger.log("  This may indicate a Docker networking issue or Chrome startup problem.", "ERROR")
                    else:
                        Logger.log("✗ Chrome process exited unexpectedly", "ERROR")
                    raise LoginError("Chrome CDP did not become available. Chrome may have failed to start.")
        
        # Connect Playwright to real Chrome via CDP
        Logger.log("Connecting Playwright to Chrome via CDP...")
        p = sync_playwright().start()
        self.playwright_instance = p
        
        try:
            self.browser = p.chromium.connect_over_cdp("http://localhost:9222")
            Logger.log("✓ Connected to Chrome via CDP")
        except Exception as e:
            raise LoginError(f"Failed to connect to Chrome via CDP: {e}. Make sure Chrome started successfully.")
        
        # Get the default context (Chrome creates one automatically)
        contexts = self.browser.contexts
        if contexts:
            self.context = contexts[0]
            Logger.log("✓ Using existing Chrome context")
        else:
            # Create new context if none exists
            self.context = self.browser.new_context()
            Logger.log("✓ Created new Chrome context")
        
        # Get or create a page
        pages = self.context.pages
        if pages:
            self.page = pages[0]
            Logger.log("✓ Using existing Chrome page")
        else:
            self.page = self.context.new_page()
            Logger.log("✓ Created new Chrome page")
        
        # Inject minimal stealth script (only webdriver override)
        # Do NOT override user-agent, viewport, or any other fingerprint properties
        # Real Chrome handles Client Hints naturally
        self.page.add_init_script(StealthPatcher.get_stealth_script())
        Logger.log("✓ Minimal stealth mode enabled (webdriver only)")
        
        # Initialize mouse simulator
        self.mouse = MouseSimulator(self.page)
        
        Logger.log("✓ Browser setup complete (real Chrome via CDP)")
    
    def navigate_to_login(self) -> None:
        """Navigate to login page with human-like behavior."""
        Logger.log(f"Navigating to login page: {LOGIN_URL}")
        
        # Small delay before navigation
        HumanBehavior.random_delay(500, 1000)
        
        try:
            response = self.page.goto(
                LOGIN_URL,
                wait_until='domcontentloaded',
                timeout=PAGE_LOAD_TIMEOUT
            )
            
            if response and response.status >= 400:
                raise LoginError(f"HTTP {response.status} error loading login page")
            
            Logger.log("✓ Page loaded")
        except PlaywrightTimeoutError:
            Logger.log("⚠ Page load timeout, continuing anyway...", "WARN")
        except Exception as e:
            raise LoginError(f"Error loading page: {e}")
        
        # Wait for network idle
        Logger.log("Waiting for page to be fully loaded...")
        try:
            self.page.wait_for_load_state('networkidle', timeout=NETWORK_IDLE_TIMEOUT)
            Logger.log("✓ Page network idle")
        except PlaywrightTimeoutError:
            Logger.log("⚠ Network idle timeout, continuing anyway...", "WARN")
        
        # Simulate reading the page
        HumanBehavior.simulate_reading(self.page)
        
        # Small random scroll
        ScrollSimulator.scroll_realistic(self.page, "down", random.randint(100, 300))
    
    def wait_for_recaptcha_scripts(self) -> bool:
        """Wait for reCAPTCHA Enterprise scripts to be fully ready."""
        Logger.log("Waiting for reCAPTCHA Enterprise to be ready...")
        
        try:
            # Wait for reCAPTCHA Enterprise to be loaded
            # Use a safer check that doesn't access properties that might not exist
            self.page.wait_for_function("""
                () => {
                    return typeof window.grecaptcha !== 'undefined' &&
                           window.grecaptcha &&
                           typeof window.grecaptcha.enterprise !== 'undefined' &&
                           window.grecaptcha.enterprise;
                }
            """, timeout=20000)
            Logger.log("✓ reCAPTCHA Enterprise loaded")
            
            # Additional check: verify it's actually functional
            is_ready = self.page.evaluate("""
                () => {
                    try {
                        if (typeof window.grecaptcha !== 'undefined' && 
                            window.grecaptcha && 
                            window.grecaptcha.enterprise) {
                            // Check if execute method exists (indicates it's ready)
                            return typeof window.grecaptcha.enterprise.execute === 'function' ||
                                   typeof window.grecaptcha.execute === 'function';
                    }
                    return false;
                    } catch (e) {
                    return false;
                    }
                }
            """)
            
            if is_ready:
                Logger.log("✓ reCAPTCHA Enterprise is ready and functional")
                return True
            else:
                Logger.log("⚠ reCAPTCHA Enterprise loaded but may not be fully ready", "WARN")
                return True  # Continue anyway - it might still work
                
        except PlaywrightTimeoutError:
            Logger.log("⚠ reCAPTCHA Enterprise not loaded within timeout", "WARN")
            return False
        except Exception as e:
            Logger.log(f"⚠ Error checking reCAPTCHA Enterprise: {e}", "WARN")
            # Continue anyway - the site might still work
        return True
        
    def fill_login_form(self) -> None:
        """Fill login form with human-like behavior."""
        Logger.log("Filling login form...")
        
        # Wait for form to be ready
        self.page.wait_for_selector(LOGIN_FORM_SELECTOR, timeout=ELEMENT_WAIT_TIMEOUT)
        HumanBehavior.random_delay(400, 800)
        
        # Fill email field
        Logger.log("Filling email field...")
        email_field = self.page.locator(EMAIL_SELECTOR)
        email_field.wait_for(state="visible", timeout=ELEMENT_WAIT_TIMEOUT)
        
        # Move mouse to email field
        self.mouse.move_to_element(email_field)
        HumanBehavior.random_delay(300, 600)
        
        # Type email
        TypingSimulator.type_human_like(self.page, EMAIL_SELECTOR, EMAIL)
        HumanBehavior.random_delay(400, 1200)
        
        # Fill password field
        Logger.log("Filling password field...")
        password_field = self.page.locator(PASSWORD_SELECTOR)
        password_field.wait_for(state="visible", timeout=ELEMENT_WAIT_TIMEOUT)
        
        # Move mouse to password field
        self.mouse.move_to_element(password_field)
        HumanBehavior.random_delay(300, 600)
        
        # Type password
        TypingSimulator.type_human_like(self.page, PASSWORD_SELECTOR, PASSWORD)
        HumanBehavior.random_delay(800, 1800)
        
        # Trigger Parsley.js validation (required for button to become enabled)
        Logger.log("Triggering Parsley.js validation...")
        self.page.evaluate("""
            const form = document.querySelector('#login-form');
            if (window.jQuery && jQuery(form).parsley) {
                jQuery('#login-form').parsley().validate();
            }
        """)
        HumanBehavior.random_delay(500, 1000)
        
        Logger.log("✓ Login form filled and validated")
    
    def trigger_captcha(self) -> None:
        """Click captcha trigger button with human-like behavior."""
        Logger.log("Triggering reCAPTCHA...")
        
        # Wait for button to be visible
        button = self.page.locator(CAPTCHA_TRIGGER_SELECTOR)
        button.wait_for(state="visible", timeout=ELEMENT_WAIT_TIMEOUT)
        
        # Scroll to button
        ScrollSimulator.scroll_to_element(self.page, button)
        HumanBehavior.random_delay(400, 800)
        
        # Explicitly wait for button to become enabled
        # This is critical - button stays disabled until Parsley validation passes
        Logger.log("Waiting for captcha button to become enabled...")
        try:
            self.page.wait_for_function(f"""
                () => {{
                    const btn = document.querySelector('{CAPTCHA_TRIGGER_SELECTOR}');
                    return btn && !btn.disabled;
                }}
            """, timeout=15000)
            Logger.log("✓ Captcha button is enabled")
        except PlaywrightTimeoutError:
            Logger.log("✗ Captcha button did not become enabled within timeout", "ERROR")
            # Check button state for debugging
            button_state = self.page.evaluate(f"""
                () => {{
                    const btn = document.querySelector('{CAPTCHA_TRIGGER_SELECTOR}');
                    return btn ? {{
                        disabled: btn.disabled,
                        visible: btn.offsetParent !== null,
                        style: window.getComputedStyle(btn).display
                    }} : null;
                }}
            """)
            Logger.log(f"Button state: {button_state}", "ERROR")
            raise CaptchaError("Captcha button did not become enabled - validation may have failed")
        
        # Move mouse to button with human-like movement
        self.mouse.move_to_element(button)
        HumanBehavior.random_delay(400, 1200)
        
        # Click button
        button.click(timeout=5000)
        Logger.log("✓ Captcha trigger button clicked")
        
        # Small delay after click
        HumanBehavior.random_delay(300, 600)
    
    def wait_for_captcha_completion(self) -> bool:
        """Wait for reCAPTCHA Enterprise to complete."""
        Logger.log("Waiting for reCAPTCHA Enterprise to complete...")
        
        start_time = time.time()
        captcha_requests_seen = set()
        login_request_sent = False
        login_response_status = None
        navigation_occurred = False
        
        def handle_request(request: Request):
            """Track captcha and login requests."""
            nonlocal login_request_sent
            url = request.url
            
            if "recaptcha" in url.lower() or "google.com/recaptcha" in url:
                captcha_requests_seen.add(url)
                Logger.log(f"  → Captcha request: {url[:80]}...")
            
            if "/Home/Login" in url and request.method == "POST":
                login_request_sent = True
                Logger.log(f"  → Login POST request detected: {url}")
        
        def handle_response(response: Response):
            """Track login responses."""
            nonlocal login_response_status
            url = response.url
            if "/Home/Login" in url and response.request.method == "POST":
                login_response_status = response.status
                Logger.log(f"  → Login response: status {response.status}")
                # 302 means redirect - login succeeded!
                if response.status == 302:
                    Logger.log("✓ 302 redirect detected - login successful!")
                # Status 200 might indicate an error page (like "Unavailable")
                elif response.status == 200:
                    # Check response body for "Unavailable" error
                    try:
                        response_text = response.text()
                        if "Unavailable" in response_text:
                            Logger.log("✗ Received 'Unavailable' error in login response", "ERROR")
                    except:
                        pass
        
        def handle_navigation(frame):
            """Track navigation events."""
            nonlocal navigation_occurred
            if frame == self.page.main_frame:
                navigation_occurred = True
                Logger.log("✓ Navigation detected - login may have succeeded")
        
        self.page.on("request", handle_request)
        self.page.on("response", handle_response)
        self.page.on("framenavigated", handle_navigation)
        
        try:
            while (time.time() - start_time) * 1000 < CAPTCHA_COMPLETE_TIMEOUT:
                # If we got a 302 redirect, login succeeded
                if login_response_status == 302:
                    Logger.log("✓ Login successful (302 redirect)")
                    time.sleep(1)  # Wait for navigation to complete
                    return True
                
                # If navigation occurred, login likely succeeded
                if navigation_occurred:
                    Logger.log("✓ Navigation occurred - login successful")
                    return True
                
                # Check for captcha token (with error handling for navigation)
                try:
                    has_token = self.page.evaluate("""
                        () => {
                            if (typeof window.grecaptcha !== 'undefined') {
                                try {
                                    const response = window.grecaptcha.getResponse();
                                    if (response && response.length > 0) {
                                        return true;
                                    }
                                } catch (e) {}
                            }
                            
                            const form = document.querySelector('#login-form');
                            if (form) {
                                const tokenInputs = form.querySelectorAll(
                                    'input[name*="recaptcha"], input[name*="g-recaptcha"], textarea[name*="recaptcha"]'
                                );
                                for (let input of tokenInputs) {
                                    if (input.value && input.value.length > 0) {
                                        return true;
                                    }
                                }
                            }
                            return false;
                        }
                    """)
                    
                    if has_token:
                        Logger.log("✓ reCAPTCHA token detected")
                        # Wait a bit more for token to be used
                        time.sleep(1)
                        return True
                except Exception as e:
                    # Navigation might have occurred during evaluation
                    if "destroyed" in str(e).lower() or "navigation" in str(e).lower():
                        Logger.log("✓ Page navigated during check - login likely succeeded")
                        return True
                    # Other errors - log and continue
                    Logger.log(f"⚠ Error checking token: {e}", "WARN")
                
                # Check if login form is gone (navigation happened)
                try:
                    is_login_page = self.page.evaluate(f"""
                        () => {{
                            const form = document.querySelector('{LOGIN_FORM_SELECTOR}');
                            return form !== null && form.offsetParent !== null;
                        }}
                    """)
                    
                    if not is_login_page:
                        Logger.log("✓ Login form not found - navigation likely occurred")
                        return True
                except Exception as e:
                    # Navigation might have occurred
                    if "destroyed" in str(e).lower() or "navigation" in str(e).lower():
                        Logger.log("✓ Page navigated - login likely succeeded")
                        return True
                
                # Check if login request was sent and we got a response
                if login_request_sent and login_response_status:
                    if login_response_status == 302:
                        Logger.log("✓ Login successful (302 redirect)")
                        time.sleep(1)
                        return True
                    elif login_response_status >= 400:
                        Logger.log(f"✗ Login failed with status {login_response_status}", "ERROR")
                        return False
                    else:
                        # Status 200 - check for "Unavailable" error
                        if self.check_for_unavailable_error():
                            Logger.log("✗ Login response returned 'Unavailable' error page", "ERROR")
                            return False
                        
                        # Wait a bit more for navigation
                        Logger.log("✓ Login request completed, waiting for navigation...")
                        time.sleep(2)
                        # Check URL to see if we navigated
                        try:
                            current_url = self.page.url
                            if "/Error" not in current_url and "/Home/Login" not in current_url:
                                Logger.log(f"✓ Navigated to: {current_url}")
                                return True
                        except:
                            pass
                
                # Check for "Unavailable" error on the page
                try:
                    if self.check_for_unavailable_error():
                        Logger.log("✗ 'Unavailable' error detected on page", "ERROR")
                        return False
                except Exception as e:
                    if "destroyed" in str(e).lower() or "navigation" in str(e).lower():
                        # Navigation occurred - likely success
                        pass
                
                # Check for errors (with navigation handling)
                try:
                    error = self.check_for_errors()
                    if error and "error" in error.lower():
                        Logger.log(f"✗ Error detected: {error}", "ERROR")
                        return False
                except Exception as e:
                    if "destroyed" in str(e).lower() or "navigation" in str(e).lower():
                        # Navigation occurred - likely success
                        return True
                
                time.sleep(1)
                
                if int(time.time() - start_time) % 5 == 0:
                    Logger.log(f"  → Still waiting... ({int(time.time() - start_time)}s elapsed)")
            
            Logger.log("✗ Timeout waiting for captcha completion", "ERROR")
            return False
            
        finally:
            try:
                self.page.remove_listener("request", handle_request)
                self.page.remove_listener("response", handle_response)
                self.page.remove_listener("framenavigated", handle_navigation)
            except:
                pass
    
    def wait_for_login_completion(self) -> Tuple[bool, Optional[str]]:
        """Wait for login to complete."""
        Logger.log("Waiting for login to complete...")
        
        initial_url = self.page.url
        start_time = time.time()
        login_success = False
        new_tab_page: Optional[Page] = None
        switched_to_new_tab = False
        response_listener_pages: List[Page] = []
        
        def register_response_listener(target_page: Optional[Page]) -> None:
            """Attach the shared response handler to the given page once."""
            if not target_page:
                return
            if target_page in response_listener_pages:
                return
            try:
                target_page.on("response", handle_response)
                response_listener_pages.append(target_page)
            except Exception as e:
                Logger.log(f"⚠ Unable to attach response listener to page: {e}", "WARN")
        
        def handle_response(response: Response):
            """Track successful login responses."""
            nonlocal login_success
            url = response.url
            
            if "/Home/Login" in url and response.request.method == "POST":
                if response.status == 302:
                    # 302 redirect means login succeeded
                    login_success = True
                    Logger.log("✓ Login successful (302 redirect detected)")
                elif response.status == 200:
                    # Check response body for success indicators
                    try:
                        body = response.text()
                        if "error" not in body.lower() and "/Error" not in url:
                            login_success = True
                    except:
                        pass
            
            # Check for redirect to dashboard/home/user area
            if "/Error" not in url and initial_url != url:
                if "/Home" in url or "/Dashboard" in url or "/Account" in url or "/UserArea" in url:
                    login_success = True
        
        def handle_new_page(page: Page):
            """Capture new tabs that may contain the authenticated session."""
            nonlocal new_tab_page
            Logger.log("✓ New browser tab detected after login attempt. Monitoring for navigation...")
            register_response_listener(page)
            new_tab_page = page
        
        def find_authenticated_tab() -> Optional[Page]:
            """Look for an already-open tab that navigated beyond the login page."""
            if not self.context:
                return None
            try:
                for candidate in self.context.pages:
                    try:
                        candidate_url = candidate.url
                    except Exception:
                        continue
                    if not candidate_url or candidate_url == "about:blank":
                        continue
                    if "/Error" in candidate_url:
                        continue
                    if "/Home/Login" in candidate_url:
                        continue
                    return candidate
            except Exception as e:
                Logger.log(f"⚠ Unable to inspect browser tabs: {e}", "WARN")
            return None

        register_response_listener(self.page)
        
        if self.context:
            self.context.on("page", handle_new_page)
        
        try:
            while (time.time() - start_time) * 1000 < LOGIN_COMPLETE_TIMEOUT:
                try:
                    current_url = self.page.url
                except:
                    # Navigation might have occurred
                    Logger.log("✓ Page navigated - login likely succeeded")
                    return True, None
                
                authenticated_page = find_authenticated_tab()
                if authenticated_page and authenticated_page is not self.page:
                    try:
                        new_url = authenticated_page.url
                    except Exception:
                        new_url = None
                    register_response_listener(authenticated_page)
                    self.page = authenticated_page
                    self.mouse = MouseSimulator(self.page)
                    if new_url and "/Error" in new_url:
                        Logger.log(f"✗ Authenticated tab landed on error page: {new_url}", "ERROR")
                        return False, new_url
                    Logger.log(f"✓ Switching automation to authenticated tab: {new_url or 'unknown'}")
                    return True, new_url
                
                # Check for error page
                if "/Error" in current_url:
                    Logger.log(f"✗ Error page detected: {current_url}", "ERROR")
                    return False, current_url
                
                # Check if we've navigated to a valid authenticated page
                # Valid pages: /UserArea, /Home, /Dashboard, /Account, /Services
                valid_authenticated_paths = ["/UserArea", "/Home", "/Dashboard", "/Account", "/Services"]
                is_valid_page = any(path in current_url for path in valid_authenticated_paths)
                
                if is_valid_page and "/Error" not in current_url and "/Home/Login" not in current_url:
                    Logger.log(f"✓ Login successful! Navigated to authenticated page: {current_url}")
                    return True, current_url
                
                # Check if we've navigated away from login page (fallback check)
                try:
                    is_login_page = self.page.evaluate(f"""
                        () => {{
                            const form = document.querySelector('{LOGIN_FORM_SELECTOR}');
                            return form !== null && form.offsetParent !== null;
                        }}
                    """)
                    
                    if not is_login_page and current_url != initial_url and "/Error" not in current_url:
                        Logger.log(f"✓ Login successful! Navigated to: {current_url}")
                        return True, current_url
                except Exception as e:
                    # Navigation might have occurred during evaluation
                    if "destroyed" in str(e).lower() or "navigation" in str(e).lower():
                        Logger.log("✓ Page navigated during check - login likely succeeded")
                        return True, None
                
                if login_success:
                    time.sleep(1)
                    # First, inspect existing tabs for a non-login page
                    authenticated_page = find_authenticated_tab()
                    if authenticated_page and authenticated_page is not self.page:
                        Logger.log(f"✓ Switching automation to authenticated tab: {authenticated_page.url}")
                        self.page = authenticated_page
                        self.mouse = MouseSimulator(self.page)
                        return True, authenticated_page.url
                    try:
                        final_url = self.page.url
                        if "/Error" not in final_url:
                            Logger.log(f"✓ Login successful! Final URL: {final_url}")
                            return True, final_url
                    except:
                        # Navigation occurred
                        return True, None
                
                # Check for "Unavailable" error on the page
                try:
                    if self.check_for_unavailable_error():
                        Logger.log("✗ 'Unavailable' error detected on page during login wait", "ERROR")
                        return False, current_url
                except Exception as e:
                    if "destroyed" in str(e).lower() or "navigation" in str(e).lower():
                        # Navigation occurred - likely success
                        pass
                
                # Check for errors (with navigation handling)
                try:
                    error = self.check_for_errors()
                    if error:
                        Logger.log(f"✗ Error detected: {error}", "ERROR")
                        return False, current_url
                except Exception as e:
                    if "destroyed" in str(e).lower() or "navigation" in str(e).lower():
                        # Navigation occurred - likely success
                        return True, None
                
                time.sleep(1)
                
                if int(time.time() - start_time) % 5 == 0:
                    Logger.log(f"  → Still waiting... ({int(time.time() - start_time)}s elapsed)")
                
                if new_tab_page and not switched_to_new_tab:
                    try:
                        new_tab_page.wait_for_load_state("domcontentloaded", timeout=PAGE_LOAD_TIMEOUT)
                    except PlaywrightTimeoutError:
                        Logger.log("⚠ New tab did not reach DOMContentLoaded within timeout; continuing to wait...", "WARN")
                    except Exception as e:
                        Logger.log(f"⚠ Error while waiting for new tab load: {e}", "WARN")
                    
                    try:
                        new_tab_url = new_tab_page.url
                    except Exception:
                        new_tab_url = None
                    
                    if new_tab_url and new_tab_url != "about:blank":
                        switched_to_new_tab = True
                        previous_page = self.page
                        self.page = new_tab_page
                        self.mouse = MouseSimulator(self.page)
                        Logger.log(f"✓ Switching automation to newly opened tab: {new_tab_url}")
                        
                        if "/Error" in new_tab_url:
                            Logger.log(f"✗ Error detected on new tab: {new_tab_url}", "ERROR")
                            return False, new_tab_url
                        
                        try:
                            if previous_page and previous_page != new_tab_page:
                                previous_page.close()
                        except Exception:
                            pass
                        
                        return True, new_tab_url
            
            Logger.log("✗ Timeout waiting for login completion", "ERROR")
            
            # Check final URL - if it's a valid authenticated page, login actually succeeded
            try:
                final_url = self.page.url
                valid_authenticated_paths = ["/UserArea", "/Home", "/Dashboard", "/Account", "/Services"]
                is_valid_page = any(path in final_url for path in valid_authenticated_paths)
                
                if is_valid_page and "/Error" not in final_url and "/Home/Login" not in final_url:
                    Logger.log(f"✓ Login actually succeeded! URL is valid authenticated page: {final_url}")
                    Logger.log("⚠ Timeout occurred but we're on a valid page - continuing...")
                    return True, final_url
            except:
                final_url = None
            
            # Check for "Unavailable" error before returning timeout
            try:
                if self.check_for_unavailable_error():
                    Logger.log("✗ 'Unavailable' error detected - this may be why login timed out", "ERROR")
            except:
                pass
            
            # Save HTML snapshot if not "Unavailable" or error page
            self.send_debug_html_snapshot("Login completion timeout")
            return False, final_url
            
        finally:
            try:
                for listener_page in response_listener_pages:
                    listener_page.remove_listener("response", handle_response)
            except:
                pass
            try:
                if self.context:
                    self.context.remove_listener("page", handle_new_page)
            except:
                pass
    
    def check_for_errors(self) -> Optional[str]:
        """Check for error messages on the page."""
        try:
            # Check URL for error page
            if "/Error" in self.page.url:
                return f"Error page: {self.page.url}"
            
            # Check for error elements
            error_selectors = [
                '.text-danger',
                '.error',
                '[role="alert"]',
                '.validation-summary-errors',
                '.field-validation-error',
                '.alert-danger'
            ]
            
            for selector in error_selectors:
                elements = self.page.locator(selector)
                if elements.count() > 0:
                    first_error = elements.first
                    if first_error.is_visible():
                        error_text = first_error.text_content()
                        if error_text and len(error_text.strip()) > 0:
                            return error_text.strip()
            
            # Check page content
            page_content = self.page.content().lower()
            if "si è verificato un errore" in page_content:
                return "Server error detected on page"
            
            return None
        except:
            return None
    
    def check_for_unavailable_error(self) -> bool:
        """Check if the page shows 'Unavailable' error after login."""
        try:
            # Check page title
            page_title = self.page.title()
            if page_title and "Unavailable" in page_title:
                Logger.log("✗ Received 'Unavailable' error after login (detected in page title)", "ERROR")
                return True
            
            # Check page body content
            body_text = self.page.locator("body").inner_text()
            if body_text and "Unavailable" in body_text.strip():
                Logger.log("✗ Received 'Unavailable' error after login (detected in page body)", "ERROR")
                return True
            
            # Check page HTML content
            page_content = self.page.content()
            if page_content and "<title>Unavailable</title>" in page_content:
                Logger.log("✗ Received 'Unavailable' error after login (detected in HTML)", "ERROR")
                return True
            
            return False
        except Exception as e:
            Logger.log(f"⚠ Error checking for 'Unavailable' error: {e}", "WARN")
            return False
    
    def send_debug_html_snapshot(self, reason: str) -> None:
        """Capture current HTML and save it to file for debugging."""
        try:
            # Check if page is "Unavailable" or error page - skip saving in those cases
            if self.check_for_unavailable_error():
                Logger.log(f"⚠ Debug snapshot skipped - page shows 'Unavailable' error", "WARN")
                return
            
            current_url = self.page.url
            if "/Error" in current_url:
                Logger.log(f"⚠ Debug snapshot skipped - page is error page: {current_url}", "WARN")
                return
            
            # Save HTML to file
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            safe_reason = reason.replace(" ", "_").replace("/", "_")[:50]
            filename = f"italy_debug_{safe_reason}_{timestamp}.html"
            
            # Ensure screenshots directory exists
            screenshots_dir = "screenshots"
            os.makedirs(screenshots_dir, exist_ok=True)
            filepath = os.path.join(screenshots_dir, filename)
            
            # Get page HTML
            html_content = self.page.content()
            
            # Save to file
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(html_content)
            
            Logger.log(f"✓ Debug HTML snapshot saved: {filepath} (reason: {reason})")
            Logger.log(f"  URL: {current_url}")
        except Exception as e:
            Logger.log(f"⚠ Failed to save debug HTML snapshot: {e}", "WARN")
    
    def navigate_to_services_tab(self) -> bool:
        """Navigate to the 'Rezerviši' (/Services) tab after login."""
        Logger.log("Navigating to 'Rezerviši' tab (/Services)...")
        
        # Check for "Unavailable" error before trying to find services tab
        if self.check_for_unavailable_error():
            Logger.log("✗ Cannot navigate to services tab - 'Unavailable' error detected", "ERROR")
            return False
        
        try:
            nav_locator = self.page.locator(SERVICES_TAB_SELECTOR)
            nav_locator.wait_for(state="visible", timeout=ELEMENT_WAIT_TIMEOUT)
            Logger.log("✓ Services tab located")
        except PlaywrightTimeoutError:
            Logger.log("✗ Services tab not found on the page", "ERROR")
            # Check if page shows "Unavailable" error
            if self.check_for_unavailable_error():
                Logger.log("✗ Services tab not found because page shows 'Unavailable' error", "ERROR")
            self.send_debug_html_snapshot("Services tab not found (timeout)")
            return False
        except Exception as e:
            Logger.log(f"✗ Unexpected error locating Services tab: {e}", "ERROR")
            # Check if page shows "Unavailable" error
            if self.check_for_unavailable_error():
                Logger.log("✗ Error locating services tab - page shows 'Unavailable' error", "ERROR")
            self.send_debug_html_snapshot(f"Services tab error: {e}")
            return False
        
        try:
            HumanBehavior.random_delay(600, 1200)
            
            if self.mouse:
                self.mouse.move_to_element(nav_locator)
            else:
                nav_locator.hover()
                HumanBehavior.random_delay(300, 700)
            
            nav_locator.click()
            Logger.log("✓ Clicked Services tab, waiting for navigation...")
        except Exception as e:
            Logger.log(f"✗ Failed to click Services tab: {e}", "ERROR")
            return False
        
        try:
            self.page.wait_for_url("**/Services*", timeout=PAGE_LOAD_TIMEOUT)
            Logger.log(f"✓ Navigation confirmed: {self.page.url}")
            HumanBehavior.simulate_reading(self.page)
            return True
        except PlaywrightTimeoutError:
            Logger.log("⚠ Navigation to /Services not confirmed within timeout", "WARN")
        except Exception as e:
            Logger.log(f"⚠ Error while waiting for /Services navigation: {e}", "WARN")
        
        current_url = self.page.url
        if "/Services" in current_url:
            Logger.log(f"✓ Already on Services page: {current_url}")
            HumanBehavior.simulate_reading(self.page)
            return True
        
        Logger.log(f"✗ Still not on Services tab (current URL: {current_url})", "ERROR")
        self.send_debug_html_snapshot("Failed to reach /Services after click")
        return False
    
    def check_booking_slots(self) -> bool:
        """Click through targeted booking buttons and look for slot availability."""
        if not BOOKING_TARGET_URLS:
            Logger.log("ℹ No booking targets configured; skipping slot check.")
            return False
        
        Logger.log(f"Checking {len(BOOKING_TARGET_URLS)} booking targets for available slots...")
        for href in BOOKING_TARGET_URLS:
            if self.try_booking_button(href):
                return True
        
        Logger.log("✗ No slots detected for monitored services.")
        return False
    
    def try_booking_button(self, href: str) -> bool:
        """Click a specific booking button and determine if slots are available."""
        Logger.log(f"→ Inspecting booking option: {href}")
        button_selector = f"a[href='{href}'] button.button.primary"
        button_locator = self.page.locator(button_selector)
        
        try:
            button_locator.wait_for(state="visible", timeout=ELEMENT_WAIT_TIMEOUT)
        except PlaywrightTimeoutError:
            Logger.log(f"✗ Booking button not found for {href}", "ERROR")
            return False
        except Exception as e:
            Logger.log(f"✗ Error locating booking button {href}: {e}", "ERROR")
            return False
        
        try:
            HumanBehavior.random_delay(700, 1400)
            
            if self.mouse:
                self.mouse.move_to_element(button_locator)
            else:
                button_locator.hover()
                HumanBehavior.random_delay(300, 600)
            
            button_locator.click()
            Logger.log(f"✓ Clicked booking button for {href}")
        except Exception as e:
            Logger.log(f"✗ Failed to click booking button {href}: {e}", "ERROR")
            return False
        
        Logger.log("⏳ Waiting 5 seconds for modal response...")
        time.sleep(5)
        
        if self.wait_for_no_slot_modal():
            Logger.log(f"✗ No slots available for {href}", "INFO")
            return False
        
        Logger.log(f"✓ No 'fully booked' modal detected for {href} – slots may be available!")
        self.notify_slots_found(href)
        return True
    
    def wait_for_no_slot_modal(self, timeout_ms: int = 6000) -> bool:
        """
        Wait for the known 'no slots' modal to appear.
        Returns True if the modal was shown (meaning no slots), False otherwise.
        """
        modal_locator = self.page.locator(".jconfirm-box").first
        try:
            modal_locator.wait_for(state="visible", timeout=timeout_ms)
        except PlaywrightTimeoutError:
            return False
        except Exception as e:
            Logger.log(f"⚠ Error while waiting for modal: {e}", "WARN")
            return False
        
        try:
            modal_text = modal_locator.inner_text().strip()
        except Exception:
            modal_text = ""
        
        lower_text = modal_text.lower()
        matched_message = None
        for message in NO_SLOT_MESSAGES:
            if message.lower() in lower_text:
                matched_message = message
                break
        
        if matched_message:
            Logger.log("ℹ No-slot modal detected: " + matched_message, "INFO")
        else:
            Logger.log(f"⚠ Modal detected with unexpected text: {modal_text}", "WARN")
        
        self.dismiss_modal(modal_locator)
        return True
    
    def dismiss_modal(self, modal_locator) -> None:
        """Attempt to close the currently visible modal."""
        try:
            ok_button = modal_locator.locator(".jconfirm-buttons button")
            if ok_button.count() > 0:
                ok_button.first.click()
                HumanBehavior.random_delay(400, 800)
        except Exception as e:
            Logger.log(f"⚠ Unable to close modal cleanly: {e}", "WARN")
    
    def notify_slots_found(self, href: str) -> None:
        """Send a Telegram notification when slots are found."""
        if self.slots_notified:
            Logger.log("ℹ Slots already reported earlier in this run; skipping duplicate notification.")
            return
        
        service_id = href.split("/")[-1] if "/" in href else href
        message = (
            "✅ SLOTS FOUND IN ITALY!\n\n"
            f"Service ID: {service_id}\n"
            f"Portal: {APPOINTMENT_PORTAL_URL}"
        )
        
        if send_telegram_message(message):
            self.slots_notified = True
            Logger.log("✓ Telegram notification sent for Italy slots.")
        else:
            Logger.log("⚠ Failed to send Telegram notification.", "WARN")
    
    def get_session_data(self) -> Dict[str, Any]:
        """Extract session data from browser context."""
        try:
            cookies = self.context.cookies()
            
            storage_data = self.page.evaluate("""
                        () => {
                    return {
                        localStorage: {...localStorage},
                        sessionStorage: {...sessionStorage}
                    };
                        }
                    """)
            
            return {
                'cookies': cookies,
                'localStorage': storage_data.get('localStorage', {}),
                'sessionStorage': storage_data.get('sessionStorage', {}),
                'url': self.page.url
            }
        except Exception as e:
            Logger.log(f"⚠ Error extracting session data: {e}", "WARN")
            return {
                'cookies': self.context.cookies(),
                'localStorage': {},
                'sessionStorage': {},
                'url': self.page.url if self.page else None
            }
    
    def cleanup(self) -> None:
        """Clean up browser and resources."""
        try:
            if self.context:
                self.context.close()
            Logger.log("✓ Context closed")
        except:
            pass
        
        try:
            if self.browser:
                self.browser.close()
            Logger.log("✓ Browser connection closed")
        except:
            pass
        
        try:
            if hasattr(self, 'playwright_instance') and self.playwright_instance:
                self.playwright_instance.stop()
        except:
            pass
        
        # Kill Chrome process
        try:
            if self.chrome_process:
                if hasattr(os, 'setsid'):
                    # Kill the process group
                    os.killpg(os.getpgid(self.chrome_process.pid), signal.SIGTERM)
                else:
                    # Windows
                    self.chrome_process.terminate()
                self.chrome_process.wait(timeout=5)
                Logger.log("✓ Chrome process terminated")
        except subprocess.TimeoutExpired:
            try:
                if hasattr(os, 'setsid'):
                    os.killpg(os.getpgid(self.chrome_process.pid), signal.SIGKILL)
                else:
                    self.chrome_process.kill()
                Logger.log("✓ Chrome process force killed")
            except:
                pass
        
        # Clean up user data directory
        try:
            if self.user_data_dir and os.path.exists(self.user_data_dir):
                import shutil
                shutil.rmtree(self.user_data_dir)
                Logger.log("✓ Chrome user data directory cleaned up")
        except:
            pass
        
        # Stop Xvfb if it was started
        try:
            if self.xvfb_process and self.xvfb_process.poll() is None:
                self.xvfb_process.terminate()
                self.xvfb_process.wait(timeout=2)
                Logger.log("✓ Xvfb virtual display stopped")
        except:
            try:
                if self.xvfb_process:
                    self.xvfb_process.kill()
            except:
                pass
    
    def wait_for_user_to_finish(self) -> None:
        """
        Keep the browser open until the operator confirms they're done inspecting.
        Falls back to a short sleep if stdin isn't interactive or in headless mode.
        """
        if not self.browser or not self.page:
            return
        
        # Skip interactive wait in headless mode (Docker/server environments)
        if HEADLESS_MODE:
            Logger.log("Headless mode: skipping interactive wait, closing browser immediately")
            return
        
        prompt = "\nPress ENTER when you are finished inspecting the browser..."
        Logger.log("Browser will remain open for inspection until you press ENTER.")
        
        try:
            input(prompt)
        except EOFError:
            Logger.log("Console input unavailable; waiting 10 seconds before closing.", "WARN")
            time.sleep(10)
    
    def run(self) -> Optional[Dict[str, Any]]:
        """Run the complete login flow."""
        Logger.log("=" * 70)
        Logger.log("Starting Anti-Detection Login Bot")
        Logger.log("=" * 70)
        
        # Validate credentials
        if not EMAIL or not PASSWORD:
            Logger.log("✗ Error: LOGIN_EMAIL/ITALY_EMAIL and LOGIN_PASSWORD/ITALY_PASSWORD must be set in .env", "ERROR")
            return None
        
        Logger.log(f"Using email: {EMAIL}")
        Logger.log(f"Login URL: {LOGIN_URL}")
        
        try:
            self.setup_browser()
            self.navigate_to_login()
            
            if not self.wait_for_recaptcha_scripts():
                Logger.log("⚠ reCAPTCHA scripts may not be loaded, continuing anyway...", "WARN")
            
            # Allow page to settle before interacting
            HumanBehavior.random_delay(1000, 2000)
            
            self.fill_login_form()
            
            # Wait before triggering captcha (important for behavioral analysis)
            HumanBehavior.random_delay(1500, 3000)
            
            self.trigger_captcha()
            
            if not self.wait_for_captcha_completion():
                raise CaptchaError("reCAPTCHA did not complete within timeout")
            
            Logger.log("✓ reCAPTCHA completed")
            
            success, final_url = self.wait_for_login_completion()
            
            if not success:
                reason = f"Login completion failed (final URL: {final_url})"
                self.send_debug_html_snapshot(reason)
                raise LoginError(f"Login did not complete successfully. Final URL: {final_url}")
            
            Logger.log("✓ Login successful!")
            
            # Check for "Unavailable" error after login
            if self.check_for_unavailable_error():
                Logger.log("⚠ Login completed but 'Unavailable' error detected on page", "WARN")
            
            slots_found = False
            if self.navigate_to_services_tab():
                slots_found = self.check_booking_slots()
                if slots_found:
                    Logger.log("✓ Slot availability detected and notification dispatched.")
                else:
                    Logger.log("ℹ No slots detected during this run.")
            else:
                Logger.log("⚠ Unable to automatically open /Services tab. Skipping slot check.", "WARN")
            
            # Extract session data
            Logger.log("Extracting session data...")
            session_data = self.get_session_data()
            Logger.log(f"✓ Extracted {len(session_data.get('cookies', []))} cookies")
            Logger.log(f"✓ Final URL: {session_data.get('url', 'unknown')}")
            
            return session_data
            
        except CaptchaError as e:
            Logger.log(f"✗ Captcha Error: {e}", "ERROR")
            return None
        except LoginError as e:
            Logger.log(f"✗ Login Error: {e}", "ERROR")
            return None
        except Exception as e:
            Logger.log(f"✗ Unexpected error: {e}", "ERROR")
            import traceback
            traceback.print_exc()
            return None
        finally:
            self.wait_for_user_to_finish()
            self.cleanup()
        
        Logger.log("=" * 70)
        Logger.log("Finished")
        Logger.log("=" * 70)
        return None


def fill_italy_login_form() -> Optional[Dict[str, Any]]:
    """
    Main entry point for Italy login form filling.
    
    Returns:
        Dictionary with session data if login successful, None otherwise
    """
    bot = ItalyLoginBot()
    return bot.run()


if __name__ == "__main__":
    result = fill_italy_login_form()
    if result:
        Logger.log("\n✓ Login successful!")
        Logger.log(f"  Cookies: {len(result.get('cookies', []))} items")
        Logger.log(f"  Final URL: {result.get('url', 'unknown')}")
        sys.exit(0)
    else:
        Logger.log("\n✗ Login failed")
        sys.exit(1)
