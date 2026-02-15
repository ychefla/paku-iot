# Hetzner Deployment Guide

This document describes how to deploy the paku-iot stack to a Hetzner Cloud VM.

## Prerequisites

### Hetzner Cloud Account

1. Create a [Hetzner Cloud](https://www.hetzner.com/cloud) account
2. Create a new project or select an existing one
3. Generate an SSH key pair if you don't have one

### Recommended Server Specifications

The paku-iot stack is designed to run on minimal resources:

- **Type**: CX11 (1 vCPU, 2 GB RAM) or CX21 (2 vCPU, 4 GB RAM)
- **Image**: Ubuntu 24.04 LTS or Debian 12
- **Location**: Choose the closest datacenter to your devices
- **Storage**: 20 GB is sufficient for initial deployment

## Server Setup

### 1. Create the VM

1. Log in to [Hetzner Cloud Console](https://console.hetzner.cloud)
2. Click "Add Server"
3. Choose your preferred location and image (Ubuntu 24.04 recommended)
4. Select server type (CX11 minimum)
5. Add your SSH public key
6. Create the server and note the public IP address

### 2. Initial Server Configuration

SSH into your new server:

```bash
ssh root@<server-ip>
```

Update the system and install Docker:

```bash
# Update system packages
apt update && apt upgrade -y

# Install Docker
curl -fsSL https://get.docker.com | sh

# Install Docker Compose plugin
apt install -y docker-compose-plugin

# Verify installation
docker --version
docker compose version
```

### 3. Create Application User

For security, run the application as a non-root user:

```bash
# Create user
useradd -m -s /bin/bash paku
usermod -aG docker paku

# Set up SSH access for the user
mkdir -p /home/paku/.ssh
cp ~/.ssh/authorized_keys /home/paku/.ssh/
chown -R paku:paku /home/paku/.ssh
chmod 700 /home/paku/.ssh
chmod 600 /home/paku/.ssh/authorized_keys
```

### 4. Configure Firewall

Set up UFW firewall rules:

```bash
# Allow SSH
ufw allow 22/tcp

# Allow HTTP/HTTPS (Caddy reverse proxy)
ufw allow 80/tcp
ufw allow 443/tcp

# Allow MQTT (edge devices connect directly)
ufw allow 1883/tcp

# Enable firewall
ufw enable
```

## Deployment

### Manual Deployment

1. SSH into the server as the paku user:

```bash
ssh paku@<server-ip>
```

2. Clone the repository:

```bash
# Use your fork URL if you've forked the repository
git clone https://github.com/ychefla/paku-iot.git
cd paku-iot
```

3. Create the environment file with production values:

```bash
cp compose/.env.example compose/.env
```

4. Edit the environment file with secure credentials:

```bash
nano compose/.env
```

**Important**: Use strong, unique passwords for production:

```bash
# Generate secure passwords
openssl rand -base64 32  # For POSTGRES_PASSWORD
openssl rand -base64 32  # For GF_SECURITY_ADMIN_PASSWORD
openssl rand -base64 32  # For MQTT_PASSWORD
```

Key variables to set:
- `POSTGRES_PASSWORD` — database
- `GF_SECURITY_ADMIN_PASSWORD` — Grafana admin
- `MQTT_USER` / `MQTT_PASSWORD` — MQTT broker (same credentials go into edge device `secrets.h`)
- `PAKU_DOMAIN` — your domain for automatic TLS (e.g. `paku.example.com`), or `:80` for HTTP-only

5. Start the stack:

```bash
docker compose -f compose/stack.prod.yaml up -d
```

6. Verify services are running:

```bash
docker compose -f compose/stack.prod.yaml ps
docker compose -f compose/stack.prod.yaml logs -f
```

### Automated Deployment via GitHub Actions

The repository includes a GitHub Actions workflow for automated deployments.

#### Setup GitHub Secrets

Add the following secrets to your GitHub repository:

1. Go to **Settings** → **Secrets and variables** → **Actions**
2. Add these repository secrets:

| Secret Name | Description |
|-------------|-------------|
| `HETZNER_HOST` | Server IP address or hostname |
| `HETZNER_SSH_KEY` | Private SSH key for deployment |
| `POSTGRES_PASSWORD` | Strong password for PostgreSQL |
| `GF_SECURITY_ADMIN_PASSWORD` | Strong password for Grafana admin |
| `MQTT_USER` | MQTT broker username |
| `MQTT_PASSWORD` | MQTT broker password |
| `PAKU_DOMAIN` | Domain for Caddy TLS (e.g. `paku.example.com`) |

#### Generate Deployment SSH Key

Create a dedicated SSH key for deployments:

```bash
# On your local machine
ssh-keygen -t ed25519 -f ~/.ssh/paku-deploy -C "paku-deploy"

# Copy public key to server
ssh-copy-id -i ~/.ssh/paku-deploy.pub paku@<server-ip>

# Add private key content to GitHub secret HETZNER_SSH_KEY
cat ~/.ssh/paku-deploy
```

#### Trigger Deployment

Deployments are triggered by:
- Pushing to the `main` branch
- Manual trigger via GitHub Actions UI (workflow_dispatch)

## Operations

### View Logs

```bash
# All services
docker compose -f compose/stack.prod.yaml logs -f

# Specific service
docker compose -f compose/stack.prod.yaml logs -f collector
```

### Restart Services

```bash
# Restart all
docker compose -f compose/stack.prod.yaml restart

# Restart specific service
docker compose -f compose/stack.prod.yaml restart collector
```

### Update Deployment

```bash
cd ~/paku-iot
git pull
docker compose -f compose/stack.prod.yaml pull
docker compose -f compose/stack.prod.yaml up -d --build
```

### Backup Database

Backups run automatically every 24 hours via the `pg-backup` service (prod stack only).
Backups are stored in the `paku_backups` volume with 7-day retention.

```bash
# List existing backups
docker exec paku_postgres ls -lh /backups/

# Manual backup
docker exec paku_postgres /usr/local/bin/backup.sh

# Restore from backup
docker exec -i paku_postgres sh -c 'gunzip -c /backups/<file>.sql.gz | psql -U paku paku'
```

## Monitoring

### Health Checks

The production compose file includes health checks for all services. View status:

```bash
docker compose -f compose/stack.prod.yaml ps
```

### Resource Usage

```bash
docker stats
```

### Grafana Access

Access Grafana at `https://<your-domain>` (via Caddy reverse proxy with automatic TLS).
In dev mode (`PAKU_DOMAIN=:80`): `http://<server-ip>`.

## Security Considerations

**Implemented:**
1. **MQTT Authentication**: Username/password required (`allow_anonymous false`)
2. **HTTPS**: Caddy reverse proxy with automatic Let's Encrypt TLS
3. **Firewall**: Only SSH, HTTP/S, and MQTT ports exposed
4. **Backups**: Automated daily `pg_dump` with 7-day retention
5. **Strong Passwords**: Generated via `openssl rand` for all services

**Pending (see BACKLOG.md):**
- MQTT TLS encryption (port 8883)
- MQTT topic ACLs (per-device access control)
- OTA firmware signature verification

## Troubleshooting

### Container Won't Start

```bash
# Check logs
docker compose -f compose/stack.prod.yaml logs <service-name>

# Check container status
docker ps -a
```

### Database Connection Issues

```bash
# Test database connection
docker exec -it paku_postgres psql -U paku -d paku -c "SELECT 1;"
```

### Password Authentication Failed

If you see errors like `FATAL: password authentication failed for user "paku"`, this typically happens when:

1. The PostgreSQL database was initialized with one password
2. The `POSTGRES_PASSWORD` in `.env` or GitHub secrets was later changed
3. PostgreSQL ignores the new password because the database already exists

**Automatic Fix (GitHub Actions)**:
The deployment workflow automatically detects existing PostgreSQL volumes and updates the password to match the current secret. This happens transparently during deployment.

**Manual Fix**:
If you need to manually reset the password:

```bash
# SSH into the server
ssh paku@<server-ip>

# Stop all containers
cd ~/paku-iot
docker compose -f compose/stack.prod.yaml down

# Start only PostgreSQL
docker compose -f compose/stack.prod.yaml up -d postgres

# Wait for it to be ready
sleep 10

# Temporarily enable trust authentication
# Step 1: Backup original pg_hba.conf
docker exec paku_postgres bash -c \
  'cp /var/lib/postgresql/data/pg_hba.conf /var/lib/postgresql/data/pg_hba.conf.bak'

# Step 2: Add trust auth rule at the top of pg_hba.conf
docker exec paku_postgres bash -c '
  echo "local all all trust" > /tmp/pg_hba.conf
  cat /var/lib/postgresql/data/pg_hba.conf >> /tmp/pg_hba.conf
  mv /tmp/pg_hba.conf /var/lib/postgresql/data/pg_hba.conf
'

# Step 3: Reload PostgreSQL configuration
docker exec paku_postgres bash -c 'kill -HUP 1'
sleep 2

# Update the password (replace YOUR_NEW_PASSWORD with your actual password)
docker exec paku_postgres psql -U paku -d paku -c "ALTER USER paku WITH PASSWORD 'YOUR_NEW_PASSWORD';"

# Restore original authentication
docker exec paku_postgres bash -c \
  'mv /var/lib/postgresql/data/pg_hba.conf.bak /var/lib/postgresql/data/pg_hba.conf'
docker exec paku_postgres bash -c 'kill -HUP 1'

# Restart the full stack
docker compose -f compose/stack.prod.yaml down
docker compose -f compose/stack.prod.yaml up -d
```

**Alternative: Fresh Start** (loses all data):
```bash
# Stop containers and remove volumes
docker compose -f compose/stack.prod.yaml down -v

# Start fresh
docker compose -f compose/stack.prod.yaml up -d
```

### MQTT Connection Issues

```bash
# Check if mosquitto is accepting connections (with auth)
docker exec paku_mosquitto mosquitto_sub -u "$MQTT_USER" -P "$MQTT_PASSWORD" -t "#" -v -C 1

# Check mosquitto logs for auth failures
docker compose -f compose/stack.prod.yaml logs mosquitto | grep -i "denied\|auth"
```

## Costs

Estimated Hetzner Cloud costs (as of 2024):

- **CX11**: ~€4.51/month (1 vCPU, 2 GB RAM, 20 GB SSD)
- **CX21**: ~€5.83/month (2 vCPU, 4 GB RAM, 40 GB SSD)

Plus optional costs for:
- Floating IP: ~€4/month
- Snapshots/Backups: varies by size
