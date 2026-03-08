# Spec Reference Corrections & Precision Updates
> Source: PCIe Base Spec 5.0r1.0 (NCB-PCI_Express_Base_5.0r1.0-2019-05-22), 1299 pages

> Based on reading PCIe Base Spec 5.0r1.0 (1299 pages).
> These corrections improve accuracy of the master test plan.

---

## 1. Lane Margining — Precise Requirements (§8.4.4, p.1066)

### Key Spec Facts (verbatim from spec):
- **Required at 16.0 GT/s (Gen4) and 32.0 GT/s (Gen5)** — not optional!
- **Voltage margining**: Optional at 16.0 GT/s, **Required at 32.0 GT/s**
- **Independent left/right timing**: Optional
- **Independent error sampler**: Optional (but critical for non-intrusive margining)
- Must work **while Link is in L0 state** (live traffic)
- **No additional external hardware** permitted for margining to function

### Margining Parameters (Table 8-11):

| Parameter | Min | Max | Description |
|-----------|-----|-----|-------------|
| MNumTimingSteps | 6 | 63 | Timing steps from default. Must cover ≥ ±0.2 UI |
| MMaxTimingOffset | 20% | 50% | Max timing offset as % of nominal UI |
| MNumVoltageSteps | 32 | 127 | Voltage steps from default. Must cover ≥ ±50mV |
| MMaxVoltageOffset | 5% | 50% | Max voltage offset as % of 1V |
| MSamplingRateVoltage | 0 | 63 | 0=1:64 ratio, 63=64:64 (all bits tested) |
| MSamplingRateTiming | 0 | 63 | Same as voltage |
| MMaxLanes | 0 | 31 | Max lanes that can margin simultaneously (should be ≥ link width - 1) |
| MErrorCount | 0 | 63 | Saturates at 63 |
| MSampleCount | 0 | 127 | 3×log2(bits margined), saturates at 127 (~5.54×10¹² bits) |

### Test Plan Updates Needed:
- LM-001: Check MNumTimingSteps ≥ 6
- LM-002/003: Verify MMaxTimingOffset ≥ 20% of UI
- LM-004/005: At Gen5 (32GT/s), voltage margining is REQUIRED (not optional)
- LM-008: Check MIndErrorSampler — if 0, margining WILL produce errors in data stream
- Add test: Verify MMaxLanes ≥ 3 (for x4 link)

---

## 2. Completion Timeout Ranges (§7.8.3.2 DevCap2, p.753)

### CTO Encoding (§7.8.3.2, Table 7-32, DevCtl2 bits 3:0, p.758):

| Value | Range | Timeout |
|-------|-------|---------|
| 0000b | Default | 50 μs to 50 ms |
| 0001b | Range A | 50 μs to 100 μs |
| 0010b | Range A | 1 ms to 10 ms |
| 0101b | Range B | 16 ms to 55 ms |
| 0110b | Range B | 65 ms to 210 ms |
| 1001b | Range C | 260 ms to 900 ms |
| 1010b | Range C | 1 s to 3.5 s |
| 1101b | Range D | 4 s to 17 s |
| 1110b | Range D | 17 s to 64 s |

**Note**: "strongly recommended that CTO not expire in less than 10 ms"
**Note**: NVMe commands like Format/Sanitize may need Range C or D

### CTO Default (if programming not supported):
- Must hardwire to 0000b = **50 μs to 50 ms**

### Test Plan Update:
- CC-007: Test at each supported CTO range (A through D)
- ERR-013: Default CTO is 50μs-50ms, not a single value
- NVMe note: NVMe commands can take seconds (e.g., format, sanitize) — CTO Range D may be needed

---

## 3. Error Classification (§6.2.7, Tables 6-2 through 6-5, p.520-523)

### Correctable Errors:
| Error | Type | Layer | Our Test |
|-------|------|-------|----------|
| Receiver Error | CE | PHY | ERR-001 |
| Bad TLP | CE | DLL | ERR-002 |
| Bad DLLP | CE | DLL | ERR-003 |
| Replay Timer Timeout | CE | DLL | ERR-004 |
| REPLAY_NUM Rollover | CE | DLL | ERR-005 |
| Corrected Internal Error | CE (masked by default) | Any | ERR-009 |
| Header Log Overflow | CE (masked by default) | Any | — (**MISSING: Add test**) |

### Uncorrectable Non-Fatal (default):
| Error | Our Test |
|-------|----------|
| Poisoned TLP Received | ERR-006 |
| ECRC Check Failed | ERR-007 |
| Unsupported Request (UR) | ERR-008 |
| Completion Timeout | ERR-013 |
| Completer Abort | ERR-014 |
| Unexpected Completion | ERR-015 |
| ACS Violation | — (**MISSING for endpoint**, but RC-side) |
| MC Blocked TLP | — (Switch only) |
| AtomicOp Egress Blocked | ATOM-006 |
| TLP Prefix Blocked | — (**MISSING: Add test**) |

### Uncorrectable Fatal (default):
| Error | Our Test |
|-------|----------|
| Data Link Protocol Error | ERR-010 |
| Surprise Down | ERR-011 |
| Flow Control Protocol Error | ERR-012 |
| Receiver Overflow | ERR-016 |
| Malformed TLP | ERR-017 |
| Uncorrectable Internal Error | ERR-018 (masked by default) |

### Gaps Identified:
1. **Header Log Overflow** (CE, masked by default) — need test
2. **TLP Prefix Blocked** (UCE Non-Fatal) — need test if device uses TLP Prefixes
3. **Poisoned TLP Egress Blocked** — only for Downstream Ports, not endpoints

---

## 4. DPC — Key Details (§6.2.10, p.526-530)

### Spec Requirements for DPC:
- DPC is **optional** for Downstream Ports
- **Disabled by default** — software must enable
- Trigger conditions:
  - 01b: ERR_FATAL only
  - 10b: ERR_NONFATAL or ERR_FATAL
- When triggered: LTSSM → **Disabled state**
- After DPC cleared: LTSSM → **Detect state** → retrain
- **DPC RP Busy bit**: SW must wait until 0 before releasing (may take "multiple seconds")
- DPC sends **ERR_COR** (not ERR_FATAL) to indicate DPC event

### For NVMe SSD Testing:
- DPC is Root Port feature, not endpoint — but we test how our device behaves when DPC is triggered on the RP
- After DPC release + link retrain: device must re-enumerate and function
- Test with both trigger modes (01b and 10b)

---

## 5. SR-IOV Key Parameters (§9.3, p.1110+)

### From Spec:
- VF BAR: VFs share a BAR aperture, each VF gets a slice
- FLR on PF: Resets all VFs
- FLR on VF: Only affects that VF, PF unaffected
- ARI required when TotalVFs + PF functions > 8
- VF Migration: Optional, for live migration support

---

## 6. LTSSM Timeout Values (§4.2.6, various)

| State/Sub-state | Timeout | Reference |
|----------------|---------|-----------|
| Detect.Quiet | 12 ms | §4.2.6.2 |
| Polling.Active | 24 ms (1024 TS1 sent) | §4.2.6.3 |
| Polling.Compliance | (see sub-states) | §4.2.6.3 |
| Config.Linkwidth.Start | 24 ms | §4.2.6.4 |
| Config.Lanenum.Wait | 2 ms | §4.2.6.4 |
| Config.Complete | 2 ms | §4.2.6.4 |
| Config.Idle | 2 ms | §4.2.6.4 |
| Recovery.RcvrLock | 24 ms | §4.2.6.5 |
| Recovery.RcvrCfg | 24 ms | §4.2.6.5 |
| Recovery.Speed | 24 ms | §4.2.6.5 |
| Recovery.EQ Phase 1 | 12 ms | §4.2.6.4.2.2.2 p.353 |
| Recovery.EQ Phase 2 | 24 ms (-0/+2ms) | §4.2.6.4.2.2.3 p.355 |
| Recovery.EQ Phase 3 | 32 ms (-0/+4ms) | §4.2.6.4.2.2.4 p.356 |
| L0s → L0 | Via FTS (N_FTS count) | §4.2.6.6 |
| L1 → Recovery | Via EIEOS | §4.2.6.7 |
| L2 → Detect | Via Beacon or PERST# | §4.2.6.8 |

### Test Plan Updates:
- LT-001: Total boot time (Detect → L0) should be < 200ms typical, but spec allows up to ~100ms+ for each state
- LT-010: Recovery timeout is 24ms per sub-state, not 24ms total
- EQ: Phase 0/1/2 have 24ms timeout (tolerance -0/+2ms); **Phase 3 has 32ms timeout** (tolerance -0/+4ms). Total EQ max = 24+24+24+32 = **104ms**
- EQ coefficient change must be effective at TX pins within **500ns** of request receipt
- EQ preset/coefficient request must be held for at least **1μs** or until evaluation complete
- EQ status bits tracked per-speed: Link Status 2 (8GT/s), 16GT/s Status Register, 32GT/s Status Register

---

## 7. Hot-Swap / Surprise Removal (§8.4.5.3)

### From Spec (§8.4.5.3 Short Circuit Requirements):
> "All Transmitters and Receivers must support surprise hot insertion/removal without damage to the component."
> "The Transmitter and Receiver must be capable of withstanding sustained short circuit to ground of D+ and D-."

This is a **MANDATORY requirement** — our U.2 hot-swap tests (FF-015, FF-016) are testing a required feature, not optional.

---

## 8. FLR Requirements (§6.6.2)

### Key FLR Requirements (§6.6.2, p.554-557):
- **FLR Duration**: Function must complete FLR within **100ms** of FLR initiation
- **FLR is OPTIONAL but strongly recommended** — verify device supports it (DevCap.FLReset)
- **Transaction Pending bit**: SW should check before issuing FLR
  - If TP=1 and CTO was enabled: SW should wait CTO duration for pending completions
  - If TP=1 and CTO disabled: SW must wait ≥100ms
- **During FLR**: Incoming Requests may be silently discarded; Completions may be discarded or treated as Unexpected
- **After FLR**: Function may return **CRS (Config Retry Status)** until initialization complete
- **Link state NOT affected** — PHY/DLL layers not reset, VC0 remains initialized
- **Registers NOT reset by FLR**: Many Link-related registers preserved (ASPM Control, RCB, CCC, MPS, Lane EQ, Margining regs, etc.)
- **Registers RESET by FLR**: Bus Master Enable, MSI Enable, BAR values → Function goes quiescent
- **Stale Completions**: Major data corruption risk — SW must wait for stale completions to drain

### Test Plan Updates Needed:
- RST-004: Verify FLR completes within 100ms (measure with LeCroy)
- RST-005: Check Transaction Pending bit transitions before/during/after FLR
- **NEW: RST-004a**: Verify CRS returned during FLR if config read issued early
- **NEW: RST-004b**: Verify Link state unaffected by FLR (no retrain, speed/width preserved)
- **NEW: RST-004c**: Verify preserved registers (ASPM, MPS, Lane EQ) retain values after FLR
- **NEW: RST-004d**: Verify silent discard of Requests during FLR (no UR error logged)
- **NEW: RST-004e**: Stale completion test — issue FLR with pending NVMe IOs, verify no data corruption when Function re-enabled

---

## 9. Transaction Ordering Rules (§2.4.1 Table 2-40, p.177)

### Master Ordering Table Key Rules:
1. **Posted must NOT pass Posted** (same TC, no RO) — ensures CQE after data
2. **Completion must pass Posted** — CplD can overtake MWr
3. **Non-Posted must NOT pass Posted** (Row B, Col 2: "a) No") — MRd pushes prior MWr
4. **With Relaxed Ordering**: "No" rules become "Y/N" — reordering permitted

### Critical for NVMe:
- Data DMA (MWr) must be visible to host BEFORE CQE (MWr) per NVMe §3.3.1
- Table 2-40 Row A/Col 2 "a) No" enforces this for same TC without RO
- If device sets RO bit: must use explicit fence between data and CQE

### Test Plan Impact:
- ORD-001, ORD-004: Verify data→CQE ordering (the money test)
- ORD-003: If RO bit set, verify fence mechanism works

---

## 10. EQ Phase Timeout Corrections (§4.2.6.4, p.350-357)

| Phase | Timeout | Source |
|-------|---------|--------|
| Phase 1 | **12 ms** | §4.2.6.4.2.2.2 p.353 |
| Phase 2 | 24 ms (-0/+2ms) | §4.2.6.4.2.2.3 p.355 |
| Phase 3 | **32 ms** (-0/+4ms) | §4.2.6.4.2.2.4 p.356 |

**Correction**: Phase 1 timeout is 12ms (not 24ms). Total EQ max = ~68ms (12+24+32).

EQ status registers are **per-speed**: 8GT/s in Link Status 2, 16GT/s in 16.0 GT/s Status Register, 32GT/s in 32.0 GT/s Status Register.

### New Tests:
- Verify EQ phase status bits set correctly per speed after training
- Measure actual EQ phase durations with LeCroy, compare against spec limits

---

## 11. Power State Transition Delays (§5.9 Table 5-13, p.492)

| Initial State | Next State | Minimum SW Delay |
|--------------|-----------|-----------------|
| D0 | D1 | 0 |
| D0 or D1 | D2 | 200 ms |
| D0, D1, D2 | D3hot | 10 ms |
| D1 | D0 | 0 |
| D2 | D0 | 200 μs |
| D3hot | D0 | **10 ms** |
| D3cold | D0 | (power cycle + 100ms PERST#) |

**Key**: D3hot→D0 requires ≥**10ms** before first config access. Device may return CRS during this period.

---

## 12. DLL Replay Mechanism (§3.6.2.1, p.228-230)

- REPLAY_NUM: 2-bit counter (00→01→10→11); rollover 11b→00b triggers Recovery
- REPLAY_TIMER: not advanced during link retrain; holds value in Recovery/Config
- After retrain: DLL state NOT reset unless PHY reports LinkUp=0

---

## 13. L1 PM Substates Config Ordering (§5.5.4, p.488)

1. Program T_POWER_ON, Common_Mode_Restore_Time, LTR_L1.2_THRESHOLD first
2. Enable DP before UP; disable UP before DP
3. ASPM L1 must be disabled during L1.x config
4. LTR_L1.2_THRESHOLD identical in both ports

L1.2 Timing (Table 5-11): T_POWER_OFF ≥ 2μs, T_COMMONMODE 0-255μs, T_POWER_ON 0-3100μs, TL1.2 ≥ 4μs

---

## 14. Transaction Ordering (§2.4.1, Table 2-40, p.177)

Key: Posted MWr must NOT pass Posted MWr (same TC, no RO). This guarantees NVMe data DMA arrives before CQE.
With Relaxed Ordering bit: reordering permitted → device must fence explicitly.
