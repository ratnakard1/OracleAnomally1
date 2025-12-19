# Oracle Disk Write Error Analysis

## Issue Description
The following errors were reported:
- `ORA-15032: not all alterations performed`
- `ORA-15096: lost disk write detected (DBD ERROR: OCIStmtExecute)`

### Error Breakdown

**ORA-15096: Lost Write Detected**
This is a critical error indicating that an I/O acknowledgment was received by the Oracle instance for a write, but a subsequent read of that block showed the write was not persistent on the disk. This usually points to:
- Faulty storage hardware (disk, controller, cache).
- Firmware bugs in the storage subsystem.
- Network issues in iSCSI/SAN/NAS environments.

**ORA-15032: Not All Alterations Performed**
This is a generic parent error indicating that an `ALTER DISKGROUP` or similar ASM command failed. It is usually accompanied by more specific errors (like ORA-15096) explaining *why* it failed.

## Diagnostic Tool
A Python script `oracle_monitor.py` has been included to demonstrate how to programmatically catch and parse these errors from application logs or database drivers.

### Usage
```bash
python3 oracle_monitor.py
```

### Recommended Actions
1. **Check OS Logs**: Look at `/var/log/messages` or `dmesg` for I/O errors.
2. **Check ASM Alert Log**: The Oracle ASM alert log will have more details on which disk and block failed.
3. **Validate Hardware**: Run diagnostics on the storage subsystem.
