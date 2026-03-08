# PCI-SIG Compliance Workshop Checklist — U.2 Gen4/Gen5 NVMe

> What PCI-SIG plugfest actually tests. Use this to prepare before attending.
> Based on publicly available PCI-SIG Compliance Program requirements.

---

## Pre-Workshop Preparation

### Hardware to Bring
- [ ] 3+ DUT samples (they may keep one for extended testing)
- [ ] U.2 to CEM adapter card (for test fixture mounting)
- [ ] Extra SFF-8643 cables (0.5m)
- [ ] Device datasheet with TX/RX specs
- [ ] FW image on USB drive (in case re-flash needed)

### Information to Prepare
- [ ] Vendor ID, Device ID, Subsystem VID/DID
- [ ] Supported Gen speeds (Gen1/2/3/4/5)
- [ ] Supported lane widths (x1/x2/x4)
- [ ] ASPM support (L0s/L1/L1.1/L1.2)
- [ ] FLR support (yes/no)
- [ ] SR-IOV support (yes/no, number of VFs)
- [ ] Device power consumption (idle, max active)
- [ ] Internal TX EQ presets and RX EQ settings
- [ ] BAR sizes

---

## Compliance Test Categories

### 1. ✅ Electrical Compliance (Required)

These are the **most important** tests. Fail = no compliance certification.

| Test | What They Measure | Our Prep Test IDs |
|------|------------------|-------------------|
| TX Eye Diagram @ Gen4 (16GT/s) | Eye height, width, mask margin | PHY-002, U2SI-001 |
| TX Eye Diagram @ Gen5 (32GT/s) | PAM4 3-eye measurement | PHY-001, G5-001~003, U2SI-002 |
| TX De-emphasis | Pre-shoot and de-emphasis at each preset | PHY-005, G5-021 |
| TX Jitter (Tj, Rj, Dj) | Total, random, deterministic jitter | PHY-006 |
| TX Rise/Fall Time | Signal transition timing | PHY-003 |
| TX Impedance (return loss) | S11 at connector | PHY-011 |
| RX Tolerance (stressed eye) | BER < 1e-12 with stressed input | PHY-007~008 |
| Receiver Detection | Current pulse characteristics | LTSSM-D01 |

**How to prepare**: Run TX eye measurement on your own scope with U.2 test fixture. If any margin is tight (<10%), fix before attending.

### 2. ✅ LTSSM Compliance (Required)

| Test | What They Check | Our Prep Test IDs |
|------|----------------|-------------------|
| Cold boot link training | Full Detect→L0 sequence | LT-001 |
| Speed negotiation | Correct Gen4/Gen5 negotiation | LT-008 |
| Equalization (Gen3+) | EQ Phase 0~3 completion | EQ-001~006, G5-020~023 |
| Recovery | Recovery entry/exit behavior | LT-010~012 |
| PERST# timing | PERST# assertion/release timing | LT-021, CEM-005 |
| L0s entry/exit | ASPM L0s behavior | PM-012 |
| L1 entry/exit | ASPM L1 + PM L1 | PM-013~014 |

### 3. ✅ Lane Margining (Required for Gen5)

| Test | What They Check | Our Prep Test IDs |
|------|----------------|-------------------|
| Margining Ready | Device reports margining capable | LM-001 |
| Timing margin all lanes | Timing margin left/right per lane | LM-002~006 |
| Voltage margin all lanes | Voltage margin up/down per lane | LM-004~006 |
| Independent error sampler | Margin without disturbing IO | LM-008 |

**This is NEW for Gen5** — many devices fail here. Test thoroughly before attending.

### 4. ✅ Configuration/Protocol Compliance (Required)

| Test | What They Check | Our Prep Test IDs |
|------|----------------|-------------------|
| Config space registers | All required registers present with correct values | CFG-001~055 |
| PCIe capability registers | DevCap, LinkCap, DevCap2, LinkCap2 | CFG-020~031 |
| Extended capabilities | AER, SN, Power Budget, L1 PM Substates | CFG-040~055 |
| MSI-X | Table, PBA, masking | INT-002~006 |
| BAR0 | 64-bit, non-prefetchable, correct size | CFG-005, NP-002 |

### 5. ✅ Interoperability Testing (Workshop-specific)

At the workshop, your device is tested against:
- Multiple Root Complex implementations (Intel, AMD, ARM)
- Multiple PCIe switch implementations (Broadcom, Microchip)
- Other endpoint devices (cross-interference)

**Prep**: Run your device on at least 2 different platforms (Intel + AMD) before attending.

---

## Common Plugfest Failures

Based on industry experience, these are the most frequent plugfest failures:

### 1. TX Eye Margin Too Tight (30% of failures)
```
Symptom: Eye diagram fails mask at Gen5
Root cause: PCB layout, connector SI, or TX EQ preset selection
Fix: Adjust TX preset, improve PCB routing, add equalization
Prevention: Measure on your own scope first!
```

### 2. Lane Margining Not Working (20% of failures)
```
Symptom: Margining returns NAK or wrong values
Root cause: FW didn't implement margining correctly
Fix: FW update to implement PCIe §8.3 correctly
Prevention: Test with LeCroy or Linux margining tool
```

### 3. EQ Phase Timeout (15% of failures)
```
Symptom: EQ phases take too long or don't complete at Gen5
Root cause: RX equalization convergence issue
Fix: Tune CTLE/DFE coefficients, adjust adaptation algorithm
Prevention: Capture LeCroy EQ trace, verify all 4 phases complete < 24ms each
```

### 4. Config Space Register Errors (15% of failures)
```
Symptom: Wrong capability ID, missing extended cap, wrong reset values
Root cause: RTL/FW config space implementation bugs
Fix: Review spec §7.5, fix register defaults
Prevention: Run pcie_full_audit.sh, compare against spec
```

### 5. ASPM Issues (10% of failures)
```
Symptom: L1 entry/exit problems, link drops after L1
Root cause: Clock recovery time, CLKREQ# implementation
Fix: Tune L1 exit latency, fix CLKREQ# timing
Prevention: CC-012 (ASPM + IO cycling), PM-013~015
```

### 6. PERST# Timing Violation (10% of failures)
```
Symptom: Device starts training before PERST# fully de-asserted
Root cause: PERST# input threshold or debounce issue
Fix: Add input filtering, check VIH/VIL thresholds
Prevention: Measure with scope, verify per CEM spec
```

---

## Timeline: How to Prepare

### 3 Months Before Workshop
- [ ] Run all PHY electrical tests on own equipment
- [ ] Fix any TX eye margin issues
- [ ] Verify config space against spec (use audit script)
- [ ] Test on 2+ platforms (Intel + AMD)

### 1 Month Before
- [ ] Run full LTSSM compliance capture (LeCroy)
- [ ] Run lane margining on all 4 lanes
- [ ] Run EQ phase capture at Gen4 and Gen5
- [ ] Fix any issues found
- [ ] Prepare final FW image

### 1 Week Before
- [ ] Final regression: pcie_full_audit.sh + performance baseline
- [ ] Prepare 3+ DUT samples with final FW
- [ ] Prepare documentation package
- [ ] Ship equipment to workshop venue

---

## Post-Workshop Actions

| Outcome | Action |
|---------|--------|
| All tests PASS | Apply for PCI-SIG Integrators List |
| Minor failures | Get detailed failure report → fix → re-test at next workshop |
| Major failures | Root cause analysis → may need silicon or board redesign |

> PCI-SIG workshops are typically held quarterly. Check pci-sig.com/events for schedule.
