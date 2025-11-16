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

# Load environment variables
load_dotenv()

# Configuration
LOGIN_URL = os.getenv("ITALY_LOGIN_URL", "https://prenotami.esteri.it/")
EMAIL = os.getenv("LOGIN_EMAIL") or os.getenv("ITALY_EMAIL", "")
PASSWORD = os.getenv("LOGIN_PASSWORD") or os.getenv("ITALY_PASSWORD", "")

# Proxy configuration (optional)
PROXY_SERVER = os.getenv("PROXY_SERVER", "")  # e.g., "http://proxy.example.com:8080"
PROXY_USERNAME = os.getenv("PROXY_USERNAME", "")
PROXY_PASSWORD = os.getenv("PROXY_PASSWORD", "")

# Selectors
EMAIL_SELECTOR = "#login-email"
PASSWORD_SELECTOR = "#login-password"
CAPTCHA_TRIGGER_SELECTOR = "#captcha-trigger"
LOGIN_FORM_SELECTOR = "#login-form"

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
        self.user_data_dir = None
    
    def setup_browser(self) -> None:
        """Setup browser by launching real Google Chrome and connecting via CDP."""
        Logger.log("Setting up real Google Chrome with CDP connection...")
        
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
        max_retries = 10
        for i in range(max_retries):
            try:
                with urllib.request.urlopen("http://localhost:9222/json/version", timeout=1) as response:
                    if response.status == 200:
                        Logger.log("✓ Chrome CDP is ready")
                        break
            except:
                if i < max_retries - 1:
                    time.sleep(1)
                else:
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
            
            # Check for redirect to dashboard/home
            if "/Error" not in url and initial_url != url:
                if "/Home" in url or "/Dashboard" in url or "/Account" in url:
                    login_success = True
        
        self.page.on("response", handle_response)
        
        try:
            while (time.time() - start_time) * 1000 < LOGIN_COMPLETE_TIMEOUT:
                try:
                    current_url = self.page.url
                except:
                    # Navigation might have occurred
                    Logger.log("✓ Page navigated - login likely succeeded")
                    return True, None
                
                # Check for error page
                if "/Error" in current_url:
                    Logger.log(f"✗ Error page detected: {current_url}", "ERROR")
                    return False, current_url
                
                # Check if we've navigated away from login page
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
                    try:
                        final_url = self.page.url
                        if "/Error" not in final_url:
                            Logger.log(f"✓ Login successful! Final URL: {final_url}")
                            return True, final_url
                    except:
                        # Navigation occurred
                        return True, None
                
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
            
            Logger.log("✗ Timeout waiting for login completion", "ERROR")
            try:
                return False, self.page.url
            except:
                return False, None
            
        finally:
            try:
                self.page.remove_listener("response", handle_response)
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
                raise LoginError(f"Login did not complete successfully. Final URL: {final_url}")
            
            Logger.log("✓ Login successful!")
            
            # Extract session data
            Logger.log("Extracting session data...")
            session_data = self.get_session_data()
            Logger.log(f"✓ Extracted {len(session_data.get('cookies', []))} cookies")
            Logger.log(f"✓ Final URL: {session_data.get('url', 'unknown')}")
            
            # Keep browser open for inspection
            Logger.log("\nBrowser will remain open for 10 seconds for inspection...")
            time.sleep(10)
            
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
