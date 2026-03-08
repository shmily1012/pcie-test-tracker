# Common PCIe Failures in NVMe SSDs

> Field data and industry experience: the most common PCIe issues found in NVMe SSD validation.
> Use this as a checklist to ensure your test plan covers real-world failure modes.

---

## Top 10 Most Common PCIe Issues (Ranked by Frequency)

### 1. 🔴 Link Training Failure at Target Speed
**Symptom**: Device trains at Gen3 instead of Gen5, or doesn't enumerate at all.
**Root Cause**: 
- TX equalization coefficients out of spec
- Channel insertion loss too high (cable/trace too long)
- REFCLK jitter exceeds budget
- PERST# timing violation (released too early before power stable)

**Test Coverage Needed**:
- PHY-001~006 (TX eye quality)
- PHY-007~008 (RX tolerance)
- PHY-013~014 (SSC, REFCLK)
- LT-008~009 (speed negotiation)
- LT-021 (PERST# timing)
- EQ-001~006 (equalization)

### 2. 🔴 Link Width Degradation (x4 → x2 or x1)
**Symptom**: lspci shows Width x2 or x1 instead of x4.
**Root Cause**:
- One or more lanes have poor signal integrity
- Lane reversal not handled correctly
- PCB routing issue on specific lanes
- Broken solder joint on connector

**Test Coverage Needed**:
- LT-005 (lane negotiation)
- LT-006 (lane reversal)
- LT-013~014 (width change)
- LM-006 (per-lane margining)
- PHY-012 (crosstalk)

### 3. 🟡 Completion Timeout Errors
**Symptom**: `dmesg` shows "completion timeout" errors. IO hangs or times out.
**Root Cause**:
- Device firmware too slow to respond to MRd
- Flow control credit exhaustion → device can't send CplD
- Internal device hang (firmware bug)
- ASPM L1 exit too slow → first TLP after wake gets CTO

**Test Coverage Needed**:
- ERR-013 (CTO injection)
- CC-007 (CTO at different timeout values)
- DLL-008 (FC credit overflow)
- PM-015 (ASPM L1 + traffic burst)
- CC-012 (ASPM + heavy IO transitions)

### 4. 🟡 Link Retrain Events During Operation
**Symptom**: LeCroy trace shows unexpected Recovery state entries. Possible brief IO stalls.
**Root Cause**:
- Marginal signal quality → occasional bit errors → Recovery
- Temperature variation shifts eye → Recovery
- EMI interference
- Unstable equalization

**Test Coverage Needed**:
- LT-010 (auto recovery)
- LT-012 (re-equalization)
- LM-001~011 (lane margining at different temps)
- PERF-013 (72h stress → check for retrain events)
- CC-001 (link stability after long idle)
- G5-033 (channel loss tolerance)

### 5. 🟡 ASPM-Related Failures
**Symptom**: Device works fine with ASPM disabled. Fails (CTO, link drop) with ASPM L1 enabled.
**Root Cause**:
- L1 exit latency exceeds advertised value
- Device doesn't wake up properly from L1.2 (CLKREQ# de-asserted)
- Race condition: IO issued before link fully back in L0

**Test Coverage Needed**:
- PM-010~016 (all ASPM tests)
- CC-012 (ASPM + heavy IO transitions)
- FW-005 (BIOS ASPM setting)

### 6. 🟡 Surprise Removal / Hot-Plug Crash
**Symptom**: System kernel panic or NMI when device physically removed.
**Root Cause**:
- Driver doesn't handle surprise removal gracefully
- AER or DPC not configured → system doesn't contain error
- Pending DMA writes to removed device → MCE

**Test Coverage Needed**:
- PLAT-013 (surprise removal)
- ERR-011 (Surprise Down Error)
- ERR-033 (DPC containment)
- RST-008 (reset during active IO)

### 7. 🟡 Power State Transition Failure
**Symptom**: Device doesn't wake from D3hot, or data loss after D3cold.
**Root Cause**:
- No_Soft_Reset bit incorrectly set
- Device doesn't save/restore context properly
- PME# not generated correctly
- PERST# not re-asserted on D3cold → D0

**Test Coverage Needed**:
- PM-001~005 (D-state transitions)
- CC-002 (rapid D3 cycling)
- FW-008 (S3 suspend/resume)
- NP-025 (D3hot + NVMe state)

### 8. 🟡 FLR Not Cleaning Up Properly
**Symptom**: After FLR, device hangs or doesn't reinitialize correctly.
**Root Cause**:
- Pending DMA not flushed before FLR
- Transaction Pending bit not set/cleared correctly
- BAR or config space corruption after FLR

**Test Coverage Needed**:
- RST-004~005 (FLR basic + Transaction Pending)
- NP-024 (FLR + NVMe state)
- CC-003 (rapid FLR cycling)
- CC-004 (SBR during active DMA)

### 9. 🟢 MSI-X Interrupt Issues
**Symptom**: Interrupts not delivered, or delivered to wrong CPU/vector.
**Root Cause**:
- MSI-X table not programmed correctly
- Interrupt masking not working
- Vector allocation mismatch between NVMe driver and MSI-X table

**Test Coverage Needed**:
- INT-002~006 (MSI-X tests)
- INT-009 (multi-queue mapping)
- NP-017 (interrupt ordering)

### 10. 🟢 MPS/MRRS Misconfiguration
**Symptom**: Suboptimal performance, or TLP size violations.
**Root Cause**:
- BIOS sets MPS too low (128B instead of 512B)
- Device sends TLP larger than MPS
- MRRS set to 4096 but device only supports 512

**Test Coverage Needed**:
- TLP-010~011 (MPS/MRRS verification)
- PERF-006~007 (MPS/MRRS impact on throughput)
- CC-008 (MPS mismatch)

---

## Failure Modes by Development Phase

### Silicon Bring-up (RTL → First Silicon)
Most common issues:
1. Link doesn't train at all (PHY timing bugs)
2. Config space not accessible (BAR mapping bug)
3. DMA to wrong address (address translation bug)
4. Interrupts don't fire (MSI-X programming bug)

### Firmware Development
Most common issues:
1. Completion Timeout under stress (FW performance)
2. FLR doesn't clean up (FW state machine)
3. Shutdown leaves dangling DMA (FW shutdown sequence)
4. Link retrain after FW update (FW reset path)

### Pre-Production Validation
Most common issues:
1. ASPM failures (power management integration)
2. Platform-specific link training issues
3. Thermal throttle + link instability
4. Surprise removal crash

### Production / Field
Most common issues:
1. Link width degradation (connector wear, solder)
2. Intermittent CTO (marginal SI + temperature)
3. BIOS update breaks enumeration (BIOS compatibility)
4. Customer-specific platform interop

---

## Red Flags in Test Results

| Observation | What It Means | Action |
|-------------|--------------|--------|
| Link trains at lower Gen than expected | SI issue or EQ failure | Run PHY + EQ + Margin tests |
| AER Correctable Errors > 0 at boot | Marginal link, bit errors during training | Run Lane Margining, check per-lane |
| AER CE count increases over time | Degrading link | Check temperature, remeasure SI |
| Link speed/width different between boots | Non-deterministic training | Capture LeCroy traces on 10 boots, analyze |
| Completion Timeout only under load | Credit exhaustion or FW bottleneck | Run DLL-008, check FC credits on LeCroy |
| Device disappears from lspci | Fatal error → link down | Check AER UCE, dmesg, LeCroy |
| D3→D0 sometimes fails | PM state machine bug | Run CC-002 (1000 cycle stress) |
| Performance drops after 1 hour | Thermal throttle | Monitor Tcase, run CC-014 |
| Works on Intel, fails on AMD (or vice versa) | RC implementation difference | Add both to interop matrix, capture LTSSM |
