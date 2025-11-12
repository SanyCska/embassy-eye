"""
Cooldown management for captcha cases.
When captcha is detected, the script will skip the next 2 runs.
"""

import json
from datetime import datetime
from pathlib import Path

COOLDOWN_FILE = Path("captcha_cooldown.json")
SKIP_RUNS_REQUIRED = 2


def check_and_handle_cooldown():
    """
    Check if we're in cooldown period and handle skip logic.
    
    Returns:
        tuple: (should_skip: bool, message: str)
    """
    if not COOLDOWN_FILE.exists():
        return (False, None)
    
    try:
        with COOLDOWN_FILE.open("r", encoding="utf-8") as f:
            data = json.load(f)
        
        detected_at = data.get("detected_at")
        skipped_runs = data.get("skipped_runs", 0)
        
        if skipped_runs >= SKIP_RUNS_REQUIRED:
            # Cooldown period is over, clear the file
            COOLDOWN_FILE.unlink()
            return (False, f"Cooldown period completed ({skipped_runs} runs skipped), resuming normal operation")
        
        # Increment skip count
        skipped_runs += 1
        data["skipped_runs"] = skipped_runs
        
        with COOLDOWN_FILE.open("w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        
        remaining = SKIP_RUNS_REQUIRED - skipped_runs
        message = (
            f"Skipping run due to captcha cooldown (detected at {detected_at}). "
            f"Run {skipped_runs}/{SKIP_RUNS_REQUIRED} skipped. "
            f"{remaining} run(s) remaining."
        )
        return (True, message)
        
    except Exception as e:
        # If there's an error reading the file, clear it and continue
        if COOLDOWN_FILE.exists():
            COOLDOWN_FILE.unlink()
        return (False, f"Error reading cooldown file, cleared and continuing: {e}")


def save_captcha_cooldown():
    """
    Save captcha detection to cooldown file.
    This will trigger skipping the next 2 runs.
    """
    try:
        data = {
            "detected_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "skipped_runs": 0
        }
        
        COOLDOWN_FILE.parent.mkdir(parents=True, exist_ok=True)
        with COOLDOWN_FILE.open("w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        
        print(f"  Captcha cooldown saved to {COOLDOWN_FILE}")
        print(f"  Next {SKIP_RUNS_REQUIRED} runs will be skipped")
        
    except Exception as e:
        print(f"  Warning: Failed to save captcha cooldown: {e}")

