-- Reprocess EcoFlow raw_data to extract power values that were missed
-- This script updates existing rows by parsing the raw_data JSONB field

-- Update watts_in_sum from various possible fields
UPDATE ecoflow_measurements
SET watts_in_sum = COALESCE(
    (raw_data->'params'->>'pd.wattsInSum')::numeric,
    (raw_data->'params'->>'pd.chgPowerAc')::numeric,
    (raw_data->'params'->>'bmsMaster.inputWatts')::numeric,
    (raw_data->'params'->>'inv.inputWatts')::numeric
)
WHERE watts_in_sum IS NULL 
  AND raw_data IS NOT NULL
  AND (
    raw_data->'params' ? 'pd.wattsInSum' OR
    raw_data->'params' ? 'pd.chgPowerAc' OR
    raw_data->'params' ? 'bmsMaster.inputWatts' OR
    raw_data->'params' ? 'inv.inputWatts'
  );

-- Update watts_out_sum from various possible fields
UPDATE ecoflow_measurements
SET watts_out_sum = COALESCE(
    (raw_data->'params'->>'pd.wattsOutSum')::numeric,
    (raw_data->'params'->>'pd.dsgPowerAc')::numeric,
    (raw_data->'params'->>'bmsMaster.outputWatts')::numeric,
    (raw_data->'params'->>'inv.outputWatts')::numeric
)
WHERE watts_out_sum IS NULL 
  AND raw_data IS NOT NULL
  AND (
    raw_data->'params' ? 'pd.wattsOutSum' OR
    raw_data->'params' ? 'pd.dsgPowerAc' OR
    raw_data->'params' ? 'bmsMaster.outputWatts' OR
    raw_data->'params' ? 'inv.outputWatts'
  );

-- Update soc_percent from pd.soc if bmsMaster.soc not available
UPDATE ecoflow_measurements
SET soc_percent = (raw_data->'params'->>'pd.soc')::int
WHERE soc_percent IS NULL 
  AND raw_data IS NOT NULL
  AND raw_data->'params' ? 'pd.soc';

-- Update remain_time_min
UPDATE ecoflow_measurements
SET remain_time_min = COALESCE(
    (raw_data->'params'->>'pd.remainTime')::int,
    (raw_data->'params'->>'bmsMaster.remainTime')::int,
    (raw_data->'params'->>'ems.chgRemainTime')::int
)
WHERE remain_time_min IS NULL 
  AND raw_data IS NOT NULL
  AND (
    raw_data->'params' ? 'pd.remainTime' OR
    raw_data->'params' ? 'bmsMaster.remainTime' OR
    raw_data->'params' ? 'ems.chgRemainTime'
  );

-- Update ac_out_watts
UPDATE ecoflow_measurements
SET ac_out_watts = COALESCE(
    (raw_data->'params'->>'inv.outputWatts')::numeric,
    (raw_data->'params'->>'inv.acOutWatts')::numeric
)
WHERE ac_out_watts IS NULL 
  AND raw_data IS NOT NULL
  AND (
    raw_data->'params' ? 'inv.outputWatts' OR
    raw_data->'params' ? 'inv.acOutWatts'
  );

-- Update dc_out_watts from car port
UPDATE ecoflow_measurements
SET dc_out_watts = COALESCE(
    (raw_data->'params'->>'mppt.carOutWatts')::numeric,
    (raw_data->'params'->>'mppt.outWatts')::numeric,
    (raw_data->'params'->>'pd.dcOutWatts')::numeric
)
WHERE dc_out_watts IS NULL 
  AND raw_data IS NOT NULL
  AND (
    raw_data->'params' ? 'mppt.carOutWatts' OR
    raw_data->'params' ? 'mppt.outWatts' OR
    raw_data->'params' ? 'pd.dcOutWatts'
  );

-- Update USB-C watts
UPDATE ecoflow_measurements
SET typec_out_watts = COALESCE(
    (raw_data->'params'->>'pd.typec1Watts')::numeric + 
    COALESCE((raw_data->'params'->>'pd.typec2Watts')::numeric, 0),
    0
)
WHERE typec_out_watts IS NULL 
  AND raw_data IS NOT NULL
  AND (raw_data->'params' ? 'pd.typec1Watts' OR raw_data->'params' ? 'pd.typec2Watts')
  AND ((raw_data->'params'->>'pd.typec1Watts')::numeric > 0 
       OR (raw_data->'params'->>'pd.typec2Watts')::numeric > 0);

-- Update USB-A watts
UPDATE ecoflow_measurements
SET usb_out_watts = COALESCE(
    (raw_data->'params'->>'pd.usb1Watts')::numeric + 
    COALESCE((raw_data->'params'->>'pd.usb2Watts')::numeric, 0) +
    COALESCE((raw_data->'params'->>'pd.qcUsb1Watts')::numeric, 0) +
    COALESCE((raw_data->'params'->>'pd.qcUsb2Watts')::numeric, 0),
    0
)
WHERE usb_out_watts IS NULL 
  AND raw_data IS NOT NULL
  AND (raw_data->'params' ? 'pd.usb1Watts' OR raw_data->'params' ? 'pd.usb2Watts' 
       OR raw_data->'params' ? 'pd.qcUsb1Watts' OR raw_data->'params' ? 'pd.qcUsb2Watts')
  AND ((raw_data->'params'->>'pd.usb1Watts')::numeric > 0 
       OR (raw_data->'params'->>'pd.usb2Watts')::numeric > 0
       OR (raw_data->'params'->>'pd.qcUsb1Watts')::numeric > 0
       OR (raw_data->'params'->>'pd.qcUsb2Watts')::numeric > 0);

-- Update solar/PV input watts
UPDATE ecoflow_measurements
SET pv_in_watts = COALESCE(
    (raw_data->'params'->>'mppt.inWatts')::numeric,
    (raw_data->'params'->>'mppt.pv1InputWatts')::numeric,
    (raw_data->'params'->>'pd.chgSunPower')::numeric
)
WHERE pv_in_watts IS NULL 
  AND raw_data IS NOT NULL
  AND (
    raw_data->'params' ? 'mppt.inWatts' OR
    raw_data->'params' ? 'mppt.pv1InputWatts' OR
    raw_data->'params' ? 'pd.chgSunPower'
  );

-- Show summary of updated rows
SELECT 
  'Updated watts_in_sum' as field,
  COUNT(*) as count 
FROM ecoflow_measurements 
WHERE watts_in_sum IS NOT NULL
UNION ALL
SELECT 
  'Updated watts_out_sum' as field,
  COUNT(*) as count 
FROM ecoflow_measurements 
WHERE watts_out_sum IS NOT NULL
UNION ALL
SELECT 
  'Updated soc_percent' as field,
  COUNT(*) as count 
FROM ecoflow_measurements 
WHERE soc_percent IS NOT NULL
UNION ALL
SELECT 
  'Total measurements' as field,
  COUNT(*) as count 
FROM ecoflow_measurements;
