#!/bin/bash
# =============================================================================
# PCIe Full Audit Script for NVMe SSD
# =============================================================================
# Usage: sudo ./pcie_full_audit.sh [BDF]
#   BDF = Bus:Device.Function (e.g., 01:00.0)
#   If not provided, auto-detects first NVMe device.
#
# Output: JSON report + human-readable summary
# Covers: ~50 test items from the master test plan (Linux-only subset)
# =============================================================================

set -euo pipefail

# --- Auto-detect or use provided BDF ---
if [ -n "${1:-}" ]; then
    BDF="$1"
else
    BDF=$(lspci | grep -i "Non-Volatile\|NVMe" | head -1 | awk '{print $1}')
    if [ -z "$BDF" ]; then
        echo "ERROR: No NVMe device found. Provide BDF manually."
        exit 1
    fi
fi

FULL_BDF="0000:${BDF}"
SYSFS="/sys/bus/pci/devices/${FULL_BDF}"
NVME_DEV=$(ls /sys/bus/pci/devices/${FULL_BDF}/nvme/ 2>/dev/null | head -1 || true)
REPORT_DIR="/tmp/pcie_audit_$(date +%Y%m%d_%H%M%S)"
mkdir -p "$REPORT_DIR"

PASS=0; FAIL=0; WARN=0; SKIP=0; INFO=0

# --- Helper functions ---
result() {
    local id=$1 name=$2 status=$3 detail=${4:-""}
    case $status in
        PASS) ((PASS++)); icon="✅";;
        FAIL) ((FAIL++)); icon="❌";;
        WARN) ((WARN++)); icon="⚠️";;
        SKIP) ((SKIP++)); icon="⏭️";;
        INFO) ((INFO++)); icon="ℹ️";;
    esac
    echo "$icon $id: $name [$status] $detail"
    echo "{\"id\":\"$id\",\"name\":\"$name\",\"status\":\"$status\",\"detail\":\"$detail\"}" >> "$REPORT_DIR/results.jsonl"
}

read_cfg() {
    setpci -s $BDF "$1" 2>/dev/null || echo "ERROR"
}

lspci_field() {
    lspci -s $BDF -vvv 2>/dev/null | grep -oP "$1\K[^\n]+" | head -1 | xargs
}

echo "╔══════════════════════════════════════════════════════════════╗"
echo "║        PCIe Full Audit — NVMe SSD Validation               ║"
echo "╠══════════════════════════════════════════════════════════════╣"
echo "║ Device:  $BDF                                              "
echo "║ Date:    $(date)                                           "
echo "║ Kernel:  $(uname -r)                                       "
echo "║ Report:  $REPORT_DIR/                                      "
echo "╚══════════════════════════════════════════════════════════════╝"
echo ""

# Save full lspci for reference
lspci -s $BDF -vvv > "$REPORT_DIR/lspci_full.txt" 2>&1
lspci -s $BDF -xxxx > "$REPORT_DIR/lspci_hex.txt" 2>&1

# ==========================================================================
echo "━━━ Section 1: Device Identity (CFG-001 ~ CFG-009) ━━━"
# ==========================================================================

# CFG-001: Vendor/Device ID
VID=$(read_cfg "00.w")
DID=$(read_cfg "02.w")
if [ "$VID" != "ffff" ] && [ "$VID" != "ERROR" ]; then
    result "CFG-001" "Vendor/Device ID" "PASS" "VID=0x${VID} DID=0x${DID}"
else
    result "CFG-001" "Vendor/Device ID" "FAIL" "VID=0x${VID} — device not detected"
    echo "FATAL: Device not accessible. Aborting."
    exit 1
fi

# CFG-002: Command Register
CMD=$(read_cfg "04.w")
BME=$(( (16#$CMD >> 2) & 1 ))
MSE=$(( (16#$CMD >> 1) & 1 ))
if [ $BME -eq 1 ] && [ $MSE -eq 1 ]; then
    result "CFG-002" "Command Register" "PASS" "BusMaster=$BME MemSpace=$MSE CMD=0x${CMD}"
else
    result "CFG-002" "Command Register" "WARN" "BusMaster=$BME MemSpace=$MSE — may not be fully enabled"
fi

# CFG-004: Class Code
BCC=$(read_cfg "0b.b")
SCC=$(read_cfg "0a.b")
PI=$(read_cfg "09.b")
if [ "$BCC" = "01" ] && [ "$SCC" = "08" ] && [ "$PI" = "02" ]; then
    result "CFG-004" "Class Code (NVMe)" "PASS" "${BCC}:${SCC}:${PI}"
else
    result "CFG-004" "Class Code" "FAIL" "Got ${BCC}:${SCC}:${PI}, expected 01:08:02"
fi

# CFG-005: BAR0
BAR0_RAW=$(read_cfg "10.l")
BAR0_TYPE=$(( (16#$BAR0_RAW >> 1) & 0x3 ))
BAR0_PREFETCH=$(( (16#$BAR0_RAW >> 3) & 0x1 ))
BAR0_INFO=$(lspci -s $BDF -vvv | grep "Region 0" || echo "NOT FOUND")

if [ $BAR0_TYPE -eq 2 ] && [ $BAR0_PREFETCH -eq 0 ]; then
    result "CFG-005" "BAR0 (64-bit, non-prefetch)" "PASS" "$BAR0_INFO"
elif [ $BAR0_TYPE -ne 2 ]; then
    result "CFG-005" "BAR0 type" "FAIL" "Type=$BAR0_TYPE (expected 2=64-bit)"
elif [ $BAR0_PREFETCH -ne 0 ]; then
    result "CFG-005" "BAR0 prefetchable" "FAIL" "Prefetchable=1 (NVMe requires non-prefetchable)"
fi

# CFG-007: Subsystem VID/DID
SVID=$(read_cfg "2c.w")
SDID=$(read_cfg "2e.w")
if [ "$SVID" != "0000" ] && [ "$SVID" != "ffff" ]; then
    result "CFG-007" "Subsystem VID/DID" "PASS" "SVID=0x${SVID} SDID=0x${SDID}"
else
    result "CFG-007" "Subsystem VID/DID" "WARN" "SVID=0x${SVID} — may not be programmed"
fi

# CFG-008: Capability List Walk
CAP_PTR=$(read_cfg "34.b")
CAP_COUNT=0
CAPS_FOUND=()
OFFSET=$((16#$CAP_PTR))
while [ $OFFSET -ne 0 ] && [ $OFFSET -lt 256 ] && [ $CAP_COUNT -lt 20 ]; do
    CAP_ID=$(read_cfg "$(printf '%02x' $OFFSET).b")
    CAPS_FOUND+=("0x${CAP_ID}@0x$(printf '%02X' $OFFSET)")
    NEXT=$(read_cfg "$(printf '%02x' $(($OFFSET + 1))).b")
    OFFSET=$((16#$NEXT))
    ((CAP_COUNT++))
done
result "CFG-008" "Capability List" "PASS" "${CAP_COUNT} caps: ${CAPS_FOUND[*]}"

# ==========================================================================
echo ""
echo "━━━ Section 2: PCIe Link (CFG-020 ~ CFG-031) ━━━"
# ==========================================================================

# CFG-024: Link Capabilities
MAX_SPEED=$(lspci_field "LnkCap:.*Speed ")
MAX_WIDTH=$(lspci_field "LnkCap:.*Width x")
ASPM_SUP=$(lspci_field "ASPM ")
result "CFG-024" "Link Capabilities" "INFO" "MaxSpeed=${MAX_SPEED} MaxWidth=x${MAX_WIDTH} ASPM=${ASPM_SUP}"

# CFG-026: Link Status (actual negotiated)
CUR_SPEED=$(lspci -s $BDF -vvv | grep "LnkSta:" | head -1 | grep -oP "Speed \K[0-9.]+GT/s" || echo "UNKNOWN")
CUR_WIDTH=$(lspci -s $BDF -vvv | grep "LnkSta:" | head -1 | grep -oP "Width x\K[0-9]+" || echo "0")

if [ "${CUR_WIDTH:-0}" -ge 4 ]; then
    result "CFG-026" "Link Status" "PASS" "Speed=${CUR_SPEED} Width=x${CUR_WIDTH}"
else
    result "CFG-026" "Link Status" "WARN" "Speed=${CUR_SPEED} Width=x${CUR_WIDTH} — width may be degraded"
fi

# Check if running at max speed
if [ "$CUR_SPEED" = "$MAX_SPEED" ]; then
    result "LT-008" "Speed Negotiation" "PASS" "Running at max speed: ${CUR_SPEED}"
else
    result "LT-008" "Speed Negotiation" "WARN" "Current ${CUR_SPEED} < Max ${MAX_SPEED} — may be slot limited"
fi

# CFG-027: Device Capabilities 2
DEVCAP2=$(lspci -s $BDF -vvv | grep -A5 "DevCap2:" || echo "NOT FOUND")
CTO_RANGES=$(echo "$DEVCAP2" | grep -oP "Completion Timeout: .*" || echo "N/A")
result "CFG-027" "Device Capabilities 2" "INFO" "$CTO_RANGES"

# ==========================================================================
echo ""
echo "━━━ Section 3: Extended Capabilities (CFG-040 ~ CFG-055) ━━━"
# ==========================================================================

# CFG-040: AER
if lspci -s $BDF -vvv | grep -q "Advanced Error Reporting"; then
    result "CFG-040" "AER Capability" "PASS" "Present"
    
    # Check current error counts
    if [ -f "${SYSFS}/aer_dev_correctable" ]; then
        CE_TOTAL=$(cat ${SYSFS}/aer_dev_correctable 2>/dev/null | awk '{s+=$2} END{print s}')
        if [ "${CE_TOTAL:-0}" -gt 0 ]; then
            result "CFG-041" "AER CE Status" "WARN" "Correctable errors present (total=$CE_TOTAL)"
            cat ${SYSFS}/aer_dev_correctable >> "$REPORT_DIR/aer_ce.txt" 2>/dev/null
        else
            result "CFG-041" "AER CE Status" "PASS" "No correctable errors"
        fi
    fi
    
    if [ -f "${SYSFS}/aer_dev_fatal" ]; then
        FE_TOTAL=$(cat ${SYSFS}/aer_dev_fatal 2>/dev/null | awk '{s+=$2} END{print s}')
        if [ "${FE_TOTAL:-0}" -gt 0 ]; then
            result "CFG-042" "AER UCE Status" "FAIL" "Uncorrectable errors present (total=$FE_TOTAL)"
        else
            result "CFG-042" "AER UCE Status" "PASS" "No uncorrectable errors"
        fi
    fi
else
    result "CFG-040" "AER Capability" "FAIL" "Not found — required for PCIe endpoints"
fi

# CFG-045: Serial Number
if lspci -s $BDF -vvv | grep -q "Device Serial Number"; then
    DSN=$(lspci -s $BDF -vvv | grep "Device Serial Number" | awk '{print $NF}')
    result "CFG-045" "Device Serial Number" "PASS" "$DSN"
else
    result "CFG-045" "Device Serial Number" "INFO" "Not present (optional)"
fi

# CFG-047: L1 PM Substates
if lspci -s $BDF -vvv | grep -q "L1SubCap"; then
    L1SUB=$(lspci -s $BDF -vvv | grep -A3 "L1SubCap" | head -4)
    result "CFG-047" "L1 PM Substates" "PASS" "Supported"
else
    result "CFG-047" "L1 PM Substates" "INFO" "Not supported"
fi

# CFG-051: Physical Layer 32 GT/s Cap (Gen5)
if lspci -s $BDF -vvv | grep -q "Physical Layer 32"; then
    result "CFG-051" "Gen5 PHY Cap" "PASS" "Present"
else
    if echo "$MAX_SPEED" | grep -q "32"; then
        result "CFG-051" "Gen5 PHY Cap" "FAIL" "Gen5 device missing 32GT/s cap"
    else
        result "CFG-051" "Gen5 PHY Cap" "SKIP" "Not a Gen5 device"
    fi
fi

# CFG-055: Full config space read
echo "  Reading 4KB config space..." 
ECAM_OK=true
for off in $(seq 0 256 3840); do
    HEX=$(printf "%03x" $off)
    if ! setpci -s $BDF "${HEX}.l" > /dev/null 2>&1; then
        ECAM_OK=false
        break
    fi
done
if $ECAM_OK; then
    result "CFG-055" "4KB Config Space Read" "PASS" "No hangs"
else
    result "CFG-055" "4KB Config Space Read" "FAIL" "Hang at offset 0x${HEX}"
fi

# ==========================================================================
echo ""
echo "━━━ Section 4: Interrupts (INT-001 ~ INT-004) ━━━"
# ==========================================================================

# INT-001: MSI
if lspci -s $BDF -vvv | grep -q "MSI:"; then
    MSI_INFO=$(lspci -s $BDF -vvv | grep "MSI:" | head -1)
    result "INT-001" "MSI Capability" "PASS" "$MSI_INFO"
else
    result "INT-001" "MSI Capability" "INFO" "Not present (MSI-X may be primary)"
fi

# INT-002: MSI-X
if lspci -s $BDF -vvv | grep -q "MSI-X:"; then
    MSIX_INFO=$(lspci -s $BDF -vvv | grep "MSI-X:" | head -1)
    MSIX_COUNT=$(echo "$MSIX_INFO" | grep -oP "Count=\K[0-9]+" || echo "?")
    result "INT-002" "MSI-X Capability" "PASS" "Count=${MSIX_COUNT} ${MSIX_INFO}"
else
    result "INT-002" "MSI-X Capability" "FAIL" "Not found — required for NVMe"
fi

# ==========================================================================
echo ""
echo "━━━ Section 5: NVMe-PCIe Interaction (NP-001 ~ NP-005) ━━━"
# ==========================================================================

if [ -n "$NVME_DEV" ]; then
    # NP-001: NVMe registers
    REGS=$(nvme show-regs /dev/${NVME_DEV} 2>/dev/null)
    if [ -n "$REGS" ]; then
        result "NP-001" "NVMe Controller Registers" "PASS" "Readable via show-regs"
        echo "$REGS" > "$REPORT_DIR/nvme_regs.txt"
        
        # NP-004: Check DSTRD
        DSTRD=$(echo "$REGS" | grep -oP "dstrd\s*:\s*\K[0-9]+" || echo "?")
        result "NP-004" "Doorbell Stride" "INFO" "DSTRD=$DSTRD"
    else
        result "NP-001" "NVMe Controller Registers" "FAIL" "Cannot read"
    fi
    
    # NP-005: Admin Queue functional
    ID_CTRL=$(nvme id-ctrl /dev/${NVME_DEV} 2>/dev/null)
    if [ -n "$ID_CTRL" ]; then
        MN=$(echo "$ID_CTRL" | grep "^mn " | awk -F: '{print $2}' | xargs)
        FW=$(echo "$ID_CTRL" | grep "^fr " | awk -F: '{print $2}' | xargs)
        SN=$(echo "$ID_CTRL" | grep "^sn " | awk -F: '{print $2}' | xargs)
        result "NP-005" "Admin Queue (Identify)" "PASS" "Model=${MN} FW=${FW} SN=${SN}"
        echo "$ID_CTRL" > "$REPORT_DIR/nvme_id_ctrl.txt"
    else
        result "NP-005" "Admin Queue" "FAIL" "Identify Controller failed"
    fi
else
    result "NP-001" "NVMe Device" "FAIL" "No NVMe device found at $BDF"
fi

# ==========================================================================
echo ""
echo "━━━ Section 6: Basic IO (DMA-001, DMA-002) ━━━"
# ==========================================================================

NVME_NS="/dev/${NVME_DEV}n1"
if [ -b "$NVME_NS" 2>/dev/null ]; then
    # DMA-001: Read
    if dd if=$NVME_NS of=/dev/null bs=1M count=10 iflag=direct 2>/dev/null; then
        result "DMA-001" "DMA Read (10MB)" "PASS" ""
    else
        result "DMA-001" "DMA Read" "FAIL" "dd read failed"
    fi
    
    # Quick bandwidth check
    BW_RESULT=$(dd if=$NVME_NS of=/dev/null bs=1M count=1000 iflag=direct 2>&1 | tail -1)
    BW_MBS=$(echo "$BW_RESULT" | grep -oP "[0-9.]+ [GM]B/s" || echo "N/A")
    result "PERF-001" "Quick Bandwidth" "INFO" "$BW_MBS (dd, not peak)"
else
    result "DMA-001" "DMA Read" "SKIP" "No namespace found at $NVME_NS"
fi

# ==========================================================================
echo ""
echo "━━━ Section 7: Power Management (PM-001 ~ PM-005) ━━━"
# ==========================================================================

# Read current power state
PM_CAP_LINE=$(lspci -s $BDF -vvv | grep "Power Management" | head -1)
if [ -n "$PM_CAP_LINE" ]; then
    PM_STATUS=$(lspci -s $BDF -vvv | grep "Status:" | grep -oP "D[0-3]" | head -1)
    result "PM-001" "Power State" "INFO" "Current state: ${PM_STATUS:-unknown}"
    
    NO_SOFT_RST=$(lspci -s $BDF -vvv | grep "NoSoftRst" | head -1 || echo "")
    result "PM-005" "No_Soft_Reset" "INFO" "${NO_SOFT_RST:-not found}"
else
    result "PM-001" "PM Capability" "FAIL" "Not found"
fi

# Check ASPM status
ASPM_STATUS=$(lspci -s $BDF -vvv | grep "LnkCtl:" | grep -oP "ASPM \K[^\s;]+" || echo "Disabled")
result "PM-010" "ASPM Status" "INFO" "Current: ${ASPM_STATUS}"

# ==========================================================================
echo ""
echo "━━━ Section 8: Reset Capabilities (RST-004) ━━━"
# ==========================================================================

if lspci -s $BDF -vvv | grep -q "FLReset+"; then
    result "RST-004" "FLR Capable" "PASS" ""
else
    result "RST-004" "FLR Capable" "WARN" "FLR not supported"
fi

# ==========================================================================
echo ""
echo "━━━ Section 9: dmesg Errors ━━━"
# ==========================================================================

PCIE_ERRORS=$(dmesg | grep -ic "pcie\|aer.*error\|nmi.*pci" 2>/dev/null || echo "0")
if [ "$PCIE_ERRORS" -eq 0 ]; then
    result "SYS-001" "dmesg PCIe Errors" "PASS" "No PCIe errors in kernel log"
else
    result "SYS-001" "dmesg PCIe Errors" "WARN" "$PCIE_ERRORS PCIe-related messages found"
    dmesg | grep -i "pcie\|aer.*error" > "$REPORT_DIR/dmesg_errors.txt" 2>/dev/null
fi

# ==========================================================================
echo ""
echo "══════════════════════════════════════════════════════════════"
echo "  SUMMARY"
echo "══════════════════════════════════════════════════════════════"
echo "  ✅ PASS: $PASS"
echo "  ❌ FAIL: $FAIL"
echo "  ⚠️  WARN: $WARN"
echo "  ⏭️  SKIP: $SKIP"
echo "  ℹ️  INFO: $INFO"
echo ""
echo "  Report dir: $REPORT_DIR/"
echo "  Files: lspci_full.txt, lspci_hex.txt, results.jsonl"
[ -f "$REPORT_DIR/nvme_regs.txt" ] && echo "         nvme_regs.txt, nvme_id_ctrl.txt"
[ -f "$REPORT_DIR/aer_ce.txt" ] && echo "         aer_ce.txt (correctable errors)"
[ -f "$REPORT_DIR/dmesg_errors.txt" ] && echo "         dmesg_errors.txt"
echo "══════════════════════════════════════════════════════════════"
