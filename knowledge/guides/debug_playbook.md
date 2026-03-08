# PCIe Debug Playbook for NVMe SSD

> When something breaks, start here. Organized by symptom.

---

## Symptom 1: Device Not Detected (lspci shows nothing)

```
Severity: Critical
Possible Causes: PHY/LTSSM failure, power issue, connector issue
```

### Step-by-step debug:

1. **Physical check**
   - Is the device firmly seated? (reseat it)
   - Correct form factor slot? (M.2 M-key, not B-key)
   - Power cable connected? (U.2/E1.S: check 12V/3.3V)
   - Any visible damage on connector pins?

2. **Power check**
   ```bash
   # Check if slot has power (if possible to measure)
   # For M.2: measure 3.3V at socket pins
   # For U.2: measure 12V and 3.3V
   ```

3. **BIOS check**
   - Enter BIOS → check if PCIe slot is enabled
   - Check bifurcation setting (M.2 slots share lanes with SATA or other slots)
   - Try disabling ASPM in BIOS
   - Check if slot is set to Gen3 only (some BIOS defaults)

4. **LeCroy capture** (if available)
   ```
   - Insert LeCroy interposer
   - Arm trigger on Detect state
   - Boot system
   - Check: Does Detect state even start?
     - No Detect → power or PERST# issue
     - Detect but no Polling → Receiver Detection failed
     - Polling but no Config → compliance pattern issue or speed mismatch
     - Config but no L0 → lane/link number negotiation failure
   ```

5. **Try different slot / platform**
   - If works in another slot → original slot or BIOS issue
   - If fails everywhere → device hardware issue

6. **Check PERST# timing**
   ```
   Oscilloscope:
   - Measure time from 3.3V/12V stable to PERST# de-assertion
   - Must be ≥ 100ms (per CEM spec)
   - Some platforms release PERST# too early
   ```

---

## Symptom 2: Device Detected but Wrong Speed/Width

```
Expected: Gen5 x4 (32GT/s, Width x4)
Actual:   Gen3 x2 (8GT/s, Width x2) [example]
```

### Speed degradation debug:

1. **Identify the limiting factor**
   ```bash
   # Check device max capability
   lspci -s $BDF -vvv | grep "LnkCap:"
   # Check upstream port (Root Port) max capability
   PARENT=$(basename $(readlink /sys/bus/pci/devices/0000:$BDF/../..))
   lspci -s $PARENT -vvv | grep "LnkCap:"
   # Actual speed is min(device, slot, BIOS setting)
   ```

2. **Speed issue: device supports Gen5 but trains at Gen3/Gen4**
   ```
   Cause A: Platform doesn't support Gen5 (most common!)
   Cause B: Equalization failure at Gen5 → fallback
   Cause C: BIOS restricts speed
   Cause D: Channel too lossy for Gen5
   
   Debug:
   - LeCroy: capture boot, check EQ phases at Gen5
   - If EQ fails → check SI (eye diagram at Gen5)
   - Try different cable/slot (U.2) or M.2 riser
   ```

3. **Width issue: x4 device training at x2 or x1**
   ```bash
   # Check dmesg for lane errors
   dmesg | grep -i "link\|pcie\|width"
   ```
   ```
   Cause A: One or more lanes have bad SI
   Cause B: Lane reversal not handled
   Cause C: PCB trace issue (open/short on specific lane)
   Cause D: Connector damage on specific pins
   
   Debug:
   - LeCroy: check per-lane receiver detection in Detect state
   - If 2 of 4 lanes fail detection → HW issue on those lanes
   - Lane Margining: run per-lane margin to find weak lane
   - Oscilloscope: measure eye on each lane separately
   ```

---

## Symptom 3: Completion Timeout Errors

```bash
# Typical dmesg output:
# pcieport 0000:00:01.0: AER: Corrected error received: id=0100
# nvme 0000:01:00.0: Completion timeout, aborting
```

### Debug:

1. **Characterize the failure**
   ```bash
   # How often?
   dmesg | grep -c "Completion timeout"
   # Under what workload?
   # After how long?
   ```

2. **Common causes & fixes**

   | Cause | How to verify | Fix |
   |-------|--------------|-----|
   | FW too slow under load | Reproduce with high QD stress | FW optimization |
   | FC credit exhaustion | LeCroy: check FC UpdateFC DLLPs | FW: release credits faster |
   | ASPM L1 exit too slow | Disable ASPM → CTO goes away? | Fix L1 exit latency |
   | MPS too large | Reduce MPS → CTO goes away? | Check MPS negotiation |
   | IOMMU mapping issue | Disable IOMMU → CTO goes away? | Fix DMA mapping |
   | Device internal hang | CTO on every IO after first | FW reset/recovery logic |

3. **LeCroy analysis**
   ```
   - Set trigger: MRd without matching CplD within 50ms
   - Capture the stuck transaction
   - Look at: Tag, Requester ID, Address
   - Is the MRd even reaching the device? (check Rx side)
   - Did the device start processing but not complete?
   - Are FC credits exhausted? (check last UpdateFC DLLP)
   ```

---

## Symptom 4: System Hang or Kernel Panic on PCIe Error

```
NMI: PCI system error (SERR) for reason XX on CPU Y
or: kernel BUG at drivers/pci/...
```

### Debug:

1. **Capture crash info**
   ```bash
   # If system still alive:
   dmesg > /tmp/crash_dmesg.txt
   journalctl -b -1 > /tmp/last_boot.txt  # previous boot
   
   # Check MCE (Machine Check Exception)
   mcelog --client
   ```

2. **Common causes**
   - Fatal AER error not contained → NMI
   - DMA to unmapped address → IOMMU fault → crash
   - Surprise removal without DPC support → MCE
   
3. **Mitigation**
   ```bash
   # Enable DPC (if RC supports it)
   # Enable AER error masking for non-fatal errors
   # Set kernel parameter: pci=noaer  (temporary, hides errors)
   # Set kernel parameter: pcie_ports=compat (less aggressive error handling)
   ```

---

## Symptom 5: Performance Lower Than Expected

```
Expected: 7 GB/s sequential read (Gen4 x4)
Actual:   3.5 GB/s
```

### Debug checklist:

1. **Verify link speed/width first!**
   ```bash
   lspci -s $BDF -vvv | grep "LnkSta:"
   # If speed/width wrong → see Symptom 2
   ```

2. **Check MPS**
   ```bash
   lspci -s $BDF -vvv | grep "MaxPayload"
   # DevCtl: MaxPayload XXXB — should be 256 or 512
   # If 128B: significant overhead → talk to BIOS team
   ```

3. **Check MRRS**
   ```bash
   lspci -s $BDF -vvv | grep "MaxReadReq"
   # Should be ≥ 512, ideally 4096
   ```

4. **Check NUMA locality**
   ```bash
   # Is the CPU running fio on the same NUMA node as the NVMe device?
   cat /sys/bus/pci/devices/0000:$BDF/numa_node
   # Run fio pinned to correct NUMA:
   numactl -N <node> -m <node> fio ...
   ```

5. **Check thermal throttle**
   ```bash
   nvme smart-log /dev/nvme0 | grep -i "therm\|temp"
   # If Warning Composite Temperature reached → throttling
   ```

6. **LeCroy efficiency analysis**
   ```
   Capture 10ms of heavy IO. Count:
   - Total TLP payload bytes
   - Total link utilization (including DLLP, SKP, idle)
   - Efficiency = payload / total
   - Good: > 85%
   - Bad: < 70% → investigate credit starvation, small TLPs, excessive SKP
   ```

---

## Symptom 6: Intermittent Link Retraining

```bash
# dmesg shows:
# pcieport 0000:00:01.0: pciehp: Slot(1-1): Link Up
# pcieport 0000:00:01.0: pciehp: Slot(1-1): Link Down
# (rapid toggling)
```

### Debug:

1. **Count retrains**
   ```bash
   # LeCroy: count Recovery state entries over 1 hour
   # Linux: watch for link status changes
   while true; do
       lspci -s $BDF -vvv | grep "LnkSta:" | head -1
       sleep 1
   done
   ```

2. **Correlate with temperature**
   ```bash
   # Run alongside: nvme smart-log temp monitoring
   watch -n5 "nvme smart-log /dev/nvme0 | grep temp"
   # If retrains correlate with temp rise → marginal SI
   ```

3. **Lane Margining**
   ```
   If Gen5: Run lane margining on all 4 lanes
   Compare margins at 25°C vs at temperature where retrains occur
   Marginal lane will show significantly less margin
   ```

---

## Quick Commands Reference

```bash
# Full device info
lspci -s $BDF -vvv

# Link speed/width
lspci -s $BDF -vvv | grep "LnkSta:"

# AER error counters
cat /sys/bus/pci/devices/0000:$BDF/aer_dev_correctable
cat /sys/bus/pci/devices/0000:$BDF/aer_dev_fatal

# NVMe health
nvme smart-log /dev/nvme0

# NVMe registers
nvme show-regs /dev/nvme0

# Full config space hex
lspci -s $BDF -xxxx

# Watch for PCIe errors in real-time
dmesg -w | grep -i "pcie\|aer\|nvme"

# Remove and rescan device (soft reset alternative)
echo 1 > /sys/bus/pci/devices/0000:$BDF/remove
echo 1 > /sys/bus/pci/rescan

# Force link retrain
setpci -s $BDF CAP_EXP+10.w=$(printf "%04x" $(( $(printf "%d" 0x$(setpci -s $BDF CAP_EXP+10.w)) | 0x20 )))
```
