"""
Paku OTA Service

REST API for Over-The-Air (OTA) firmware updates for ESP devices.
Provides endpoints for:
- Firmware artifact hosting and serving
- Version metadata management
- Device update status tracking
- Rollout orchestration and targeting
- Monitoring and metrics

Environment variables:
    PGHOST, PGPORT, PGUSER, PGPASSWORD, PGDATABASE
    FIRMWARE_STORAGE_PATH (default: /firmware)
    API_KEY (optional: for admin endpoints)
    PORT (default: 8080)
"""

import hashlib
import json
import logging
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import aiofiles
import psycopg
import uvicorn
from fastapi import FastAPI, HTTPException, Header, UploadFile, File, Query, Depends, Request
from fastapi.responses import FileResponse, JSONResponse
from fastapi.exceptions import RequestValidationError
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings


# ---------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------
class Settings(BaseSettings):
    # Database
    pghost: str = "postgres"
    pgport: int = 5432
    pguser: str
    pgpassword: str
    pgdatabase: str
    
    # Storage
    firmware_storage_path: str = "/firmware"
    
    # API Security
    api_key: Optional[str] = None
    
    # Server
    port: int = 8080
    host: str = "0.0.0.0"
    
    class Config:
        env_file = ".env"
        case_sensitive = False


settings = Settings()

# ---------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
    stream=sys.stdout,
)
logger = logging.getLogger("ota-service")

# ---------------------------------------------------------------------
# FastAPI App
# ---------------------------------------------------------------------
app = FastAPI(
    title="Paku OTA Service",
    description="Firmware update orchestration for ESP devices",
    version="1.0.0",
)

# ---------------------------------------------------------------------
# Exception Handlers
# ---------------------------------------------------------------------
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Handle validation errors with detailed logging."""
    logger.error(f"Validation error for {request.method} {request.url}")
    logger.error(f"Headers: {dict(request.headers)}")
    logger.error(f"Query params: {dict(request.query_params)}")
    logger.error(f"Validation errors: {exc.errors()}")
    return JSONResponse(
        status_code=422,
        content={
            "detail": exc.errors(),
            "body": str(exc.body) if hasattr(exc, 'body') else None
        }
    )

@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Log all incoming requests."""
    logger.info(f"Request: {request.method} {request.url}")
    logger.debug(f"Headers: {dict(request.headers)}")
    logger.debug(f"Query params: {dict(request.query_params)}")
    response = await call_next(request)
    logger.info(f"Response status: {response.status_code}")
    return response

# ---------------------------------------------------------------------
# Database Connection
# ---------------------------------------------------------------------
def get_db_connection() -> psycopg.Connection:
    """Get database connection."""
    return psycopg.connect(
        host=settings.pghost,
        port=settings.pgport,
        user=settings.pguser,
        password=settings.pgpassword,
        dbname=settings.pgdatabase,
        autocommit=True,
    )


# ---------------------------------------------------------------------
# Security
# ---------------------------------------------------------------------
def verify_api_key(x_api_key: Optional[str] = Header(None)) -> bool:
    """Verify API key for admin endpoints (optional)."""
    if settings.api_key and x_api_key != settings.api_key:
        raise HTTPException(status_code=401, detail="Invalid API key")
    return True


# ---------------------------------------------------------------------
# Data Models
# ---------------------------------------------------------------------
class FirmwareMetadata(BaseModel):
    version: str
    device_model: str
    min_version: Optional[str] = None
    file_size: int
    checksum_sha256: str
    changelog: Optional[str] = None
    release_notes: Optional[str] = None
    is_signed: bool = False
    created_at: Optional[datetime] = None


class DeviceInfo(BaseModel):
    device_id: str
    device_model: str
    current_firmware_version: Optional[str] = None


class UpdateStatus(BaseModel):
    device_id: str
    firmware_version: str
    status: str = Field(..., pattern="^(pending|downloading|downloaded|installing|success|failed|rolled_back)$")
    error_message: Optional[str] = None
    progress_percent: Optional[int] = Field(None, ge=0, le=100)


class RolloutConfig(BaseModel):
    name: str
    firmware_version: str
    device_model: str
    target_type: str = Field(..., pattern="^(all|group|canary|specific)$")
    target_filter: Optional[Dict[str, Any]] = None
    rollout_percentage: int = Field(100, ge=0, le=100)
    is_active: bool = True


class FirmwareCheckResponse(BaseModel):
    update_available: bool
    current_version: Optional[str] = None
    latest_version: Optional[str] = None
    download_url: Optional[str] = None
    file_size: Optional[int] = None
    checksum_sha256: Optional[str] = None
    release_notes: Optional[str] = None


# ---------------------------------------------------------------------
# API Endpoints - Device Facing
# ---------------------------------------------------------------------
@app.get("/api/firmware/check", response_model=FirmwareCheckResponse)
async def check_firmware_update(
    device_id: str = Query(..., description="Unique device identifier"),
    device_model: str = Query(..., description="Device model identifier"),
    current_version: str = Query(..., description="Current firmware version"),
):
    """
    Check if a firmware update is available for a device.
    
    This endpoint is called by ESP devices to check for OTA updates.
    Considers active rollout configurations and device eligibility.
    """
    logger.info(f"Firmware check: device={device_id}, model={device_model}, version={current_version}")
    
    try:
        conn = get_db_connection()
        
        # Register/update device info
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO devices (device_id, device_model, current_firmware_version, last_seen)
                VALUES (%(device_id)s, %(device_model)s, %(current_version)s, NOW())
                ON CONFLICT (device_id) 
                DO UPDATE SET 
                    current_firmware_version = %(current_version)s,
                    last_seen = NOW()
            """, {
                "device_id": device_id,
                "device_model": device_model,
                "current_version": current_version,
            })
        
        # Find latest firmware for this device model
        with conn.cursor() as cur:
            cur.execute("""
                SELECT version, file_path, file_size, checksum_sha256, release_notes
                FROM firmware_releases
                WHERE device_model = %(device_model)s
                ORDER BY created_at DESC
                LIMIT 1
            """, {"device_model": device_model})
            
            row = cur.fetchone()
            if not row:
                return FirmwareCheckResponse(
                    update_available=False,
                    current_version=current_version,
                )
            
            latest_version, file_path, file_size, checksum, release_notes = row
        
        # Check if update is needed
        if latest_version == current_version:
            return FirmwareCheckResponse(
                update_available=False,
                current_version=current_version,
                latest_version=latest_version,
            )
        
        # Check rollout configuration to see if this device is eligible
        with conn.cursor() as cur:
            cur.execute("""
                SELECT id, target_type, target_filter, rollout_percentage
                FROM rollout_configurations
                WHERE firmware_version = %(version)s
                  AND device_model = %(device_model)s
                  AND is_active = true
                ORDER BY created_at DESC
                LIMIT 1
            """, {
                "version": latest_version,
                "device_model": device_model,
            })
            
            rollout = cur.fetchone()
            
            # If no active rollout, don't offer update
            if not rollout:
                logger.info(f"No active rollout for {device_model} v{latest_version}")
                return FirmwareCheckResponse(
                    update_available=False,
                    current_version=current_version,
                    latest_version=latest_version,
                )
            
            rollout_id, target_type, target_filter, rollout_percentage = rollout
            
            # Check device eligibility based on rollout rules
            eligible = _check_device_eligibility(
                device_id, target_type, target_filter, rollout_percentage
            )
            
            if not eligible:
                logger.info(f"Device {device_id} not eligible for rollout")
                return FirmwareCheckResponse(
                    update_available=False,
                    current_version=current_version,
                    latest_version=latest_version,
                )
        
        # Log update event
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO ota_events (event_type, device_id, firmware_version, event_data)
                VALUES ('update_started', %(device_id)s, %(version)s, %(data)s)
            """, {
                "device_id": device_id,
                "version": latest_version,
                "data": json.dumps({"from_version": current_version}),
            })
        
        conn.close()
        
        return FirmwareCheckResponse(
            update_available=True,
            current_version=current_version,
            latest_version=latest_version,
            download_url=f"/api/firmware/download/{latest_version}",
            file_size=file_size,
            checksum_sha256=checksum,
            release_notes=release_notes,
        )
        
    except Exception as e:
        logger.exception(f"Error checking firmware update: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@app.get("/api/firmware/download/{version}")
async def download_firmware(version: str):
    """
    Download firmware binary by version.
    
    Serves the firmware file for OTA update.
    """
    logger.info(f"Firmware download request: version={version}")
    
    try:
        conn = get_db_connection()
        
        with conn.cursor() as cur:
            cur.execute("""
                SELECT file_path, file_size, checksum_sha256
                FROM firmware_releases
                WHERE version = %(version)s
            """, {"version": version})
            
            row = cur.fetchone()
            if not row:
                raise HTTPException(status_code=404, detail="Firmware version not found")
            
            file_path, file_size, checksum = row
        
        conn.close()
        
        # Serve firmware file
        full_path = Path(settings.firmware_storage_path) / file_path
        if not full_path.exists():
            logger.error(f"Firmware file not found: {full_path}")
            raise HTTPException(status_code=404, detail="Firmware file not found")
        
        return FileResponse(
            path=str(full_path),
            media_type="application/octet-stream",
            filename=file_path,
            headers={
                "X-Firmware-Version": version,
                "X-Checksum-SHA256": checksum,
                "Content-Length": str(file_size),
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Error downloading firmware: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@app.post("/api/device/{device_id}/update-status")
async def report_update_status(device_id: str, status: UpdateStatus):
    """
    Report device update status.
    
    Devices call this endpoint to report OTA update progress and results.
    """
    logger.info(f"Update status from {device_id}: {status.status} ({status.progress_percent}%)")
    
    try:
        conn = get_db_connection()
        
        with conn.cursor() as cur:
            # Insert status update
            cur.execute("""
                INSERT INTO device_update_status (
                    device_id, firmware_version, status, error_message,
                    progress_percent, started_at, completed_at
                )
                VALUES (
                    %(device_id)s, %(firmware_version)s, %(status)s,
                    %(error_message)s, %(progress_percent)s,
                    CASE WHEN %(status)s = 'downloading' THEN NOW() ELSE NULL END,
                    CASE WHEN %(status)s IN ('success', 'failed') THEN NOW() ELSE NULL END
                )
            """, {
                "device_id": device_id,
                "firmware_version": status.firmware_version,
                "status": status.status,
                "error_message": status.error_message,
                "progress_percent": status.progress_percent,
            })
            
            # Update device current version on success
            if status.status == "success":
                cur.execute("""
                    UPDATE devices
                    SET current_firmware_version = %(version)s, last_seen = NOW()
                    WHERE device_id = %(device_id)s
                """, {
                    "version": status.firmware_version,
                    "device_id": device_id,
                })
                
                # Log completion event
                cur.execute("""
                    INSERT INTO ota_events (event_type, device_id, firmware_version)
                    VALUES ('update_completed', %(device_id)s, %(version)s)
                """, {
                    "device_id": device_id,
                    "version": status.firmware_version,
                })
            
            # Log failure event
            elif status.status == "failed":
                cur.execute("""
                    INSERT INTO ota_events (event_type, device_id, firmware_version, event_data)
                    VALUES ('update_failed', %(device_id)s, %(version)s, %(data)s)
                """, {
                    "device_id": device_id,
                    "version": status.firmware_version,
                    "data": json.dumps({"error": status.error_message}),
                })
        
        conn.close()
        
        return {"status": "ok", "message": "Status reported successfully"}
        
    except Exception as e:
        logger.exception(f"Error reporting update status: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


# ---------------------------------------------------------------------
# API Endpoints - Admin/Management
# ---------------------------------------------------------------------
@app.post("/api/admin/firmware/upload")
async def upload_firmware(
    file: UploadFile = File(...),
    version: str = Query(...),
    device_model: str = Query(...),
    min_version: Optional[str] = Query(None),
    changelog: Optional[str] = Query(None),
    release_notes: Optional[str] = Query(None),
    is_signed: bool = Query(False),
    _: bool = Depends(verify_api_key),
):
    """
    Upload a new firmware release.
    
    Admin endpoint for uploading firmware artifacts and metadata.
    Requires API key authentication.
    """
    logger.info(f"Firmware upload: version={version}, model={device_model}")
    
    try:
        # Create firmware storage directory if not exists
        storage_path = Path(settings.firmware_storage_path)
        storage_path.mkdir(parents=True, exist_ok=True)
        
        # Save firmware file
        file_name = f"{device_model}_{version}.bin"
        file_path = storage_path / file_name
        
        # Calculate checksum while saving
        sha256_hash = hashlib.sha256()
        file_size = 0
        
        async with aiofiles.open(file_path, 'wb') as f:
            while chunk := await file.read(8192):
                await f.write(chunk)
                sha256_hash.update(chunk)
                file_size += len(chunk)
        
        checksum = sha256_hash.hexdigest()
        
        # Store metadata in database
        conn = get_db_connection()
        
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO firmware_releases (
                    version, device_model, min_version, file_path,
                    file_size, checksum_sha256, changelog, release_notes,
                    is_signed, created_by
                )
                VALUES (
                    %(version)s, %(device_model)s, %(min_version)s,
                    %(file_path)s, %(file_size)s, %(checksum)s,
                    %(changelog)s, %(release_notes)s, %(is_signed)s,
                    'admin'
                )
            """, {
                "version": version,
                "device_model": device_model,
                "min_version": min_version,
                "file_path": file_name,
                "file_size": file_size,
                "checksum": checksum,
                "changelog": changelog,
                "release_notes": release_notes,
                "is_signed": is_signed,
            })
            
            # Log upload event
            cur.execute("""
                INSERT INTO ota_events (event_type, firmware_version, event_data)
                VALUES ('firmware_uploaded', %(version)s, %(data)s)
            """, {
                "version": version,
                "data": json.dumps({
                    "device_model": device_model,
                    "file_size": file_size,
                    "checksum": checksum,
                }),
            })
        
        conn.close()
        
        return {
            "status": "ok",
            "message": "Firmware uploaded successfully",
            "version": version,
            "file_size": file_size,
            "checksum_sha256": checksum,
        }
        
    except Exception as e:
        logger.exception(f"Error uploading firmware: {e}")
        # Clean up file on error
        if file_path.exists():
            file_path.unlink()
        raise HTTPException(status_code=500, detail="Internal server error")


@app.get("/api/admin/firmware/releases")
async def list_firmware_releases(
    device_model: Optional[str] = Query(None),
    limit: int = Query(10, ge=1, le=100),
):
    """
    List firmware releases.
    
    Admin endpoint to view firmware release history.
    """
    try:
        conn = get_db_connection()
        
        with conn.cursor() as cur:
            if device_model:
                cur.execute("""
                    SELECT version, device_model, file_size, checksum_sha256,
                           is_signed, created_at, release_notes
                    FROM firmware_releases
                    WHERE device_model = %(device_model)s
                    ORDER BY created_at DESC
                    LIMIT %(limit)s
                """, {"device_model": device_model, "limit": limit})
            else:
                cur.execute("""
                    SELECT version, device_model, file_size, checksum_sha256,
                           is_signed, created_at, release_notes
                    FROM firmware_releases
                    ORDER BY created_at DESC
                    LIMIT %(limit)s
                """, {"limit": limit})
            
            releases = []
            for row in cur.fetchall():
                releases.append({
                    "version": row[0],
                    "device_model": row[1],
                    "file_size": row[2],
                    "checksum_sha256": row[3],
                    "is_signed": row[4],
                    "created_at": row[5].isoformat() if row[5] else None,
                    "release_notes": row[6],
                })
        
        conn.close()
        
        return {"releases": releases}
        
    except Exception as e:
        logger.exception(f"Error listing firmware releases: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@app.post("/api/admin/rollout/create")
async def create_rollout(
    rollout: RolloutConfig,
    _: bool = Depends(verify_api_key),
):
    """
    Create a new rollout configuration.
    
    Admin endpoint to define firmware rollout rules and targeting.
    """
    logger.info(f"Creating rollout: {rollout.name} for {rollout.firmware_version}")
    
    try:
        conn = get_db_connection()
        
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO rollout_configurations (
                    name, firmware_version, device_model, target_type,
                    target_filter, rollout_percentage, is_active, created_by
                )
                VALUES (
                    %(name)s, %(firmware_version)s, %(device_model)s,
                    %(target_type)s, %(target_filter)s, %(rollout_percentage)s,
                    %(is_active)s, 'admin'
                )
            """, {
                "name": rollout.name,
                "firmware_version": rollout.firmware_version,
                "device_model": rollout.device_model,
                "target_type": rollout.target_type,
                "target_filter": json.dumps(rollout.target_filter) if rollout.target_filter else None,
                "rollout_percentage": rollout.rollout_percentage,
                "is_active": rollout.is_active,
            })
            
            # Log rollout creation
            cur.execute("""
                INSERT INTO ota_events (event_type, firmware_version, event_data)
                VALUES ('rollout_created', %(version)s, %(data)s)
            """, {
                "version": rollout.firmware_version,
                "data": json.dumps({
                    "name": rollout.name,
                    "target_type": rollout.target_type,
                    "rollout_percentage": rollout.rollout_percentage,
                }),
            })
        
        conn.close()
        
        return {"status": "ok", "message": "Rollout created successfully"}
        
    except Exception as e:
        logger.exception(f"Error creating rollout: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@app.get("/api/admin/devices")
async def list_devices(
    device_model: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=500),
):
    """
    List registered devices.
    
    Admin endpoint to view device inventory and firmware status.
    """
    try:
        conn = get_db_connection()
        
        with conn.cursor() as cur:
            if device_model:
                cur.execute("""
                    SELECT device_id, device_model, current_firmware_version,
                           last_seen, created_at
                    FROM devices
                    WHERE device_model = %(device_model)s
                    ORDER BY last_seen DESC
                    LIMIT %(limit)s
                """, {"device_model": device_model, "limit": limit})
            else:
                cur.execute("""
                    SELECT device_id, device_model, current_firmware_version,
                           last_seen, created_at
                    FROM devices
                    ORDER BY last_seen DESC
                    LIMIT %(limit)s
                """, {"limit": limit})
            
            devices = []
            for row in cur.fetchall():
                devices.append({
                    "device_id": row[0],
                    "device_model": row[1],
                    "current_firmware_version": row[2],
                    "last_seen": row[3].isoformat() if row[3] else None,
                    "created_at": row[4].isoformat() if row[4] else None,
                })
        
        conn.close()
        
        return {"devices": devices}
        
    except Exception as e:
        logger.exception(f"Error listing devices: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@app.get("/api/admin/update-status")
async def get_update_status(
    device_id: Optional[str] = Query(None),
    firmware_version: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=500),
):
    """
    Get device update status history.
    
    Admin endpoint to monitor OTA update progress and results.
    """
    try:
        conn = get_db_connection()
        
        with conn.cursor() as cur:
            query = """
                SELECT device_id, firmware_version, status, error_message,
                       progress_percent, started_at, completed_at, reported_at
                FROM device_update_status
                WHERE 1=1
            """
            params = {"limit": limit}
            
            if device_id:
                query += " AND device_id = %(device_id)s"
                params["device_id"] = device_id
            
            if firmware_version:
                query += " AND firmware_version = %(firmware_version)s"
                params["firmware_version"] = firmware_version
            
            query += " ORDER BY reported_at DESC LIMIT %(limit)s"
            
            cur.execute(query, params)
            
            updates = []
            for row in cur.fetchall():
                updates.append({
                    "device_id": row[0],
                    "firmware_version": row[1],
                    "status": row[2],
                    "error_message": row[3],
                    "progress_percent": row[4],
                    "started_at": row[5].isoformat() if row[5] else None,
                    "completed_at": row[6].isoformat() if row[6] else None,
                    "reported_at": row[7].isoformat() if row[7] else None,
                })
        
        conn.close()
        
        return {"updates": updates}
        
    except Exception as e:
        logger.exception(f"Error getting update status: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


# ---------------------------------------------------------------------
# Health & Metrics
# ---------------------------------------------------------------------
@app.get("/health")
async def health_check():
    """Health check endpoint."""
    try:
        conn = get_db_connection()
        conn.close()
        return {"status": "healthy"}
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        raise HTTPException(status_code=503, detail="Service unavailable")


@app.get("/metrics")
async def get_metrics():
    """
    Get OTA metrics for monitoring.
    
    Returns statistics on firmware versions, updates, and device status.
    """
    try:
        conn = get_db_connection()
        
        metrics = {}
        
        # Total devices
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM devices")
            metrics["total_devices"] = cur.fetchone()[0]
        
        # Devices by model
        with conn.cursor() as cur:
            cur.execute("""
                SELECT device_model, COUNT(*)
                FROM devices
                GROUP BY device_model
            """)
            metrics["devices_by_model"] = {row[0]: row[1] for row in cur.fetchall()}
        
        # Recent updates (last 24h)
        with conn.cursor() as cur:
            cur.execute("""
                SELECT status, COUNT(*)
                FROM device_update_status
                WHERE reported_at > NOW() - INTERVAL '24 hours'
                GROUP BY status
            """)
            metrics["recent_updates_24h"] = {row[0]: row[1] for row in cur.fetchall()}
        
        # Active rollouts
        with conn.cursor() as cur:
            cur.execute("""
                SELECT COUNT(*)
                FROM rollout_configurations
                WHERE is_active = true
            """)
            metrics["active_rollouts"] = cur.fetchone()[0]
        
        conn.close()
        
        return metrics
        
    except Exception as e:
        logger.exception(f"Error getting metrics: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


# ---------------------------------------------------------------------
# Helper Functions
# ---------------------------------------------------------------------
def _check_device_eligibility(
    device_id: str,
    target_type: str,
    target_filter: Optional[str],
    rollout_percentage: int,
) -> bool:
    """
    Check if a device is eligible for update based on rollout rules.
    
    Args:
        device_id: Device identifier
        target_type: Targeting strategy (all, group, canary, specific)
        target_filter: JSON filter criteria
        rollout_percentage: Percentage of devices to target
    
    Returns:
        True if device is eligible, False otherwise
    """
    # All devices
    if target_type == "all":
        return _percentage_match(device_id, rollout_percentage)
    
    # Specific devices
    if target_type == "specific":
        if not target_filter:
            return False
        try:
            filter_dict = json.loads(target_filter) if isinstance(target_filter, str) else target_filter
            device_ids = filter_dict.get("device_ids", [])
            return device_id in device_ids
        except:
            return False
    
    # Canary rollout (percentage-based)
    if target_type == "canary":
        return _percentage_match(device_id, rollout_percentage)
    
    # Group-based targeting
    if target_type == "group":
        # TODO: Implement group membership check
        # This would query device metadata for group assignments
        return _percentage_match(device_id, rollout_percentage)
    
    return False


def _percentage_match(device_id: str, percentage: int) -> bool:
    """
    Determine if device matches percentage criteria using consistent hashing.
    
    Uses SHA-256 for consistent hashing to ensure secure, deterministic device selection
    for percentage-based rollouts. The same device will always get the same result for
    the same percentage, enabling gradual rollout increases.
    
    Args:
        device_id: Device identifier
        percentage: Target percentage (0-100)
    
    Returns:
        True if device falls within percentage, False otherwise
    """
    if percentage >= 100:
        return True
    if percentage <= 0:
        return False
    
    # Use SHA-256 for secure consistent hashing
    hash_value = int(hashlib.sha256(device_id.encode()).hexdigest(), 16)
    return (hash_value % 100) < percentage


# ---------------------------------------------------------------------
# Entry Point
# ---------------------------------------------------------------------
if __name__ == "__main__":
    logger.info(f"Starting OTA service on {settings.host}:{settings.port}")
    uvicorn.run(
        "ota_service:app",
        host=settings.host,
        port=settings.port,
        log_level="info",
    )
