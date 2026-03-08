# NVMe SMART Log ↔ PCIe Health Correlation

> How to cross-reference NVMe device health with PCIe link health.
> Essential for root-cause analysis when issues span both layers.

---

## 1. Quick Health Check Script

```bash
#!/bin/bash
# nvme_pcie_health.sh — Combined NVMe + PCIe health snapshot
BDF=$1
NVME=${2:-nvme0}

echo "╔═══════════════════════════════════════════════════════╗"
echo "║  NVMe + PCIe Health Report                           ║"
echo "╠═══════════════════════════════════════════════════════╣"

# PCIe Link
echo "║ PCIe Link:"
LINK=$(lspci -s $BDF -vvv 2>/dev/null | grep "LnkSta:" | head -1)
echo "║   $LINK"

# AER
CE=$(cat /sys/bus/pci/devices/0000:$BDF/aer_dev_correctable 2>/dev/null | awk '{s+=$2} END{print s+0}')
UCE=$(cat /sys/bus/pci/devices/0000:$BDF/aer_dev_fatal 2>/dev/null | awk '{s+=$2} END{print s+0}')
echo "║   AER: CE=$CE UCE=$UCE"

# NVMe SMART
echo "║"
echo "║ NVMe SMART:"
SMART=$(nvme smart-log /dev/$NVME 2>/dev/null)
TEMP=$(echo "$SMART" | grep "^temperature" | awk -F: '{print $2}' | xargs)
CW=$(echo "$SMART" | grep "critical_warning" | awk -F: '{print $2}' | xargs)
MEDIA=$(echo "$SMART" | grep "media_errors" | awk -F: '{print $2}' | xargs)
UNSAFE=$(echo "$SMART" | grep "unsafe_shutdowns" | awk -F: '{print $2}' | xargs)
PCT=$(echo "$SMART" | grep "percent_used" | awk -F: '{print $2}' | xargs)
PH=$(echo "$SMART" | grep "power_on_hours" | awk -F: '{print $2}' | xargs)
echo "║   Temp: ${TEMP}°C"
echo "║   Critical Warning: $CW"
echo "║   Media Errors: $MEDIA"
echo "║   Unsafe Shutdowns: $UNSAFE"
echo "║   Percent Used: ${PCT}%"
echo "║   Power-on Hours: $PH"

# Correlations
echo "║"
echo "║ Health Assessment:"

ISSUES=0

if [ "$CE" -gt 0 ]; then
    echo "║   ⚠️  PCIe correctable errors present ($CE) — check SI"
    ((ISSUES++))
fi
if [ "$UCE" -gt 0 ]; then
    echo "║   🔴 PCIe UNCORRECTABLE errors ($UCE) — critical"
    ((ISSUES++))
fi
if [ "${TEMP%%.*}" -gt 70 ] 2>/dev/null; then
    echo "║   ⚠️  Temperature high (${TEMP}°C) — may affect PCIe margins"
    ((ISSUES++))
fi
if [ "$CW" != "0" ] && [ "$CW" != "0x0" ]; then
    echo "║   ⚠️  NVMe Critical Warning active ($CW)"
    ((ISSUES++))
fi
if [ "$MEDIA" -gt 0 ] 2>/dev/null; then
    echo "║   ⚠️  Media errors ($MEDIA) — check if correlated with PCIe errors"
    ((ISSUES++))
fi
if [ "$UNSAFE" -gt 10 ] 2>/dev/null; then
    echo "║   ⚠️  High unsafe shutdown count ($UNSAFE) — check PLP"
    ((ISSUES++))
fi
if [ "$ISSUES" -eq 0 ]; then
    echo "║   ✅ All healthy"
fi

echo "╚═══════════════════════════════════════════════════════╝"
```

---

## 2. Correlation Matrix

> When you see an NVMe issue, check the PCIe column — and vice versa.

| NVMe Symptom | Possible PCIe Cause | PCIe Check |
|-------------|-------------------|------------|
| Command timeout (IO timeout) | Completion Timeout | AER UCE: CTO bit |
| Controller Fatal Status (CSTS.CFS=1) | PCIe link error → FW crash | AER UCE, link retrain count |
| Media errors increasing | Unlikely PCIe-related (NAND issue) | Verify no DMA corruption |
| High p99 latency spikes | ASPM L1 exit latency | Disable ASPM, re-measure |
| Namespace disappeared | PCIe link down event | lspci, dmesg, AER |
| FW update failure | PCIe error during FW download | AER during fw-download |
| Unsafe shutdown count high | Surprise power removal (U.2 hot-swap) | Check backplane power |
| Temperature warning | High temp may degrade PCIe margins | Run lane margining |

| PCIe Symptom | Possible NVMe Cause | NVMe Check |
|-------------|-------------------|------------|
| AER Correctable (Bad TLP) | Device FW generating bad TLPs | FW bug, check FW version |
| AER Correctable (Replay) | SI issue on channel | Lane margining, eye diagram |
| Completion Timeout | FW hang, command processing stuck | NVMe SMART: media errors, FW log |
| Link width degraded (x4→x2) | Hardware (connector/PCB), not FW | Re-seat U.2, check connector |
| Link speed downgrade | SI marginal at high speed | Lane margining, thermal check |
| Surprise Down | Physical removal or power loss | Unsafe shutdown counter |
| Device disappears | Controller crash or power issue | SMART: critical_warning |

---

## 3. NVMe Error Log Analysis

```bash
# Get NVMe error log
nvme error-log /dev/nvme0 --log-entries=16

# Each entry has:
#   error_count: Running error counter
#   sqid: Which submission queue
#   cmdid: Command ID
#   status_field: NVMe status code
#   parm_err_loc: Parameter error location
#   lba: LBA (if applicable)

# Cross-reference with PCIe:
# If status_field shows:
#   0x00: Success (no error)
#   0x02: Invalid Field in Command (NVMe-level error, not PCIe)
#   0x04: Data Transfer Error → CHECK PCIe! DMA may have failed
#   0x06: Internal Error → May be PCIe-related
#   0x0A: Namespace Not Ready → Check if PCIe reset happened
#   0x81: Abort Requested → Timeout? Check PCIe CTO

# Correlate timestamps:
# NVMe error log doesn't have timestamps, but:
# 1. Note the error_count value
# 2. Check dmesg for PCIe errors around same time
# 3. Check AER counters before/after
```

---

## 4. Continuous Monitoring Dashboard

```bash
#!/bin/bash
# pcie_nvme_dashboard.sh — Real-time monitoring (runs in terminal)
BDF=$1
NVME=${2:-nvme0}

while true; do
    clear
    echo "═══════ NVMe + PCIe Dashboard ═══════"
    echo "Device: $BDF / $NVME | $(date '+%H:%M:%S')"
    echo ""
    
    # PCIe
    SPEED=$(lspci -s $BDF -vvv 2>/dev/null | grep "LnkSta:" | head -1 | grep -oP "Speed \K[^\s,]+")
    WIDTH=$(lspci -s $BDF -vvv 2>/dev/null | grep "LnkSta:" | head -1 | grep -oP "Width x\K[0-9]+")
    CE=$(cat /sys/bus/pci/devices/0000:$BDF/aer_dev_correctable 2>/dev/null | awk '{s+=$2} END{print s+0}')
    UCE=$(cat /sys/bus/pci/devices/0000:$BDF/aer_dev_fatal 2>/dev/null | awk '{s+=$2} END{print s+0}')
    
    printf "PCIe: %-10s x%-2s  CE:%-5d UCE:%-5d\n" "$SPEED" "$WIDTH" "$CE" "$UCE"
    
    # NVMe
    SMART=$(nvme smart-log /dev/$NVME 2>/dev/null)
    TEMP=$(echo "$SMART" | grep "^temperature" | awk -F: '{print $2}' | xargs)
    PCT=$(echo "$SMART" | grep "percent_used" | awk -F: '{print $2}' | xargs)
    
    printf "NVMe: Temp=%-4s°C Used=%-3s%%\n" "$TEMP" "$PCT"
    
    # IO stats
    if [ -f /sys/block/${NVME}n1/stat ]; then
        STAT=$(cat /sys/block/${NVME}n1/stat)
        RD_IOS=$(echo $STAT | awk '{print $1}')
        WR_IOS=$(echo $STAT | awk '{print $5}')
        printf "IO:   Reads=%-10s Writes=%-10s\n" "$RD_IOS" "$WR_IOS"
    fi
    
    # Recent errors
    echo ""
    ERRS=$(dmesg | tail -5 | grep -i "pcie\|aer\|nvme.*error" 2>/dev/null)
    if [ -n "$ERRS" ]; then
        echo "Recent errors:"
        echo "$ERRS"
    else
        echo "No recent errors ✅"
    fi
    
    sleep 5
done
```

---

## 5. Failure Scenarios — NVMe ↔ PCIe Interaction

### Scenario A: NVMe Timeout → PCIe CTO → Driver Recovery

```
Timeline:
1. Host submits NVMe command (MWr doorbell)
2. Device DMA reads SQE (MRd + CplD)
3. Device starts processing... but FW hangs (bug/overload)
4. Device never DMAs completion (CQE MWr never sent)
5. NVMe driver: command timeout (~30s default)
6. NVMe driver: sends Abort command → device still hung
7. NVMe driver: controller reset (CC.EN=0→1 or FLR)
8. PCIe link may retrain during reset
9. Device recovers (hopefully)

PCIe evidence: Completion Timeout AER, possible link retrain
NVMe evidence: Timeout in error log, controller reset count
```

### Scenario B: PCIe Link Error → NVMe Data Corruption

```
Timeline:
1. Device DMAs write data to host (CQE MWr)
2. PCIe bit error corrupts CQE data (but LCRC matches by chance — rare)
3. Host reads corrupted CQE → may interpret wrong
4. Or: DMA data MWr corrupted → host receives bad data
5. If ECRC enabled: caught and reported as error
6. If ECRC not enabled: silent data corruption!

Prevention:
- Enable ECRC (DevCtl.ECRCGenerationEnable + ECRCCheckEnable)
- NVMe data protection (PI, end-to-end): protects against DMA corruption
- Monitor AER correctable errors → non-zero indicates risk
```

### Scenario C: Thermal Throttle → Performance Drop → Timeout

```
Timeline:
1. Sustained write workload
2. Controller temp reaches Tc_max
3. Device enters thermal throttle → reduces NAND/controller speed
4. IO latency increases dramatically (10x-100x)
5. If latency > NVMe timeout (30s): Command Timeout
6. NVMe driver resets controller
7. Controller reset during throttle → may take longer than expected

PCIe evidence: No PCIe errors (link is fine), but CTO may appear
NVMe evidence: Critical Warning bit 1 (temperature), high latency
```
