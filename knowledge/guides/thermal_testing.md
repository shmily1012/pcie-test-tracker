# Thermal Testing & PCIe Signal Integrity Correlation

> Temperature directly affects PCIe signal quality. This guide covers thermal testing
> specific to U.2 NVMe SSDs and how thermal events impact PCIe link health.

---

## 1. U.2 Thermal Design Points

```
Operating temperature range (typical enterprise SSD):
  Case temperature (Tc):     0°C to 70°C
  Storage temperature:       -40°C to 85°C
  
U.2 thermal path:
  NAND dies → SSD PCB → case (metal shell) → airflow
  Controller → thermal pad → heatsink → airflow

Key measurement locations:
  - Tc (case temperature): Top center of metal case
  - Controller junction temp: Via SMART log (NVMe)
  - NAND temp: Via SMART log
  - Ambient: At JBOF intake
```

---

## 2. Temperature vs PCIe Signal Quality

### 2.1 How Temperature Affects PCIe

| Mechanism | Effect | Temp Direction |
|-----------|--------|---------------|
| TX driver transistor characteristics | Eye height/width change | Both directions |
| RX comparator offset | Voltage margin shift | High temp |
| PLL/CDR jitter | Increased timing jitter | High temp |
| Trace insertion loss (PCB Df) | Higher loss at higher freq | High temp |
| Connector contact resistance | Slight increase | High temp |
| Equalization convergence | May need re-adaptation | Both |

### 2.2 Expected Margin Degradation

```
Typical Gen4 margin degradation from 25°C to 70°C:
  Timing margin:  -10% to -15% (relative)
  Voltage margin: -15% to -25% (relative)

Typical Gen5 PAM4 margin degradation from 25°C to 70°C:
  Timing margin:  -15% to -20% (relative)
  Voltage margin: -20% to -35% (relative)  ← PAM4 more sensitive!

If margin at 25°C is already tight, 70°C will fail.
```

---

## 3. Thermal Test Procedures

### 3.1 Static Temperature Test Matrix

| Test | Procedure | Measurements |
|------|-----------|-------------|
| Room temp (25°C) baseline | Device at 25°C, all tests | Eye diagram, lane margin, performance |
| Cold start (0°C) | Cool to 0°C in chamber, power on, boot | Link training time, initial eye, performance |
| Hot (55°C ambient) | Heat chamber to 55°C (~65-70°C case), run IO | Lane margin, AER errors, performance |
| Max Tc (70°C case) | Force case temp to 70°C via heater/chamber | Lane margin, thermal throttle behavior |
| Temperature cycling | Cycle 0°C ↔ 55°C (30 min ramp, 30 min dwell) | Continuous AER monitoring, link retrain count |

### 3.2 Procedure: Lane Margin vs Temperature

```bash
#!/bin/bash
# thermal_margin_sweep.sh
# Run at each temperature point. Record results in CSV.

BDF=$1
TEMP=$2  # Manually measured and input
OUTPUT="/tmp/margin_temp_${TEMP}C_$(date +%Y%m%d_%H%M%S).csv"

echo "Temperature,Lane,Direction,Steps,Margin_UI_or_mV" > $OUTPUT

# This is a placeholder — actual margin commands depend on:
# - Linux kernel version (sysfs interface may differ)
# - Device-specific margin capabilities
# - Or use LeCroy Protocol Analyzer margin function

echo "=== Lane Margining at ${TEMP}°C ==="
echo "Use LeCroy or platform-specific margin tool"
echo "Record timing margin (left/right) and voltage margin (up/down) per lane"
echo ""
echo "Template:"
for lane in 0 1 2 3; do
    echo "  Lane $lane:"
    echo "    Timing Left:  __ steps = __% UI"
    echo "    Timing Right: __ steps = __% UI"
    echo "    Voltage Up:   __ steps = __ mV"
    echo "    Voltage Down: __ steps = __ mV"
done

echo ""
echo "Enter results into: $OUTPUT"
```

### 3.3 Procedure: Thermal Throttle + PCIe Behavior

```bash
#!/bin/bash
# thermal_throttle_pcie.sh — Monitor PCIe during thermal throttle

BDF=$1
DEVICE="/dev/nvme0"
NS="/dev/nvme0n1"
LOG="/tmp/thermal_throttle_$(date +%Y%m%d).log"

echo "=== Thermal Throttle + PCIe Test ===" | tee $LOG
echo "Start time: $(date)" | tee -a $LOG

# Start sustained write to heat up device
echo "Starting sustained sequential write (will heat up device)..." | tee -a $LOG
fio --name=heat --filename=$NS --rw=write --bs=128k --iodepth=256 \
    --numjobs=4 --direct=1 --time_based --runtime=3600 \
    --write_bw_log=/tmp/thermal_bw --log_avg_msec=5000 \
    --output=/dev/null &
FIO_PID=$!

# Monitor loop
while kill -0 $FIO_PID 2>/dev/null; do
    TS=$(date '+%H:%M:%S')
    
    # NVMe temperature
    TEMP=$(nvme smart-log $DEVICE 2>/dev/null | grep "temperature" | head -1 | awk '{print $NF}')
    WARN=$(nvme smart-log $DEVICE 2>/dev/null | grep "critical_warning" | awk '{print $NF}')
    
    # PCIe link status
    SPEED=$(lspci -s $BDF -vvv 2>/dev/null | grep "LnkSta:" | head -1 | grep -oP "Speed \K[^\s,]+")
    WIDTH=$(lspci -s $BDF -vvv 2>/dev/null | grep "LnkSta:" | head -1 | grep -oP "Width x\K[0-9]+")
    
    # AER errors
    CE=$(cat /sys/bus/pci/devices/0000:$BDF/aer_dev_correctable 2>/dev/null | awk '{s+=$2} END{print s+0}')
    
    echo "[$TS] Temp=${TEMP}°C Warning=${WARN} Link=${SPEED}/x${WIDTH} CE=${CE}" | tee -a $LOG
    
    # Alert if temperature exceeds threshold
    if [ "${TEMP%%.*}" -gt 75 ] 2>/dev/null; then
        echo "  ⚠️  TEMPERATURE > 75°C — thermal throttle likely active" | tee -a $LOG
    fi
    
    # Alert if link changed
    if [ "$SPEED" != "$PREV_SPEED" ] 2>/dev/null && [ -n "$PREV_SPEED" ]; then
        echo "  🔴 LINK SPEED CHANGED: $PREV_SPEED → $SPEED" | tee -a $LOG
    fi
    if [ "$WIDTH" != "$PREV_WIDTH" ] 2>/dev/null && [ -n "$PREV_WIDTH" ]; then
        echo "  🔴 LINK WIDTH CHANGED: x$PREV_WIDTH → x$WIDTH" | tee -a $LOG
    fi
    
    PREV_SPEED=$SPEED
    PREV_WIDTH=$WIDTH
    
    sleep 10
done

echo "" | tee -a $LOG
echo "=== Test Complete ===" | tee -a $LOG
echo "Review: $LOG" | tee -a $LOG
echo "Bandwidth over time: /tmp/thermal_bw_bw.*.log" | tee -a $LOG
```

---

## 4. Thermal Test Matrix Template

### Fill in measured values at each temperature:

| Measurement | 0°C | 25°C | 40°C | 55°C | 70°C (Tc) |
|-------------|-----|------|------|------|-----------|
| Link Speed | | | | | |
| Link Width | | | | | |
| Seq Read BW (GB/s) | | | | | |
| Seq Write BW (GB/s) | | | | | |
| Rand Read IOPS (K) | | | | | |
| QD=1 Lat avg (μs) | | | | | |
| QD=1 Lat p99 (μs) | | | | | |
| AER CE count | | | | | |
| Lane 0 timing margin (% UI) | | | | | |
| Lane 1 timing margin (% UI) | | | | | |
| Lane 2 timing margin (% UI) | | | | | |
| Lane 3 timing margin (% UI) | | | | | |
| Lane 0 voltage margin (mV) | | | | | |
| Lane 1 voltage margin (mV) | | | | | |
| Lane 2 voltage margin (mV) | | | | | |
| Lane 3 voltage margin (mV) | | | | | |
| Controller temp (°C) | | | | | |
| NAND temp (°C) | | | | | |
| Power consumption (W) | | | | | |
| Thermal throttle active? | | | | | |

### Expected Results

```
0°C:   Performance may be slightly lower (NAND cold penalty)
       PCIe margins should be good (cooler transistors)
       
25°C:  Baseline — best overall performance + margins
       
40°C:  Performance should be near-baseline
       Margins start to decrease slightly

55°C:  Margins noticeably reduced vs 25°C
       Performance still OK if no throttle
       
70°C:  Thermal throttle may activate
       Performance may drop 20-50%
       PCIe margins at minimum — if link is stable here, it's robust
       AER CE count should still be 0
       
If AER CE > 0 at any temperature: INVESTIGATE immediately
If link speed/width changes at high temp: SI margin issue
```

---

## 5. CWDP (Composite Worst-case Data Pattern) Test

```
For PCIe Gen5, the worst-case data patterns for PAM4 are:
- Patterns that create maximum ISI (Inter-Symbol Interference)
- Patterns that stress the CDR (Clock/Data Recovery)
- Patterns with maximum peak-to-average power ratio

LeCroy can generate CWDP patterns via exerciser.
Alternatively, specific fio patterns can stress certain data paths:

- All-zeros write: Repetitive pattern → stresses CDR frequency lock
- All-ones write: Same concern
- PRBS31 (pseudo-random): Best for eye diagram measurement
- Walking ones/zeros: Stresses specific lane transitions

For U.2 cable channels specifically:
- Long runs of same symbol → loss of CDR tracking
- Rapid transitions → maximum crosstalk between lanes
```
