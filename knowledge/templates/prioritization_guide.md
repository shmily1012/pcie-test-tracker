# Test Prioritization Guide

> Which tests to run first depends on your goal. Use this guide to select the right subset.

---

## Scenario 1: "We just taped out / got first silicon — does it work?"

**Goal**: Basic functional bring-up. Answer: "Does the device enumerate and do IO?"

**Run these (25 tests, ~2 hours)**:
```
CFG-001  Vendor/Device ID
CFG-004  Class Code
CFG-005  BAR0 verification
CFG-008  Capability list walk
CFG-024  Link Capabilities
CFG-026  Link Status (speed/width)
CFG-040  AER present
CFG-055  Config space read (no hang)
INT-002  MSI-X present
NP-001   NVMe registers readable
NP-005   Admin Queue (Identify Controller)
DMA-001  Basic DMA read
DMA-002  Basic DMA write
LT-001   Cold boot link training (LeCroy)
LT-007   L0 achieved
LT-008   Speed negotiation to max
PM-001   D3hot transition
PM-002   D3hot→D0 recovery
RST-001  Cold reset
RST-004  FLR (if supported)
PERF-001 Sequential read bandwidth (sanity)
PERF-003 Random read IOPS (sanity)
PERF-009 QD=1 latency (sanity)
NP-020   Normal shutdown
NP-023   Disable (CC.EN=0)
```

**Tool needed**: Linux box + LeCroy (for LT tests)

---

## Scenario 2: "Preparing for customer qualification"

**Goal**: Pass customer eval. Typical enterprise customer (cloud/OEM) test suite.

**Run these (80 tests, ~1 week)**:
```
All of Scenario 1 (25 tests)
+ Full Config Space audit (CFG-001~CFG-055)
+ Link training deep dive (LT-001~LT-015)
+ All Error Handling (ERR-001~ERR-035) — customers care about error resilience
+ All Reset tests (RST-001~RST-010)
+ Power Management (PM-001~PM-016)
+ Performance suite (PERF-001~PERF-014)
+ NVMe-PCIe interaction (NP-001~NP-026)
+ Corner cases (CC-001~CC-015)
+ Platform matrix: Customer's platform (IOP-xxx)
```

**Tool needed**: Linux + LeCroy + fio + oscilloscope (for PHY if customer asks)

---

## Scenario 3: "Preparing for PCI-SIG CEM Compliance Workshop"

**Goal**: Pass CEM compliance test at PCI-SIG plugfest.

**Must-pass tests**:
```
PHY-001~PHY-017  All electrical compliance (TX/RX eye, jitter, impedance)
LT-001~LT-022   Full LTSSM compliance
EQ-001~EQ-006   Equalization compliance
LM-001~LM-011   Lane Margining (Gen5)
G5-001~G5-035   Gen5 specific (if Gen5 device)
CEM-001~CEM-010  Card electromechanical
CFG-020~CFG-031  PCIe capability registers
```

**Tool needed**: Oscilloscope (≥50GHz for Gen5), BERT, VNA, LeCroy, CEM test fixture

---

## Scenario 4: "Field issue — device not training / drops link"

**Goal**: Debug a specific problem.

**Diagnostic sequence**:
```
1. CFG-026  — What speed/width did it train at?
2. LT-001   — Capture boot training trace
3. LT-008   — Did speed negotiation fail?
4. LT-010   — Is it going into Recovery repeatedly?
5. LT-011   — Is it downgrading speed?
6. ERR-001~003 — Check AER for correctable errors
7. PHY-016  — Lane Margining (how much margin?)
8. LM-006   — Per-lane margin (find the weak lane)
9. PHY-001~006 — Electrical compliance (eye diagram)
10. CC-001   — Link stability after long idle
11. CC-012   — ASPM interaction
12. CC-014   — Thermal throttle impact
```

---

## Scenario 5: "Continuous regression (CI/CD for firmware)"

**Goal**: Run after every FW build to catch regressions.

**Automated suite (~30 min)**:
```
pcie_full_audit.sh (smoke test — 5 min)
+ PERF-001~004 (bandwidth/IOPS baseline — 5 min)
+ PERF-009 (QD=1 latency — 2 min)
+ RST-004 (FLR — 1 min)
+ CC-002 (D3 cycling × 100 — 3 min)
+ CC-003 (FLR cycling × 100 — 3 min)
+ PM-001~002 (D3hot roundtrip — 1 min)
+ NP-020~024 (Shutdown/disable — 5 min)
+ ERR check (AER counters — 1 min)
+ Compare results to baseline → flag regressions
```

---

## Priority Matrix

| Category | First Silicon | Customer Qual | CEM Compliance | Field Debug | CI/CD |
|----------|:---:|:---:|:---:|:---:|:---:|
| Config Space | ✅ | ✅ | ✅ | ✅ | ✅ |
| Link Training | 🔸 | ✅ | ✅ | ✅ | 🔸 |
| PHY Electrical | | 🔸 | ✅ | ✅ | |
| Data Link Layer | | ✅ | ✅ | 🔸 | |
| Transaction Layer | | ✅ | ✅ | | |
| Power Management | 🔸 | ✅ | 🔸 | 🔸 | 🔸 |
| Interrupts | ✅ | ✅ | | | ✅ |
| Error Handling | | ✅ | ✅ | ✅ | |
| Reset | ✅ | ✅ | ✅ | 🔸 | ✅ |
| DMA | ✅ | ✅ | | | ✅ |
| Performance | ✅ | ✅ | | | ✅ |
| NVMe-PCIe | ✅ | ✅ | | ✅ | ✅ |
| CEM/Form Factor | | 🔸 | ✅ | | |
| BIOS/FW | | ✅ | | 🔸 | |
| Corner Cases | | ✅ | | ✅ | 🔸 |
| Interop Matrix | | ✅ | | 🔸 | |
| Gen5 Specific | | 🔸 | ✅ | ✅ | |
| Lane Margining | | 🔸 | ✅ | ✅ | |

✅ = Must run | 🔸 = Recommended | (blank) = Not needed for this scenario

---

## Estimated Effort by Category

| Category | # Tests | Estimated Time | Equipment Cost |
|----------|---------|---------------|----------------|
| Config Space (Linux only) | 36 | 2 hours | $0 (Linux) |
| Link Training (LeCroy) | 22 | 1-2 days | $50K-200K (analyzer) |
| PHY Electrical (scope) | 17 | 3-5 days | $100K-500K (scope+fixture) |
| Error Injection (LeCroy) | 21 | 2-3 days | $100K+ (exerciser) |
| Performance (fio) | 14 | 4 hours | $0 (Linux) |
| Power Management (mixed) | 16 | 1 day | $0-50K |
| NVMe-PCIe (LeCroy + Linux) | 26 | 2 days | $50K+ |
| CEM (lab equipment) | 10 | 1-2 days | $50K+ (VNA, TDR) |
| Form Factor | 12 | 0.5 day | $0-5K (calipers, adapters) |
| Interop Matrix | 18 | 5-10 days | Multiple platforms |
| Gen5 + Margining | 32+11 | 3-5 days | $200K+ (Gen5 scope+analyzer) |
| Corner Cases | 15 | 2-3 days | Mixed |
| **TOTAL** | **~335** | **~25-40 working days** | **~$300K-800K (equipment)** |

> Note: Many tests share equipment. Total wall-clock time with 1 engineer + full equipment: ~2 months for complete coverage. With 2 engineers working in parallel: ~1 month.
