# Database Installation Guide

Quick guide for setting up PostgreSQL on your server for the first time.

## Ubuntu/Debian Server

```bash
# 1. Install PostgreSQL
sudo apt update
sudo apt install postgresql postgresql-contrib -y

# 2. Start PostgreSQL
sudo systemctl start postgresql
sudo systemctl enable postgresql

# 3. Create database and user
sudo -u postgres psql << EOF
CREATE USER embassy_user WITH PASSWORD 'embassy_pass';
CREATE DATABASE embassy_eye;
GRANT ALL PRIVILEGES ON DATABASE embassy_eye TO embassy_user;
\c embassy_eye
GRANT ALL ON SCHEMA public TO embassy_user;
GRANT CREATE ON SCHEMA public TO embassy_user;
EOF

# 4. Configure authentication (allow password login)
echo "host all all 127.0.0.1/32 md5" | sudo tee -a /etc/postgresql/*/main/pg_hba.conf

# 5. Restart PostgreSQL
sudo systemctl restart postgresql

# 6. Test connection
psql -h localhost -U embassy_user -d embassy_eye
# Enter password: embassy_pass
# Type \q to exit
```

## Configure Application

```bash
# 1. Go to your project directory
cd /root/embassy-eye

# 2. Add database URL to .env file
echo "DATABASE_URL=postgresql://embassy_user:embassy_pass@localhost:5432/embassy_eye" >> .env
echo "DB_ECHO=false" >> .env

# 3. Rebuild Docker image (to include new database dependencies)
./build_docker.sh

# 4. Initialize database tables
docker-compose run --rm embassy-eye python scripts/init_database.py

# Note: No need to install Python dependencies on host if using Docker!
```

You should see:
```
✓ Database connection successful
✓ Database tables created successfully
✓ All required tables exist
```

## Verify Installation

```bash
# Check PostgreSQL is running
sudo systemctl status postgresql

# Check tables were created
psql -h localhost -U embassy_user -d embassy_eye -c "\dt"
```

You should see:
```
             List of relations
 Schema |      Name        | Type  |    Owner     
--------+------------------+-------+--------------
 public | blocked_vpns     | table | embassy_user
 public | slot_statistics  | table | embassy_user
```

## What Gets Tracked

### blocked_vpns table
Logs every time a VPN IP is blocked:
- IP address
- Country
- Which embassy blocked it (hungary/italy)
- Timestamp
- Additional notes

### slot_statistics table
Logs every time appointment slots are found:
- Embassy name (hungary/italy)
- Location (subotica/belgrade for Hungary)
- Service ID (for Italy booking services)
- Timestamp
- Notes (special cases like captcha/email verification)

## Query Examples

```bash
# View recent blocked IPs
psql -h localhost -U embassy_user -d embassy_eye -c \
  "SELECT blocked_at, ip_address, country, embassy FROM blocked_vpns ORDER BY blocked_at DESC LIMIT 20;"

# View recent slots found
psql -h localhost -U embassy_user -d embassy_eye -c \
  "SELECT detected_at, embassy, location, service FROM slot_statistics ORDER BY detected_at DESC LIMIT 20;"

# Count blocked IPs by country
psql -h localhost -U embassy_user -d embassy_eye -c \
  "SELECT country, COUNT(*) as count FROM blocked_vpns GROUP BY country ORDER BY count DESC;"

# Slots found in last 7 days
psql -h localhost -U embassy_user -d embassy_eye -c \
  "SELECT embassy, COUNT(*) FROM slot_statistics WHERE detected_at > NOW() - INTERVAL '7 days' GROUP BY embassy;"
```

## Backup Database

```bash
# Backup
pg_dump -h localhost -U embassy_user -d embassy_eye > embassy_eye_backup.sql

# Restore
psql -h localhost -U embassy_user -d embassy_eye < embassy_eye_backup.sql
```

## Clean Old Data

```bash
# Delete blocked IPs older than 30 days
psql -h localhost -U embassy_user -d embassy_eye -c \
  "DELETE FROM blocked_vpns WHERE blocked_at < NOW() - INTERVAL '30 days';"

# Delete slot statistics older than 90 days
psql -h localhost -U embassy_user -d embassy_eye -c \
  "DELETE FROM slot_statistics WHERE detected_at < NOW() - INTERVAL '90 days';"
```

## Troubleshooting

### Can't connect to database

```bash
# Check if PostgreSQL is running
sudo systemctl status postgresql

# Check if port 5432 is listening
sudo netstat -plunt | grep 5432

# Restart PostgreSQL
sudo systemctl restart postgresql
```

### Permission denied errors

```bash
sudo -u postgres psql embassy_eye << EOF
GRANT ALL ON SCHEMA public TO embassy_user;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO embassy_user;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO embassy_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO embassy_user;
EOF
```

### Authentication failed

Check that `pg_hba.conf` has the md5 authentication line:
```bash
sudo grep "md5" /etc/postgresql/*/main/pg_hba.conf
```

If not found, add it:
```bash
echo "host all all 127.0.0.1/32 md5" | sudo tee -a /etc/postgresql/*/main/pg_hba.conf
sudo systemctl restart postgresql
```

## Change Default Password

Don't use default password in production:

```bash
# Generate strong password
openssl rand -base64 32

# Change password in PostgreSQL
sudo -u postgres psql << EOF
ALTER USER embassy_user WITH PASSWORD 'your_new_strong_password';
EOF

# Update .env file
nano .env
# Change: DATABASE_URL=postgresql://embassy_user:your_new_strong_password@localhost:5432/embassy_eye
```

## Security Recommendations

1. **Use strong passwords**: Not the default `embassy_pass`
2. **Limit network access**: Only allow localhost in `pg_hba.conf`
3. **Regular backups**: Set up automated backups
4. **Keep PostgreSQL updated**: `sudo apt update && sudo apt upgrade postgresql`
5. **Monitor disk usage**: Clean old data periodically
