# U.2 Signal Integrity Guide for Gen4/Gen5 NVMe SSD

> U.2 has unique SI challenges: SFF-8639 connector, cables (SFF-8643/8644),
> backplane traces, and potential retimers. This guide covers what to measure and how.

---

## 1. U.2 PCIe Signal Path

```
SSD Controller TX ──► PCB trace ──► SFF-8639 connector ──► Cable/Backplane trace
                                                                    │
                                                              [Optional Retimer]
                                                                    │
                    ──► Root Complex RX ◄── PCB trace ◄── Connector ◄┘

Total channel loss budget (Gen5 x4):
  SSD PCB trace:     2-4 dB @ 16 GHz
  SFF-8639 connector: 1-2 dB
  Cable (0.5m):      4-8 dB
  Backplane trace:   2-6 dB  
  Server connector:  1-2 dB
  Server PCB trace:  2-4 dB
  ────────────────────────────
  Total:             12-26 dB @ 16 GHz (Nyquist for 32GT/s)

Gen5 loss budget: ~28-30 dB max (with retimer: ~40 dB+)
Gen4 loss budget: ~28-30 dB max (more margin since NRZ)
```

---

## 2. Measurement Points (TP = Test Point)

```
Per PCIe Base Spec:

TP1 (near-end TX):    At SSD controller TX ball
TP2 (package exit):   At SSD connector (SFF-8639 pin)
TP3 (far-end RX):     At host RC connector pin  
TP4 (RX EQ output):   At host RC RX after equalization

For U.2 SSD validation, measure at:
- TP2: SFF-8639 connector (your TX output)
- TP3: After cable/backplane (what the host receives)

Fixture requirements:
- SFF-8639 breakout board for probing
- High-BW differential probe (≥50 GHz for Gen5)
- Calibrated channel (de-embedding required)
```

---

## 3. TX Compliance Measurements

### 3.1 Gen4 (16 GT/s, NRZ)

| Measurement | Spec Limit | Typical Good | Tool |
|-------------|-----------|-------------|------|
| Eye Height (min) | ≥ 80 mV (at TP2) | 120-200 mV | Scope |
| Eye Width (min) | ≥ 0.30 UI | 0.40-0.55 UI | Scope |
| Total Jitter (Tj) | ≤ 0.30 UI | 0.15-0.25 UI | Scope |
| Random Jitter (Rj) | ≤ 3.0 ps RMS | 1-2 ps | Scope |
| Deterministic Jitter (Dj) | ≤ 0.15 UI | 0.05-0.12 UI | Scope |
| TX Rise Time (20-80%) | 10-25 ps | 15-20 ps | Scope |
| Differential Impedance | 85-115 Ω | 90-100 Ω | VNA/TDR |
| Return Loss (S11) | Per template | -15 dB @ 8 GHz | VNA |
| Crossover Voltage | 0.35V-0.65V × Vdiff | Within range | Scope |

### 3.2 Gen5 (32 GT/s, PAM4)

| Measurement | Spec Limit | Notes | Tool |
|-------------|-----------|-------|------|
| Upper Eye Height | ≥ Spec min | PAM4 level 3→2 transition | Scope (≥50 GHz) |
| Middle Eye Height | ≥ Spec min | PAM4 level 2→1 transition (typically tightest) | Scope |
| Lower Eye Height | ≥ Spec min | PAM4 level 1→0 transition | Scope |
| RLM (Ratio Level Mismatch) | ≥ 0.90 | Measures PAM4 level spacing uniformity | Scope |
| Total Jitter per eye | ≤ Spec | Each of 3 eyes has own jitter budget | Scope |
| Pre-FEC BER | ≤ 1e-6 (correctable) | PAM4 accepts higher pre-FEC BER | BERT |
| Post-FEC BER | ≤ 1e-12 | After FEC correction | BERT |
| Linearity (DNL) | ≤ Spec | PAM4 level spacing non-linearity | Scope |

### Key Difference: Gen4 NRZ vs Gen5 PAM4

```
NRZ (Gen4):  2 voltage levels → 1 eye → 1 bit per symbol
PAM4 (Gen5): 4 voltage levels → 3 eyes → 2 bits per symbol

Implications:
- Gen5 PAM4 has ~6 dB less SNR than NRZ at same baud rate
- Gen5 requires FEC (Forward Error Correction) — Gen4 does not
- Gen5 eye heights are ~1/3 of Gen4 NRZ eye heights
- Gen5 is much more sensitive to noise, crosstalk, and ISI
- Gen5 TX equalization is more critical

Bottom line: Gen5 testing requires better equipment and tighter margins.
```

---

## 4. Cable Characterization

### 4.1 SFF-8643 Cable S-Parameter Measurements

```
Equipment: VNA (Vector Network Analyzer) with TDR option
           Calibration kit for SFF-8643 connectors
           Reference cable (known good)

Procedure:
1. Calibrate VNA (SOLT or TRL) at SFF-8643 connector interface
2. Connect cable (SFF-8643 to SFF-8643)
3. Measure all 16 S-parameters (4 differential lanes × 4):
   - S21 (insertion loss) per lane: Target < -8 dB @ 8 GHz (Gen4), < -12 dB @ 16 GHz (Gen5)
   - S11 (return loss) per lane: Target < -10 dB across band
   - S31, S41 (NEXT - near-end crosstalk): Target < -25 dB
   - S23, S24 (FEXT - far-end crosstalk): Target < -20 dB
4. Plot S21 vs frequency (all 4 lanes overlaid)
5. Check: All 4 lanes within 1 dB of each other (balanced)
```

### 4.2 Cable Qualification Matrix

| Cable Length | Gen4 Status | Gen5 Status | Notes |
|-------------|-------------|-------------|-------|
| 0.3m SFF-8643 | □ Pass/Fail | □ Pass/Fail | Typical internal |
| 0.5m SFF-8643 | □ Pass/Fail | □ Pass/Fail | Common deployment |
| 0.75m SFF-8643 | □ Pass/Fail | □ Pass/Fail | Extended reach |
| 1.0m SFF-8643 | □ Pass/Fail | □ Pass/Fail | Max recommended |
| 2.0m SFF-8644 (external) | □ Pass/Fail | □ Pass/Fail | Likely Gen5 fail |

---

## 5. Backplane Channel Analysis

### 5.1 Server Backplane Characterization

```
A typical 24-bay U.2 JBOF backplane:

Signal path through backplane:
  Server HBA connector ──► Backplane trace (2-6 inches) 
    ──► [Optional redriver/retimer]
    ──► Backplane trace (2-6 inches) ──► U.2 connector

Worst case: Slot farthest from HBA connector
Best case: Slot closest to HBA connector

Measurement:
1. VNA with TDR: Measure insertion loss from HBA connector to each U.2 slot
2. Identify worst-case slot (highest loss)
3. Test SSD in worst-case slot
4. Measure lane margining in worst-case slot

Expected results:
  Backplane only (no cable): 4-10 dB @ 16 GHz
  With cable: Total 8-20 dB @ 16 GHz
  Gen5 may require retimer in backplane for distant slots
```

### 5.2 Per-Slot Margin Map

```
Create a "heat map" of lane margins across all 24 slots:

Slot  Lane0  Lane1  Lane2  Lane3  Status
───────────────────────────────────────
 0    35%    33%    36%    34%    ✅ Good
 1    32%    30%    34%    31%    ✅ Good
 ...
 12   22%    20%    24%    21%    ⚠️ OK
 ...
 23   14%    12%    15%    13%    🔴 Marginal!

→ Slot 23 has marginal margin → may fail at high temp
→ Recommend retimer for distant slots or limit to Gen4
```

---

## 6. Retimer Considerations

### When is a retimer needed?

```
Channel loss at 16 GHz (Gen5 Nyquist):
  < 20 dB:  No retimer needed (direct connect)
  20-28 dB: May work without retimer if TX/RX EQ excellent
  > 28 dB:  Retimer recommended
  > 40 dB:  Two retimers needed

For typical U.2 deployment:
  Direct-attach (no cable): Usually OK for Gen5
  With 0.5m cable: Borderline for Gen5
  With 1.0m cable: Likely needs retimer for Gen5
  Through backplane + cable: Retimer usually needed for Gen5
```

### Retimer Test Items

| ID | Test | Description |
|----|------|-------------|
| RT-01 | Retimer transparency | SSD behind retimer: verify same link speed, width, functionality as direct |
| RT-02 | Retimer latency | Measure added latency: LeCroy TLP timestamp with/without retimer |
| RT-03 | Retimer EQ interaction | Verify retimer + SSD EQ cooperate (2-stage EQ) |
| RT-04 | Retimer error handling | Error injection through retimer: verify AER correct |
| RT-05 | Retimer power management | ASPM L1 through retimer: verify correct entry/exit |
| RT-06 | Retimer protocol support | Verify retimer supports all required PCIe features (LTSSM, margining) |

---

## 7. PCB Design Guidelines for U.2 SSD

> For HW team reference when designing the SSD PCB.

```
Critical traces (TX/RX differential pairs):

Impedance:     100Ω ± 10% differential
               50Ω ± 10% single-ended
Trace routing: Matched length within pair (< 5 mil skew)
               Matched length between lanes (< 100 ps skew)
Layer:         Inner stripline preferred (better shielding)
Via:           Back-drilled stubs (< 5 mil stub for Gen5)
               Anti-pad optimized for impedance matching
Spacing:       ≥ 3× trace width between pairs (crosstalk)
Reference:     Continuous ground plane under all high-speed traces

For Gen5 PAM4 (32 GT/s):
- Trace loss budget on SSD PCB: ≤ 3 dB @ 16 GHz
- Via stub length: ≤ 3 mil (back-drill required)
- Material: Megtron 6 or equivalent (low Df)
- Surface finish: ENIG or immersion silver (not HASL)
```
