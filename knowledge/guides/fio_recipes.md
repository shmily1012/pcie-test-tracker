# fio Recipes for PCIe NVMe SSD Testing

> Standard fio command lines mapped to specific test items.
> Copy-paste ready. Adjust DEVICE and runtime as needed.

---

## Setup

```bash
DEVICE="/dev/nvme0n1"  # Change to your namespace
# For destructive write tests, use a test namespace or partition
# For read-only tests, safe on any namespace

# Precondition (write entire device once — optional but recommended for consistent results)
# WARNING: DESTROYS DATA
# fio --name=precondition --filename=$DEVICE --rw=write --bs=1M --iodepth=32 --direct=1 --numjobs=1
```

---

## PERF-001: Sequential Read Bandwidth

```bash
# Target: Measure peak sequential read bandwidth
# Expected Gen5 x4: ~12-15 GB/s (device dependent)
# Expected Gen4 x4: ~6-7 GB/s
# Expected Gen3 x4: ~3-3.5 GB/s

fio --name=seq_read \
    --filename=$DEVICE \
    --rw=read \
    --bs=128k \
    --iodepth=256 \
    --numjobs=4 \
    --direct=1 \
    --group_reporting \
    --time_based --runtime=60 \
    --output-format=json+ \
    --output=/tmp/perf001_seq_read.json
```

## PERF-002: Sequential Write Bandwidth

```bash
# WARNING: DESTRUCTIVE — writes to device
fio --name=seq_write \
    --filename=$DEVICE \
    --rw=write \
    --bs=128k \
    --iodepth=256 \
    --numjobs=4 \
    --direct=1 \
    --group_reporting \
    --time_based --runtime=60 \
    --output-format=json+ \
    --output=/tmp/perf002_seq_write.json
```

## PERF-003: Random Read 4K IOPS

```bash
fio --name=rand_read_4k \
    --filename=$DEVICE \
    --rw=randread \
    --bs=4k \
    --iodepth=256 \
    --numjobs=4 \
    --direct=1 \
    --group_reporting \
    --time_based --runtime=60 \
    --output-format=json+ \
    --output=/tmp/perf003_rand_read.json
```

## PERF-004: Random Write 4K IOPS

```bash
# WARNING: DESTRUCTIVE
fio --name=rand_write_4k \
    --filename=$DEVICE \
    --rw=randwrite \
    --bs=4k \
    --iodepth=256 \
    --numjobs=4 \
    --direct=1 \
    --group_reporting \
    --time_based --runtime=60 \
    --output-format=json+ \
    --output=/tmp/perf004_rand_write.json
```

## PERF-005: Mixed 70/30 Read/Write

```bash
# WARNING: DESTRUCTIVE
fio --name=mixed_70_30 \
    --filename=$DEVICE \
    --rw=randrw --rwmixread=70 \
    --bs=4k \
    --iodepth=128 \
    --numjobs=4 \
    --direct=1 \
    --group_reporting \
    --time_based --runtime=60 \
    --output-format=json+ \
    --output=/tmp/perf005_mixed.json
```

## PERF-008: Multi-Queue Scalability

```bash
# Run for each queue count: 1, 2, 4, 8, 16, 32
for JOBS in 1 2 4 8 16 32; do
    echo "=== Testing with $JOBS queues ==="
    fio --name=scale_${JOBS}q \
        --filename=$DEVICE \
        --rw=randread \
        --bs=4k \
        --iodepth=64 \
        --numjobs=$JOBS \
        --direct=1 \
        --group_reporting \
        --time_based --runtime=30 \
        --output-format=json+ \
        --output=/tmp/perf008_scale_${JOBS}q.json
done
```

## PERF-009: QD=1 Latency

```bash
fio --name=lat_qd1 \
    --filename=$DEVICE \
    --rw=randread \
    --bs=4k \
    --iodepth=1 \
    --numjobs=1 \
    --direct=1 \
    --time_based --runtime=60 \
    --lat_percentiles=1 \
    --output-format=json+ \
    --output=/tmp/perf009_lat_qd1.json
```

## PERF-010: Latency Under Load

```bash
# Two jobs: background load + latency probe
fio --name=bg_load \
    --filename=$DEVICE \
    --rw=randread \
    --bs=4k \
    --iodepth=128 \
    --numjobs=3 \
    --direct=1 \
    --time_based --runtime=60 \
    --new_group \
    --name=lat_probe \
    --filename=$DEVICE \
    --rw=randread \
    --bs=4k \
    --iodepth=1 \
    --numjobs=1 \
    --direct=1 \
    --time_based --runtime=60 \
    --lat_percentiles=1 \
    --output-format=json+ \
    --output=/tmp/perf010_lat_under_load.json
```

## PERF-013: 72-Hour Stress

```bash
# WARNING: DESTRUCTIVE, long running
fio --name=stress_72h \
    --filename=$DEVICE \
    --rw=randrw --rwmixread=70 \
    --bs=4k \
    --iodepth=128 \
    --numjobs=4 \
    --direct=1 \
    --time_based --runtime=259200 \
    --eta-newline=3600 \
    --write_bw_log=/tmp/stress72h_bw \
    --write_lat_log=/tmp/stress72h_lat \
    --write_iops_log=/tmp/stress72h_iops \
    --log_avg_msec=60000 \
    --output-format=json+ \
    --output=/tmp/perf013_stress.json

# Post-analysis: plot bandwidth over time to detect degradation
# gnuplot or fio_generate_plots
```

## PERF-006: MPS Impact

```bash
BDF="01:00.0"  # Change this
for MPS in 128 256 512; do
    MPS_VAL=$(python3 -c "import math; print(int(math.log2($MPS/128)))")
    
    # Set MPS (bits 7:5 of DevCtl)
    DEVCTL=$(setpci -s $BDF CAP_EXP+8.w)
    NEW_DEVCTL=$(python3 -c "print(f'{(int(\"$DEVCTL\",16) & 0xFF1F) | ($MPS_VAL << 5):04x}')")
    setpci -s $BDF CAP_EXP+8.w=$NEW_DEVCTL
    
    echo "=== MPS=$MPS ==="
    fio --name=mps_${MPS} \
        --filename=$DEVICE \
        --rw=read \
        --bs=128k \
        --iodepth=256 \
        --numjobs=4 \
        --direct=1 \
        --group_reporting \
        --time_based --runtime=30 \
        --output-format=json+ \
        --output=/tmp/perf006_mps_${MPS}.json
done
```

---

## Results Parser

```python
#!/usr/bin/env python3
"""Parse fio JSON output and print summary table."""
import json, sys, glob

print(f"{'Test':<30} {'BW (GB/s)':>12} {'IOPS (K)':>12} {'Lat avg(μs)':>12} {'Lat p99(μs)':>12}")
print("-" * 80)

for path in sorted(glob.glob("/tmp/perf*.json")):
    try:
        data = json.load(open(path))
        job = data['jobs'][0]
        name = job['jobname']
        
        r = job.get('read', {})
        w = job.get('write', {})
        
        bw = (r.get('bw', 0) + w.get('bw', 0)) / 1024 / 1024  # GB/s
        iops = (r.get('iops', 0) + w.get('iops', 0)) / 1000  # KIOPS
        lat_avg = r.get('lat_ns', w.get('lat_ns', {})).get('mean', 0) / 1000  # μs
        
        clat = r.get('clat_ns', w.get('clat_ns', {}))
        p99 = clat.get('percentile', {}).get('99.000000', 0) / 1000 if clat else 0
        
        print(f"{name:<30} {bw:>12.2f} {iops:>12.1f} {lat_avg:>12.1f} {p99:>12.1f}")
    except Exception as e:
        print(f"  Error parsing {path}: {e}")
```

---

## Quick Reference: fio Parameters for PCIe Testing

| Parameter | Typical Values | Notes |
|-----------|---------------|-------|
| `--bs` | 4k (IOPS), 128k (BW) | Match to your use case |
| `--iodepth` | 1 (latency), 256 (peak BW/IOPS) | Higher QD = more PCIe TLP parallelism |
| `--numjobs` | 1 (single queue), 4+ (multi-queue) | Maps to NVMe IO queues |
| `--direct=1` | Always use | Bypass OS page cache |
| `--ioengine` | libaio (default), io_uring | io_uring lower CPU overhead |
| `--runtime` | 30s (quick), 60s (standard), 259200 (72h) | |
| `--ramp_time` | 10 (recommended for steady-state) | Warm up before measuring |
| `--size` | 100% (default) or specific range | Full device for realistic results |
| `--norandommap` | For large devices with rand workloads | Reduces memory for random map |
