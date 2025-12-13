> **📜 HISTORICAL DOCUMENT**
>
> This document represents a snapshot from a specific point in time and may not reflect the current state of the system.
> For current documentation, see [README.md](../README.md) and [docs/](../docs/).

---

# EcoFlow Data Collection Summary

## Data Status

The EcoFlow collector is successfully collecting data and storing it in the database. As of the last check:

### Available Data Fields

| Field | Records (last 24h) | Min | Max | Avg | Notes |
|-------|-------------------|-----|-----|-----|-------|
| **State of Charge (SOC)** | 886 | 89% | 89% | 89% | Battery level - stable |
| **Output Power** | 1,044 | 0W | 26W | 0.6W | Mostly idle, occasional 24-26W loads |
| **Input Power** | 1,044 | 0W | 0W | 0W | Not charging (AC or solar) |
| **Remaining Time** | 300 | 6,938 min | 7,904 min | 7,375 min | ~5 days at current usage |
| **USB-C Output** | 8 | 1W | 1W | 1W | Minimal USB-C usage detected |

### Data Collection Details

**Collection Rate:** ~30 seconds between measurements

**Device:** Delta Pro (SN: DCEBZ8ZE2110138)

**Data Source:** EcoFlow Cloud MQTT stream

**Database:** PostgreSQL table `ecoflow_measurements`

## Dashboard Metrics

The Grafana dashboard displays:

1. **Current Status**
   - Battery SOC: 89%
   - Output Power: 0-26W (varies)
   - Input Power: 0W (not charging)
   - Estimated Runtime: ~5 days

2. **Time Series Charts**
   - Battery level over time (flat at 89%)
   - Power in/out over time (mostly flat at 0W with occasional spikes to 24-26W)
   - Solar input (no data - no solar connected)

3. **Statistics**
   - Average output: 0.6W
   - Peak output: 26W
   - No charging activity detected

## Raw Data Fields Available

The collector captures over 200+ individual data points in the `raw_data` JSONB field, including:

- Battery management: temp, voltage, current, cycles, health
- Power delivery: All ports (AC, DC, USB-A, USB-C)
- Charging: AC, solar, car
- System: temperatures, fan state, error codes
- Configuration: charge limits, standby settings

## Notes

- Device is currently idle (89% charge, minimal load)
- No active charging (AC or solar)
- Small loads detected (~24-26W) periodically - likely internal systems or small connected devices
- USB-C port shows minimal 1W usage
- System is healthy with ~5 days of runtime at current usage

## Recent Fix (2025-12-06)

Fixed data extraction to properly parse `pd.*` (Power Delivery) fields from the EcoFlow MQTT stream. Previously, the collector was only looking for `inv.*` (inverter) fields, but the actual power data is in:

- `pd.wattsInSum` / `pd.chgPowerAc` - Input power
- `pd.wattsOutSum` / `pd.dsgPowerAc` - Output power
- `pd.soc` - State of charge
- `pd.remainTime` - Runtime estimate

Applied reprocessing script to extract power data from existing 2,932 measurements in database.
