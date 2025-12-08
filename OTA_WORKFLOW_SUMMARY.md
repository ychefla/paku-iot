# OTA Workflow Implementation Summary

**Implementation Date**: December 8, 2025

## Overview

Created a GitHub Actions workflow for automated ESP device firmware updates via the OTA service. The workflow is **separate** from the existing auto-deployment workflow (`deploy.yaml`) and is **manually triggered** only when you want to update ESP device firmware.

## Files Created

### 1. Workflow File
**`.github/workflows/ota-update-esp.yaml`**

A complete GitHub Actions workflow that:
- ✅ Checks out the `paku-core` repository (main branch)
- ✅ Builds firmware using PlatformIO
- ✅ Calculates SHA-256 checksums
- ✅ Uploads firmware to OTA service
- ✅ Creates rollout configuration
- ✅ Generates deployment summary with details
- ✅ Provides helpful error messages on failure

### 2. Documentation
**`docs/ota_workflow_guide.md`** (11KB)

Comprehensive guide covering:
- Prerequisites and required secrets
- Step-by-step usage instructions
- Rollout strategy explanations (test, canary, full)
- Monitoring and troubleshooting
- Security best practices
- Advanced usage scenarios
- Integration examples

### 3. Secrets Reference
**`.github/SECRETS_REFERENCE.md`**

Reference document listing:
- All required GitHub secrets
- Secret generation instructions
- Security best practices
- Troubleshooting common issues

### 4. README Updates
**`README.md`** (Modified)

Added section on automated OTA updates via GitHub Actions, including:
- Link to workflow guide
- Quick overview of features
- Setup requirements

## Workflow Features

### Input Parameters

The workflow accepts these inputs when triggered:

1. **Rollout Strategy** (Required)
   - `test` - Deploy to specific test devices
   - `canary-10` - Deploy to 10% of fleet
   - `canary-25` - Deploy to 25% of fleet
   - `canary-50` - Deploy to 50% of fleet
   - `full` - Deploy to all devices

2. **Device Model** (Required)
   - Default: `esp32`
   - Must match PlatformIO environment

3. **Test Devices** (Optional)
   - Comma-separated device IDs for test rollouts
   - Example: `esp32_001, esp32_002, esp32_lab`

4. **Release Notes** (Optional)
   - Description of firmware changes
   - Stored in OTA service metadata

### Workflow Steps

1. **Checkout paku-core**: Gets latest code from paku-core main branch
2. **Setup Python**: Installs Python 3.11 for PlatformIO
3. **Cache PlatformIO**: Speeds up builds with caching
4. **Build Firmware**: Compiles firmware for specified device model
5. **Generate Version**: Creates version string from commit + timestamp
6. **Upload to OTA**: Sends firmware binary to OTA service
7. **Create Rollout**: Configures rollout based on strategy
8. **Generate Summary**: Creates deployment report with all details

### Automatic Version Numbering

Versions are auto-generated using:
- Git commit hash (short, 7 characters)
- Timestamp (YYYYMMDD-HHMMSS)

Example: `a1b2c3d-20251208-153045`

This ensures every build has a unique, traceable version number.

## Required GitHub Secrets

### Mandatory
1. **`OTA_SERVICE_URL`**
   - URL of your OTA service
   - Example: `https://your-server.com:8080` or `http://server-ip:8080`
   
2. **`OTA_API_KEY`**
   - API key for OTA admin endpoints
   - Must match the `OTA_API_KEY` in server's `compose/.env`
   - Generate with: `openssl rand -hex 32`

### Optional
3. **`PAKU_CORE_REPO`**
   - Full repository path (e.g., `ychefla/paku-core`)
   - Only needed if different from default or in different org

4. **`PAKU_CORE_TOKEN`**
   - GitHub Personal Access Token
   - Only needed if paku-core is private
   - Requires `repo` scope

## Usage Example

### Test Deployment

1. Go to GitHub → Actions → "OTA Update ESP Devices"
2. Click "Run workflow"
3. Configure:
   - **Rollout Strategy**: `test`
   - **Device Model**: `esp32`
   - **Test Devices**: `esp32_dev001, esp32_dev002`
   - **Release Notes**: `Testing new WiFi reconnection logic`
4. Click "Run workflow"

### Progressive Canary Rollout

**Phase 1 - 10%**:
- Strategy: `canary-10`
- Monitor for 24-48 hours

**Phase 2 - 25%**:
- Strategy: `canary-25`
- Monitor for 24-48 hours

**Phase 3 - 50%**:
- Strategy: `canary-50`
- Monitor for 24-48 hours

**Phase 4 - Full**:
- Strategy: `full`
- Complete rollout

### Full Production Deployment

1. After testing with `test` or `canary-10`:
2. Configure:
   - **Rollout Strategy**: `full`
   - **Device Model**: `esp32`
   - **Release Notes**: `v2.0.0: New features and improvements`
3. Monitor in Grafana dashboard

## Monitoring Updates

### During Workflow Execution

Watch in GitHub Actions:
- Build progress and logs
- Upload status
- Rollout creation confirmation
- Deployment summary

### After Deployment

Monitor device updates:
- **Grafana**: OTA Monitoring dashboard
- **Metrics API**: `http://your-server:8080/metrics`
- **Service Logs**: `docker logs paku_ota_service`
- **Admin API**: List update status and devices

## Security Features

1. **API Key Authentication**: Admin endpoints require `X-API-Key` header
2. **Secure Secrets**: All credentials stored in GitHub Secrets
3. **Checksum Verification**: SHA-256 checksums for firmware integrity
4. **Audit Logging**: All actions logged in OTA service
5. **Access Control**: Workflow requires repository access to trigger

## Separation from Auto-Deploy

This workflow is **completely separate** from the existing `deploy.yaml`:

| Feature | deploy.yaml | ota-update-esp.yaml |
|---------|-------------|---------------------|
| **Purpose** | Deploy backend services | Update ESP firmware |
| **Trigger** | Auto on main push | Manual only |
| **Repository** | paku-iot | paku-core |
| **Target** | Hetzner server | ESP devices (via OTA service) |
| **Secrets** | HETZNER_*, POSTGRES_*, etc. | OTA_SERVICE_URL, OTA_API_KEY |

They can run independently without interfering with each other.

## Integration with paku-core

The workflow is designed to work with the `paku-core` repository structure:

### Expected Structure
```
paku-core/
├── platformio.ini       # PlatformIO configuration
├── src/                 # Source code
└── .pio/build/         # Build output (auto-generated)
    └── esp32/
        └── firmware.bin # Built firmware
```

### PlatformIO Configuration

Your `platformio.ini` should have environments matching device models:

```ini
[env:esp32]
platform = espressif32
board = esp32dev
framework = arduino

[env:esp8266]
platform = espressif8266
board = nodemcuv2
framework = arduino
```

## Troubleshooting

### Build Fails

**Problem**: PlatformIO build fails

**Solutions**:
- Verify `platformio.ini` exists in paku-core
- Check device model matches environment name
- Test build locally: `pio run -e esp32`
- Review build logs in GitHub Actions

### Upload Fails

**Problem**: Cannot upload to OTA service

**Solutions**:
- Verify `OTA_SERVICE_URL` is accessible from GitHub
- Check `OTA_API_KEY` matches server configuration
- Test manually: `curl http://server:8080/health`
- Check server firewall rules

### Rollout Creation Fails

**Problem**: Rollout creation fails

**Solutions**:
- Ensure firmware uploaded successfully (previous step)
- Verify test_devices provided for `test` strategy
- Check OTA service logs: `docker logs paku_ota_service`
- Test API manually with curl

### Devices Not Updating

**Problem**: Devices don't receive updates

**Solutions**:
- Verify devices are online and checking for updates
- Check device model matches rollout configuration
- Ensure rollout is active in OTA service
- Review device logs for errors
- Verify network connectivity from devices

## Next Steps

1. **Configure Secrets** in GitHub:
   ```bash
   gh secret set OTA_SERVICE_URL
   gh secret set OTA_API_KEY
   ```

2. **Test Workflow** with test devices:
   - Use `test` strategy with known device IDs
   - Verify firmware builds and uploads
   - Monitor device update in Grafana

3. **Production Rollout** after successful testing:
   - Start with `canary-10`
   - Monitor for 24-48 hours
   - Gradually increase percentage
   - Complete with `full` deployment

4. **Monitor and Iterate**:
   - Review update success rates
   - Identify and fix issues
   - Update documentation with learnings

## Benefits

1. ✅ **Zero Manual Steps**: Just click and run
2. ✅ **Automatic Builds**: Always builds latest paku-core main
3. ✅ **Version Tracking**: Every build has unique version
4. ✅ **Safe Rollouts**: Progressive deployment strategies
5. ✅ **Full Audit Trail**: Complete logging and monitoring
6. ✅ **Error Handling**: Clear error messages and summaries
7. ✅ **Separation**: Doesn't interfere with backend deployments

## Files Modified/Created Summary

### New Files (3)
1. `.github/workflows/ota-update-esp.yaml` - Main workflow (268 lines)
2. `docs/ota_workflow_guide.md` - Complete guide (430 lines)
3. `.github/SECRETS_REFERENCE.md` - Secrets reference (180 lines)

### Modified Files (1)
1. `README.md` - Added OTA workflow section

### Total Lines Added
- Workflow: 268 lines
- Documentation: 610 lines
- **Total: 878 lines of new content**

## Conclusion

The OTA workflow provides a production-ready, automated solution for ESP device firmware updates. It requires minimal configuration (just two secrets), works independently of the backend deployment, and supports safe, progressive rollout strategies. The comprehensive documentation ensures team members can use it effectively without deep technical knowledge of the OTA system internals.
