# Cron Setup Guide

This guide explains how to run the embassy-eye script every 10 minutes using cron on your server.

## Prerequisites

1. **Docker and Docker Compose installed** (recommended)
   - Or Python 3.11+ with all dependencies installed

2. **WireGuard VPN configured**
   - VPN configuration file should be at `/etc/wireguard/rs-beg.conf`
   - The script will automatically start VPN before running and shut it down after

3. **Passwordless sudo for wg-quick** (required for cron)
   - The script needs to run `sudo wg-quick up rs-beg` and `sudo wg-quick down rs-beg`
   - Configure passwordless sudo by editing `/etc/sudoers`:
     ```bash
     sudo visudo
     ```
   - Add this line (replace `youruser` with your actual username):
     ```
     youruser ALL=(ALL) NOPASSWD: /usr/bin/wg-quick
     ```
   - Or more restrictively, only allow the specific VPN:
     ```
     youruser ALL=(ALL) NOPASSWD: /usr/bin/wg-quick up rs-beg, /usr/bin/wg-quick down rs-beg
     ```

4. **Environment file configured**
   - Make sure `.env` file exists with:
     ```
     TELEGRAM_BOT_TOKEN=your_bot_token_here
     TELEGRAM_USER_ID=your_user_id_here
     ```

## Option 1: Using Docker (Recommended)

### Step 1: Make the wrapper script executable
```bash
chmod +x run_docker.sh
```

### Step 2: Edit crontab
```bash
crontab -e
```

### Step 3: Add the cron job
Add this line to run every 10 minutes:
```cron
*/10 * * * * /full/path/to/embassy-eye/run_docker.sh >> /full/path/to/embassy-eye/cron.log 2>&1
```

**Example with absolute path:**
```cron
*/10 * * * * /home/user/embassy-eye/run_docker.sh >> /home/user/embassy-eye/cron.log 2>&1
```

### Step 4: Verify cron is running
```bash
# Check if cron service is running
sudo systemctl status cron

# View cron logs
tail -f /home/user/embassy-eye/cron.log
```

## Option 2: Using Python directly (without Docker)

### Step 1: Set up Python virtual environment
```bash
cd /path/to/embassy-eye
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### Step 2: Make the wrapper script executable
```bash
chmod +x run_script.sh
```

### Step 3: Edit crontab
```bash
crontab -e
```

### Step 4: Add the cron job with virtual environment
```cron
*/10 * * * * cd /full/path/to/embassy-eye && /full/path/to/embassy-eye/venv/bin/python fill_form.py >> /full/path/to/embassy-eye/cron.log 2>&1
```

Or use the wrapper:
```cron
*/10 * * * * /full/path/to/embassy-eye/run_script.sh >> /full/path/to/embassy-eye/cron.log 2>&1
```

## Cron Schedule Format

The format is: `minute hour day month weekday`

- `*/10 * * * *` - Every 10 minutes
- `*/5 * * * *` - Every 5 minutes
- `0 * * * *` - Every hour
- `0 */2 * * *` - Every 2 hours
- `0 9 * * *` - Every day at 9:00 AM

## Troubleshooting

### Check if cron is running
```bash
sudo systemctl status cron
# or on some systems
sudo systemctl status crond
```

### View cron logs
```bash
# Check your application log
tail -f /path/to/embassy-eye/cron.log

# Check system cron logs
sudo tail -f /var/log/syslog | grep CRON
# or
sudo journalctl -u cron -f
```

### Test the script manually
```bash
# Test Docker version (will start/stop VPN automatically)
./run_docker.sh

# Test Python version (will start/stop VPN automatically)
./run_script.sh

# Test VPN commands manually
sudo wg-quick up rs-beg
sudo wg-quick down rs-beg
```

### Common issues

1. **Permission denied**: Make sure scripts are executable
   ```bash
   chmod +x run_docker.sh run_script.sh
   ```

2. **VPN fails to start (sudo password required)**: Configure passwordless sudo
   - See "Prerequisites" section above for sudoers configuration
   - Test manually: `sudo wg-quick up rs-beg` (should not ask for password)

3. **VPN already running**: The script will handle this gracefully
   - If VPN is already up, `wg-quick up` may return an error, but the script will continue
   - The shutdown will still work correctly

4. **Docker not found**: Make sure Docker is in PATH for cron
   - Add full path to docker: `/usr/bin/docker`
   - Or set PATH in cron job:
   ```cron
   */10 * * * * PATH=/usr/bin:/usr/local/bin:$PATH /path/to/run_docker.sh >> /path/to/cron.log 2>&1
   ```

5. **Environment variables not loaded**: Cron runs with minimal environment
   - Use absolute paths in cron jobs
   - Load .env file explicitly in the script (already done in wrapper scripts)

6. **Docker Compose not found**: Use full path or alias
   ```cron
   */10 * * * * /usr/local/bin/docker-compose -f /path/to/docker-compose.yml run --rm embassy-eye >> /path/to/cron.log 2>&1
   ```

## Log Rotation (Optional)

To prevent log files from growing too large, add log rotation:

Create `/etc/logrotate.d/embassy-eye`:
```
/path/to/embassy-eye/cron.log {
    daily
    rotate 7
    compress
    missingok
    notifempty
}
```

## Security Notes

1. Make sure `.env` file has proper permissions (not world-readable):
   ```bash
   chmod 600 .env
   ```

2. Don't commit `.env` to version control (already in `.gitignore`)

3. Consider running as a dedicated user instead of root


