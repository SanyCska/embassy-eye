# Embassy Eye

An automated appointment monitoring and booking system for embassy appointment scheduling. This tool continuously checks for available appointment slots and sends notifications via Telegram when slots become available.

## Features

- 🤖 **Automated Form Filling**: Automatically fills booking forms with configurable data
- 🔍 **Slot Monitoring**: Continuously checks for available appointment slots
- 📱 **Telegram Notifications**: Sends instant notifications when slots are found
- 🐳 **Docker Support**: Easy deployment with Docker and Docker Compose
- 🔒 **VPN Integration**: Built-in WireGuard VPN support for secure connections
- ⏰ **Cron Scheduling**: Run automatically on a schedule (e.g., every 10 minutes)
- 🎭 **Undetected Automation**: Uses undetected-chromedriver to avoid detection
- 📸 **Screenshot Capture**: Automatically captures and sends screenshots when slots are found
- ⏸️ **Captcha Cooldown**: Automatically skips runs when captcha is detected to avoid triggering rate limits
- 💾 **HTML Saving**: Saves page HTML when slots are found (except for captcha cases)

## Requirements

- Python 3.11+ (if running without Docker)
- Docker and Docker Compose (recommended)
- WireGuard VPN configured (optional, but recommended)
- Telegram Bot Token and User ID (for notifications)

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
   # Edit .env and add your Telegram credentials
   ```

3. **Build and run:**
   ```bash
   ./build_docker.sh
   docker-compose up -d embassy-eye
   ```

### Option 2: Using Python Directly

1. **Clone the repository:**
   ```bash
   git clone <repository-url>
   cd embassy-eye
   ```

2. **Create a virtual environment:**
   ```bash
   python3 -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Set up environment variables:**
   ```bash
   cp env.example .env
   # Edit .env and add your Telegram credentials
   ```

## Configuration

### Environment Variables

Create a `.env` file in the project root with the following variables:

```env
TELEGRAM_BOT_TOKEN=your_bot_token_here
TELEGRAM_USER_ID=your_user_id_here
```

**Getting your Telegram credentials:**
- **Bot Token**: Create a bot using [@BotFather](https://t.me/BotFather) on Telegram
- **User ID**: Get your user ID from [@userinfobot](https://t.me/userinfobot) on Telegram

### Form Configuration

Edit `config.py` to customize:
- Default form values (name, email, phone, etc.)
- Field mappings
- Dropdown selections (consulate, visa type)
- Timing constants
- Booking URL

### VPN Configuration

If using VPN, ensure your WireGuard configuration is at `/etc/wireguard/rs-beg.conf`. The script will automatically start and stop the VPN connection.

For passwordless VPN access (required for cron), configure sudoers:
```bash
sudo visudo
# Add this line (replace 'youruser' with your username):
youruser ALL=(ALL) NOPASSWD: /usr/bin/wg-quick
```

## Usage

### Manual Execution

**Using Docker:**
```bash
docker-compose run --rm embassy-eye
```

**Using Python:**
```bash
python fill_form.py
# or
./run_script.sh
```

The `run_script.sh` script automatically:
- Starts VPN connection (if configured)
- Runs the automation (using Docker if available, otherwise Python)
- Stops VPN connection when finished

### Scheduled Execution (Cron)

To run automatically every 10 minutes:

1. **Make the script executable:**
   ```bash
   chmod +x run_script.sh
   ```

2. **Edit crontab:**
   ```bash
   crontab -e
   ```

3. **Add the cron job:**
   ```cron
   */10 * * * * /full/path/to/embassy-eye/run_script.sh >> /full/path/to/embassy-eye/cron.log 2>&1
   ```

For more detailed cron setup instructions, see [CRON_SETUP.md](CRON_SETUP.md).

## How It Works

1. **Cooldown Check**: Before starting, checks if the script should skip this run due to captcha cooldown
2. **Initialization**: Starts Chrome browser with undetected-chromedriver
3. **Navigation**: Navigates to the embassy booking page
4. **Form Inspection**: Analyzes available form fields
5. **Form Filling**: 
   - Selects consulate and visa type from dropdowns
   - Fills all required fields with configured data
   - Handles special fields (email, checkboxes, textareas)
6. **Slot Checking**: Clicks "Next" and checks for available appointment slots
7. **Notification**: If slots are found, sends Telegram notification with screenshot
8. **HTML Saving**: Saves page HTML to `screenshots/` folder when slots are found (skipped for captcha cases)
9. **Captcha Handling**: If captcha is detected, saves cooldown info and skips next 2 runs
10. **Cleanup**: Closes browser and shuts down VPN (if used)

### Captcha Cooldown Mechanism

When the script detects that slots are available but a captcha is required, it automatically:

- **Saves cooldown information** to `captcha_cooldown.json`
- **Skips the next 2 scheduled runs** to avoid triggering rate limits
- **Automatically resumes** normal operation after the cooldown period

This helps prevent the script from repeatedly hitting captcha challenges. The cooldown file is automatically managed and cleared after the required number of skips.

**Cooldown File Location**: `captcha_cooldown.json` in the project root

## Project Structure

```
embassy-eye/
├── embassy_eye/          # Main package
│   ├── automation/       # Web automation utilities
│   ├── config/          # Configuration modules
│   ├── notifications/   # Telegram notification system
│   └── runner/          # Main execution logic
├── scripts/             # CLI entry points
├── screenshots/         # Captured screenshots and HTML
├── captcha_cooldown.json  # Cooldown state file (auto-managed)
├── config.py            # Default configuration values
├── fill_form.py         # Backward-compatible entry point
├── run_script.sh        # Wrapper script with VPN management
├── docker-compose.yml   # Docker Compose configuration
├── Dockerfile           # Docker image definition
└── requirements.txt     # Python dependencies
```

## Deployment

For deployment instructions, see [DEPLOYMENT.md](DEPLOYMENT.md).

Quick deployment steps:
```bash
# Stop existing containers
docker stop embassy-eye || true
docker rm embassy-eye || true

# Update code
git pull --rebase

# Rebuild and start
./build_docker.sh
docker-compose up --build --remove-orphans -d embassy-eye

# Check logs
docker logs -f embassy-eye
```

## Troubleshooting

### Common Issues

1. **VPN fails to start**: Ensure passwordless sudo is configured (see VPN Configuration)
2. **Telegram notifications not working**: Verify `.env` file has correct credentials
3. **Docker not found**: Use full paths in cron jobs or ensure Docker is in PATH
4. **Form fields not filling**: Check `config.py` for correct field mappings
5. **No slots found**: This is expected - the tool will continue monitoring
6. **Script skipping runs**: Check `captcha_cooldown.json` - the script automatically skips runs after captcha detection

### Logs

- **Docker logs**: `docker logs -f embassy-eye`
- **Cron logs**: Check `cron.log` in the project directory
- **System logs**: `sudo journalctl -u cron -f`

## Security Notes

- Keep your `.env` file secure and never commit it to version control
- Use proper file permissions: `chmod 600 .env`
- Consider running as a dedicated user instead of root
- VPN credentials should be properly secured

## License

See [LICENSE](LICENSE) file for details.

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## Disclaimer

This tool is for educational and personal use only. Use responsibly and in accordance with the terms of service of the booking system. The authors are not responsible for any misuse of this software.

