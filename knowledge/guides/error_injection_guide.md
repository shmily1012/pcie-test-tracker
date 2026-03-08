# PCIe Error Injection Guide for U.2 NVMe SSD

> How to inject PCIe errors for testing AER, error recovery, and resilience.
> Multiple methods: LeCroy, Linux EINJ, custom scripts.

---

## 1. Error Injection Methods

### 1.1 LeCroy Protocol Analyzer (Best Method)

```
Capabilities:
- Inject bit errors on specific TLPs (LCRC corruption)
- Block/delay specific TLPs (trigger CTO)
- Insert malformed TLPs
- Corrupt DLLP CRC
- Inject TS errors during link training
- Modify TLP header fields (poison, EP bit)

Setup:
1. LeCroy in-line between host and DUT (interposer)
2. Configure "Jammer" or "Error Injection" module
3. Set trigger condition (e.g., "next CplD to address X")
4. Set error type (LCRC corrupt, delay, drop, modify)
5. Arm → trigger → capture result
```

### 1.2 Linux EINJ (ACPI Error Injection)

```bash
# Check if EINJ is available
modprobe einj
ls /sys/kernel/debug/apei/einj/

# Available error types
cat /sys/kernel/debug/apei/einj/available_error_type
# Typical: Memory CE, Memory UCE, PCIe CE, PCIe UCE

# Inject PCIe Correctable Error
echo 0x40 > /sys/kernel/debug/apei/einj/error_type  # PCIe CE
echo $((16#01000000)) > /sys/kernel/debug/apei/einj/param1  # PCI SBDF
echo 1 > /sys/kernel/debug/apei/einj/error_inject

# Inject PCIe Uncorrectable Non-Fatal
echo 0x80 > /sys/kernel/debug/apei/einj/error_type
echo 1 > /sys/kernel/debug/apei/einj/error_inject

# Check results
dmesg | grep -i "aer\|error\|mce"
cat /sys/bus/pci/devices/0000:$BDF/aer_dev_correctable
```

**Note**: EINJ depends on BIOS/UEFI support. Not all platforms support PCIe error injection via EINJ.

### 1.3 AER Inject (Linux Kernel Module)

```bash
# Requires CONFIG_PCIEAER_INJECT=m in kernel config
modprobe aer_inject

# Create error injection file
cat > /tmp/aer_inject.txt << 'EOF'
# Domain Bus Dev Fn
AER 0000:01:00.0
# Correctable Error Status (bit positions)
COR_STATUS BAD_TLP
EOF

# Inject
# Note: aer_inject writes to the AER registers directly
# This tests the AER handling path, not actual PCIe errors

# Alternative: Use aer-inject tool
# https://git.kernel.org/pub/scm/linux/kernel/git/gong.chen/aer-inject.git
```

### 1.4 setpci-based AER Register Manipulation

```bash
BDF="01:00.0"

# Find AER Extended Capability offset
AER_OFF=$(lspci -s $BDF -vvv | grep "Advanced Error Reporting" | grep -oP '\[(\w+)\]' | tr -d '[]')

if [ -z "$AER_OFF" ]; then
    echo "AER not found"
    exit 1
fi

echo "AER capability at offset 0x$AER_OFF"

# AER registers (offsets from AER cap base):
# +04h: Uncorrectable Error Status
# +08h: Uncorrectable Error Mask
# +0Ch: Uncorrectable Error Severity
# +10h: Correctable Error Status
# +14h: Correctable Error Mask
# +18h: Advanced Error Capabilities and Control
# +1Ch: Header Log (4 DWORDs)

# Read current CE status
CE_STATUS_OFF=$(printf "%x" $(( 16#$AER_OFF + 0x10 )))
CE_STATUS=$(setpci -s $BDF ${CE_STATUS_OFF}.l)
echo "Correctable Error Status: 0x$CE_STATUS"

# Read current UCE status
UCE_STATUS_OFF=$(printf "%x" $(( 16#$AER_OFF + 0x04 )))
UCE_STATUS=$(setpci -s $BDF ${UCE_STATUS_OFF}.l)
echo "Uncorrectable Error Status: 0x$UCE_STATUS"

# Decode CE status bits
python3 << EOF
status = int("$CE_STATUS", 16)
ce_bits = {
    0: "Receiver Error",
    6: "Bad TLP",
    7: "Bad DLLP", 
    8: "REPLAY_NUM Rollover",
    12: "Replay Timer Timeout",
    13: "Advisory Non-Fatal Error",
    14: "Correctable Internal Error",
    15: "Header Log Overflow",
}
print("CE Status decode:")
for bit, name in sorted(ce_bits.items()):
    if status & (1 << bit):
        print(f"  [{bit}] {name}: SET")
    else:
        print(f"  [{bit}] {name}: clear")
EOF

# Decode UCE status bits
python3 << EOF
status = int("$UCE_STATUS", 16)
uce_bits = {
    4: "Data Link Protocol Error",
    5: "Surprise Down Error",
    12: "Poisoned TLP Received",
    13: "Flow Control Protocol Error",
    14: "Completion Timeout",
    15: "Completer Abort",
    16: "Unexpected Completion",
    17: "Receiver Overflow",
    18: "Malformed TLP",
    19: "ECRC Error",
    20: "Unsupported Request Error",
    22: "ACS Violation",
    23: "Uncorrectable Internal Error",
    26: "TLP Prefix Blocked Error",
}
print("UCE Status decode:")
for bit, name in sorted(uce_bits.items()):
    if status & (1 << bit):
        print(f"  [{bit}] {name}: SET !!!")
    else:
        print(f"  [{bit}] {name}: clear")
EOF

# Clear CE status (write 1 to clear)
# setpci -s $BDF ${CE_STATUS_OFF}.l=$CE_STATUS

# Clear UCE status
# setpci -s $BDF ${UCE_STATUS_OFF}.l=$UCE_STATUS
```

---

## 2. Error Injection Test Procedures

### 2.1 ERR-001: Bad TLP (LCRC Error)

```
Goal: Verify device/RC handles corrupted TLP correctly.

Method A (LeCroy):
1. Start fio random read (4K, QD=32)
2. LeCroy Jammer: corrupt LCRC on next CplD from device
3. Capture trace

Expected PCIe behavior:
  - RC detects bad LCRC on received CplD
  - RC sends NAK DLLP
  - Device replays TLP from Replay Buffer (good copy)
  - RC accepts replayed TLP (good LCRC)
  - AER Correctable Error status bit set: "Bad TLP" or "Receiver Error"
  - ERR_COR message sent to Root Port

Expected host behavior:
  - dmesg: "Corrected error" logged
  - AER counter incremented
  - IO continues normally (no data corruption)

Method B (Linux EINJ, if supported):
  See §1.2 above

Verification:
  cat /sys/bus/pci/devices/0000:$BDF/aer_dev_correctable
  # "bad_tlp" count should increment
```

### 2.2 ERR-013: Completion Timeout

```
Goal: Verify correct behavior when device fails to complete a request.

Method A (LeCroy — block completions):
1. Configure LeCroy to drop/block next CplD from device
2. Issue single NVMe read (nvme read /dev/nvme0n1 ...)
3. Device processes read → sends CplD → LeCroy drops it
4. RC waits → Completion Timeout fires

Expected PCIe behavior:
  - CTO after programmed timeout (DevCtl2.CTO Value)
  - AER UCE status: "Completion Timeout" bit set
  - ERR_NONFATAL or ERR_FATAL message (depends on severity setting)
  - If FATAL: link may go down
  - If NON-FATAL: device should continue operating

Expected host behavior:
  - dmesg: "Completion Timeout" error
  - NVMe driver: command timeout → abort → possible controller reset
  - Verify system doesn't hang

Method B (Software — inject at device FW level):
  If device FW has debug hooks: configure FW to not send completion for specific Tag
  This tests the full stack behavior

Verification:
  dmesg | grep -i "completion timeout"
  cat /sys/bus/pci/devices/0000:$BDF/aer_dev_nonfatal  # or aer_dev_fatal
```

### 2.3 ERR-010: Data Link Protocol Error

```
Goal: Verify behavior on sustained DLL errors (sequence number corruption).

Method (LeCroy):
1. Corrupt sequence numbers on multiple consecutive TLPs from device
2. This breaks DLL protocol → should escalate to UCE

Expected:
  - Multiple NAK DLLPs
  - REPLAY_NUM Rollover (CE first)
  - If sustained → Data Link Protocol Error (UCE)
  - Link may retrain (Recovery → L0)
  - AER UCE: "Data Link Protocol Error" set

Verification:
  - LeCroy trace shows Recovery entry
  - AER counters updated
  - System survives (no panic)
  - After Recovery: link is back up and functional
```

### 2.4 Surprise Down Error (U.2 Hot-Unplug)

```
Goal: Verify system survives when U.2 drive is physically removed without warning.

Method:
1. Start fio on U.2 device
2. Physically yank the U.2 drive from the backplane
3. Monitor system stability

Expected:
  - AER UCE: "Surprise Down Error" at Root Port
  - If DPC enabled: Downstream Port Containment triggered
    → Link disabled at Root Port
    → No propagation to rest of system
  - If DPC not enabled:
    → ERR_FATAL message to RC
    → NMI possible (SERR)
    → System should still survive (no panic ideally)
  - NVMe driver: device gone, errors logged
  - No kernel panic (CRITICAL requirement for DC deployment)

Verification:
  dmesg | grep -i "surprise\|dpc\|fatal\|nvme"
  # System still responsive after removal
  
Recovery:
  echo 1 > /sys/bus/pci/rescan  # Re-insert drive first
```

---

## 3. Automated Error Resilience Test Suite

```bash
#!/bin/bash
# error_resilience.sh — Test device error recovery capabilities
# Requires: Root, AER support, optional EINJ
# This tests the HOST-SIDE error handling. For device-side testing, use LeCroy.

BDF=$1
DEVICE="/dev/nvme0n1"

echo "=== PCIe Error Resilience Test Suite ==="
echo "Device: $BDF"
echo "Date: $(date)"
echo ""

# Test 1: AER Status — no errors at baseline
echo "--- Test 1: Baseline AER Status ---"
echo "CE:"
cat /sys/bus/pci/devices/0000:$BDF/aer_dev_correctable 2>/dev/null
echo "UCE:"
cat /sys/bus/pci/devices/0000:$BDF/aer_dev_fatal 2>/dev/null
echo ""

# Test 2: IO under AER monitoring
echo "--- Test 2: IO with AER monitoring (60s) ---"
CE_BEFORE=$(cat /sys/bus/pci/devices/0000:$BDF/aer_dev_correctable 2>/dev/null | awk '{s+=$2} END{print s+0}')
fio --name=err_test --filename=$DEVICE --rw=randrw --rwmixread=70 --bs=4k \
    --iodepth=128 --numjobs=4 --direct=1 --time_based --runtime=60 \
    --output=/dev/null 2>/dev/null
CE_AFTER=$(cat /sys/bus/pci/devices/0000:$BDF/aer_dev_correctable 2>/dev/null | awk '{s+=$2} END{print s+0}')
CE_DIFF=$((CE_AFTER - CE_BEFORE))
if [ $CE_DIFF -eq 0 ]; then
    echo "  ✅ No new correctable errors during IO"
else
    echo "  ⚠️  $CE_DIFF new correctable errors during IO"
fi
echo ""

# Test 3: FLR recovery
echo "--- Test 3: FLR Recovery ---"
if lspci -s $BDF -vvv | grep -q "FLReset+"; then
    echo 1 > /sys/bus/pci/devices/0000:$BDF/reset
    sleep 2
    if lspci -s $BDF 2>/dev/null | grep -q "NVMe"; then
        echo "  ✅ Device recovered after FLR"
        # Re-probe driver
        echo 1 > /sys/bus/pci/devices/0000:$BDF/remove
        echo 1 > /sys/bus/pci/rescan
        sleep 3
        if nvme list 2>/dev/null | grep -q nvme; then
            echo "  ✅ NVMe functional after FLR"
        else
            echo "  ❌ NVMe not functional after FLR"
        fi
    else
        echo "  ❌ Device missing after FLR"
    fi
else
    echo "  ⏭️  FLR not supported, skipping"
fi
echo ""

# Test 4: Remove/rescan cycle (simulates some error recovery paths)
echo "--- Test 4: Remove/Rescan (10 cycles) ---"
RESCAN_FAIL=0
for i in $(seq 1 10); do
    echo 1 > /sys/bus/pci/devices/0000:$BDF/remove 2>/dev/null
    sleep 0.5
    echo 1 > /sys/bus/pci/rescan 2>/dev/null
    sleep 2
    if ! lspci -s $BDF 2>/dev/null | grep -q "NVMe"; then
        echo "  ❌ Device missing after remove/rescan cycle $i"
        ((RESCAN_FAIL++))
        sleep 5
        echo 1 > /sys/bus/pci/rescan 2>/dev/null
        sleep 3
    fi
done
if [ $RESCAN_FAIL -eq 0 ]; then
    echo "  ✅ 10/10 remove/rescan cycles passed"
else
    echo "  ⚠️  $RESCAN_FAIL/10 remove/rescan failures"
fi
echo ""

# Test 5: D3hot under IO (potential error trigger)
echo "--- Test 5: D3hot During IO ---"
fio --name=d3test --filename=$DEVICE --rw=randread --bs=4k --iodepth=32 \
    --direct=1 --time_based --runtime=60 &
FIO_PID=$!
sleep 5

# Force D3hot while IO running (may cause errors — that's the test)
PM_CAP=$(lspci -s $BDF -vvv | grep "Power Management" | grep -oP '\[(\w+)\]' | tr -d '[]')
if [ -n "$PM_CAP" ]; then
    PMCSR_OFF=$(printf "%x" $(( 16#$PM_CAP + 4 )))
    PMCSR=$(setpci -s $BDF ${PMCSR_OFF}.w)
    D3VAL=$(printf "%04x" $(( (16#$PMCSR & 0xFFFC) | 3 )))
    setpci -s $BDF ${PMCSR_OFF}.w=$D3VAL 2>/dev/null
    sleep 1
    D0VAL=$(printf "%04x" $(( 16#$PMCSR & 0xFFFC )))
    setpci -s $BDF ${PMCSR_OFF}.w=$D0VAL 2>/dev/null
    sleep 2
fi

kill $FIO_PID 2>/dev/null; wait $FIO_PID 2>/dev/null

# Check if system survived
if lspci -s $BDF 2>/dev/null | grep -q "NVMe"; then
    echo "  ✅ System survived D3hot during IO"
else
    echo "  ❌ Device gone after D3hot during IO"
    echo 1 > /sys/bus/pci/rescan
    sleep 3
fi
echo ""

# Final AER check
echo "--- Final AER Status ---"
echo "CE:"
cat /sys/bus/pci/devices/0000:$BDF/aer_dev_correctable 2>/dev/null
echo "UCE:"
cat /sys/bus/pci/devices/0000:$BDF/aer_dev_fatal 2>/dev/null
echo ""
echo "dmesg errors:"
dmesg | tail -20 | grep -i "pcie\|aer\|nvme\|error" || echo "  (none)"

echo ""
echo "=== Error Resilience Test Complete ==="
```

---

## 4. AER Error Counter Monitoring Script

```bash
#!/bin/bash
# aer_monitor.sh — Continuous AER error monitoring
# Usage: ./aer_monitor.sh 01:00.0 [interval_seconds]

BDF=$1
INTERVAL=${2:-10}
SYSFS="/sys/bus/pci/devices/0000:${BDF}"

echo "Monitoring AER errors for $BDF every ${INTERVAL}s"
echo "Press Ctrl+C to stop"
echo ""
echo "Timestamp                CE_Total  UCE_Total  Link_Speed  Link_Width"
echo "────────────────────────────────────────────────────────────────────"

while true; do
    TS=$(date '+%Y-%m-%d %H:%M:%S')
    CE=$(cat ${SYSFS}/aer_dev_correctable 2>/dev/null | awk '{s+=$2} END{print s+0}')
    UCE=$(cat ${SYSFS}/aer_dev_fatal 2>/dev/null | awk '{s+=$2} END{print s+0}')
    SPEED=$(lspci -s $BDF -vvv 2>/dev/null | grep "LnkSta:" | head -1 | grep -oP "Speed \K[^\s,]+" || echo "N/A")
    WIDTH=$(lspci -s $BDF -vvv 2>/dev/null | grep "LnkSta:" | head -1 | grep -oP "Width x\K[0-9]+" || echo "0")
    
    printf "%s  %8d  %9d  %10s  x%-9s\n" "$TS" "$CE" "$UCE" "$SPEED" "$WIDTH"
    
    # Alert on new errors
    if [ "${PREV_CE:-0}" -ne 0 ] && [ "$CE" -gt "$PREV_CE" ]; then
        echo "  ⚠️  NEW Correctable Errors: +$((CE - PREV_CE))"
    fi
    if [ "${PREV_UCE:-0}" -ne 0 ] && [ "$UCE" -gt "$PREV_UCE" ]; then
        echo "  🔴 NEW Uncorrectable Errors: +$((UCE - PREV_UCE)) !!!"
    fi
    if [ "${PREV_WIDTH:-4}" -ne "$WIDTH" ] 2>/dev/null; then
        echo "  ⚠️  LINK WIDTH CHANGED: x${PREV_WIDTH:-?} → x${WIDTH}"
    fi
    
    PREV_CE=$CE
    PREV_UCE=$UCE
    PREV_WIDTH=$WIDTH
    
    sleep $INTERVAL
done
```
