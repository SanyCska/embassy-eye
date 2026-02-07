# Embassy Eye

Automated appointment monitoring system for embassy appointment booking. Continuously checks for available appointment slots and sends notifications via Telegram.

## 🎯 Features

- 🤖 **Automated Monitoring**: Checks Hungary (Subotica/Belgrade) and Italy embassy appointments
- 📱 **Telegram Notifications**: Instant alerts when slots are found
- 🔒 **VPN Integration**: Built-in WireGuard VPN rotation with IP blocking detection
- 🐳 **Docker Support**: Easy deployment with Docker Compose
- 💾 **Database Logging**: PostgreSQL database for tracking blocked IPs and slot statistics
- 📊 **Run Statistics**: Track every run with detailed outcomes and success rates
- ⏰ **Cron Scheduling**: Runs automatically every 10 minutes
- 📸 **Screenshot Capture**: Saves screenshots and HTML when slots are found
- ⏸️ **Smart Cooldown**: Automatically pauses after captcha detection

## 📋 Requirements

- Python 3.11+ (if running without Docker)
- Docker and Docker Compose (recommended)
- PostgreSQL 14+ (for database logging)
- WireGuard VPN configured (optional, but recommended)
- Telegram Bot Token and User ID

## 🚀 Quick Start

### 1. Install PostgreSQL

See [DATABASE_INSTALL.md](DATABASE_INSTALL.md) for complete instructions.

Quick version:
```bash
sudo apt install postgresql postgresql-contrib -y
sudo -u postgres psql << EOF
CREATE USER embassy_user WITH PASSWORD 'embassy_pass';
CREATE DATABASE embassy_eye;
GRANT ALL PRIVILEGES ON DATABASE embassy_eye TO embassy_user;
\c embassy_eye
GRANT ALL ON SCHEMA public TO embassy_user;
EOF
echo "host all all 127.0.0.1/32 md5" | sudo tee -a /etc/postgresql/*/main/pg_hba.conf
sudo systemctl restart postgresql
```

### 2. Clone and Configure

```bash
git clone <repository-url>
cd embassy-eye

# Setup environment
cp env.example .env
nano .env  # Add your credentials

# Install dependencies and initialize database
pip install -r requirements.txt
python scripts/init_database.py
```

### 3. Run with Docker (Recommended)

```bash
# Build images
./build_docker.sh

# Test run (Hungary - both locations)
./run_script.sh

# Setup cron for every 10 minutes
crontab -e
# Add: */10 * * * * /root/embassy-eye/run_script.sh >> /root/embassy-eye/cron.log 2>&1
```

## 📁 Project Structure

```
embassy-eye/
├── embassy_eye/
│   ├── automation/         # Web automation utilities
│   ├── database/          # PostgreSQL models and operations
│   ├── notifications/     # Telegram notifications
│   ├── runner/           # Main execution logic
│   └── scrapers/
│       ├── hungary/      # Hungary embassy scraper (Subotica & Belgrade)
│       └── italy/        # Italy embassy scraper
├── scripts/              # Utility scripts
├── run_script.sh        # Main wrapper with VPN management
├── .env                 # Configuration (not in git)
└── DATABASE_INSTALL.md  # Database setup guide
```

## ⚙️ Configuration

### Environment Variables

Edit `.env` file:

```bash
# Telegram (Required)
TELEGRAM_BOT_TOKEN=your_bot_token_here
TELEGRAM_USER_ID=your_user_id_here
HEALTHCHECK_BOT_TOKEN=your_healthcheck_bot_here  # Optional

# Database (Required)
DATABASE_URL=postgresql://embassy_user:embassy_pass@localhost:5432/embassy_eye
DB_ECHO=false

# Italy credentials (if using Italy scraper)
ITALY_EMAIL=your_email@example.com
ITALY_PASSWORD=your_password
```

**Getting Telegram credentials:**
- Bot Token: Create bot with [@BotFather](https://t.me/BotFather)
- User ID: Get from [@userinfobot](https://t.me/userinfobot)

### VPN Configuration

The `run_script.sh` automatically manages VPN connections using WireGuard.

**Available VPN locations** (edit `run_script.sh` to customize):
- Albania, Bosnia, Bulgaria, Croatia, Cyprus, Georgia
- Greece, Hungary, Moldova, Montenegro, North Macedonia
- Poland, Romania, Serbia, Slovakia, Slovenia, Turkey

**Setup passwordless sudo for cron:**
```bash
sudo visudo
# Add: youruser ALL=(ALL) NOPASSWD: /usr/bin/wg-quick
```

## 🏃 Usage

### Manual Run
```bash
# With VPN rotation and Docker
./run_script.sh

# Docker only (no VPN)
docker-compose run --rm embassy-eye python fill_form.py hungary both

# Python directly
python fill_form.py hungary both
```

### Cron Scheduling

Run every 10 minutes:
```bash
crontab -e
```

Add:
```cron
*/10 * * * * /root/embassy-eye/run_script.sh >> /root/embassy-eye/cron.log 2>&1
```

Other schedules:
- `*/5 * * * *` - Every 5 minutes
- `*/15 * * * *` - Every 15 minutes
- `0 * * * *` - Every hour

## 📊 Database

The system automatically tracks:

### Blocked VPN IPs
Every time a VPN IP is blocked:
- IP address, country, embassy, timestamp

### Slot Statistics  
Every time slots are found:
- Embassy, location, service, timestamp, notes

**Query examples:**
```bash
# Recent blocked IPs
psql -h localhost -U embassy_user -d embassy_eye -c \
  "SELECT * FROM blocked_vpns ORDER BY blocked_at DESC LIMIT 10;"

# Recent slots found
psql -h localhost -U embassy_user -d embassy_eye -c \
  "SELECT * FROM slot_statistics ORDER BY detected_at DESC LIMIT 10;"

# Blocked IPs by country
psql -h localhost -U embassy_user -d embassy_eye -c \
  "SELECT country, COUNT(*) FROM blocked_vpns GROUP BY country ORDER BY COUNT(*) DESC;"
```

## 🔍 How It Works

### Hungary Scraper
1. Connects via random VPN
2. Checks if IP is in blocked list
3. Fills booking form for Subotica and/or Belgrade
4. Detects available slots or blocks
5. Sends Telegram notification if slots found
6. Logs to database
7. If IP blocked: rotates VPN and retries (up to 3 times)

### Italy Scraper
1. Uses real Chrome with CDP (Chrome DevTools Protocol)
2. Handles reCAPTCHA Enterprise
3. Checks multiple booking services
4. Detects "no slots" modals
5. Account rotation to avoid blocks
6. Sends notification with service details

See scraper-specific docs:
- [Hungary Scraper Details](embassy_eye/scrapers/hungary/README.md)
- [Italy Scraper Details](embassy_eye/scrapers/italy/README.md)

## 📊 Statistics & Monitoring

View detailed run statistics to analyze success rates and system behavior:

```bash
# View detailed statistics for last 7 days
python scripts/view_run_statistics.py --detailed

# View last 30 days
python scripts/view_run_statistics.py --detailed --days 30

# View specific location
python scripts/view_run_statistics.py --detailed --location subotica

# View recent runs
python scripts/view_run_statistics.py --recent --limit 50
```

The system tracks every run with outcomes:
- ✅ **Slots Found**: slots_found, slots_found_captcha, slots_found_email_verification
- ❌ **No Slots (Modal)**: no_slots_modal - reliable "no slots" indicator
- 🚫 **IP Blocked**: ip_blocked - triggers VPN rotation
- ⚠️ **No Slots (Other)**: no_slots_other - ambiguous cases

See [STATISTICS.md](STATISTICS.md) for complete documentation on viewing and analyzing statistics.

## 🔧 Troubleshooting

### Check Logs
```bash
# Cron logs
tail -f /root/embassy-eye/cron.log

# Docker logs
docker logs -f embassy-eye

# Database connection
python scripts/init_database.py
```

### Common Issues

1. **VPN fails**: Check passwordless sudo setup
2. **Database errors**: Verify PostgreSQL is running and DATABASE_URL is correct
3. **No notifications**: Check Telegram credentials in .env
4. **IP keeps getting blocked**: Script will rotate through VPN locations automatically

### Deployment

Update and rebuild:
```bash
cd /root/embassy-eye
git pull --rebase
./build_docker.sh
docker-compose up --build --remove-orphans -d
```

## 🔐 Security

- Keep `.env` file secure: `chmod 600 .env`
- Don't commit `.env` to version control
- Use strong database passwords
- Limit PostgreSQL network access
- Run as non-root user when possible

## 📝 License

See [LICENSE](LICENSE) file.

## ⚠️ Disclaimer

This tool is for educational and personal use only. Use responsibly and in accordance with embassy terms of service. The authors are not responsible for any misuse.
