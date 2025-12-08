# ESP OTA Update Workflow Guide

This guide explains how to use the GitHub Actions workflow for automated OTA (Over-The-Air) firmware updates to ESP devices.

## Overview

The OTA update workflow (`ota-update-esp.yaml`) automates the process of:
1. Building firmware from the `paku-core` repository
2. Uploading firmware to the OTA service
3. Creating rollout configurations
4. Deploying updates to ESP devices

This workflow is **separate** from the main `paku-iot` deployment workflow and is manually triggered only when you want to update ESP device firmware.

## Prerequisites

### Required GitHub Secrets

Configure the following secrets in your GitHub repository settings (Settings → Secrets and variables → Actions):

| Secret Name | Description | Example |
|-------------|-------------|---------|
| `OTA_SERVICE_URL` | URL of your OTA service | `https://your-server.com:8080` or `http://your-server-ip:8080` |
| `OTA_API_KEY` | API key for OTA service admin endpoints | The value from your `.env` file's `OTA_API_KEY` |
| `PAKU_CORE_REPO` | (Optional) Full repository path for paku-core | `ychefla/paku-core` or `yourusername/paku-core` |
| `PAKU_CORE_TOKEN` | (Optional) GitHub token if paku-core is private | Personal Access Token with repo access |

### OTA Service Requirements

Ensure your OTA service is:
- Running and accessible from GitHub Actions (public IP or proper networking)
- Configured with `OTA_API_KEY` in the environment
- PostgreSQL database is initialized with OTA schema

You can verify the OTA service is accessible:
```bash
curl http://your-server:8080/health
```

## Using the Workflow

### 1. Navigate to GitHub Actions

1. Go to your `paku-iot` repository on GitHub
2. Click on the "Actions" tab
3. Select "OTA Update ESP Devices" from the workflows list
4. Click "Run workflow" button

### 2. Configure Workflow Parameters

The workflow requires the following inputs:

#### **Rollout Strategy** (Required)
Choose how to deploy the update:

- **`test`**: Deploy to specific test devices only
  - Requires: `test_devices` parameter with comma-separated device IDs
  - Use for: Initial testing on known devices
  - Example test devices: `esp32_001, esp32_002, esp32_test`

- **`canary-10`**: Deploy to 10% of devices (canary rollout)
  - Uses consistent hashing to select devices
  - Use for: Initial production rollout validation

- **`canary-25`**: Deploy to 25% of devices
  - Use for: Expanding rollout after 10% succeeds

- **`canary-50`**: Deploy to 50% of devices
  - Use for: Expanding rollout after 25% succeeds

- **`full`**: Deploy to all devices of the model
  - Use for: Final rollout after validation
  - ⚠️ Use with caution in production

#### **Device Model** (Required)
The device model/environment to build for:
- Examples: `esp32`, `esp8266`, `esp32-c3`, `esp32-s3`
- Must match an environment in your `platformio.ini`
- Default: `esp32`

#### **Test Devices** (Optional, required for `test` strategy)
Comma-separated list of device IDs for test rollout:
- Example: `esp32_001, esp32_test, esp32_lab`
- Only used when rollout strategy is `test`

#### **Release Notes** (Optional)
Description of the changes in this firmware update:
- Will be stored in the firmware release metadata
- Visible in OTA monitoring dashboard
- Default: "Automated OTA update from paku-core main branch"

### 3. Example Workflows

#### Test Deployment
1. **Rollout Strategy**: `test`
2. **Device Model**: `esp32`
3. **Test Devices**: `esp32_dev001, esp32_dev002`
4. **Release Notes**: `Testing new WiFi reconnection logic`

#### Canary Rollout (Progressive)
**Phase 1:**
1. **Rollout Strategy**: `canary-10`
2. **Device Model**: `esp32`
3. **Release Notes**: `Production release: Fixed memory leak, improved stability`

Monitor for 24-48 hours, then proceed to Phase 2.

**Phase 2:**
1. **Rollout Strategy**: `canary-25`
2. **Device Model**: `esp32`

Monitor, then Phase 3.

**Phase 3:**
1. **Rollout Strategy**: `canary-50`
2. **Device Model**: `esp32`

Monitor, then Phase 4.

**Phase 4:**
1. **Rollout Strategy**: `full`
2. **Device Model**: `esp32`

#### Full Deployment (After Testing)
1. **Rollout Strategy**: `full`
2. **Device Model**: `esp32`
3. **Release Notes**: `v2.0.0: New features - temperature monitoring, battery optimization`

## Monitoring Updates

### Viewing Progress

After triggering the workflow:

1. **GitHub Actions**: Watch the workflow execution in real-time
   - Build logs
   - Upload status
   - Rollout creation confirmation

2. **Grafana Dashboard**: Monitor device updates
   - Navigate to your Grafana instance
   - Open the "OTA Monitoring" dashboard
   - View:
     - Update success rate
     - Device update status
     - Failed updates with error messages
     - Firmware version distribution

3. **OTA Service Metrics**: Check raw metrics
   ```bash
   curl http://your-server:8080/metrics
   ```

4. **Admin API**: List update status
   ```bash
   curl http://your-server:8080/api/admin/update-status \
     -H "X-API-Key: your-api-key"
   ```

### Success Indicators

A successful deployment shows:
- ✅ GitHub workflow completes successfully
- ✅ Firmware uploaded to OTA service
- ✅ Rollout configuration created
- ✅ Devices begin checking for updates
- ✅ Devices report "success" status
- ✅ Success rate increases in Grafana

### Handling Failures

If devices fail to update:

1. **Check device logs**: Look for error messages
2. **Review Grafana**: Identify failure patterns
3. **Deactivate rollout** if needed:
   ```bash
   curl -X POST "http://your-server:8080/api/admin/rollout/{rollout_id}/deactivate" \
     -H "X-API-Key: your-api-key"
   ```
4. **Investigate issues**: Check firmware compatibility, network issues, etc.

## Workflow Architecture

```
┌─────────────────────┐
│  GitHub Actions     │
│  (ota-update-esp)   │
└──────────┬──────────┘
           │
           ├─ 1. Checkout paku-core
           ├─ 2. Build firmware (PlatformIO)
           ├─ 3. Calculate checksum
           │
           ▼
┌─────────────────────┐
│   OTA Service       │
│   (Your Server)     │
└──────────┬──────────┘
           │
           ├─ Upload firmware binary
           ├─ Create rollout config
           │
           ▼
┌─────────────────────┐
│  ESP Devices        │
│  (In the field)     │
└─────────────────────┘
           │
           ├─ Check for updates
           ├─ Download firmware
           ├─ Install & reboot
           └─ Report status
```

## Version Numbering

The workflow automatically generates version numbers using:
- Git commit hash (short, 7 characters)
- Timestamp (YYYYMMDD-HHMMSS)

Example: `a1b2c3d-20251208-153045`

To use semantic versioning (v1.0.0), you can:
1. Tag commits in paku-core: `git tag v1.0.0`
2. Modify the workflow to use tag-based versioning

## Security Best Practices

1. **Keep OTA_API_KEY secret**: Never commit or expose it
2. **Use HTTPS**: Configure TLS/SSL for OTA service in production
3. **Sign firmware**: Enable firmware signing for production
4. **Limit access**: Restrict who can trigger the workflow
5. **Monitor rollouts**: Always watch initial deployments carefully
6. **Test first**: Always use `test` or `canary-10` strategy initially

## Troubleshooting

### Workflow Fails at Build Step

**Problem**: PlatformIO build fails

**Solutions**:
- Check `platformio.ini` exists in paku-core
- Verify device model matches environment name
- Check paku-core code compiles locally
- Review build logs for specific errors

### Workflow Fails at Upload Step

**Problem**: Cannot upload firmware to OTA service

**Solutions**:
- Verify `OTA_SERVICE_URL` is correct and accessible
- Check `OTA_API_KEY` matches server configuration
- Ensure OTA service is running: `docker ps | grep ota`
- Test connectivity: `curl http://your-server:8080/health`
- Check firewall rules allow port 8080

### Workflow Fails at Rollout Creation

**Problem**: Rollout creation fails

**Solutions**:
- Check firmware was uploaded successfully (previous step)
- Verify test_devices are provided for `test` strategy
- Ensure device_model is correct
- Review OTA service logs: `docker logs paku_ota_service`

### Devices Not Updating

**Problem**: Rollout created but devices not updating

**Solutions**:
- Verify devices are online and checking for updates
- Check device model matches rollout configuration
- Ensure devices are running OTA-capable firmware
- Review device logs for update check errors
- Check network connectivity from devices to OTA service
- Verify rollout is active: `curl http://your-server:8080/api/admin/rollout/releases`

### Builds Wrong Architecture

**Problem**: Firmware builds but wrong for device

**Solutions**:
- Verify `device_model` parameter matches device type
- Check `platformio.ini` has correct board configuration
- Ensure paku-core is up to date with correct platform settings

## Advanced Usage

### Custom Version Numbers

To use custom version numbers instead of auto-generated ones:

1. Modify the workflow file (`.github/workflows/ota-update-esp.yaml`)
2. Change the "Generate version from commit" step:
   ```yaml
   - name: Generate version from commit
     run: |
       VERSION="v1.2.3"  # Or get from tag/file
       echo "VERSION=$VERSION" >> $GITHUB_ENV
   ```

### Multiple Device Models

To deploy to multiple device models in one workflow:

1. Duplicate the build steps for each model
2. Or run the workflow multiple times with different `device_model` values
3. Or modify workflow to use matrix strategy

### Scheduled Updates

To automatically deploy updates on schedule:

1. Add to workflow trigger:
   ```yaml
   on:
     schedule:
       - cron: '0 2 * * 0'  # Weekly on Sunday at 2 AM
     workflow_dispatch:
       # ... existing inputs
   ```

### Integration with paku-core CI

To trigger OTA deployment automatically when paku-core is updated:

1. In paku-core repository, add workflow:
   ```yaml
   on:
     push:
       branches: [main]
   jobs:
     trigger-ota:
       runs-on: ubuntu-latest
       steps:
         - uses: actions/github-script@v7
           with:
             github-token: ${{ secrets.PAT_TOKEN }}
             script: |
               await github.rest.actions.createWorkflowDispatch({
                 owner: 'yourusername',
                 repo: 'paku-iot',
                 workflow_id: 'ota-update-esp.yaml',
                 ref: 'main',
                 inputs: {
                   rollout_strategy: 'canary-10',
                   device_model: 'esp32',
                   release_notes: 'Auto-deployed from paku-core commit'
                 }
               });
   ```

## Related Documentation

- [OTA Updates Guide](./ota_updates.md) - Complete OTA system documentation
- [OTA Service README](../stack/ota-service/README.md) - Service-specific docs
- [ESP Device Integration](./ota_updates.md#device-integration) - How to add OTA to ESP firmware

## Support

For issues or questions:
1. Check this guide and main OTA documentation
2. Review workflow logs in GitHub Actions
3. Check OTA service logs: `docker logs paku_ota_service`
4. Review Grafana dashboard for device-side issues
5. Open an issue in the repository
