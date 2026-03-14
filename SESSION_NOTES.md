# Augment Session Notes - 2026-03-13

## Context
Working on PCIe Test Tracker validation using Glean MCP.

## What We Accomplished

### 1. Test Case Analysis
- **414 test cases** across 8 YAML files in `data/seeds/`
- Priority breakdown: P0=187, P1=179, P2=47, P3=1
- Test methods: protocol_analyzer (198), software_driver (118), hardware_lab (86)

### 2. PCIe 5.0 Spec Index Built
Using the PDF at `/home/azhang/workspace/device-validation-test/docs/spec/PCI_Express_Base_5.0r1.0-2019-05-22.pdf`:
- 1184 sections indexed
- 456 tables indexed  
- 603 figures indexed

Temp files created:
- `/tmp/pcie_sections.json`
- `/tmp/pcie_tables.json`
- `/tmp/pcie_figures.json`
- `/tmp/validation_results.json`

### 3. Spec Reference Validation Results
| Category | Count | Status |
|----------|-------|--------|
| ✓ Valid | 381 | All sections/tables/figures found |
| ~ Partial | 5 | Some refs valid, some not found |
| ✗ Invalid | 5 | Non-PCIe refs (SFF specs) |
| 📖 NVMe | 23 | Not validated (different spec) |

**Partial References to Fix:**
- `§7.5.1.7` - TXN-012, TXN-054
- `§2.8.1` - TXN-022
- `§4.2.6.2.5` - LTSSM-007
- `§3.2.6` - PLAT-043

### 4. Glean PCIe Q&A Agent Testing
Agent ID: `b189f70c39fc4ae690d3a2c3cae13fa6`

Tested 3 DLL tests:
- DLL-001 (Ack DLLP): ✓ Valid
- DLL-002 (Nak DLLP): ✓ Valid  
- DLL-003 (InitFC1): ⚠ Pass criteria needs verification

## Next Steps (TODO)

1. [x] ~~Automate Glean validation for remaining 184 P0 tests~~ **COMPLETED 2026-03-13**
2. [ ] Fix the 5 partial spec references
3. [ ] Build PCIe config space parser (JSON schema design started)
4. [ ] Export validation results to permanent report

---

## Glean Validation Session — 2026-03-13

### Summary
- **All 187 P0 test cases validated** across 8 YAML seed files
- **144 tests marked as "valid"** (spec refs and pass criteria accurate)
- **43 tests marked as "corrected"** (spec refs and/or pass criteria updated)

### Files Updated
| File | P0 Tests | Valid | Corrected |
|------|----------|-------|-----------|
| 01_physical_layer.yaml | 24 | 1 | 23 |
| 02_data_link_layer.yaml | 32 | 21 | 11 |
| 03_transaction_layer.yaml | 23 | 18 | 5 |
| 04_ltssm.yaml | 23 | 19 | 4 |
| 05_configuration_space.yaml | 22 | 22 | 0 |
| 06_power_management.yaml | 28 | 28 | 0 |
| 07_error_handling.yaml | 25 | 25 | 0 |
| 08_platform_nvme.yaml | 10 | 10 | 0 |

### Common Corrections Made
1. **PHY Layer (23 corrections):** Table number mismatches (e.g., Table 8-5/8-6 vs 8-9/8-14 for eye/jitter), missing spec refs for CEM/OCP specs, internal vs spec-required pass criteria
2. **DLL Layer (11 corrections):** UpdateFC timing (30 μs not 34 μs), section refs (§3.4 vs §3.5.1), AER table refs
3. **Transaction Layer (5 corrections):** Message TLP refs (§2.2.4 + Table 2-28), Config Type 0/1 refs (§2.2.6)
4. **LTSSM (4 corrections):** L0s refs (§4.2.6.6 not §5.3.2), Configuration N_FTS refs

### YAML Structure Added
Each validated test now includes:
```yaml
validation:
  status: valid|corrected
  validated_at: "2026-03-13"
  changes_made:
    - "Description of change/validation"
```

For corrected tests, original values preserved in:
- `original_spec_ref`
- `original_pass_criteria`

## Earlier Discussion: PCIe Config Space Parser

Designed JSON schema structure for PCIe configuration space:
- Approach B (Modular Files) selected
- Template-based for extended capabilities
- Both schema + runtime values

Directory structure planned:
```
src/pcie/config_schema/
├── headers/type0_header.json, type1_header.json
├── standard_caps/power_management.json, msi.json, etc.
└── extended_caps/aer.json, dpc.json, etc.
```

## Commands to Rebuild Environment

```bash
# Activate venv with pymupdf
cd /home/azhang/workspace/device-validation-test
source .venv/bin/activate

# Re-run validation script if needed
python3 -c "import fitz; print('pymupdf ready')"
```

