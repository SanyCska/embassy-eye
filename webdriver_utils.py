"""
WebDriver setup and utility functions.
"""

import sys
import os
import random
import json
import time

# Disable PyCharm debugger tracing to avoid warnings
if 'pydevd' in sys.modules:
    os.environ['PYTHONDONTWRITEBYTECODE'] = '1'

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException

try:
    import undetected_chromedriver as uc
    UC_AVAILABLE = True
except ImportError:
    UC_AVAILABLE = False

from config import BOOKING_URL, PAGE_LOAD_WAIT


# Large pool of realistic, up-to-date user agents (2024-2025)
USER_AGENTS = [
    # Chrome on Windows
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Windows NT 11.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36',
    
    # Chrome on macOS
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 13_6_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 14_7_1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36',
    
    # Chrome on Linux
    'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
    'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36',
    'Mozilla/5.0 (X11; Ubuntu; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
    
    # Edge on Windows
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36 Edg/131.0.0.0',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36 Edg/130.0.0.0',
    'Mozilla/5.0 (Windows NT 11.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36 Edg/131.0.0.0',
    
    # Edge on macOS
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36 Edg/131.0.0.0',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 13_6_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36 Edg/131.0.0.0',
    
    # Firefox on Windows
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:133.0) Gecko/20100101 Firefox/133.0',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:132.0) Gecko/20100101 Firefox/132.0',
    'Mozilla/5.0 (Windows NT 11.0; Win64; x64; rv:133.0) Gecko/20100101 Firefox/133.0',
    
    # Firefox on macOS
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:133.0) Gecko/20100101 Firefox/133.0',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:132.0) Gecko/20100101 Firefox/132.0',
    
    # Safari on macOS
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.1 Safari/605.1.15',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.6 Safari/605.1.15',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 13_6_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.1 Safari/605.1.15',
]

# Common screen resolutions
SCREEN_RESOLUTIONS = [
    (1920, 1080), (1366, 768), (1536, 864), (1440, 900), (1280, 720),
    (1600, 900), (2560, 1440), (1920, 1200), (1680, 1050), (1280, 1024),
    (2560, 1600), (3840, 2160), (2048, 1152), (1920, 1080), (1360, 768),
]

# Common timezones
TIMEZONES = [
    'America/New_York', 'America/Los_Angeles', 'America/Chicago', 'America/Denver',
    'Europe/London', 'Europe/Paris', 'Europe/Berlin', 'Europe/Rome', 'Europe/Madrid',
    'Europe/Amsterdam', 'Europe/Vienna', 'Europe/Budapest', 'Europe/Prague',
    'Asia/Tokyo', 'Asia/Shanghai', 'Asia/Hong_Kong', 'Asia/Singapore',
    'Australia/Sydney', 'Australia/Melbourne',
]

# Common languages
LANGUAGES = [
    ['en-US', 'en'], ['en-GB', 'en'], ['de-DE', 'de', 'en'], ['fr-FR', 'fr', 'en'],
    ['es-ES', 'es', 'en'], ['it-IT', 'it', 'en'], ['pt-BR', 'pt', 'en'],
    ['nl-NL', 'nl', 'en'], ['pl-PL', 'pl', 'en'], ['ru-RU', 'ru', 'en'],
    ['ja-JP', 'ja', 'en'], ['zh-CN', 'zh', 'en'], ['ko-KR', 'ko', 'en'],
]


def get_random_device_profile():
    """Generate a random device profile for fingerprinting."""
    user_agent = random.choice(USER_AGENTS)
    width, height = random.choice(SCREEN_RESOLUTIONS)
    timezone = random.choice(TIMEZONES)
    languages = random.choice(LANGUAGES)
    
    # Determine platform from user agent
    if 'Windows' in user_agent:
        platform = 'Win32'
        platform_version = random.choice(['10.0', '11.0'])
    elif 'Macintosh' in user_agent:
        platform = 'MacIntel'
        platform_version = random.choice(['10.15.7', '13.6.7', '14.7.1'])
    else:
        platform = 'Linux x86_64'
        platform_version = '5.15.0'
    
    # Hardware concurrency (CPU cores) - typically 4, 8, 12, 16
    hardware_concurrency = random.choice([4, 8, 8, 12, 16, 16])  # Weighted towards common values
    
    # Device memory in GB (converted to bytes)
    device_memory = random.choice([4, 8, 8, 16, 16, 32])  # Weighted towards common values
    
    # Color depth
    color_depth = random.choice([24, 24, 24, 30, 32])  # Mostly 24-bit
    
    # Pixel ratio
    pixel_ratio = random.choice([1.0, 1.0, 1.25, 1.5, 2.0])  # Weighted towards 1.0
    
    return {
        'user_agent': user_agent,
        'width': width,
        'height': height,
        'timezone': timezone,
        'languages': languages,
        'platform': platform,
        'platform_version': platform_version,
        'hardware_concurrency': hardware_concurrency,
        'device_memory': device_memory,
        'color_depth': color_depth,
        'pixel_ratio': pixel_ratio,
    }


def create_driver(headless=False):
    """Create and configure a Chrome WebDriver instance with anti-detection measures.
    
    Each run uses a randomly generated device profile to avoid fingerprinting.
    """
    # Generate a random device profile for this session
    profile = get_random_device_profile()
    
    if UC_AVAILABLE:
        # Try undetected-chromedriver first, fall back to regular selenium on error
        try:
            # Use undetected-chromedriver for better anti-detection
            options = uc.ChromeOptions()
            if headless:
                options.add_argument('--headless=new')  # Use new headless mode
                options.add_argument('--no-sandbox')
                options.add_argument('--disable-dev-shm-usage')
            
            # Additional stealth options
            options.add_argument('--disable-blink-features=AutomationControlled')
            options.add_argument('--disable-features=IsolateOrigins,site-per-process')
            options.add_argument('--disable-site-isolation-trials')
            options.add_argument('--disable-web-security')
            options.add_argument('--disable-features=VizDisplayCompositor')
            
            # Use random user agent from profile
            options.add_argument(f'user-agent={profile["user_agent"]}')
            
            # Use random window size from profile
            options.add_argument(f'--window-size={profile["width"]},{profile["height"]}')
            
            # Create driver with undetected_chromedriver (let it auto-detect version)
            driver = uc.Chrome(options=options, use_subprocess=True)
            
            # Apply comprehensive fingerprinting protection via CDP
            _apply_fingerprint_protection(driver, profile)
            
            return driver
        except Exception as e:
            print(f"Warning: undetected-chromedriver failed ({e}), falling back to regular selenium with stealth")
            # Fall through to regular selenium implementation
    
    # Fallback to regular selenium with manual anti-detection (used if UC not available or fails)
    options = webdriver.ChromeOptions()
    
    # Anti-detection arguments
    options.add_argument('--disable-blink-features=AutomationControlled')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-features=IsolateOrigins,site-per-process')
    options.add_argument('--disable-site-isolation-trials')
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option('useAutomationExtension', False)
    
    # Use random user agent from profile
    options.add_argument(f'user-agent={profile["user_agent"]}')
    
    if headless:
        options.add_argument('--headless=new')
    
    # Use random window size from profile
    options.add_argument(f'--window-size={profile["width"]},{profile["height"]}')
    
    driver = webdriver.Chrome(options=options)
    
    # Apply comprehensive fingerprinting protection via CDP
    _apply_fingerprint_protection(driver, profile)
    
    return driver


def _apply_fingerprint_protection(driver, profile):
    """Apply comprehensive fingerprinting protection via Chrome DevTools Protocol."""
    # Format languages array for JavaScript
    languages_js = json.dumps(profile["languages"])
    
    # Enhanced stealth script with device profile
    stealth_script = f'''
        // Remove webdriver property
        Object.defineProperty(navigator, 'webdriver', {{
            get: () => undefined
        }});
        
        // Spoof plugins
        Object.defineProperty(navigator, 'plugins', {{
            get: () => {{
                const plugins = [
                    {{ name: 'Chrome PDF Plugin', filename: 'internal-pdf-viewer', description: 'Portable Document Format' }},
                    {{ name: 'Chrome PDF Viewer', filename: 'mhjfbmdgcfjbbpaeojofohoefgiehjai', description: '' }},
                    {{ name: 'Native Client', filename: 'internal-nacl-plugin', description: '' }}
                ];
                return plugins;
            }}
        }});
        
        // Spoof languages from profile
        Object.defineProperty(navigator, 'languages', {{
            get: () => {languages_js}
        }});
        
        // Spoof platform
        Object.defineProperty(navigator, 'platform', {{
            get: () => '{profile["platform"]}'
        }});
        
        // Add chrome object
        window.chrome = {{
            runtime: {{}},
            loadTimes: function() {{}},
            csi: function() {{}},
            app: {{}}
        }};
        
        // Spoof permissions
        Object.defineProperty(navigator, 'permissions', {{
            get: () => ({{
                query: () => Promise.resolve({{ state: 'granted' }})
            }})
        }});
        
        // Spoof hardware concurrency
        Object.defineProperty(navigator, 'hardwareConcurrency', {{
            get: () => {profile["hardware_concurrency"]}
        }});
        
        // Spoof device memory
        Object.defineProperty(navigator, 'deviceMemory', {{
            get: () => {profile["device_memory"]}
        }});
        
        // Spoof max touch points
        Object.defineProperty(navigator, 'maxTouchPoints', {{
            get: () => 0
        }});
        
        // Override screen properties
        Object.defineProperty(screen, 'width', {{
            get: () => {profile["width"]}
        }});
        Object.defineProperty(screen, 'height', {{
            get: () => {profile["height"]}
        }});
        Object.defineProperty(screen, 'availWidth', {{
            get: () => {profile["width"]}
        }});
        Object.defineProperty(screen, 'availHeight', {{
            get: () => {profile["height"] - 40}
        }});
        Object.defineProperty(screen, 'colorDepth', {{
            get: () => {profile["color_depth"]}
        }});
        Object.defineProperty(screen, 'pixelDepth', {{
            get: () => {profile["color_depth"]}
        }});
        
        // Override device pixel ratio
        Object.defineProperty(window, 'devicePixelRatio', {{
            get: () => {profile["pixel_ratio"]}
        }});
        
        // Canvas fingerprinting protection - add noise to canvas
        const originalToDataURL = HTMLCanvasElement.prototype.toDataURL;
        HTMLCanvasElement.prototype.toDataURL = function() {{
            const context = this.getContext('2d');
            if (context) {{
                const imageData = context.getImageData(0, 0, this.width, this.height);
                for (let i = 0; i < imageData.data.length; i += 4) {{
                    imageData.data[i] += Math.random() < 0.1 ? Math.floor(Math.random() * 2) - 1 : 0;
                }}
                context.putImageData(imageData, 0, 0);
            }}
            return originalToDataURL.apply(this, arguments);
        }};
        
        // WebGL fingerprinting protection
        const getParameter = WebGLRenderingContext.prototype.getParameter;
        WebGLRenderingContext.prototype.getParameter = function(parameter) {{
            if (parameter === 37445) {{
                return 'Intel Inc.';
            }}
            if (parameter === 37446) {{
                return 'Intel Iris OpenGL Engine';
            }}
            return getParameter.apply(this, arguments);
        }};
        
        // Audio context fingerprinting protection
        if (window.AudioContext || window.webkitAudioContext) {{
            const AudioContext = window.AudioContext || window.webkitAudioContext;
            const originalCreateAnalyser = AudioContext.prototype.createAnalyser;
            AudioContext.prototype.createAnalyser = function() {{
                const analyser = originalCreateAnalyser.apply(this, arguments);
                const originalGetFloatFrequencyData = analyser.getFloatFrequencyData;
                analyser.getFloatFrequencyData = function(array) {{
                    originalGetFloatFrequencyData.apply(this, arguments);
                    for (let i = 0; i < array.length; i++) {{
                        array[i] += Math.random() * 0.0001;
                    }}
                }};
                return analyser;
            }};
        }}
        
        // Override timezone
        const originalGetTimezoneOffset = Date.prototype.getTimezoneOffset;
        Date.prototype.getTimezoneOffset = function() {{
            // Return a random offset within reasonable range (-12 to +14 hours)
            return Math.floor(Math.random() * 26) - 12;
        }};
    '''
    
    driver.execute_cdp_cmd('Page.addScriptToEvaluateOnNewDocument', {
        'source': stealth_script
    })
    
    # Set timezone via CDP
    try:
        driver.execute_cdp_cmd('Emulation.setTimezoneOverride', {
            'timezoneId': profile['timezone']
        })
    except Exception:
        # Some CDP versions may not support this, ignore
        pass
    
    # Set geolocation to a random location (optional, can be disabled if not needed)
    try:
        # Random location within reasonable bounds
        driver.execute_cdp_cmd('Emulation.setGeolocationOverride', {
            'latitude': random.uniform(40.0, 50.0),
            'longitude': random.uniform(-5.0, 20.0),
            'accuracy': 100
        })
    except Exception:
        # Some CDP versions may not support this, ignore
        pass


def navigate_to_booking_page(driver):
    """Navigate to the booking page and wait for form to load."""
    print("Opening https://konzinfobooking.mfa.gov.hu/...")
    
    # Add random delay before navigation to simulate human behavior
    time.sleep(random.uniform(1, 3))
    
    driver.get(BOOKING_URL)
    
    wait = WebDriverWait(driver, PAGE_LOAD_WAIT)
    print("Waiting for page to load...")
    
    try:
        wait.until(EC.presence_of_element_located((By.TAG_NAME, "form")))
        print("Form detected")
    except TimeoutException:
        print("Warning: Form not found, but continuing...")
    
    # Give page extra time to render with random delay
    time.sleep(random.uniform(2, 4))
    return wait


def inspect_form_fields(driver):
    """Inspect and print all form fields."""
    print("\n=== Inspecting Form Fields ===")
    
    inputs = driver.find_elements(By.TAG_NAME, "input")
    selects = driver.find_elements(By.TAG_NAME, "select")
    textareas = driver.find_elements(By.TAG_NAME, "textarea")
    
    print(f"Found {len(inputs)} input fields, {len(selects)} select fields, {len(textareas)} textarea fields\n")
    
    # Debug: Print all input fields
    print("All input fields:")
    for i, inp in enumerate(inputs):
        input_type = inp.get_attribute("type") or "text"
        input_id = inp.get_attribute("id")
        input_name = inp.get_attribute("name")
        input_placeholder = inp.get_attribute("placeholder")
        print(f"  [{i}] type='{input_type}', id='{input_id}', name='{input_name}', placeholder='{input_placeholder}'")
    
    return inputs, selects, textareas


def scroll_to_element(driver, element):
    """Scroll an element into view with human-like behavior."""
    driver.execute_script("arguments[0].scrollIntoView({block: 'center', behavior: 'smooth'});", element)
    # Random delay to simulate human scrolling speed
    time.sleep(random.uniform(0.3, 0.7))


