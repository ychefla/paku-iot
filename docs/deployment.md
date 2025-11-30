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

# Allow Grafana (or consider using a reverse proxy)
ufw allow 3000/tcp

# Allow MQTT (if devices connect directly)
ufw allow 1883/tcp

# Enable firewall
ufw enable
```

**Note**: In production, consider using a reverse proxy (Caddy/Nginx) with HTTPS instead of exposing ports directly.

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
```

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

```bash
# Create backup
docker exec paku_postgres pg_dump -U paku paku > backup_$(date +%Y%m%d).sql

# Restore backup
cat backup_20240101.sql | docker exec -i paku_postgres psql -U paku paku
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

Access Grafana at `http://<server-ip>:3000`

**Production recommendation**: Set up a reverse proxy with HTTPS using Caddy or Nginx.

## Security Considerations

1. **Strong Passwords**: Always use strong, unique passwords in production
2. **Firewall**: Limit exposed ports to only what's necessary
3. **HTTPS**: Use a reverse proxy with TLS certificates for web interfaces
4. **MQTT Security**: Consider enabling authentication and TLS for MQTT
5. **Updates**: Keep the server and Docker images updated
6. **Backups**: Implement regular database backups

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

### MQTT Connection Issues

```bash
# Check if mosquitto is listening
docker exec -it paku_mosquitto mosquitto_sub -t "#" -v
```

## Costs

Estimated Hetzner Cloud costs (as of 2024):

- **CX11**: ~€4.51/month (1 vCPU, 2 GB RAM, 20 GB SSD)
- **CX21**: ~€5.83/month (2 vCPU, 4 GB RAM, 40 GB SSD)

Plus optional costs for:
- Floating IP: ~€4/month
- Snapshots/Backups: varies by size
