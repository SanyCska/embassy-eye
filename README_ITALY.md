# Italy Embassy Appointment Scraper

Automated appointment monitoring system for the Italian Embassy appointment booking system (prenotami.esteri.it). This script automatically logs in, navigates to the services page, and checks for available appointment slots.

## Features

- 🔐 **Automated Login**: Handles reCAPTCHA Enterprise login automatically
- 🔍 **Slot Monitoring**: Checks multiple booking services for available slots
- 📱 **Telegram Notifications**: Sends instant notifications when slots are found
- 🔄 **Credential Rotation**: Cycles through multiple Italy user accounts automatically
- 🎭 **Anti-Detection**: Uses real Google Chrome via CDP (Chrome DevTools Protocol) for natural browser fingerprint
- 🐳 **Docker Support**: Easy deployment with Docker and Docker Compose
- ⏰ **Scheduled Execution**: Can run automatically on a schedule
- 🔒 **VPN Integration**: Supports proxy configuration for secure connections

## Requirements

- Python 3.11+ (if running without Docker)
- Docker and Docker Compose (recommended)
- Google Chrome installed (for CDP connection)
- Telegram Bot Token and User ID (for notifications)
- Italy Embassy login credentials

## Installation

### Option 1: Using Docker (Recommended)

1. **Clone the repository:**
   ```bash
   git clone <repository-url>
   cd embassy-eye
   ```

2. **Set up environment variables:**
   ```bash
   cp env.example .env
   # Edit .env and add your credentials:
   # - TELEGRAM_BOT_TOKEN
   # - TELEGRAM_USER_ID
   # - ITALY_EMAIL
   # - ITALY_PASSWORD
   ```

3. **Build and run:**
   ```bash
   docker-compose -f docker-compose.italy.yml build
   docker-compose -f docker-compose.italy.yml run --rm embassy-eye-italy
   ```

### Option 2: Using Python Directly

1. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   playwright install chromium
   ```

2. **Set up environment variables:**
   ```bash
   cp env.example .env
   # Edit .env and add your credentials
   ```

3. **Run the script:**
   ```bash
   python -m embassy_eye.scrapers.italy.runner
   ```

## Configuration

### Environment Variables

Create a `.env` file in the project root with the following variables:

```env
# Telegram Bot Configuration
TELEGRAM_BOT_TOKEN=your_bot_token_here
TELEGRAM_USER_ID=your_user_id_here

# Italy Embassy Login Credentials
ITALY_EMAIL=your_email@example.com
ITALY_PASSWORD=your_password_here

# Optional: Rotate across multiple accounts (JSON or newline-separated text)
# JSON example:
# ITALY_USERS='[
#   {"email":"primary@example.com","password":"pass1","label":"Primary"},
#   {"email":"backup@example.com","password":"pass2","label":"Backup"}
# ]'
# Text example (use $'...' to keep newlines):
# ITALY_USERS=$'primary@example.com|pass1|Primary\nbackup@example.com|pass2|Backup'

# Optional: Load the rotation list from disk (same formats as above)
ITALY_USERS_FILE=/path/to/italy_users.txt

# Optional: Persist the round-robin pointer somewhere specific
ITALY_ROTATION_STATE_FILE=/app/state/italy_user_rotation.json

# Optional: Store the list of blocked credentials detected at runtime
ITALY_BLOCKED_USERS_FILE=/app/state/italy_blocked_accounts.json

# Optional: Custom login URL
ITALY_LOGIN_URL=https://prenotami.esteri.it/

# Optional: Proxy Configuration
PROXY_SERVER=http://proxy.example.com:8080
PROXY_USERNAME=proxy_user
PROXY_PASSWORD=proxy_pass
```

**Getting your Telegram credentials:**
- **Bot Token**: Create a bot using [@BotFather](https://t.me/BotFather) on Telegram
- **User ID**: Get your user ID from [@userinfobot](https://t.me/userinfobot) on Telegram

### Credential Rotation

- Define multiple accounts either via `ITALY_USERS` (JSON or newline-separated `email|password|label`) or by pointing `ITALY_USERS_FILE` to a file that contains the same content.
- On every run the scraper picks the next account in round-robin order and stores the pointer in `ITALY_ROTATION_STATE_FILE` (defaults to `italy_user_rotation.json` in the working directory).
- You can still override the rotation temporarily by setting `LOGIN_EMAIL` and `LOGIN_PASSWORD` for a one-off run.
- If the site shows the “Account bloccato / Account Blocked” page after login, the script automatically marks that account as blocked and writes it to `ITALY_BLOCKED_USERS_FILE` so future runs skip it.

### Booking Service IDs

The script checks multiple booking services by default. You can modify the `BOOKING_TARGET_URLS` list in `embassy_eye/scrapers/italy/runner.py`:

```python
BOOKING_TARGET_URLS = [
    "/Services/Booking/1151",
    "/Services/Booking/1258",
]
```

## Usage

### Manual Execution

**Using Docker:**
```bash
docker-compose -f docker-compose.italy.yml run --rm embassy-eye-italy
```

**Using Python:**
```bash
python -m embassy_eye.scrapers.italy.runner
```

### Scheduled Execution (Cron)

To run automatically every 10 minutes:

1. **Create a wrapper script** (`run_italy.sh`):
   ```bash
   #!/bin/bash
   cd /path/to/embassy-eye
   docker-compose -f docker-compose.italy.yml run --rm embassy-eye-italy
   ```

2. **Make it executable:**
   ```bash
   chmod +x run_italy.sh
   ```

3. **Edit crontab:**
   ```bash
   crontab -e
   ```

4. **Add the cron job:**
   ```cron
   */10 * * * * /full/path/to/embassy-eye/run_italy.sh >> /full/path/to/embassy-eye/cron_italy.log 2>&1
   ```

## How It Works

1. **Browser Setup**: Launches real Google Chrome with remote debugging enabled
2. **Login**: Navigates to the login page and fills credentials
3. **reCAPTCHA**: Waits for and handles reCAPTCHA Enterprise challenge
4. **Navigation**: After successful login, navigates to the Services tab
5. **Slot Checking**: 
   - Finds all "Rezerviši" booking buttons
   - Clicks each button one by one
   - Waits 5 seconds for modal response
   - Checks if "no slots" modal appears
6. **Notification**: If any button doesn't show the "no slots" modal, sends Telegram notification
7. **Inspection**: Browser stays open until you press ENTER (for debugging)

### Slot Detection Logic

The script considers slots available if:
- Clicking a booking button does **not** trigger the "no slots" modal
- The modal doesn't contain messages like:
  - "Sorry, all appointments for this service are currently booked..."
  - "Stante l'elevata richiesta i posti disponibili per il servizio scelto sono esauriti."

**Important**: The script only needs to find slots for **one** of the booking services (not all) to send a notification.

## Troubleshooting

### Common Issues

1. **Chrome not found**: Ensure Google Chrome is installed on the system
2. **CDP connection failed**: Check that Chrome can start with remote debugging (port 9222)
3. **Login fails**: Verify credentials in `.env` file
4. **reCAPTCHA timeout**: The script waits up to 90 seconds for reCAPTCHA completion
5. **Modal not detected**: The script waits 5 seconds after clicking - increase timeout if needed
6. **Telegram notifications not working**: Verify `.env` file has correct credentials

### Debugging

The script keeps the browser open after execution for inspection. Press ENTER in the console when done.

**View logs:**
```bash
# Docker logs
docker-compose -f docker-compose.italy.yml logs embassy-eye-italy

# Cron logs
tail -f cron_italy.log
```

### Browser Inspection

When running the script, the browser will remain open until you press ENTER. This allows you to:
- Inspect the page state
- Check for errors
- Verify slot availability manually
- Debug login issues

## Security Notes

- Keep your `.env` file secure and never commit it to version control
- Use proper file permissions: `chmod 600 .env`
- Consider running as a dedicated user instead of root
- VPN/proxy credentials should be properly secured

## Technical Details

### Chrome CDP Connection

The script uses Chrome DevTools Protocol (CDP) to connect to a real Google Chrome instance. This ensures:
- Natural browser fingerprint (not detected as automation)
- Full reCAPTCHA Enterprise support
- Real Client Hints (Sec-CH-UA* headers)
- Proper Trusted Types and CSP handling

### Anti-Detection Measures

- Uses real Chrome (not Chromium)
- Minimal stealth (only removes `navigator.webdriver`)
- Human-like mouse movements and typing
- Realistic delays and behavior simulation
- No fingerprint spoofing (allows reCAPTCHA to work properly)

## License

See [LICENSE](LICENSE) file for details.

## Disclaimer

This tool is for educational and personal use only. Use responsibly and in accordance with the terms of service of the booking system. The authors are not responsible for any misuse of this software.

