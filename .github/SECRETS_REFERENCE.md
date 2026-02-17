# GitHub Secrets Reference

This document lists all GitHub secrets required for the workflows in this repository.

## Deployment Workflow (deploy.yaml)

Used for automated deployment to Hetzner server.

| Secret Name | Description | Required |
|-------------|-------------|----------|
| `HETZNER_SSH_KEY` | Private SSH key for server access | ✅ Yes |
| `HETZNER_HOST` | Server hostname or IP address | ✅ Yes |
| `POSTGRES_PASSWORD` | PostgreSQL database password | ✅ Yes |
| `GF_SECURITY_ADMIN_PASSWORD` | Grafana admin password | ✅ Yes |
| `MQTT_USER` | MQTT broker username (port 8883 TLS listener, default: `edge`) | ✅ Yes |
| `MQTT_PASSWORD` | MQTT broker password | ✅ Yes |
| `MQTT_CN` | Hostname/IP for MQTT TLS certificate SAN | ⚠️ Optional (default: `paku-mqtt`) |
| `PAKU_DOMAIN` | Domain for Caddy auto-TLS (e.g. `paku.example.com`) | ⚠️ Optional (default: `:80`) |
| `OTA_API_KEY` | API key for OTA admin endpoints | ✅ Yes |
| `ECOFLOW_ACCESS_KEY` | EcoFlow API access key | ⚠️ Optional |
| `ECOFLOW_SECRET_KEY` | EcoFlow API secret key | ⚠️ Optional |
| `ECOFLOW_DEVICE_SN` | EcoFlow device serial number | ⚠️ Optional |
| `ECOFLOW_API_URL` | EcoFlow API URL | ⚠️ Optional |

## OTA Update Workflow (ota-update-esp.yaml)

Used for automated firmware updates to ESP devices.

| Secret Name | Description | Required | Example |
|-------------|-------------|----------|---------|
| `OTA_SERVICE_URL` | URL of OTA service | ✅ Yes | `https://your-server.com:8080` |
| `OTA_API_KEY` | API key for OTA admin endpoints | ✅ Yes | Same as `OTA_API_KEY` in compose/.env |
| `WIFI_SSIDS` | WiFi SSIDs as JSON array | ✅ Yes | `["MyWifi", "Hotspot"]` |
| `WIFI_PASSWORDS` | WiFi passwords as JSON array | ✅ Yes | `["pass1", "pass2"]` |
| `MQTT_SERVER` | Cloud MQTT broker hostname | ✅ Yes | `mqtt.example.com` |
| `MQTT_USER` | Cloud MQTT username | ✅ Yes | `edge` |
| `MQTT_PASSWORD` | Cloud MQTT password | ✅ Yes | *(your password)* |
| `MQTT_LOCAL` | Local RPi/HA MQTT hostname | ⚠️ Optional | `homeassistant.local` (default) |
| `PAKU_CORE_REPO` | Full path to paku-core repository | ⚠️ Optional* | `ychefla/paku-core` |
| `PAKU_CORE_TOKEN` | GitHub token for private paku-core | ⚠️ Optional** | Personal Access Token |

**MQTT broker mapping in firmware:**
- `MQTT_LOCAL` → primary broker (`MQTT_SERVER` define, tried first)
- `MQTT_SERVER` → fallback broker (`MQTT_FALLBACK_SERVER` define, cloud with TLS)
- `MQTT_USER` / `MQTT_PASSWORD` → fallback broker credentials

\* Required if paku-core is in a different organization or has a different name  
\*\* Required only if paku-core repository is private

## Setting Up Secrets

### Via GitHub Web Interface

1. Go to your repository on GitHub
2. Navigate to **Settings** → **Secrets and variables** → **Actions**
3. Click **New repository secret**
4. Enter the **Name** and **Value**
5. Click **Add secret**

### Via GitHub CLI

```bash
# Set a secret
gh secret set SECRET_NAME

# Set from a file
gh secret set SECRET_NAME < secret.txt

# List all secrets
gh secret list
```

## Generating Secrets

### OTA_API_KEY

Generate a strong random API key:

```bash
# Option 1: Using OpenSSL
openssl rand -hex 32

# Option 2: Using Python
python3 -c "import secrets; print(secrets.token_hex(32))"

# Option 3: Using /dev/urandom
head -c 32 /dev/urandom | base64
```

Make sure to use the **same value** in:
1. GitHub Secrets: `OTA_API_KEY`
2. Server: `compose/.env` → `OTA_API_KEY=...`

### SSH Key (HETZNER_SSH_KEY)

Generate SSH key pair if you don't have one:

```bash
ssh-keygen -t ed25519 -C "github-actions" -f ~/.ssh/github_deploy

# Copy public key to server
ssh-copy-id -i ~/.ssh/github_deploy.pub user@server

# Use private key as secret
cat ~/.ssh/github_deploy
# Copy entire output including -----BEGIN and -----END lines
```

### GitHub Personal Access Token (PAKU_CORE_TOKEN)

If paku-core is private:

1. Go to GitHub → **Settings** → **Developer settings** → **Personal access tokens** → **Tokens (classic)**
2. Click **Generate new token (classic)**
3. Give it a descriptive name: "OTA Workflow - paku-core access"
4. Select scopes: `repo` (Full control of private repositories)
5. Click **Generate token**
6. Copy the token immediately (you won't see it again)

## Security Best Practices

1. **Never commit secrets to Git**
   - All secrets should be in GitHub Secrets or `.env` files (git-ignored)
   - Review commits before pushing

2. **Rotate secrets regularly**
   - Change passwords and API keys every 90 days
   - Update in both GitHub Secrets and production server

3. **Use minimum required permissions**
   - SSH keys: Read-only where possible
   - API keys: Scope to specific actions only
   - Personal Access Tokens: Minimum required scopes

4. **Monitor secret usage**
   - Review workflow runs for unauthorized access
   - Check server logs for API key usage
   - Enable alerts for failed authentication attempts

5. **Backup secret metadata**
   - Keep encrypted list of secret names and where they're used
   - Document which services depend on which secrets
   - Don't store actual secret values in documentation

## Troubleshooting

### "Secret not found" error

**Problem**: Workflow fails with missing secret error

**Solution**:
1. Verify secret name matches exactly (case-sensitive)
2. Check secret is set at repository level (not environment)
3. Ensure you have admin access to the repository

### "Authentication failed" error

**Problem**: OTA workflow fails during upload/rollout

**Solution**:
1. Verify `OTA_API_KEY` matches server configuration
2. Test manually: `curl -H "X-API-Key: YOUR_KEY" http://server:8080/health`
3. Check OTA service logs: `docker logs paku_ota_service`
4. Regenerate key if compromised

### "Repository not found" error

**Problem**: Cannot checkout paku-core

**Solution**:
1. Check `PAKU_CORE_REPO` format: `owner/repo`
2. Verify `PAKU_CORE_TOKEN` has `repo` scope
3. Test token: `curl -H "Authorization: token YOUR_TOKEN" https://api.github.com/user`
4. Ensure token hasn't expired

## Related Documentation

- [OTA Workflow Guide](../docs/ota_workflow_guide.md) - How to use the OTA workflow
- [Deployment Guide](../docs/deployment.md) - Server deployment instructions
- [OTA Updates](../docs/ota_updates.md) - OTA system architecture and API
