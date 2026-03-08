# PCIe / NVMe Specification Cross-Reference

> Maps each section of the PCIe Base Spec and NVMe Spec to our test items.
> Use this to verify: "Do we have tests covering this spec section?"

---

## PCIe Base Specification 6.0 (applicable to Gen5 and below)

| Spec Chapter | Title | Our Test IDs | Gap? |
|-------------|-------|-------------|------|
| §2.2 | Transaction Layer — TLP Format | TLP-001~005 | Covered |
| §2.2.7 | TLP Digest (ECRC) | TLP-020 | Covered |
| §2.4 | Transaction Ordering | ORD-001~010 | ✅ New |
| §2.5 | Flow Control | DLL-006~008 | Covered |
| §2.6 | Data Integrity — ECRC | TLP-020 | Covered |
| §2.7 | Completion Handling | TLP-006~009, ERR-013 | Covered |
| §3.2 | Link Initialization & Training (LTSSM) | LT-001~022 | Covered |
| §3.3 | Link Power Management | PM-010~016 | Covered |
| §3.4 | 8b/10b, 128b/130b Encoding | PHY-009, PHY-010 | Covered |
| §4.2 | TX Electrical (Gen1~5) | PHY-001~006 | Covered |
| §4.3 | RX Electrical | PHY-007~008 | Covered |
| §4.4 | Reference Clock | PHY-013~014 | Covered |
| §4.5 | Impedance | PHY-011 | Covered |
| §4.6 | Channel Compliance | PHY-012, G5-033 | Covered |
| §5.3 | PCI Power Management | PM-001~005 | Covered |
| §5.4 | ASPM | PM-010~016 | Covered |
| §5.5 | Clock Power Management | PM-016 | Covered |
| §6.2 | Error Signaling & Logging | ERR-001~035 | Covered |
| §6.3 | Error Forwarding | ERR-018 | Covered |
| §6.6 | Function-Level Reset | RST-004~005 | Covered |
| §6.7 | Hot Reset / Warm Reset | RST-002~003, RST-006 | Covered |
| §6.8 | Conventional Reset | RST-001 | Covered |
| §6.12 | Access Control Services (ACS) | P2P-005 | ✅ New |
| §6.13 | ARI | SRIOV-012 | ✅ New |
| §6.15 | Atomic Operations | ATOM-001~008 | ✅ New |
| §7.5 | MSI / MSI-X | INT-001~009 | Covered |
| §7.8 | Config Space | CFG-001~055 | Covered |
| §8.3 | Lane Margining at Receiver | LM-001~011 | ✅ New |
| §9.3 | SR-IOV | SRIOV-001~015 | ✅ New |
| §10 | Peer-to-Peer | P2P-001~005 | ✅ New |
| CEM 5.0 | Card Electromechanical | CEM-001~010 | ✅ New |

### Spec Sections NOT Covered (Potential Gaps)

| Spec Section | Title | Relevance to NVMe SSD | Priority |
|-------------|-------|----------------------|----------|
| §6.9 | DPC (Downstream Port Containment) | RC-side, not endpoint. But test DPC interaction: ERR-033 covers partially. | P2 |
| §6.10 | LTR (Latency Tolerance Reporting) | Endpoint reports latency tolerance for PM. May affect ASPM behavior. | P2 |
| §6.11 | OBFF (Optimized Buffer Flush/Fill) | Rarely used by NVMe. Low priority. | P2 |
| §6.14 | TPH (TLP Processing Hints) | Performance optimization. NVMe doesn't typically use. | P2 |
| §6.16 | Page Request Interface (PRI) | Used with ATS/PASID for shared virtual memory. Emerging for CXL. | P2 |
| §6.17 | PASID | Used with SR-IOV + ATS for SVM. Emerging feature. | P2 |
| §6.18 | ATS (Address Translation Services) | Important for IOMMU bypass in VM. | P2 |
| §8.4 | Flit Mode (Gen6) | Future. Not applicable to Gen5 and below. | — |

---

## NVMe Specification 2.0 (PCIe-relevant sections)

| NVMe Section | Title | Our Test IDs | Notes |
|-------------|-------|-------------|-------|
| §2.1 | PCI Header | CFG-001~009 | |
| §2.1.10 | BAR | CFG-005, NP-002 | |
| §2.1.13 | Capabilities | CFG-008, CFG-020~031 | |
| §3.1 | Controller Registers | NP-001, NP-003, NP-004 | |
| §3.1.5 | Shutdown | NP-020~024 | |
| §3.3 | Queue Mechanisms | NP-005, NP-010~017 | |
| §3.5 | CMB | NP-007, NOF-001~003 | |
| §3.6 | PMR | NP-008, NOF-004 | |
| §4.1 | Submission/Completion Queues | NP-010~012 | |
| §4.2 | Data Transfer | NP-013~016 | |
| §4.4 | PRP | NP-015 | |
| §4.5 | SGL | NP-016 | |
| §5.8 | Firmware Update | FW-012, FW-013 | |
| §7.5 | Interrupts | NP-017, INT-001~009 | |
| §8.2 | Power Loss Protection | NP-026 | |
| §8.11 | Namespace Management | SRIOV-005 | |
| §8.12 | SR-IOV | SRIOV-001~015 | |

---

## Form Factor Specifications

| Spec | Our Test IDs | Notes |
|------|-------------|-------|
| M.2 (PCI-SIG M.2 Spec) | FF-001~005 | Key M, 2280/2242/2230 |
| SFF-8639 (U.2) | FF-010~013 | |
| SFF-TA-1001 (U.3) | FF-012 | Tri-mode |
| SFF-TA-1006 (E1.S EDSFF) | FF-020~022 | |
| SFF-TA-1008 (E3.S EDSFF) | FF-023 | |

---

## Industry Test Suites Cross-Reference

| Industry Suite | What It Tests | Our Equivalent |
|---------------|---------------|----------------|
| PCI-SIG CEM Compliance | PHY electrical + LTSSM | PHY-*, LT-*, EQ-*, CEM-* |
| UNH-IOL NVMe Test Suite | NVMe protocol compliance | NP-*, mostly NVMe-level (not PCIe) |
| Intel VROC Certification | Intel platform interop | IOP-001~004 |
| AMD EPYC Ready | AMD platform interop | IOP-005~007 |
| Microsoft HLK/HCK | Windows driver certification | IOP-034~035 |
| VMware vSAN Ready | ESXi compatibility | IOP-036 |
| OCP Cloud SSD Spec | Data center SSD requirements | Subset of all categories |
