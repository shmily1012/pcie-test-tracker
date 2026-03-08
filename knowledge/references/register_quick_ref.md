# PCIe Register Quick Reference for NVMe SSD Debug

> Commonly accessed registers during debug. All offsets relative to config space base.
> Use `setpci -s BDF OFFSET.SIZE` to read/write.

---

## 1. Type 0 Configuration Header (00h-3Fh)

```
Offset  Size  Register             setpci Example          Expected (NVMe)
──────────────────────────────────────────────────────────────────────────
00h     W     Vendor ID             setpci -s $B 00.w       Your VID
02h     W     Device ID             setpci -s $B 02.w       Your DID
04h     W     Command               setpci -s $B 04.w       0x0406 (BME+MSE+PERR)
06h     W     Status                setpci -s $B 06.w       0x0010 (CapList)
08h     B     Revision ID           setpci -s $B 08.b       FW dependent
09h     3B    Class Code            setpci -s $B 09.b/0a.b/0b.b  02/08/01
0Ch     B     Cache Line Size       setpci -s $B 0c.b       
0Dh     B     Latency Timer         setpci -s $B 0d.b       0x00
0Eh     B     Header Type           setpci -s $B 0e.b       0x00 (Type 0)
10h     L     BAR0 (low)            setpci -s $B 10.l       Memory, 64-bit, NP
14h     L     BAR0 (high)           setpci -s $B 14.l       Upper 32 bits
2Ch     W     Subsystem VID         setpci -s $B 2c.w       
2Eh     W     Subsystem DID         setpci -s $B 2e.w       
34h     B     Capability Pointer    setpci -s $B 34.b       First cap offset
```

---

## 2. PCIe Capability (Cap ID = 10h)

```
Typically at offset 40h-7Fh (varies per device). Find with:
  lspci -s $B -vvv | grep "Express"

Offset from PCIe Cap base:
+00h  W   PCIe Capabilities        Type (Endpoint=0), Version
+02h  W   Device Capabilities      MPS support, FLR, Phantom Func
+04h  W   Device Control           MPS, Enable bits
+06h  W   Device Status            CE/NFE/FE Detected, Transaction Pending
+08h  W   Link Capabilities        MaxSpeed, MaxWidth, ASPM, L0s/L1 Latency
+0Ah  W   Link Control             ASPM Control, Retrain Link, CCC
+0Ch  W   Link Status              CurrentSpeed, CurrentWidth, Training
+24h  L   Device Capabilities 2    CTO Ranges, LTR, OBFF, AtomicOp
+28h  W   Device Control 2         CTO Value, LTR Enable, OBFF Enable
+2Ch  L   Link Capabilities 2      Supported Link Speeds
+30h  W   Link Control 2           Target Link Speed, EQ Control
+32h  W   Link Status 2            Current De-emphasis, EQ Complete

Common operations:
  # Read current link speed/width
  lspci -s $B -vvv | grep "LnkSta:"
  
  # Read MPS setting (bits 7:5 of DevCtl)
  DevCtl=setpci -s $B CAP_EXP+8.w  # e.g., offset 48h
  MPS = (DevCtl >> 5) & 7  → 0=128B, 1=256B, 2=512B
  
  # Set Target Link Speed (bits 3:0 of LnkCtl2)
  # 1=Gen1, 2=Gen2, 3=Gen3, 4=Gen4, 5=Gen5
  setpci -s $B CAP_EXP+30.w  # Read LnkCtl2
  
  # Trigger Retrain (bit 5 of LnkCtl)
  setpci -s $B CAP_EXP+10.w  # Read LnkCtl, set bit 5
```

---

## 3. Power Management Capability (Cap ID = 01h)

```
Offset from PM Cap base:
+00h  W   PM Capabilities        PME support, D1/D2 support, Aux Current
+02h  W   PM Control/Status (PMCSR)
              Bits 1:0 = Power State: 00=D0, 01=D1, 10=D2, 11=D3hot
              Bit 8    = PME Enable
              Bit 15   = PME Status

Common operations:
  # Read current power state
  PM_OFF=$(lspci -s $B -vvv | grep "Power Management" | grep -oP '\[\K\w+')
  PMCSR_OFF=$((16#$PM_OFF + 4))
  setpci -s $B $(printf %x $PMCSR_OFF).w
  # Last 2 bits: 00=D0, 11=D3hot
  
  # Set D3hot
  PMCSR=$(setpci -s $B $(printf %x $PMCSR_OFF).w)
  setpci -s $B $(printf %x $PMCSR_OFF).w=$(printf %04x $(( (16#$PMCSR & 0xFFFC) | 3 )))
  
  # Restore D0
  setpci -s $B $(printf %x $PMCSR_OFF).w=$(printf %04x $(( 16#$PMCSR & 0xFFFC )))
```

---

## 4. MSI-X Capability (Cap ID = 11h)

```
Offset from MSI-X Cap base:
+00h  W   Message Control
              Bits 10:0 = Table Size (N-1)
              Bit 14    = Function Mask (global)
              Bit 15    = MSI-X Enable
+02h  L   Table Offset / BIR
              Bits 2:0  = BIR (BAR Indicator Register)
              Bits 31:3 = Offset into BAR
+06h  L   PBA Offset / BIR

MSI-X Table Entry (in BAR memory, 16 bytes each):
  +00h  L   Message Address (low)
  +04h  L   Message Address (high)
  +08h  L   Message Data
  +0Ch  L   Vector Control (bit 0 = Mask)
```

---

## 5. AER Extended Capability (Cap ID = 0001h)

```
Find offset: lspci -s $B -vvv | grep "Advanced Error"
Typically at 100h in extended config space.

Offset from AER base:
+04h  L   Uncorrectable Error Status (RW1C)
              Bit 4:  Data Link Protocol Error
              Bit 5:  Surprise Down
              Bit 12: Poisoned TLP
              Bit 13: FC Protocol Error
              Bit 14: Completion Timeout
              Bit 15: Completer Abort
              Bit 16: Unexpected Completion
              Bit 17: Receiver Overflow
              Bit 18: Malformed TLP
              Bit 19: ECRC Error
              Bit 20: Unsupported Request

+08h  L   Uncorrectable Error Mask
+0Ch  L   Uncorrectable Error Severity (1=Fatal, 0=Non-Fatal)

+10h  L   Correctable Error Status (RW1C)
              Bit 0:  Receiver Error
              Bit 6:  Bad TLP
              Bit 7:  Bad DLLP
              Bit 8:  REPLAY_NUM Rollover
              Bit 12: Replay Timer Timeout
              Bit 13: Advisory Non-Fatal
              Bit 14: Correctable Internal Error
              Bit 15: Header Log Overflow

+14h  L   Correctable Error Mask

+18h  L   Advanced Error Capabilities and Control
              Bit 0:  First Error Pointer (bits 4:0)
              Bit 5:  ECRC Generation Capable
              Bit 6:  ECRC Generation Enable
              Bit 7:  ECRC Check Capable
              Bit 8:  ECRC Check Enable

+1Ch  16B  Header Log (4 DWORDs of offending TLP header)
+2Ch  L   Root Error Command (Root Port only)
+30h  L   Root Error Status (Root Port only)
+34h  L   Error Source Identification
+38h  L   TLP Prefix Log

Common operations:
  AER_OFF="100"  # Adjust if different
  
  # Read CE status
  setpci -s $B $(printf %x $((16#$AER_OFF + 0x10))).l
  
  # Clear CE status (write 1 to clear)
  CE_VAL=$(setpci -s $B $(printf %x $((16#$AER_OFF + 0x10))).l)
  setpci -s $B $(printf %x $((16#$AER_OFF + 0x10))).l=$CE_VAL
  
  # Enable ECRC
  AEC_OFF=$(printf %x $((16#$AER_OFF + 0x18)))
  AEC=$(setpci -s $B ${AEC_OFF}.l)
  # Set bits 6 (Gen Enable) and 8 (Check Enable)
  NEW=$(printf %08x $(( 16#$AEC | 0x140 )))
  setpci -s $B ${AEC_OFF}.l=$NEW
```

---

## 6. L1 PM Substates Extended Capability (Cap ID = 001Eh)

```
+04h  L   L1 PM Substates Capabilities
              Bit 0: PCI-PM L1.2 Supported
              Bit 1: PCI-PM L1.1 Supported
              Bit 2: ASPM L1.2 Supported
              Bit 3: ASPM L1.1 Supported
              Bit 4: L1 PM Substates Supported
              Bits 15:8:  Port Common Mode Restore Time (μs)
              Bits 23:16: Port T_POWER_ON Scale
              Bits 28:24: Port T_POWER_ON Value

+08h  L   L1 PM Substates Control 1
              Bit 0: PCI-PM L1.2 Enable
              Bit 1: PCI-PM L1.1 Enable
              Bit 2: ASPM L1.2 Enable
              Bit 3: ASPM L1.1 Enable
              Bits 31:16: LTR L1.2 Threshold

+0Ch  L   L1 PM Substates Control 2
              Bits 7:0: T_POWER_ON (composite timing)
```

---

## 7. Physical Layer 32 GT/s Extended Capability (Cap ID = 002Ah)

> Gen5 specific. Lane Margining registers are here.

```
+04h  L   32 GT/s Capabilities
              Bit 0:  Equalization Bypass to Highest Rate
              Bit 1:  No Equalization Needed
              Bit 2:  Modified TS Usage Mode 1 Supported
              Bit 3:  Modified TS Usage Mode 2 Supported

+08h  L   32 GT/s Control

+0Ch  L   32 GT/s Status
              Bit 0:  Equalization 32 GT/s Complete
              Bits 6:1: Equalization 32 GT/s Phase 1-3 Status

+10h  8×L  Lane Equalization Control (per lane, 2 DWORDs each)

Lane Margining:
+100h (varies)  Lane Margining Extended Capability
  +04h  W   Margining Port Capabilities
  +06h  W   Margining Port Status
  +08h  W   Margining Lane Control (per lane)
  +0Ah  W   Margining Lane Status (per lane)
```

---

## 8. Cheat Sheet: Common Debug Commands

```bash
BDF="01:00.0"

# --- Identity ---
lspci -s $BDF -nn                          # VID:DID, class
lspci -s $BDF -vvv                         # Full verbose
lspci -s $BDF -xxxx                        # Full hex dump

# --- Link ---
lspci -s $BDF -vvv | grep "LnkSta:"       # Current speed/width
lspci -s $BDF -vvv | grep "LnkCap:"       # Max speed/width

# --- Errors ---
cat /sys/bus/pci/devices/0000:$BDF/aer_dev_correctable
cat /sys/bus/pci/devices/0000:$BDF/aer_dev_fatal
cat /sys/bus/pci/devices/0000:$BDF/aer_dev_nonfatal

# --- NVMe ---
nvme list                                   # Device list
nvme show-regs /dev/nvme0                  # Controller regs
nvme id-ctrl /dev/nvme0                    # Identify
nvme smart-log /dev/nvme0                  # SMART health
nvme error-log /dev/nvme0                  # Error history

# --- Power ---
lspci -s $BDF -vvv | grep "Status:" | head -1  # D0/D3hot

# --- Reset ---
echo 1 > /sys/bus/pci/devices/0000:$BDF/reset     # FLR
echo 1 > /sys/bus/pci/devices/0000:$BDF/remove     # Remove
echo 1 > /sys/bus/pci/rescan                        # Rescan

# --- Driver ---
lspci -s $BDF -k                           # Kernel driver in use
ls /sys/bus/pci/devices/0000:$BDF/driver   # Driver binding
```
