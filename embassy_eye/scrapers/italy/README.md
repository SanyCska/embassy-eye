# Italy Embassy Scraper

Automated appointment monitoring for Italian Embassy appointment booking system (prenotami.esteri.it).

## Features

- 🔐 **Automated Login**: Handles reCAPTCHA Enterprise login automatically
- 🔍 **Multi-Service Monitoring**: Checks multiple booking services for slots
- 🔄 **Account Rotation**: Cycles through multiple user accounts automatically
- 🎭 **Anti-Detection**: Uses real Google Chrome via CDP (Chrome DevTools Protocol)
- 📱 **Telegram Notifications**: Instant alerts when slots are found
- 💾 **Database Logging**: Records slot statistics

## How It Works

1. **Browser Setup**: Launches real Google Chrome with remote debugging (CDP)
2. **Login**: Navigates to login page and fills credentials
3. **reCAPTCHA**: Waits for and handles reCAPTCHA Enterprise challenge (manual solve required)
4. **Services Tab**: Navigates to Services tab after successful login
5. **Slot Checking**:
   - Finds all "Prenota" booking buttons
   - Clicks each button one by one
   - Waits 5 seconds for modal response
   - Checks if "no slots" modal appears
6. **Notification**: If any service doesn't show "no slots" modal, sends Telegram notification
7. **Account Management**: Tracks and rotates blocked accounts automatically

## Configuration

### Environment Variables

Edit `.env` file:

```bash
# Single account
ITALY_EMAIL=your_email@example.com
ITALY_PASSWORD=your_password

# Multiple accounts (JSON format)
ITALY_USERS='[
  {"email":"user1@example.com","password":"pass1","label":"Primary"},
  {"email":"user2@example.com","password":"pass2","label":"Backup"}
]'

# Or load from file
ITALY_USERS_FILE=/path/to/italy_users.txt

# State files
ITALY_ROTATION_STATE_FILE=italy_user_rotation.json
ITALY_BLOCKED_USERS_FILE=italy_blocked_accounts.json

# Optional: Custom login URL
ITALY_LOGIN_URL=https://prenotami.esteri.it/

# Optional: Proxy configuration
PROXY_SERVER=http://proxy.example.com:8080
PROXY_USERNAME=proxy_user
PROXY_PASSWORD=proxy_pass

# Headless mode (true for server, false for local debug)
ITALY_HEADLESS=true
```

### Booking Services

Edit `embassy_eye/scrapers/italy/runner.py`:

```python
BOOKING_TARGET_URLS = [
    "/Services/Booking/1151",
    "/Services/Booking/1258",
    # Add more service IDs as needed
]
```

## Usage

### With Docker
```bash
docker-compose -f docker-compose.italy.yml run --rm embassy-eye-italy
```

### With Python
```bash
python -m embassy_eye.scrapers.italy.runner
```

### Scheduled (Cron)
```bash
# Edit run_script.sh to enable Italy scraper (currently disabled)
# Then use cron:
*/10 * * * * /root/embassy-eye/run_script.sh >> /root/embassy-eye/cron.log 2>&1
```

## Account Rotation

### How It Works
- Maintains list of accounts in `ITALY_USERS` or `ITALY_USERS_FILE`
- Tracks current account in `ITALY_ROTATION_STATE_FILE` (round-robin)
- Automatically skips blocked accounts (tracked in `ITALY_BLOCKED_USERS_FILE`)
- Each run uses next available account

### Account Formats

**JSON format:**
```json
[
  {"email":"user1@example.com","password":"pass1","label":"Primary"},
  {"email":"user2@example.com","password":"pass2","label":"Backup"}
]
```

**Text format (newline-separated):**
```
user1@example.com|pass1|Primary
user2@example.com|pass2|Backup
```

### Blocked Account Detection
If login shows "Account bloccato / Account Blocked" page:
1. Account is automatically marked as blocked
2. Saved to `ITALY_BLOCKED_USERS_FILE`
3. Skipped in future runs
4. Next account is tried

## Slot Detection Logic

### Available Slots Detected When:
1. ✅ No "no slots" modal appears after clicking booking button
2. ✅ Modal doesn't contain messages like:
   - "Sorry, all appointments for this service are currently booked..."
   - "Stante l'elevata richiesta i posti disponibili per il servizio scelto sono esauriti."

### Important Notes:
- Script only needs **one** service to have slots to send notification
- Checks each service independently
- 5 second wait after clicking each button
- Browser stays open until ENTER is pressed (for debugging)

## Chrome DevTools Protocol (CDP)

### Why CDP?
- Uses **real Google Chrome** (not Chromium)
- Natural browser fingerprint (not detected as automation)
- Full reCAPTCHA Enterprise support
- Real Client Hints (Sec-CH-UA* headers)
- Proper Trusted Types and CSP handling

### Setup
Chrome must be installed and startable with remote debugging:
```bash
google-chrome --remote-debugging-port=9222 --user-data-dir=/tmp/chrome-profile
```

The scraper automatically handles this.

## Anti-Detection Measures

- ✅ Uses real Chrome (not Chromium)
- ✅ Minimal stealth (only removes `navigator.webdriver`)
- ✅ Human-like mouse movements and typing
- ✅ Realistic delays and behavior simulation
- ✅ No fingerprint spoofing (allows reCAPTCHA to work)

## Notifications

When slots are found:
- 📱 Telegram message with:
  - Service URL
  - Timestamp
  - Current IP and country
  - Account used
- 💽 Entry in `slot_statistics` database table

## Database Tables Used

### slot_statistics
Logs when slots are found:
```sql
embassy    | 'italy'
location   | NULL
service    | '1151' (booking service ID)
detected_at| timestamp
notes      | 'Booking service: /Services/Booking/1151'
```

## State Files

### italy_user_rotation.json
Tracks current account in rotation:
```json
{"index": 2}
```

### italy_blocked_accounts.json
List of blocked accounts to skip:
```json
{
  "blocked": [
    {"email": "blocked@example.com", "password": "pass", "label": "Blocked Account"}
  ]
}
```

## Troubleshooting

### reCAPTCHA timeout
- Script waits up to 90 seconds for reCAPTCHA completion
- Solve manually in the browser window
- Consider using accounts with good reCAPTCHA history

### Login fails
- Verify credentials in `.env` file
- Check if account is blocked on website
- Review account rotation state files

### Chrome not found
- Ensure Google Chrome is installed (not just Chromium)
- Check Chrome can start with remote debugging
- Verify port 9222 is not in use

### Modal not detected
- Script waits 5 seconds after clicking
- May need to increase timeout for slow connections
- Check if modal HTML structure changed

### Browser stays open
- Intentional for debugging
- Press ENTER in console when ready to close
- Allows manual inspection of page state

## Performance

- Average run time: 2-5 minutes
- Login: 30-60 seconds
- reCAPTCHA: 10-90 seconds (manual solve)
- Service checking: 10-30 seconds per service
- Browser startup: 5-10 seconds

## Security Notes

- Credentials stored in `.env` file (not committed to git)
- Use proper file permissions: `chmod 600 .env`
- Account rotation helps prevent blocks
- Proxy support available for additional security

## Technical Details

### Browser Platform
- Linux AMD64 platform specified
- Chrome runs in headed mode locally, headless on server
- Uses Chrome's native CDP protocol
- Playwright for automation

### Dependencies
- `playwright>=1.40.0`
- `playwright-stealth>=1.0.6`
- `playwright-recaptcha>=0.3.0`

### Playwright Installation
```bash
pip install playwright
playwright install chromium
```

## Exit Codes

- `0`: Success (slots checked, no errors)
- `1`: Login failed or other error
- `2`: Account blocked

## Known Limitations

- reCAPTCHA requires manual solving (no automation)
- Browser must stay open during execution
- Requires real Google Chrome installed
- Account rotation limited by number of available accounts
