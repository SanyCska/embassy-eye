# Hungary Embassy Scraper

Automated appointment monitoring for Hungarian Embassy appointment booking (konzinfobooking.mfa.gov.hu).

## Features

- ✅ Monitors both **Subotica** and **Belgrade** consulate locations
- 🔄 Automatic IP blocking detection and VPN rotation
- 📱 Telegram notifications when slots are found
- 💾 Logs blocked IPs and slot statistics to database
- ⏸️ Captcha cooldown mechanism
- 📸 Saves screenshots and HTML when slots found

## How It Works

1. **Form Inspection**: Analyzes available form fields on the booking page
2. **Consulate Selection**: Selects consulate (Subotica or Belgrade) from dropdown
3. **Visa Type Selection**: Selects visa type from dropdown
4. **Form Filling**: Fills all form fields with configured data
5. **Slot Checking**: Clicks "Next" button and checks for available slots
6. **IP Block Detection**: Detects if IP is blocked and triggers VPN rotation
7. **Notification**: Sends Telegram message with screenshot if slots found
8. **Database Logging**: Records blocked IPs and slot statistics

## Configuration

Edit `embassy_eye/scrapers/hungary/config.py`:

```python
# Booking URL
BOOKING_URL = "https://konzinfobooking.mfa.gov.hu/"

# Page load wait time (seconds)
PAGE_LOAD_WAIT = 5

# Locations
LOCATIONS = ["subotica", "belgrade"]
```

## Usage

### Run Both Locations
```bash
python fill_form.py hungary both
```

### Run Subotica Only
```bash
python fill_form.py hungary subotica
```

### Run Belgrade Only
```bash
python fill_form.py hungary belgrade
```

### With Docker
```bash
docker-compose run --rm embassy-eye python fill_form.py hungary both
```

## Slot Detection

The scraper detects available slots by:

1. **Email Verification Modal**: If present, slots are available
2. **Captcha Modal**: If present, slots are available (but captcha required)
3. **No "No Appointments" Modal**: If neither modal appears, likely slots available
4. **"Select Date" Button**: If enabled, slots are available

When slots are found:
- 📸 Full-page screenshot captured
- 💾 Page HTML saved to `screenshots/slots_found_YYYYMMDD_HHMMSS.html`
- 📱 Telegram notification sent
- 💽 Entry logged to `slot_statistics` database table

## IP Blocking Handling

### Detection
The scraper detects IP blocking by looking for:
- Message: "Your IP (X.X.X.X) has been blocked"
- Pattern in page source or body text

### Response
When IP is blocked:
1. 🚫 Logs IP to `blocked_vpns` database table
2. 📝 Logs to file backup: `logs/blocked_ips.log`
3. 📱 Sends healthcheck notification (if configured)
4. 🔄 Script exits with code 2 (triggers VPN rotation in `run_script.sh`)
5. 🔁 Wrapper script rotates to different VPN and retries (up to 3 times)

### Blocked IPs List
Blocked IPs are tracked in:
- **Database**: `blocked_vpns` table (recommended)
- **File backup**: `logs/blocked_ips.log` (legacy, still written for safety)

The VPN rotation logic checks blocked IPs before running to avoid using known blocked IPs.

## Captcha Handling

When captcha is detected:
- ⏸️ Saves cooldown to `captcha_cooldown.json`
- 🔕 Skips next 2 scheduled runs
- 📱 Sends notification without screenshot
- ⏰ Automatically resumes normal operation after cooldown

## Form Field Configuration

Default form data configured in `embassy_eye/automation/form_helpers.py`:

```python
FIELD_MAP = {
    "email": "test@example.com",
    "name": "John Doe",
    "phone": "+381123456789",
    # ... more fields
}
```

## Exit Codes

- `0`: Success (slots checked, no errors)
- `1`: General error
- `2`: IP blocked (triggers VPN rotation)
- Other: Form filling errors or exceptions

## Logs and Screenshots

- **Cron logs**: `/root/embassy-eye/cron.log`
- **Screenshots**: `screenshots/slots_found_*.html`
- **Blocked IPs**: `logs/blocked_ips.log` and database
- **VPN usage**: `logs/vpn_usage.log`

## Database Tables Used

### slot_statistics
Logs when slots are found:
```sql
embassy    | 'hungary'
location   | 'subotica' or 'belgrade'
service    | NULL
detected_at| timestamp
notes      | 'Special case: captcha_required' or NULL
```

### blocked_vpns
Logs when IPs are blocked:
```sql
ip_address | '203.0.113.42'
country    | 'Romania'
embassy    | 'hungary'
blocked_at | timestamp
notes      | NULL
```

## Troubleshooting

### No fields filled
- Check form field names haven't changed on website
- Review form inspection output in logs
- Update `FIELD_MAP` in `form_helpers.py`

### IP keeps getting blocked
- VPN rotation will automatically try different locations
- Check `logs/blocked_ips.log` or database for blocked IPs
- May need to wait before retrying certain VPN locations

### Captcha appearing frequently
- Cooldown mechanism will skip next 2 runs automatically
- Consider reducing check frequency in cron
- May need to solve captcha manually on the website

### Form submission fails
- Website structure may have changed
- Check if new fields were added
- Review error messages in logs

## Technical Details

### Browser Setup
- Uses `undetected-chromedriver` to avoid bot detection
- Chrome runs in headless mode
- Randomizes user agent and device info per run

### Retry Logic
- Retries form filling once if no fields filled
- Retries if slots detected but no modal found
- Reloads page and tries again before giving up

### Modal Detection
Checks for multiple modal types:
- Email verification modal (slots available)
- Captcha modal (slots available, captcha required)
- "No appointments" modal (no slots)
- Alert elements on page

## Performance

- Average run time: 30-60 seconds
- VPN connection: 5-10 seconds
- Form filling: 10-20 seconds
- Slot checking: 10-20 seconds

## Dependencies

Main dependencies (see `requirements.txt`):
- `selenium>=4.0.0`
- `undetected-chromedriver>=3.5.0`
- `requests>=2.31.0`
- `sqlalchemy>=2.0.0`
- `psycopg2-binary>=2.9.0`
