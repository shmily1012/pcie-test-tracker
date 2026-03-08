# IO Workload Matrix for PCIe NVMe SSD Testing

> Different tests require different IO patterns. This matrix maps test goals to fio workloads.

---

## 1. Workload Profiles

### Profile A: Maximum Bandwidth (saturate PCIe link)
```bash
# Purpose: Measure peak PCIe bandwidth utilization
# Use for: PERF-001/002, U2SI bandwidth tests, Gen4↔Gen5 comparison
fio --rw=read --bs=128k --iodepth=256 --numjobs=4 --direct=1
# Expected Gen4 x4: ~6.5-7.0 GB/s
# Expected Gen5 x4: ~12-14 GB/s
```

### Profile B: Maximum IOPS (saturate PCIe TLP processing)
```bash
# Purpose: Measure peak small-block IOPS
# Use for: PERF-003/004, multi-queue scaling, TLP efficiency
fio --rw=randread --bs=4k --iodepth=256 --numjobs=4 --direct=1
# Expected: 1M-2M IOPS depending on controller
```

### Profile C: Latency-Sensitive (QD=1)
```bash
# Purpose: Measure pure IO latency (PCIe round-trip visible)
# Use for: PERF-009, ASPM latency impact, L1 exit latency
fio --rw=randread --bs=4k --iodepth=1 --numjobs=1 --direct=1
# Expected: 80-120 μs avg for enterprise NVMe
```

### Profile D: Bursty (ASPM cycling)
```bash
# Purpose: Create idle gaps to trigger ASPM, then burst IO
# Use for: ASPM-40, CC-012, L0s/L1 entry+exit cycling
fio --rw=randread --bs=4k --iodepth=32 --numjobs=1 --direct=1 \
    --thinktime=100000 --thinktime_blocks=100
# 100 IOs → 100ms pause → 100 IOs → 100ms pause ...
```

### Profile E: Sustained Write (heat generation, GC trigger)
```bash
# Purpose: Heat up device, trigger GC, test sustained write
# Use for: Thermal tests, DC-063 (GC latency), PERF-013
fio --rw=write --bs=128k --iodepth=256 --numjobs=4 --direct=1 \
    --time_based --runtime=3600
# Writes for 1 hour continuously
```

### Profile F: Mixed Enterprise Workload
```bash
# Purpose: Simulate real DC workload
# Use for: DC-060 (steady-state), DC-061 (QoS)
fio --rw=randrw --rwmixread=70 --bs=4k --iodepth=128 \
    --numjobs=4 --direct=1
```

### Profile G: Background Load + Latency Probe
```bash
# Purpose: Measure latency under realistic load
# Use for: PERF-010, DC-061/062
fio --name=bg --rw=randrw --rwmixread=70 --bs=4k --iodepth=128 \
    --numjobs=3 --direct=1 --group_reporting \
    --new_group \
    --name=probe --rw=randread --bs=4k --iodepth=1 \
    --numjobs=1 --direct=1 --lat_percentiles=1
```

### Profile H: Power Measurement (idle → burst → idle)
```bash
# Purpose: Create defined power states for measurement
# Use for: Power measurement procedures
for phase in idle load idle; do
    if [ "$phase" = "load" ]; then
        fio --rw=write --bs=128k --iodepth=256 --numjobs=4 \
            --direct=1 --time_based --runtime=60 --output=/dev/null
    else
        sleep 60  # idle for power measurement
    fi
done
```

---

## 2. Test → Workload Mapping

| Test Category | Recommended Profile | Duration | Notes |
|--------------|-------------------|----------|-------|
| PHY Electrical | B (max IOPS) | 30s | Need active link for eye measurement |
| Link Training | None (boot) | N/A | Passive capture during boot |
| DLL ACK/NAK | A or B | 10s | Need TLP flow for error injection |
| TLP Ordering | A + C | 30s each | Sequential for ordering, QD=1 for verification |
| Config Space | None | N/A | Config register reads, no IO needed |
| ASPM | D (bursty) | 300s | Must have idle gaps for ASPM entry |
| Error Handling | B (max IOPS) | Varies | Error injection during heavy IO |
| Reset | B (max IOPS) | 10s | Reset during active IO |
| Performance Baseline | A, B, C | 60s each | Standard benchmark |
| Steady-State Perf | F (mixed) | 4h+ | Long duration for consistency |
| Thermal | E (sustained write) | 1h+ | Maximize heat generation |
| Power Loss | E or F | Until power cut | IO running when power yanked |
| Hot-Swap | B (max IOPS) | Until removal | IO active during removal |
| Lane Margining | B (max IOPS) | During margin | IO concurrent with margining |
| 72-Hour Stress | F (mixed) | 72h | Long endurance |
| SR-IOV | B per VF | 60s | Same workload on each VF |

---

## 3. Data Integrity Verification

```bash
# For tests where data integrity matters (power loss, error injection):

# Method 1: Known pattern write + read-back verify
fio --name=write --rw=write --bs=4k --size=1G --direct=1 \
    --verify=crc32c --verify_pattern=0xDEADBEEF \
    --do_verify=0  # Write only

# [do the test: power loss, reset, error injection, etc.]

fio --name=verify --rw=read --bs=4k --size=1G --direct=1 \
    --verify=crc32c --verify_pattern=0xDEADBEEF \
    --do_verify=1  # Verify on read

# Method 2: fio with verify during IO
fio --name=verify_test --rw=randrw --rwmixread=50 --bs=4k \
    --iodepth=32 --direct=1 --verify=crc32c \
    --time_based --runtime=3600

# Method 3: md5sum blocks
dd if=/dev/nvme0n1 bs=1M count=100 | md5sum  # Before test
# [test]
dd if=/dev/nvme0n1 bs=1M count=100 | md5sum  # After test
# Compare: should match if read-only workload
```

---

## 4. Quick Reference: fio Parameters

| Parameter | Low Stress | Medium | High Stress | Max Stress |
|-----------|-----------|--------|-------------|------------|
| `--iodepth` | 1 | 32 | 128 | 256-512 |
| `--numjobs` | 1 | 2 | 4 | 8-16 |
| `--bs` | 4k | 16k | 64k | 128k-1M |
| `--rw` | randread | randrw | write | randrw |
| Approx IOPS | ~10K | ~200K | ~1M | ~2M |
| Approx BW | ~40MB/s | ~3GB/s | ~6GB/s | ~14GB/s |
| PCIe Link Load | <5% | ~40% | ~80% | ~95% |
