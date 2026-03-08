# Ready-to-Use Checklists

---

## Checklist 1: Day 1 — New Silicon / New Device Bring-Up

> You just received first silicon or a new device sample. Run these checks in order.
> Estimated time: 2-4 hours (no special equipment needed, Linux only).

### Pre-flight
- [ ] Record device info: VID/DID, FW version, serial number, form factor
- [ ] Identify test platform: CPU, chipset, BIOS version, kernel version
- [ ] Photo the device (front/back) for documentation

### Step 1: Physical Install & Power (15 min)
- [ ] Install U.2 device in slot
- [ ] Verify power LED (if present)
- [ ] Boot system
- [ ] No smoke, no burning smell (seriously)

### Step 2: Enumeration (15 min)
- [ ] `lspci | grep -i nvme` → device visible?
- [ ] `lspci -s $BDF -nn` → VID/DID correct?
- [ ] `lspci -s $BDF -vvv | grep "LnkSta:"` → speed and width?
  - Expected: Gen4 x4 (16GT/s) or Gen5 x4 (32GT/s)
  - If x2 or x1: SI problem, stop and investigate
  - If Gen3 instead of Gen4: platform or device issue
- [ ] `lspci -s $BDF -vvv | grep "LnkCap:"` → max capability?
- [ ] Save: `lspci -s $BDF -vvv > /tmp/day1_lspci.txt`

### Step 3: NVMe Functional (15 min)
- [ ] `nvme list` → device shows model, serial, FW?
- [ ] `nvme id-ctrl /dev/nvme0` → Identify Controller succeeds?
- [ ] `nvme show-regs /dev/nvme0` → registers readable?
- [ ] `nvme smart-log /dev/nvme0` → SMART data looks reasonable?
  - Temperature: 25-45°C at idle
  - Media errors: 0
  - Critical warning: 0

### Step 4: Basic IO (30 min)
- [ ] Read test: `dd if=/dev/nvme0n1 of=/dev/null bs=1M count=100 iflag=direct`
- [ ] Sequential read bandwidth:
  ```
  fio --name=t --filename=/dev/nvme0n1 --rw=read --bs=128k --iodepth=256 \
      --numjobs=4 --direct=1 --group_reporting --time_based --runtime=30
  ```
  Expected Gen4 x4: ~6-7 GB/s
- [ ] Write test (if acceptable to write):
  ```
  fio --name=t --filename=/dev/nvme0n1 --rw=write --bs=128k --iodepth=256 \
      --numjobs=4 --direct=1 --group_reporting --time_based --runtime=30
  ```
- [ ] Random 4K read:
  ```
  fio --name=t --filename=/dev/nvme0n1 --rw=randread --bs=4k --iodepth=256 \
      --numjobs=4 --direct=1 --group_reporting --time_based --runtime=30
  ```
- [ ] QD=1 latency:
  ```
  fio --name=t --filename=/dev/nvme0n1 --rw=randread --bs=4k --iodepth=1 \
      --numjobs=1 --direct=1 --time_based --runtime=30 --lat_percentiles=1
  ```
  Expected: 80-120 μs average

### Step 5: Config Space Audit (30 min)
- [ ] Run: `sudo bash scripts/pcie_full_audit.sh $BDF`
- [ ] Review results: any FAIL or WARN?
- [ ] Save report from /tmp/pcie_audit_*/

### Step 6: Basic Stability (30 min)
- [ ] 10-minute mixed IO stress:
  ```
  fio --name=stress --filename=/dev/nvme0n1 --rw=randrw --rwmixread=70 --bs=4k \
      --iodepth=128 --numjobs=4 --direct=1 --time_based --runtime=600
  ```
- [ ] During stress: check `dmesg` for any errors
- [ ] After stress: AER error counters still zero?

### Step 7: Quick Reset Test (15 min)
- [ ] FLR: `echo 1 > /sys/bus/pci/devices/0000:$BDF/reset`
- [ ] Wait 3s → `lspci -s $BDF` → device back?
- [ ] Remove/rescan: `echo 1 > /sys/bus/pci/devices/0000:$BDF/remove; sleep 1; echo 1 > /sys/bus/pci/rescan`
- [ ] `nvme list` → device functional?

### Step 8: Document Results
- [ ] Save all results to project directory
- [ ] Note any anomalies, unexpected values, or failures
- [ ] If all pass: device is ready for full validation
- [ ] If failures: log bugs, don't proceed to full validation

---

## Checklist 2: Pre-Production Validation Sign-Off

> Before mass production, ensure all critical tests pass.
> This is the gate between engineering samples and production.

### Gate 1: Core Functionality (Must ALL Pass)
- [ ] Enumerates correctly on Intel server (Gen4 and Gen5 if applicable)
- [ ] Enumerates correctly on AMD server (Gen4 and Gen5)
- [ ] Link speed: Gen4 x4 confirmed on 3+ platforms
- [ ] Link speed: Gen5 x4 confirmed on 2+ Gen5 platforms
- [ ] FLR works (1000 cycle stress: CC-003)
- [ ] D3hot/D0 works (1000 cycle stress: CC-002)
- [ ] Config space audit: all PASS (pcie_full_audit.sh)
- [ ] AER capability present and functional
- [ ] MSI-X present and functional
- [ ] BAR0: 64-bit, non-prefetchable, ≥16KB

### Gate 2: Performance (Must Meet Spec)
- [ ] Sequential Read ≥ _____ GB/s (datasheet spec)
- [ ] Sequential Write ≥ _____ GB/s
- [ ] Random Read 4K ≥ _____ KIOPS
- [ ] Random Write 4K ≥ _____ KIOPS
- [ ] QD=1 latency ≤ _____ μs (p99)
- [ ] Steady-state (4-hour) variation < 20%

### Gate 3: Reliability (Must ALL Pass)
- [ ] 72-hour stress test: zero AER errors, zero link retrains
- [ ] Power loss 100-cycle: zero data loss (with PLP)
- [ ] Power loss 100-cycle: device always re-enumerates
- [ ] Temperature 0°C-70°C: link stable at all temperatures
- [ ] Lane margining at 70°C: all lanes > 15% UI timing margin
- [ ] FW update during IO: no PCIe errors
- [ ] U.2 hot-swap: 50 cycles, zero failures

### Gate 4: Compliance (Must Pass for Certification)
- [ ] TX eye diagram meets Gen4 mask (all 4 lanes)
- [ ] TX eye diagram meets Gen5 mask (if Gen5 claimed)
- [ ] Lane Margining functional (Gen5)
- [ ] LTSSM compliance: clean boot training capture
- [ ] EQ Phase 0-3 complete (Gen4 and Gen5)
- [ ] Config space registers match PCIe spec defaults
- [ ] ECRC generation/checking supported

### Gate 5: Enterprise Features (If Applicable)
- [ ] SR-IOV: VFs enumerate and function in VM
- [ ] ASPM L1: functional with < 5% performance impact
- [ ] MCTP/NVMe-MI: BMC can read health data
- [ ] Multi-drive: 24-drive JBOF all enumerate and run IO

### Gate 6: Documentation
- [ ] Test report generated and reviewed
- [ ] All failures documented with root cause
- [ ] Known issues documented with workarounds
- [ ] FW release notes reviewed for PCIe-relevant fixes

### Sign-Off

| Role | Name | Date | Signature |
|------|------|------|-----------|
| PCIe Validation Lead | | | |
| FW Engineering Lead | | | |
| HW Engineering Lead | | | |
| Quality Assurance | | | |
| Program Manager | | | |

---

## Checklist 3: Field Issue Triage (When Customer Reports Problem)

> Customer reports a PCIe-related issue. Use this to collect info and triage.

### Information Gathering
- [ ] Customer platform: CPU model, motherboard, BIOS version
- [ ] OS and kernel version
- [ ] SSD model, FW version, serial number
- [ ] Form factor and connection type (U.2 direct, U.2 cable, backplane)
- [ ] Is issue reproducible? (Always / Intermittent / One-time)
- [ ] When did issue start? (Since install / After BIOS update / After FW update)

### Remote Diagnostics (Ask customer to run)
```bash
# Generate diagnostic bundle
BDF="XX:YY.Z"  # Customer fills in
mkdir /tmp/pcie_diag && cd /tmp/pcie_diag
lspci -vvv > lspci_full.txt
lspci -xxxx > lspci_hex.txt
nvme smart-log /dev/nvme0 > smart.txt
nvme error-log /dev/nvme0 --log-entries=64 > error_log.txt
nvme show-regs /dev/nvme0 > regs.txt
dmesg > dmesg.txt
cat /sys/bus/pci/devices/0000:$BDF/aer_dev_correctable > aer_ce.txt
cat /sys/bus/pci/devices/0000:$BDF/aer_dev_fatal > aer_uce.txt
uname -a > system.txt
tar czf /tmp/pcie_diag_$(date +%Y%m%d).tar.gz /tmp/pcie_diag/
echo "Send /tmp/pcie_diag_*.tar.gz to support"
```

### Triage Decision Tree
```
1. Device not detected?
   → Check physical connection, BIOS settings
   → See debug_playbook.md Symptom 1

2. Wrong speed/width?
   → Check platform capability, BIOS restrictions
   → See debug_playbook.md Symptom 2

3. IO errors/timeouts?
   → Check AER counters, NVMe error log
   → Check ASPM setting
   → See debug_playbook.md Symptom 3

4. Performance lower than spec?
   → Verify link speed, MPS, NUMA
   → See debug_playbook.md Symptom 5

5. System crash/panic?
   → Check dmesg, MCE log
   → DPC support on platform?
   → See debug_playbook.md Symptom 4

6. Intermittent link drops?
   → Temperature correlation?
   → ASPM related?
   → See debug_playbook.md Symptom 6
```
