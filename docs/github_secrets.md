# GitHub Secrets Configuration

This document describes the GitHub repository secrets required for automated deployment.

## Required Secrets

These secrets must be configured in your GitHub repository settings: **Settings → Secrets and variables → Actions → New repository secret**

### Core Infrastructure Secrets

| Secret Name | Description | Example |
|-------------|-------------|---------|
| `HETZNER_HOST` | SSH hostname or IP of your Hetzner VM | `static.107.192.27.37.clients.your-server.de` |
| `HETZNER_SSH_KEY` | Private SSH key for authentication | Contents of your private key file |
| `POSTGRES_PASSWORD` | PostgreSQL database password | Strong random password |
| `GF_SECURITY_ADMIN_PASSWORD` | Grafana admin password | Strong random password |

### Optional: EcoFlow Collector Secrets

These are **optional** - only needed if you want to collect EcoFlow power station data:

| Secret Name | Description | Where to Get It |
|-------------|-------------|-----------------|
| `ECOFLOW_ACCESS_KEY` | EcoFlow Developer API access key | [EcoFlow Developer Portal](https://developer.ecoflow.com/) |
| `ECOFLOW_SECRET_KEY` | EcoFlow Developer API secret key | [EcoFlow Developer Portal](https://developer.ecoflow.com/) |
| `ECOFLOW_DEVICE_SN` | Device serial number (optional) | EcoFlow app → Device Settings → About |

## How to Add Secrets

1. Go to your GitHub repository
2. Click **Settings** → **Secrets and variables** → **Actions**
3. Click **New repository secret**
4. Enter the **Name** (e.g., `ECOFLOW_ACCESS_KEY`)
5. Paste the **Value**
6. Click **Add secret**
7. Repeat for each secret

## EcoFlow Setup (Optional)

If you want to enable EcoFlow data collection:

### Step 1: Get EcoFlow API Credentials

1. Visit [EcoFlow Developer Portal](https://developer.ecoflow.com/)
2. Sign up / Log in
3. Create a new application
4. Copy your **Access Key** and **Secret Key**

### Step 2: Add to GitHub Secrets

Add these three secrets to your repository:
- `ECOFLOW_ACCESS_KEY` - Your access key from step 1
- `ECOFLOW_SECRET_KEY` - Your secret key from step 1
- `ECOFLOW_DEVICE_SN` - (Optional) Your device serial number

### Step 3: Deploy

The next deployment to the `main` branch will automatically:
- Detect the EcoFlow credentials
- Build the EcoFlow collector
- Start it with the `--profile ecoflow` flag
- Begin collecting power station data

## How the Workflow Uses Secrets

### Without EcoFlow Secrets

```bash
# Deployment script checks for credentials
if [ -n "${ECOFLOW_ACCESS_KEY}" ] && [ -n "${ECOFLOW_SECRET_KEY}" ]; then
  # EcoFlow enabled
else
  # EcoFlow disabled - normal deployment
  docker compose -f compose/stack.prod.yaml up -d
fi
```

Result: Only core services (Postgres, Grafana, Collector, Mosquitto) are deployed.

### With EcoFlow Secrets

```bash
# Credentials found - enable ecoflow profile
docker compose --profile ecoflow -f compose/stack.prod.yaml up -d
```

Result: All services including EcoFlow collector are deployed.

## Verifying Deployment

After pushing to `main`, check the GitHub Actions workflow:

1. Go to **Actions** tab in your repository
2. Click on the latest workflow run
3. Expand the **Deploy to server** step
4. Look for:
   ```
   EcoFlow credentials found - starting with ecoflow profile...
   ```
   or
   ```
   No EcoFlow credentials - starting without ecoflow profile...
   ```

## Security Notes

- **Never commit secrets to the repository** - always use GitHub Secrets
- Secrets are **encrypted** and only exposed to GitHub Actions runners
- Secrets are **not visible** in workflow logs
- Use **strong passwords** for all credentials
- Rotate secrets **periodically**

## Troubleshooting

### EcoFlow collector not starting

Check:
1. Are all three secrets set? (ACCESS_KEY, SECRET_KEY are required; DEVICE_SN is optional)
2. Are the credentials valid? Test locally with `test_config.py`
3. Check deployment logs for "EcoFlow credentials found" message
4. SSH to server and check: `docker logs paku_ecoflow_collector`

### Authentication errors after deployment

The workflow automatically updates the PostgreSQL password if secrets change. If you still have issues:

```bash
# SSH to server
ssh paku@your-server

# Check .env file has correct credentials
cat /home/paku/paku-iot/compose/.env

# Restart services
cd /home/paku/paku-iot
docker compose -f compose/stack.prod.yaml down
docker compose --profile ecoflow -f compose/stack.prod.yaml up -d
```

## Related Documentation

- [ECOFLOW_QUICKSTART.md](../ECOFLOW_QUICKSTART.md) - Quick start guide for EcoFlow
- [ECOFLOW_FIX_SUMMARY.md](../ECOFLOW_FIX_SUMMARY.md) - Recent fixes and changes
- [deployment.md](deployment.md) - General deployment documentation
- [ecoflow_integration.md](ecoflow_integration.md) - Detailed EcoFlow integration guide
