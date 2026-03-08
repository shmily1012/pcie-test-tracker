# U.2 NVMe SSD Power Measurement Guide

> Comprehensive power measurement procedures for U.2 form factor.
> Covers PCIe power states, active workload, and thermal design.

---

## 1. Measurement Setup

### Equipment
- **DC Power Analyzer**: Keysight N6705C or equivalent (measures 12V + 3.3V rails simultaneously)
- **Current Probe**: For inline current measurement on U.2 cable
- **Oscilloscope**: 4-channel, ≥500MHz for transient analysis
- **Thermal Sensors**: Type-K thermocouples + IR camera for case temp

### U.2 Power Rails
```
Pin Group    Rail      Typical Current   Max (SFF-8639)
─────────────────────────────────────────────────────
P1-P3        12V       0.5-2.0A         2.1A (25W)
P4-P6        3.3V      0.1-0.5A         3.0A (10W)  
P7           3.3Vaux   <10mA            200mA
─────────────────────────────────────────────────────
Total budget: 25W typical for standard U.2
```

### Measurement Points
```
Option A (preferred): DC Power Analyzer with sense leads
  - 12V supply → DPA Channel 1 → U.2 pin
  - 3.3V supply → DPA Channel 2 → U.2 pin
  - DPA measures V and I simultaneously, logs to CSV

Option B: Inline shunt + scope
  - Insert 10mΩ shunt resistor on 12V line
  - Measure voltage across shunt → I = V/R
  - Scope channel 1: 12V rail voltage
  - Scope channel 2: 12V rail current (via shunt)
  - Scope channel 3: 3.3V rail voltage
  - Scope channel 4: PERST# signal (for timing reference)
```

---

## 2. Power States to Measure

### 2.1 PCIe Power State Measurements

| State | How to Enter | Expected Power | Duration |
|-------|-------------|----------------|----------|
| D0 Active (idle) | Boot, no IO | 3-6W | Continuous |
| D0 Active (max IO) | fio seq write max QD | 15-25W | 30s stable |
| D3hot | `setpci` PM CSR | <1W | Hold 10s |
| D3cold (PERST# asserted) | Assert PERST# or 3.3Vaux only | <100mW | Hold 10s |
| L1 (ASPM) | Enable ASPM L1, idle | 1-3W | Wait 30s |
| L1.1 | Enable L1 substates, idle | 0.5-1.5W | Wait 60s |
| L1.2 (deepest) | Enable L1.2, CLKREQ# | <500mW | Wait 60s |

### 2.2 Measurement Procedure for Each State

```bash
#!/bin/bash
# power_state_measure.sh — Measure power in each PCIe state
# Start DPA data logging before running this script

BDF=$1
DEVICE="/dev/nvme0n1"

echo "=== Power Measurement Sequence ==="
echo "Ensure DPA is logging. Press Enter to start each phase."

# Phase 1: Idle power (D0, no IO)
echo "Phase 1: D0 IDLE — measuring for 60 seconds"
read -p "Press Enter..."
sleep 60
echo "  → Record: D0_Idle average power"

# Phase 2: Sequential Read
echo "Phase 2: Sequential Read — 60 seconds"
read -p "Press Enter..."
fio --name=power_seqrd --filename=$DEVICE --rw=read --bs=128k \
    --iodepth=256 --numjobs=4 --direct=1 --time_based --runtime=60 \
    --output=/dev/null
echo "  → Record: Seq_Read peak and average power"

# Phase 3: Sequential Write (highest power typically)
echo "Phase 3: Sequential Write — 60 seconds"
read -p "Press Enter..."
fio --name=power_seqwr --filename=$DEVICE --rw=write --bs=128k \
    --iodepth=256 --numjobs=4 --direct=1 --time_based --runtime=60 \
    --output=/dev/null
echo "  → Record: Seq_Write peak and average power (should be highest)"

# Phase 4: Random Mixed (typical DC workload)
echo "Phase 4: Random Mixed 70/30 — 60 seconds"
read -p "Press Enter..."
fio --name=power_mixed --filename=$DEVICE --rw=randrw --rwmixread=70 --bs=4k \
    --iodepth=128 --numjobs=4 --direct=1 --time_based --runtime=60 \
    --output=/dev/null
echo "  → Record: Mixed average power"

# Phase 5: Return to idle, measure idle again
echo "Phase 5: Back to Idle — 60 seconds"
sleep 60
echo "  → Record: D0_Idle (post-workload, GC may run)"

# Phase 6: D3hot
echo "Phase 6: D3hot — 30 seconds"
read -p "Press Enter..."
PM_CAP=$(lspci -s $BDF -vvv | grep "Power Management" | grep -oP '\[(\w+)\]' | tr -d '[]')
PMCSR_OFF=$(printf "%x" $(( 16#$PM_CAP + 4 )))
PMCSR=$(setpci -s $BDF ${PMCSR_OFF}.w)
D3VAL=$(printf "%04x" $(( (16#$PMCSR & 0xFFFC) | 3 )))
setpci -s $BDF ${PMCSR_OFF}.w=$D3VAL
echo "  Device in D3hot"
sleep 30
echo "  → Record: D3hot power"
# Restore D0
D0VAL=$(printf "%04x" $(( 16#$PMCSR & 0xFFFC )))
setpci -s $BDF ${PMCSR_OFF}.w=$D0VAL
sleep 2
echo "  Restored to D0"

echo ""
echo "=== Power Measurement Complete ==="
echo "Stop DPA logging and export CSV for analysis."
```

---

## 3. Inrush Current Measurement

Critical for U.2 hot-swap. Backplane has inrush current limit.

```
Setup:
1. Scope Channel 1: 12V rail voltage (AC coupled, 1V/div)
2. Scope Channel 2: 12V current (via current probe or shunt)
3. Scope Channel 3: 3.3V rail voltage
4. Scope Channel 4: PERST# signal
5. Trigger: Rising edge on 12V rail

Procedure:
1. Remove U.2 drive from backplane
2. Arm scope trigger
3. Insert U.2 drive → scope captures inrush event

Measurements:
- Peak inrush current: Must be < backplane limit (typically 3-5A for 100μs)
- 12V settling time: Time for 12V to reach 95% of final value
- 3.3V vs 12V sequencing: Check which comes first

Pass Criteria:
- Peak inrush < spec limit
- No voltage dip below Vmin on other drives (backplane shared rail)
- Monotonic rise (no double-tap)
```

---

## 4. Power Consumption Budget

### Template — Fill in measured values

| State | 12V Current | 12V Power | 3.3V Current | 3.3V Power | Total Power |
|-------|-------------|-----------|---------------|------------|-------------|
| D0 Idle | ___mA | ___W | ___mA | ___W | ___W |
| Seq Read Max | ___mA | ___W | ___mA | ___W | ___W |
| Seq Write Max | ___mA | ___W | ___mA | ___W | ___W |
| Rand Mix 70/30 | ___mA | ___W | ___mA | ___W | ___W |
| D3hot | ___mA | ___W | ___mA | ___W | ___W |
| L1 (ASPM) | ___mA | ___W | ___mA | ___W | ___W |
| L1.2 | ___mA | ___W | ___mA | ___W | ___W |

### Thermal Design Power (TDP) Check

```
TDP (from datasheet): ___W
Measured max sustained: ___W (seq write, 5 min average)

If measured > TDP: 
  - Check FW power limiting
  - May need better heatsink/airflow
  
Typical U.2 NVMe SSD power consumption:
  Idle:        3-6W
  Active Read: 8-15W  
  Active Write: 12-25W
  D3hot:       <1W
```

---

## 5. PCIe Power State Transition Timing

```
Measure with oscilloscope (trigger on state change):

D0 → D3hot transition:
  Time from PM CSR write to power drop: ___μs
  Spec requirement: Device must stop all DMA within 10ms

D3hot → D0 transition:
  Time from PM CSR write to device ready: ___ms
  Spec requirement: ≤ 10ms (per PCIe spec)
  NVMe additional: May need CC.EN + CSTS.RDY polling

L0 → L1 transition (ASPM):
  Time from last TLP to L1 entry: ___μs
  Check: Matches L1 entrance latency reported in LnkCap

L1 → L0 transition:
  Time from IO submit to first TLP: ___μs
  Check: Matches L1 exit latency reported in LnkCap
```
