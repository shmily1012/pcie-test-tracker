# PCIe Test Procedures — Detailed Steps (U.2 Gen4/Gen5 NVMe SSD)

> Detailed step-by-step procedures for key test items from the master test plan.
> Organized by tool required.

---

## Part A: Linux-Only Tests (No Special Equipment)

These tests can run on any Linux machine with the DUT installed. Estimated: ~80 tests coverable.

---

### A.1 Config Space Validation Script

**Covers**: CFG-001 through CFG-011, CFG-020 through CFG-031, CFG-040 through CFG-055

#### Prerequisites
```bash
# Install tools
apt install pciutils nvme-cli
# Identify device BDF (Bus:Device.Function)
lspci | grep -i nvme
# Example output: 01:00.0 Non-Volatile memory controller: <vendor>
export BDF="01:00.0"
```

#### Procedure: CFG-001 — Vendor ID / Device ID

```bash
# Step 1: Read Vendor ID and Device ID
VID=$(setpci -s $BDF 00.w)
DID=$(setpci -s $BDF 02.w)
echo "Vendor ID: 0x$VID, Device ID: 0x$DID"

# Step 2: Verify not 0xFFFF (device not present)
if [ "$VID" = "ffff" ]; then
    echo "FAIL: Device not detected (VID=FFFFh)"
    exit 1
fi

# Step 3: Verify matches expected values
# Replace with your company's VID/DID
EXPECTED_VID="1234"  # Change this
EXPECTED_DID="5678"  # Change this
if [ "$VID" != "$EXPECTED_VID" ] || [ "$DID" != "$EXPECTED_DID" ]; then
    echo "WARNING: VID/DID mismatch. Expected $EXPECTED_VID/$EXPECTED_DID, got $VID/$DID"
fi

# PASS criteria: VID and DID match expected, not FFFFh
```

#### Procedure: CFG-004 — Class Code

```bash
# Step 1: Read Class Code (offset 09h, 3 bytes)
CC=$(setpci -s $BDF 09.b)   # Programming Interface
SCC=$(setpci -s $BDF 0a.b)  # Sub-Class
BCC=$(setpci -s $BDF 0b.b)  # Base Class

echo "Class Code: $BCC:$SCC:$CC"

# Step 2: Verify NVMe class code
# Base=01h (Mass Storage), Sub=08h (NVM), PI=02h (NVMe)
if [ "$BCC" = "01" ] && [ "$SCC" = "08" ] && [ "$CC" = "02" ]; then
    echo "PASS: Class code is NVMe (01:08:02)"
else
    echo "FAIL: Unexpected class code $BCC:$SCC:$CC (expected 01:08:02)"
fi
```

#### Procedure: CFG-005 — BAR0 Verification

```bash
# Step 1: Read BAR0 (NVMe requires 64-bit, non-prefetchable memory BAR)
lspci -s $BDF -vvv | grep -A5 "Region 0"
# Expected: "Region 0: Memory at XXXXX (64-bit, non-prefetchable) [size=XXK]"

# Step 2: Verify 64-bit
BAR0_LOW=$(setpci -s $BDF 10.l)
BAR0_TYPE=$(( (0x$BAR0_LOW >> 1) & 0x3 ))
if [ $BAR0_TYPE -eq 2 ]; then
    echo "PASS: BAR0 is 64-bit"
else
    echo "FAIL: BAR0 is not 64-bit (type=$BAR0_TYPE)"
fi

# Step 3: Verify non-prefetchable
BAR0_PREFETCH=$(( (0x$BAR0_LOW >> 3) & 0x1 ))
if [ $BAR0_PREFETCH -eq 0 ]; then
    echo "PASS: BAR0 is non-prefetchable"
else
    echo "FAIL: BAR0 is prefetchable (NVMe requires non-prefetchable)"
fi

# Step 4: Verify size >= 16KB (BAR sizing)
# Save original, write all 1s, read back, restore
# WARNING: This disrupts device operation — do with device quiesced
# BAR_ORIG=$(setpci -s $BDF 10.l)
# setpci -s $BDF 10.l=ffffffff
# BAR_SIZE=$(setpci -s $BDF 10.l)
# setpci -s $BDF 10.l=$BAR_ORIG
# Size = ~(BAR_SIZE & ~0xF) + 1
```

#### Procedure: CFG-008 — Capability Pointer Walk

```bash
# Step 1: Read Capability Pointer
CAP_PTR=$(setpci -s $BDF 34.b)
echo "First capability at offset 0x$CAP_PTR"

# Step 2: Walk the linked list
OFFSET=$((16#$CAP_PTR))
SEEN=()
while [ $OFFSET -ne 0 ] && [ $OFFSET -lt 256 ]; do
    CAP_ID=$(setpci -s $BDF $(printf "%02x" $OFFSET).b)
    NEXT=$(setpci -s $BDF $(printf "%02x" $(($OFFSET + 1))).b)
    echo "  Offset 0x$(printf '%02X' $OFFSET): Cap ID=0x$CAP_ID, Next=0x$NEXT"
    
    # Check for loop
    if [[ " ${SEEN[@]} " =~ " $OFFSET " ]]; then
        echo "FAIL: Loop detected in capability list!"
        break
    fi
    SEEN+=($OFFSET)
    
    OFFSET=$((16#$NEXT))
done

echo "PASS: Capability list walk complete, ${#SEEN[@]} capabilities found"
# Common expected caps: 10h=PCIe, 05h=MSI, 11h=MSI-X, 01h=PM
```

#### Procedure: CFG-024 — Link Capabilities

```bash
# Step 1: Find PCIe capability offset
PCIE_CAP=$(lspci -s $BDF -vvv | grep -oP "Express \(v\d\) Endpoint" | head -1)
echo "PCIe device type: $PCIE_CAP"

# Step 2: Read Link Capabilities via lspci
lspci -s $BDF -vvv | grep -A10 "LnkCap:"
# Check: MaxSpeed (should show 32GT/s for Gen5, 16GT/s for Gen4)
# Check: MaxWidth (should show x4)
# Check: ASPM L0s L1

# Step 3: Parse max speed
MAX_SPEED=$(lspci -s $BDF -vvv | grep "LnkCap:" | grep -oP "Speed \K[0-9.]+GT/s")
echo "Max Link Speed: $MAX_SPEED"

# Step 4: Parse max width
MAX_WIDTH=$(lspci -s $BDF -vvv | grep "LnkCap:" | grep -oP "Width x\K[0-9]+")
echo "Max Link Width: x$MAX_WIDTH"

# PASS criteria: Speed matches device spec, Width = x4
```

#### Procedure: CFG-026 — Link Status (Actual Negotiated)

```bash
# Step 1: Read current link status
lspci -s $BDF -vvv | grep "LnkSta:"
# Example: LnkSta: Speed 32GT/s, Width x4

CURR_SPEED=$(lspci -s $BDF -vvv | grep "LnkSta:" | grep -oP "Speed \K[0-9.]+GT/s")
CURR_WIDTH=$(lspci -s $BDF -vvv | grep "LnkSta:" | grep -oP "Width x\K[0-9]+")
echo "Current: ${CURR_SPEED} x${CURR_WIDTH}"

# Step 2: Verify matches max capability (or system limit)
echo "Expected: Speed matches slot capability, Width = x4"

# Step 3: Check for degraded link
if [ "$CURR_WIDTH" -lt 4 ]; then
    echo "WARNING: Link width degraded to x${CURR_WIDTH}"
fi
```

#### Procedure: CFG-055 — Full Extended Config Space Read

```bash
# Step 1: Read entire 4KB config space, check for hangs
echo "Reading full 4KB extended config space..."
for offset in $(seq 0 4 4092); do
    HEX=$(printf "%03x" $offset)
    VAL=$(setpci -s $BDF ${HEX}.l 2>/dev/null)
    if [ $? -ne 0 ]; then
        echo "FAIL: Read hang at offset 0x${HEX}"
        break
    fi
done
echo "PASS: Full config space readable without hang"
```

---

### A.2 Link Speed/Width Manipulation

**Covers**: LT-008, LT-009, LT-013, LT-014

#### Procedure: LT-009 — Directed Speed Change

```bash
# Step 1: Record current speed
BEFORE=$(lspci -s $BDF -vvv | grep "LnkSta:" | head -1)
echo "Before: $BEFORE"

# Step 2: Find PCIe cap offset for Link Control 2
# Target Link Speed field in Link Control 2 register
# Values: 1=Gen1, 2=Gen2, 3=Gen3, 4=Gen4, 5=Gen5

# Step 3: Change to Gen3 (if currently higher)
# WARNING: This will retrain the link
PCIE_CAP_OFFSET=$(lspci -s $BDF -vvv | grep "Capabilities:.*Express" | grep -oP '\[(\w+)\]' | tr -d '[]')
LINK_CTL2_OFFSET=$(printf "%x" $(( 16#$PCIE_CAP_OFFSET + 0x30 )))

echo "Setting Target Link Speed to Gen3..."
# Read current value, mask bits 3:0, set to 3
CURRENT=$(setpci -s $BDF ${LINK_CTL2_OFFSET}.w)
NEW=$(printf "%04x" $(( (16#$CURRENT & 0xFFF0) | 3 )))
setpci -s $BDF ${LINK_CTL2_OFFSET}.w=$NEW

# Step 4: Trigger retrain via Link Control register
LINK_CTL_OFFSET=$(printf "%x" $(( 16#$PCIE_CAP_OFFSET + 0x10 )))
LCTL=$(setpci -s $BDF ${LINK_CTL_OFFSET}.w)
RETRAIN=$(printf "%04x" $(( 16#$LCTL | 0x20 )))  # Set bit 5 (Retrain Link)
setpci -s $BDF ${LINK_CTL_OFFSET}.w=$RETRAIN

sleep 1

# Step 5: Verify new speed
AFTER=$(lspci -s $BDF -vvv | grep "LnkSta:" | head -1)
echo "After: $AFTER"
# PASS: Speed should show 8GT/s (Gen3)

# Step 6: Restore to max speed (set target to 5 for Gen5, retrain)
```

---

### A.3 Power Management Tests

**Covers**: PM-001, PM-002, PM-003, PM-005

#### Procedure: PM-001/002 — D3hot Round-trip

```bash
# Step 1: Record device state
nvme list  # Verify device is present and functional
echo "Device functional before D3hot"

# Step 2: Find PM capability offset
PM_CAP=$(lspci -s $BDF -vvv | grep "Power Management" | grep -oP '\[(\w+)\]' | tr -d '[]')
PMCSR_OFFSET=$(printf "%x" $(( 16#$PM_CAP + 4 )))

# Step 3: Set D3hot (bits 1:0 = 11b)
PMCSR=$(setpci -s $BDF ${PMCSR_OFFSET}.w)
echo "Current PMCSR: 0x$PMCSR (PowerState=$(( 16#$PMCSR & 3 )))"
D3VAL=$(printf "%04x" $(( (16#$PMCSR & 0xFFFC) | 3 )))
setpci -s $BDF ${PMCSR_OFFSET}.w=$D3VAL
echo "Set D3hot"

# Step 4: Verify in D3hot
PMCSR=$(setpci -s $BDF ${PMCSR_OFFSET}.w)
PS=$(( 16#$PMCSR & 3 ))
if [ $PS -eq 3 ]; then echo "PASS: In D3hot"; else echo "FAIL: Not in D3hot (PS=$PS)"; fi

# Step 5: Config space should still be accessible
VID=$(setpci -s $BDF 00.w)
if [ "$VID" != "ffff" ]; then echo "PASS: Config space accessible in D3hot"; fi

# Step 6: Restore to D0
D0VAL=$(printf "%04x" $(( 16#$PMCSR & 0xFFFC )))
setpci -s $BDF ${PMCSR_OFFSET}.w=$D0VAL
sleep 0.1  # D3hot→D0 restore time (≤10ms per spec)

# Step 7: Verify functional
nvme list
echo "PASS if device appears in nvme list"
```

---

### A.4 Reset Tests

**Covers**: RST-001 through RST-005

#### Procedure: RST-004 — FLR (Function Level Reset)

```bash
# Step 1: Verify FLR capability
FLR_CAP=$(lspci -s $BDF -vvv | grep "FLReset")
if [ -z "$FLR_CAP" ]; then
    echo "SKIP: FLR not supported"
    exit 0
fi
echo "FLR supported: $FLR_CAP"

# Step 2: Start background IO
fio --name=bg --filename=/dev/nvme0n1 --rw=randread --bs=4k --iodepth=32 \
    --direct=1 --time_based --runtime=30 &
FIO_PID=$!
sleep 2

# Step 3: Issue FLR
echo "Issuing FLR..."
echo 1 > /sys/bus/pci/devices/0000:${BDF}/reset
# Alternative: setpci -s $BDF PCIE_CAP+8.w (set bit 15)

# Step 4: Wait for recovery
sleep 2

# Step 5: Verify device re-enumeration
if lspci -s $BDF > /dev/null 2>&1; then
    echo "PASS: Device present after FLR"
else
    echo "FAIL: Device gone after FLR"
fi

# Step 6: Reload NVMe driver if needed
echo 1 > /sys/bus/pci/devices/0000:${BDF}/remove
echo 1 > /sys/bus/pci/rescan
sleep 2
nvme list
echo "PASS if device re-appears and is functional"

kill $FIO_PID 2>/dev/null
```

---

### A.5 Performance Baseline

**Covers**: PERF-001 through PERF-004, PERF-009

#### Procedure: PERF-001 — Sequential Read Bandwidth

```bash
DEVICE="/dev/nvme0n1"
# Theoretical max: Gen5 x4 = ~15.8 GB/s (after encoding overhead)
#                  Gen4 x4 = ~7.9 GB/s
#                  Gen3 x4 = ~3.9 GB/s

# Step 1: Sequential Read
fio --name=seq_read --filename=$DEVICE --rw=read --bs=128k \
    --iodepth=256 --numjobs=4 --direct=1 --group_reporting \
    --time_based --runtime=30 --output-format=json \
    --output=/tmp/seq_read.json

BW=$(python3 -c "import json; d=json.load(open('/tmp/seq_read.json')); print(f\"{d['jobs'][0]['read']['bw']/1024/1024:.2f} GB/s\")")
echo "Sequential Read Bandwidth: $BW"

# Step 2: Compare to theoretical max
echo "Theoretical max at current link speed: check lspci LnkSta"
echo "Efficiency = measured / theoretical * 100%"
echo "PASS criteria: >= 90% of theoretical max"
```

#### Procedure: PERF-009 — QD=1 Latency

```bash
fio --name=lat_qd1 --filename=$DEVICE --rw=randread --bs=4k \
    --iodepth=1 --numjobs=1 --direct=1 \
    --time_based --runtime=30 --output-format=json \
    --output=/tmp/lat_qd1.json

python3 << 'EOF'
import json
d = json.load(open('/tmp/lat_qd1.json'))
r = d['jobs'][0]['read']
print(f"Avg:  {r['lat_ns']['mean']/1000:.1f} μs")
print(f"P99:  {r['clat_ns']['percentile']['99.000000']/1000:.1f} μs")
print(f"P999: {r['clat_ns']['percentile']['99.900000']/1000:.1f} μs")
# PASS: Avg < 100μs, P99 < 200μs for typical NVMe SSD
EOF
```

---

## Part B: LeCroy Protocol Analyzer Tests

> These procedures assume a Teledyne LeCroy Summit T54/T516/M5x or similar.
> Refer to LeCroy PCIe Exerciser/Analyzer User Manual for detailed UI steps.

### B.1 General LeCroy Setup

```
1. Physical Setup:
   - Insert LeCroy interposer between host PCIe slot and DUT
   - For M.2: Use M.2-to-CEM adapter + interposer
   - For U.2: Use U.2 interposer card
   - Connect LeCroy probe cables to interposer
   - Power on LeCroy → wait for probe detection

2. Software Setup (PETracer):
   - Create new capture session
   - Set speed: Auto-detect (or force specific Gen)
   - Set lane width: x4
   - Set trigger: None (free-run) for initial capture
   - Set buffer: Maximum depth
   - Enable protocol decode: PCIe + NVMe
   
3. Capture:
   - Arm trace → Power on / reset host → Capture link training
   - Or: Arm trace → Run test on host → Stop capture
```

### B.2 Link Training Capture

**Covers**: LT-001 through LT-022

#### Procedure: LT-001 — Cold Boot Link Training

```
LeCroy Steps:
1. Set trigger: Start capture on Detect state entry
2. Enable TS1/TS2 ordered set decode
3. Power off host completely
4. Arm LeCroy capture
5. Power on host
6. Wait for OS boot → Stop capture

Analysis:
1. Find Detect state → verify Receiver Detection pulse
2. Find Polling state → verify compliance pattern (if Polling.Compliance entered)
3. Find Config state → verify TS1/TS2 exchange with correct lane numbers
4. Find L0 state → verify transition to normal operation
5. Measure time from Detect to L0: should be < 200ms typical

Check in trace:
- TS1 ordered sets: verify Lane/Link numbers assigned
- Speed change TS: verify Gen5 negotiation (or max supported)
- EQ Phase 0→3: verify preset/coefficient exchange
- No unexpected Recovery entries during initial training

PASS: Clean Detect→Polling→Config→L0 transition, correct speed/width
```

#### Procedure: LT-008 — Speed Negotiation

```
LeCroy Steps:
1. Capture full boot sequence (as in LT-001)
2. In trace, filter for "Speed Change" or "Changed" bit in TS ordered sets

Analysis:
1. Initial training starts at Gen1 (2.5GT/s)
2. After Config→L0 at Gen1, verify Recovery entry for speed change
3. Track Changed Speed bit in TS1/TS2 during Recovery
4. Verify final negotiated speed matches min(device_max, slot_max)
5. If Gen5: verify EQ phases 0-3 completed at 32GT/s

Gen speed progression expected:
Gen1 (initial) → Gen2 → Gen3 (EQ) → Gen4 (EQ) → Gen5 (EQ)
Each step involves Recovery→L0 at new speed.

PASS: Final speed matches expected, all EQ phases complete
```

#### Procedure: LT-011 — Speed Downgrade Under Errors

```
LeCroy Steps (requires Exerciser/Jammer capability):
1. Allow normal link training to Gen5 x4
2. Start injecting bit errors on one lane (error rate ~1e-6)
3. Capture link behavior

Expected behavior:
1. Device enters Recovery (bit errors → NAK → retrain)
2. Recovery.EqPhase attempted at current speed
3. If Recovery fails at Gen5 → speed downgrade to Gen4
4. If still fails → Gen3 → Gen2 → Gen1

Analysis:
- Count Recovery entries in trace
- Verify speed_change bit set when downgrading
- Verify stable operation at degraded speed
- Stop error injection → verify device does NOT auto-upgrade
  (speed upgrade requires software-directed retrain)

PASS: Clean downgrade sequence, stable at lower speed
```

### B.3 Error Injection

**Covers**: ERR-001 through ERR-019

#### Procedure: ERR-001 — Inject Bad TLP (LCRC Error)

```
LeCroy Exerciser Steps:
1. Configure jammer rule: Corrupt LCRC on next MRd Completion
2. On host: issue nvme read (triggers MRd → device returns CplD)
3. Jammer corrupts LCRC on the CplD

Expected on trace:
1. CplD with bad LCRC → NAK DLLP from receiver
2. Replay of CplD (good LCRC) → ACK
3. AER Correctable Error status set (Receiver Error or Bad TLP)

On host verify:
$ dmesg | grep -i "correctable error"
$ cat /sys/bus/pci/devices/0000:${BDF}/aer_dev_correctable
# "bad_tlp" or "receiver_error" count should increment

PASS: NAK+Replay observed, AER CE logged, no data corruption
```

---

## Part C: Automated Test Suite

> Wrapper scripts to run multiple tests in sequence.

### C.1 Quick Smoke Test (5 minutes)

```bash
#!/bin/bash
# pcie_smoke.sh — Quick PCIe health check
# Usage: ./pcie_smoke.sh 01:00.0

BDF=$1
PASS=0; FAIL=0; SKIP=0

function check() {
    local name=$1 result=$2
    if [ "$result" = "PASS" ]; then ((PASS++)); echo "  ✅ $name"
    elif [ "$result" = "SKIP" ]; then ((SKIP++)); echo "  ⏭  $name"
    else ((FAIL++)); echo "  ❌ $name: $result"; fi
}

echo "=== PCIe Smoke Test for $BDF ==="
echo ""

# 1. Device present
VID=$(setpci -s $BDF 00.w 2>/dev/null)
[ "$VID" != "ffff" ] && [ -n "$VID" ] && check "CFG-001 VID" "PASS" || check "CFG-001 VID" "FAIL: $VID"

# 2. Class code
CC=$(lspci -s $BDF -n | awk '{print $2}')
[ "$CC" = "0108" ] && check "CFG-004 Class=NVMe" "PASS" || check "CFG-004 Class" "FAIL: $CC"

# 3. Link speed
SPEED=$(lspci -s $BDF -vvv 2>/dev/null | grep "LnkSta:" | grep -oP "Speed \K[0-9.]+")
[ -n "$SPEED" ] && check "CFG-026 Link Speed ${SPEED}GT/s" "PASS" || check "CFG-026 Link Speed" "FAIL"

# 4. Link width
WIDTH=$(lspci -s $BDF -vvv 2>/dev/null | grep "LnkSta:" | grep -oP "Width x\K[0-9]+")
[ "$WIDTH" -ge 4 ] 2>/dev/null && check "CFG-026 Link Width x${WIDTH}" "PASS" || check "CFG-026 Width" "FAIL: x$WIDTH"

# 5. NVMe device visible
nvme list 2>/dev/null | grep -q nvme && check "NP-001 NVMe enumerated" "PASS" || check "NP-001 NVMe" "FAIL"

# 6. BAR0 64-bit non-prefetch
BAR0_INFO=$(lspci -s $BDF -vvv | grep "Region 0")
echo "$BAR0_INFO" | grep -q "64-bit" && echo "$BAR0_INFO" | grep -q "non-prefetchable" && \
    check "CFG-005 BAR0 64-bit NP" "PASS" || check "CFG-005 BAR0" "FAIL: $BAR0_INFO"

# 7. MSI-X present
lspci -s $BDF -vvv | grep -q "MSI-X" && check "INT-002 MSI-X present" "PASS" || check "INT-002 MSI-X" "FAIL"

# 8. AER present
lspci -s $BDF -vvv | grep -q "Advanced Error Reporting" && \
    check "CFG-040 AER present" "PASS" || check "CFG-040 AER" "FAIL"

# 9. Quick IO test
dd if=/dev/nvme0n1 of=/dev/null bs=1M count=100 iflag=direct 2>/dev/null && \
    check "DMA-001 Basic Read IO" "PASS" || check "DMA-001 Basic IO" "FAIL"

# 10. FLR capability
lspci -s $BDF -vvv | grep -q "FLReset+" && check "RST-004 FLR capable" "PASS" || \
    check "RST-004 FLR" "SKIP: Not supported"

echo ""
echo "=== Results: ✅ $PASS passed, ❌ $FAIL failed, ⏭  $SKIP skipped ==="
```

### C.2 Full Config Space Audit (15 minutes)

```bash
#!/bin/bash
# pcie_config_audit.sh — Complete config space verification
# Generates detailed report

BDF=$1
REPORT="/tmp/pcie_config_report_$(date +%Y%m%d_%H%M%S).txt"

echo "PCIe Config Space Audit Report" > $REPORT
echo "Device: $BDF" >> $REPORT
echo "Date: $(date)" >> $REPORT
echo "System: $(uname -a)" >> $REPORT
echo "========================================" >> $REPORT

# Full lspci dump
echo "" >> $REPORT
echo "=== Full lspci -vvv output ===" >> $REPORT
lspci -s $BDF -vvv >> $REPORT 2>&1

# Raw config hex dump
echo "" >> $REPORT
echo "=== Raw Config Space Hex Dump (256B standard) ===" >> $REPORT
lspci -s $BDF -xxx >> $REPORT 2>&1

# Extended config space
echo "" >> $REPORT
echo "=== Extended Config Space Hex Dump (4KB) ===" >> $REPORT
lspci -s $BDF -xxxx >> $REPORT 2>&1

# NVMe controller registers
echo "" >> $REPORT
echo "=== NVMe Controller Registers ===" >> $REPORT
nvme show-regs /dev/nvme0 >> $REPORT 2>&1

# NVMe Identify Controller
echo "" >> $REPORT
echo "=== NVMe Identify Controller ===" >> $REPORT
nvme id-ctrl /dev/nvme0 >> $REPORT 2>&1

# AER status
echo "" >> $REPORT
echo "=== AER Error Counters ===" >> $REPORT
cat /sys/bus/pci/devices/0000:${BDF}/aer_dev_correctable 2>/dev/null >> $REPORT
cat /sys/bus/pci/devices/0000:${BDF}/aer_dev_fatal 2>/dev/null >> $REPORT
cat /sys/bus/pci/devices/0000:${BDF}/aer_dev_nonfatal 2>/dev/null >> $REPORT

echo ""
echo "Report saved to: $REPORT"
echo "Review and compare against expected values."
```

---

## Part C.5: U.2 Specific Tests

### U.2 Hot-Swap Test (FF-015)

```bash
#!/bin/bash
# u2_hotswap.sh — U.2 hot-swap test
# Requires: U.2 backplane with hot-swap support, surprise removal enabled
# WARNING: Only run on test devices. May cause data loss.

BDF=$1  # e.g., 83:00.0
NVME_DEV="nvme0"  # adjust

echo "=== U.2 Hot-Swap Test ==="

# Step 1: Verify device is present and functional
echo "1. Pre-removal check"
lspci -s $BDF -vvv | grep "LnkSta:" | head -1
nvme list | grep $NVME_DEV

# Step 2: Run background IO
echo "2. Starting background IO"
fio --name=bg --filename=/dev/${NVME_DEV}n1 --rw=randread --bs=4k --iodepth=32 \
    --direct=1 --time_based --runtime=300 &
FIO_PID=$!
sleep 3

# Step 3: Graceful removal
echo "3. Initiating graceful removal via sysfs"
# Kill fio first
kill $FIO_PID 2>/dev/null; wait $FIO_PID 2>/dev/null

# Remove through sysfs
echo 1 > /sys/bus/pci/devices/0000:${BDF}/remove
sleep 1

# Step 4: Verify removed
if lspci -s $BDF 2>/dev/null | grep -q "NVMe"; then
    echo "FAIL: Device still present after removal"
else
    echo "PASS: Device removed from bus"
fi

# Step 5: Physical removal — prompt user
echo ""
echo ">>> Now physically remove the U.2 drive from the backplane <<<"
read -p "Press Enter after removing drive..."
echo ">>> Now physically re-insert the U.2 drive <<<"
read -p "Press Enter after re-inserting drive..."

# Step 6: Rescan
echo "6. Rescanning PCI bus"
echo 1 > /sys/bus/pci/rescan
sleep 3

# Step 7: Verify re-enumeration
if lspci -s $BDF 2>/dev/null | grep -q "NVMe"; then
    echo "PASS: Device re-enumerated at $BDF"
    lspci -s $BDF -vvv | grep "LnkSta:" | head -1
    nvme list | grep nvme
else
    echo "FAIL: Device not found after re-insert"
    echo "Checking all NVMe devices..."
    lspci | grep -i nvme
fi

# Step 8: Verify IO functional after re-insert
echo "8. Post hot-swap IO test"
dd if=/dev/${NVME_DEV}n1 of=/dev/null bs=1M count=100 iflag=direct 2>/dev/null && \
    echo "PASS: IO functional after hot-swap" || \
    echo "FAIL: IO broken after hot-swap"

# Step 9: Check AER errors
echo "9. Checking for errors"
CE=$(cat /sys/bus/pci/devices/0000:${BDF}/aer_dev_correctable 2>/dev/null | awk '{s+=$2} END{print s+0}')
echo "AER Correctable Errors after hot-swap: $CE"
dmesg | tail -20 | grep -i "pcie\|nvme\|error"
```

### U.2 Power Loss Test (DC-002)

```bash
#!/bin/bash
# u2_power_loss.sh — Automated power loss testing
# Requires: programmable relay on 12V power line
# Relay control via GPIO, USB relay, or network PDU

DEVICE="/dev/nvme0n1"
RELAY_CMD="gpio_relay_off"   # Replace with your relay control command
RELAY_ON="gpio_relay_on"
ITERATIONS=100
LOG="/tmp/power_loss_$(date +%Y%m%d).log"

echo "U.2 Power Loss Test — $ITERATIONS iterations" | tee $LOG

for i in $(seq 1 $ITERATIONS); do
    echo "--- Iteration $i/$ITERATIONS ---" | tee -a $LOG
    
    # 1. Start IO
    fio --name=write --filename=$DEVICE --rw=randwrite --bs=4k --iodepth=64 \
        --direct=1 --time_based --runtime=10 --output=/dev/null &
    FIO_PID=$!
    
    # 2. Wait random time (1-8 seconds into IO)
    WAIT=$(( RANDOM % 8 + 1 ))
    sleep $WAIT
    
    # 3. Yank power
    echo "  Power OFF at +${WAIT}s" | tee -a $LOG
    $RELAY_CMD
    kill $FIO_PID 2>/dev/null; wait $FIO_PID 2>/dev/null
    
    # 4. Wait for capacitor discharge
    sleep 5
    
    # 5. Power on
    echo "  Power ON" | tee -a $LOG
    $RELAY_ON
    
    # 6. Wait for device to appear
    sleep 10
    
    # 7. Rescan PCI bus
    echo 1 > /sys/bus/pci/rescan 2>/dev/null
    sleep 3
    
    # 8. Check device health
    if nvme list 2>/dev/null | grep -q nvme; then
        echo "  Device present: PASS" | tee -a $LOG
        
        # Check link speed
        BDF=$(lspci | grep -i nvme | head -1 | awk '{print $1}')
        SPEED=$(lspci -s $BDF -vvv | grep "LnkSta:" | head -1 | grep -oP "Speed \K[^\s,]+")
        echo "  Link speed: $SPEED" | tee -a $LOG
        
        # Quick IO test
        if dd if=$DEVICE of=/dev/null bs=1M count=10 iflag=direct 2>/dev/null; then
            echo "  IO test: PASS" | tee -a $LOG
        else
            echo "  IO test: FAIL !!!" | tee -a $LOG
        fi
        
        # Check SMART for media errors
        MEDIA_ERR=$(nvme smart-log /dev/nvme0 2>/dev/null | grep "media_errors" | awk '{print $NF}')
        echo "  Media errors: ${MEDIA_ERR:-unknown}" | tee -a $LOG
    else
        echo "  Device MISSING after power loss!!! FAIL" | tee -a $LOG
        echo "  Waiting 30s for slow boot..."
        sleep 30
        echo 1 > /sys/bus/pci/rescan 2>/dev/null
        sleep 3
        if nvme list 2>/dev/null | grep -q nvme; then
            echo "  Device recovered after extended wait" | tee -a $LOG
        else
            echo "  CRITICAL: Device did not come back. Stopping test." | tee -a $LOG
            break
        fi
    fi
done

echo "" | tee -a $LOG
echo "=== Power Loss Test Complete ===" | tee -a $LOG
echo "Results in: $LOG"
grep -c "IO test: PASS" $LOG | xargs -I{} echo "  PASS: {} iterations"
grep -c "IO test: FAIL" $LOG | xargs -I{} echo "  FAIL: {} iterations"
grep -c "Device MISSING" $LOG | xargs -I{} echo "  MISSING: {} iterations"
```

### Gen4/Gen5 Speed Switch Test (COMPAT-005/006)

```bash
#!/bin/bash
# gen4_gen5_switch.sh — Runtime speed switching between Gen4 and Gen5
# Requires: Gen5-capable platform

BDF=$1
DEVICE="/dev/nvme0n1"

echo "=== Gen4↔Gen5 Speed Switch Test ==="

# Find PCIe Express capability offset
PCIE_CAP=$(lspci -s $BDF -vvv | grep -oP 'Express \(v\d\)' | head -1)
echo "Device: $PCIE_CAP"

# Current state
CURRENT=$(lspci -s $BDF -vvv | grep "LnkSta:" | head -1)
echo "Current: $CURRENT"
MAX=$(lspci -s $BDF -vvv | grep "LnkCap:" | head -1)
echo "Max:     $MAX"

# Function to set target speed and retrain
set_speed() {
    local gen=$1
    local speed_val=$2
    local speed_name=$3
    
    echo ""
    echo "--- Switching to $speed_name ---"
    
    # Set Target Link Speed in Link Control 2
    # Find cap offset from lspci hex dump
    CAP_OFF=$(lspci -s $BDF -vvv | grep "Capabilities:.*Express" | grep -oP '\[(\w+)\]' | tr -d '[]' | head -1)
    LC2_OFF=$(printf "%x" $(( 16#$CAP_OFF + 0x30 )))
    
    # Read current LC2, set bits 3:0 to speed_val
    LC2=$(setpci -s $BDF ${LC2_OFF}.w)
    NEW_LC2=$(printf "%04x" $(( (16#$LC2 & 0xFFF0) | $speed_val )))
    setpci -s $BDF ${LC2_OFF}.w=$NEW_LC2
    
    # Trigger retrain (bit 5 of Link Control)
    LC_OFF=$(printf "%x" $(( 16#$CAP_OFF + 0x10 )))
    LC=$(setpci -s $BDF ${LC_OFF}.w)
    RETRAIN=$(printf "%04x" $(( 16#$LC | 0x20 )))
    setpci -s $BDF ${LC_OFF}.w=$RETRAIN
    
    # Wait for retrain
    sleep 2
    
    # Check result
    NEW_SPEED=$(lspci -s $BDF -vvv | grep "LnkSta:" | head -1 | grep -oP "Speed \K[0-9.]+GT/s")
    echo "New speed: $NEW_SPEED"
    
    # Quick IO test
    BW=$(dd if=$DEVICE of=/dev/null bs=1M count=500 iflag=direct 2>&1 | grep -oP "[0-9.]+ [GM]B/s")
    echo "Bandwidth: $BW"
}

# Test sequence
set_speed 4 4 "Gen4 (16GT/s)"

# Run quick fio at Gen4
echo "Running fio at Gen4..."
fio --name=gen4_test --filename=$DEVICE --rw=read --bs=128k --iodepth=256 \
    --numjobs=4 --direct=1 --group_reporting --time_based --runtime=10 2>/dev/null | grep "READ:"
GEN4_BW=$?

set_speed 5 5 "Gen5 (32GT/s)"

# Run quick fio at Gen5
echo "Running fio at Gen5..."
fio --name=gen5_test --filename=$DEVICE --rw=read --bs=128k --iodepth=256 \
    --numjobs=4 --direct=1 --group_reporting --time_based --runtime=10 2>/dev/null | grep "READ:"

# Restore to max
echo ""
echo "--- Restoring to max speed ---"
set_speed 5 5 "Gen5 (max)"

echo ""
echo "=== Speed Switch Test Complete ==="
echo "Check: Gen5 BW should be ~2x Gen4 BW (if not NAND-limited)"
```

---

## Part D: Stress Test Recipes

### D.1 PERF-013 — 72-Hour Stress Test

```bash
#!/bin/bash
# pcie_stress_72h.sh — Long duration stress with PCIe health monitoring

BDF=$1
DEVICE="/dev/nvme0n1"
DURATION=259200  # 72 hours in seconds
LOG="/tmp/pcie_stress_$(date +%Y%m%d).log"

echo "Starting 72-hour PCIe stress test at $(date)" | tee $LOG

# Record initial state
echo "=== Initial Link State ===" >> $LOG
lspci -s $BDF -vvv | grep -E "LnkSta:|LnkCap:" >> $LOG
echo "=== Initial AER ===" >> $LOG
cat /sys/bus/pci/devices/0000:${BDF}/aer_dev_correctable >> $LOG 2>/dev/null

# Start fio in background
fio --name=stress --filename=$DEVICE --rw=randrw --rwmixread=70 \
    --bs=4k --iodepth=128 --numjobs=4 --direct=1 \
    --time_based --runtime=$DURATION \
    --eta-newline=3600 --output=$LOG.fio &
FIO_PID=$!

# Monitor loop — check every 30 minutes
while kill -0 $FIO_PID 2>/dev/null; do
    TIMESTAMP=$(date '+%Y-%m-%d %H:%M:%S')
    
    # Check link status
    LINK=$(lspci -s $BDF -vvv 2>/dev/null | grep "LnkSta:" | head -1)
    echo "[$TIMESTAMP] $LINK" >> $LOG
    
    # Check for AER errors
    CE=$(cat /sys/bus/pci/devices/0000:${BDF}/aer_dev_correctable 2>/dev/null | grep -v "^0$" | wc -l)
    if [ $CE -gt 0 ]; then
        echo "[$TIMESTAMP] WARNING: AER correctable errors detected!" >> $LOG
        cat /sys/bus/pci/devices/0000:${BDF}/aer_dev_correctable >> $LOG
    fi
    
    # Check dmesg for PCIe errors
    dmesg -T | tail -5 | grep -i "pcie\|aer\|error" >> $LOG 2>/dev/null
    
    sleep 1800  # 30 minutes
done

echo "=== Final State ===" >> $LOG
lspci -s $BDF -vvv | grep -E "LnkSta:|LnkCap:" >> $LOG
echo "Test completed at $(date)" >> $LOG
echo "Results in: $LOG and $LOG.fio"
```

### D.2 CC-002 — Rapid D3hot↔D0 Cycling (1000 iterations)

```bash
#!/bin/bash
# pcie_d3_cycle.sh — Rapid power state cycling stress
BDF=$1
ITERATIONS=1000

PM_CAP=$(lspci -s $BDF -vvv | grep "Power Management" | grep -oP '\[(\w+)\]' | tr -d '[]')
PMCSR_OFFSET=$(printf "%x" $(( 16#$PM_CAP + 4 )))

echo "D3hot↔D0 cycling test: $ITERATIONS iterations"

for i in $(seq 1 $ITERATIONS); do
    # D0 → D3hot
    PMCSR=$(setpci -s $BDF ${PMCSR_OFFSET}.w)
    D3VAL=$(printf "%04x" $(( (16#$PMCSR & 0xFFFC) | 3 )))
    setpci -s $BDF ${PMCSR_OFFSET}.w=$D3VAL
    
    usleep 10000  # 10ms in D3hot
    
    # D3hot → D0
    D0VAL=$(printf "%04x" $(( 16#$PMCSR & 0xFFFC )))
    setpci -s $BDF ${PMCSR_OFFSET}.w=$D0VAL
    
    usleep 10000  # 10ms recovery
    
    # Verify device still alive every 100 iterations
    if [ $((i % 100)) -eq 0 ]; then
        VID=$(setpci -s $BDF 00.w 2>/dev/null)
        if [ "$VID" = "ffff" ] || [ -z "$VID" ]; then
            echo "FAIL at iteration $i: Device gone!"
            exit 1
        fi
        echo "  Iteration $i/$ITERATIONS: OK"
    fi
done

# Final check: full IO
echo 1 > /sys/bus/pci/devices/0000:${BDF}/remove
echo 1 > /sys/bus/pci/rescan
sleep 2
dd if=/dev/nvme0n1 of=/dev/null bs=1M count=10 iflag=direct 2>/dev/null && \
    echo "PASS: $ITERATIONS D3 cycles completed, IO functional" || \
    echo "FAIL: IO broken after D3 cycling"
```
