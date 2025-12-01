# EcoFlow Dashboard Layout

## Visual Layout Reference

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    🔌 EcoFlow Power Station Overview                        │
│                                                                             │
│  Device: [R331ZEB4ZEA0012345 ▼]    ⏰ Last 6 hours    🔄 Refresh: 30s     │
└─────────────────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────────────────┐
│ ROW 1: CURRENT STATUS                                                        │
├──────────────────┬──────────────────┬──────────────────┬────────────────────┤
│  🔋 Battery      │  ⚡ Power        │  🔌 Power        │  ⏱️ Remaining     │
│     Level        │     Output       │     Input        │     Time          │
│                  │                  │                  │                   │
│      85%         │     300W         │     120W         │    407 min        │
│   ━━━━━━━━━━    │   ━━━━━━━━━━    │   ━━━━━━━━━━    │                   │
│   [Sparkline]    │   [Sparkline]    │   [Sparkline]    │                   │
│   🟢 Green       │   🟡 Yellow      │   🟢 Green       │   🟢 Green        │
└──────────────────┴──────────────────┴──────────────────┴────────────────────┘

┌──────────────────────────────────────────────────────────────────────────────┐
│ ROW 2: POWER TRENDS                                                          │
├───────────────────────────────────────┬──────────────────────────────────────┤
│  📊 Battery State of Charge (%)       │  📈 Power Flow (Input/Output)       │
│                                       │                                      │
│  100┤                                 │  500┤                                │
│   80┤     ╱───────╲                  │  400┤  ╱─────Input─────╲            │
│   60┤    ╱         ╲                 │  300┤ ╱                 ╲           │
│   40┤   ╱           ╲──╲             │  200┤                    ╲──Output  │
│   20┤  ╱                ╲            │  100┤                              │
│    0└─────────────────────────       │    0└───────────────────────────── │
│      10:00   12:00   14:00   16:00   │      10:00   12:00   14:00   16:00 │
│      [Color gradient: Red→Green]     │      [Green=Input, Red=Output]     │
└───────────────────────────────────────┴──────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────────────────┐
│ ROW 3: DETAILED ANALYSIS                                                     │
├───────────────────────────────────────┬──────────────────────────────────────┤
│  ☀️ Solar (PV) Input (W)              │  🔌 Output Ports Breakdown (W)      │
│                                       │                                      │
│  200┤        ╱‾‾‾‾╲                  │  400┤                                │
│  150┤      ╱        ╲                │  300┤  ═══ AC Output                │
│  100┤    ╱            ╲              │  200┤  ─── DC Output                │
│   50┤  ╱                ╲            │  100┤  ··· USB-C                    │
│    0└─────────────────────────       │   50┤  ─·─ USB-A                    │
│      10:00   12:00   14:00   16:00   │    0└───────────────────────────── │
│      [Yellow line]                   │      10:00   12:00   14:00   16:00 │
└───────────────────────────────────────┴──────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────────────────┐
│ ROW 4: SUMMARY AND DETAILS                                                   │
├──────────────────────┬─────────────────────┬──────────────────────────────────┤
│  🎯 Current Power    │  📊 Energy Stats    │  📋 Recent Measurements         │
│     Output Gauge     │  (Last Hour)        │                                 │
│                      │                     │ Time    Bat% In   Out  Remain   │
│        ╱─────╲       │ Avg Output: 280W    │ 16:00   85  120  300   407     │
│      ╱   300W  ╲     │ Peak Output: 450W   │ 15:59   84  125  310   395     │
│     │  ═══════   │   │ Avg Input: 115W     │ 15:58   84  120  305   398     │
│      ╲         ╱     │                     │ 15:57   83  110  320   380     │
│        ╰─────╯       │                     │ 15:56   83  100  315   375     │
│    0  1k  2k  3.6k   │                     │ ...                             │
│    [Green→Yellow→Red]│                     │ [Color-coded battery %]         │
└──────────────────────┴─────────────────────┴──────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────────────────┐
│ ROW 5: ADVANCED ANALYSIS (FULL WIDTH)                                       │
├──────────────────────────────────────────────────────────────────────────────┤
│  🔄 Net Power Flow (Charging/Discharging) (W)                               │
│                                                                              │
│  200┤        ╱‾‾‾‾╲    Charging ⚡                                          │
│  100┤      ╱        ╲                                                       │
│    0┼────────────────────────────────────── Balanced                        │
│ -100┤                    ╲                                                  │
│ -200┤                      ╲____╱  Discharging 🔋                          │
│ -300┤                            ╲                                          │
│      └──────────────────────────────────────                                │
│        10:00      12:00      14:00      16:00                               │
│      [Green fill above 0, Red fill below 0, Gradient]                      │
└──────────────────────────────────────────────────────────────────────────────┘
```

## Panel Grid Layout

Dashboard uses 24-column grid system:

### Row 1 (Height: 6)
- Battery Level: x=0, w=6
- Power Output: x=6, w=6
- Power Input: x=12, w=6
- Remaining Time: x=18, w=6

### Row 2 (Height: 9)
- Battery SoC: x=0, w=12
- Power Flow: x=12, w=12

### Row 3 (Height: 8)
- Solar Input: x=0, w=12
- Ports Breakdown: x=12, w=12

### Row 4 (Height: 8)
- Power Gauge: x=0, w=8
- Energy Stats: x=8, w=8
- Recent Table: x=16, w=8

### Row 5 (Height: 8)
- Net Power Flow: x=0, w=24 (full width)

## Color Schemes

### Battery Level
```
  0% ━━━━━━━ 20% ━━━━━━━ 50% ━━━━━━━ 80% ━━━━━━━ 100%
  🔴  Red     🟠 Orange   🟡 Yellow   🟢  Green
  Critical   Low         Medium      Good
```

### Power Output
```
  0W ━━━━━ 1000W ━━━━━ 2000W ━━━━━ 3000W ━━━━━ 3600W
  🟢 Green  🟡 Yellow   🟠 Orange   🔴  Red
  Light     Medium      Heavy       Very Heavy
```

### Net Power Flow
```
  -3000W ━━━━━ -1000W ━━━━━ 0W ━━━━━ +100W
  🔴   Red      🟠 Orange    🟡 Yellow  🟢 Green
  Heavy Drain  Draining     Balanced   Charging
```

## Panel Types Used

| Panel Type | Count | Used For |
|------------|-------|----------|
| Stat | 4 | Current values (battery, power, time) |
| Time Series | 6 | Historical trends (charts) |
| Gauge | 1 | Visual power meter |
| Table | 1 | Recent measurements list |

## Responsive Behavior

The dashboard is designed for desktop viewing (1920x1080+). For smaller screens:

**1080p Display (1920x1080):**
- All panels visible without scrolling
- Optimal viewing experience

**Laptop (1366x768):**
- Vertical scrolling required
- Panels maintain readability

**Tablet (768x1024):**
- Portrait mode recommended
- Panels stack vertically
- Touch-friendly controls

**Mobile (375x667):**
- Use Grafana mobile app for better experience
- Or access via mobile browser in landscape
- Consider creating mobile-specific dashboard

## Keyboard Shortcuts

When viewing dashboard:
- `d` + `k`: Open keyboard shortcuts help
- `Esc`: Exit panel full screen
- `r`: Refresh dashboard
- `t` + `s`: Star/unstar dashboard
- `Ctrl/Cmd + S`: Save dashboard (if editing)

## Panel Interactions

### Hover Tooltips
```
┌─────────────────────┐
│ 14:30:15           │
│ Battery: 85%       │
│ ───────────────    │
│ Value: 85          │
└─────────────────────┘
```

### Legend Toggle
```
Battery SoC ⚫ ON
Power Out   ⚪ OFF  ← Click to toggle
Solar Input ⚫ ON
```

### Zoom Interaction
```
Click + Drag → Zoom in
Double Click → Reset zoom
```

## Dashboard Variables

### Device Selector
```
┌──────────────────────────────┐
│ Device: ▼                    │
├──────────────────────────────┤
│ R331ZEB4ZEA0012345          │
│ R331ZEB4ZEA0067890          │
│ R331ZEB4ZEA0111213          │
└──────────────────────────────┘
```

All panels update when device changes.

## Panel Refresh Behavior

```
Dashboard Refresh (30s)
         ↓
    ┌─────────────────┐
    │ All SQL queries │
    │  re-executed    │
    └─────────────────┘
         ↓
    ┌─────────────────┐
    │  Panels update  │
    │   with new data │
    └─────────────────┘
```

## Database Query Patterns

### Pattern 1: Latest Value
```sql
SELECT metric FROM table 
WHERE device = '$device_sn' 
ORDER BY ts DESC LIMIT 1
```
→ Used by: Stats, Gauge

### Pattern 2: Time Series
```sql
SELECT ts, metric FROM table 
WHERE device = '$device_sn' 
AND $__timeFilter(ts) 
ORDER BY ts
```
→ Used by: Line charts

### Pattern 3: Aggregation
```sql
SELECT AVG(metric), MAX(metric) 
FROM table 
WHERE device = '$device_sn' 
AND ts >= NOW() - INTERVAL '1h'
```
→ Used by: Energy stats

### Pattern 4: Recent List
```sql
SELECT * FROM table 
WHERE device = '$device_sn' 
ORDER BY ts DESC LIMIT 10
```
→ Used by: Table panel

## Performance Considerations

- **Query Optimization**: All queries use indexed columns (device_sn, ts)
- **Time Range**: Default 6 hours balances detail vs performance
- **Refresh Rate**: 30s prevents database overload
- **Row Limit**: Recent table limited to 10 rows
- **Caching**: Grafana caches query results

## Customization Examples

### Add Energy Cost Panel
```sql
SELECT 
  SUM(watts_out_sum) / 1000.0 * 0.15 AS "Cost ($)"
FROM ecoflow_measurements
WHERE device_sn = '$device_sn'
  AND ts >= NOW() - INTERVAL '24 hours'
```

### Add Temperature Panel (if available in raw_data)
```sql
SELECT
  ts AS "time",
  (raw_data->'params'->'bmsMaster'->>'temp')::float AS "Battery Temp (°C)"
FROM ecoflow_measurements
WHERE device_sn = '$device_sn'
  AND $__timeFilter(ts)
ORDER BY ts
```

### Add Efficiency Panel
```sql
SELECT
  ts AS "time",
  (watts_in_sum::float / NULLIF(watts_out_sum, 0)) * 100 AS "Efficiency %"
FROM ecoflow_measurements
WHERE device_sn = '$device_sn'
  AND $__timeFilter(ts)
  AND watts_out_sum > 0
ORDER BY ts
```

## Troubleshooting Visual Issues

### Panels Too Small
- Adjust grid height in panel settings
- Increase dashboard height in settings

### Text Cutoff
- Reduce font size in panel options
- Increase panel width
- Adjust legend placement (bottom/right/hidden)

### Overlapping Lines
- Adjust Y-axis scale (fixed min/max)
- Use different line styles (solid/dashed/dotted)
- Separate into multiple panels

### Slow Loading
- Reduce time range
- Increase refresh interval
- Add query timeout limits
- Check database performance

## Related Files

- Dashboard JSON: `stack/grafana/dashboards/ecoflow_overview.json`
- Provisioning config: `stack/grafana/provisioning/dashboards/dashboards.yml`
- Dashboard guide: `docs/ecoflow_dashboard.md`

## Legend

Symbols used in this document:
- 🔋 Battery/Power
- ⚡ Electricity/Energy
- 🔌 Outlets/Connections
- ⏱️ Time/Duration
- 📊 Charts/Statistics
- 📈 Trends/Growth
- ☀️ Solar/PV
- 🎯 Target/Goal
- 📋 List/Table
- 🔄 Cycle/Flow
