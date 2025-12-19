# Quick Reference Guide - Oracle ASM Disk Errors

## Error Quick Reference

### ORA-15096: lost disk write detected

**Severity**: CRITICAL ⚠️

**What it means**: A write operation to an ASM disk was not confirmed by the storage layer.

**Immediate Actions**:
```bash
# 1. Check system logs for I/O errors
sudo tail -100 /var/log/messages | grep -i "error\|fail"

# 2. Check ASM disk status
sqlplus / as sysasm
SELECT name, path, state, write_errs FROM v$asm_disk WHERE write_errs > 0;

# 3. Check storage array (example for EMC)
naviseccli -h <array_ip> getagent
```

**Root Causes**:
- ❌ Disk hardware failure
- ❌ Storage controller malfunction  
- ❌ Cable/HBA issues
- ❌ Firmware bugs
- ❌ Write cache problems

---

### ORA-15032: not all alterations performed

**Severity**: HIGH ⚠️

**What it means**: An ALTER DISKGROUP command couldn't complete all operations.

**Immediate Actions**:
```sql
-- 1. Check which disks are problematic
SELECT name, path, header_status, state 
FROM v$asm_disk 
WHERE state != 'NORMAL';

-- 2. Check disk group status
SELECT name, state, offline_disks 
FROM v$asm_diskgroup;

-- 3. Check for failed operations
SELECT * FROM v$asm_operation WHERE state = 'ERROR';
```

**Root Causes**:
- ❌ Insufficient disks for redundancy
- ❌ Disks in FORCING state
- ❌ Path accessibility issues
- ❌ Insufficient space

---

## Command Cheat Sheet

### Diagnostic Tool Usage

```bash
# Run full diagnostics
python oracle_disk_diagnostics.py \
  --connection 'sys/password@host:1521/+ASM' \
  --sysdba

# Simulate errors (no DB needed)
python oracle_disk_diagnostics.py --simulate both

# Run tests
python test.py
```

### Essential SQL Queries

```sql
-- 1. Check all disk status
SELECT name, path, state, mount_status, read_errs, write_errs 
FROM v$asm_disk 
ORDER BY group_number, disk_number;

-- 2. Check disk group health
SELECT name, state, type, total_mb, free_mb, offline_disks 
FROM v$asm_diskgroup;

-- 3. Check for errors in alert log
SELECT originating_timestamp, message_text 
FROM v$diag_alert_ext 
WHERE message_text LIKE '%ORA-15%' 
  AND originating_timestamp > SYSTIMESTAMP - 1
ORDER BY originating_timestamp DESC;

-- 4. Check rebalance progress
SELECT operation, state, power, sofar, est_work,
       ROUND((sofar/est_work)*100, 2) as pct_complete
FROM v$asm_operation;

-- 5. Check disk I/O statistics
SELECT name, reads, writes, read_time, write_time,
       ROUND(read_time/NULLIF(reads,0), 2) as avg_read_ms,
       ROUND(write_time/NULLIF(writes,0), 2) as avg_write_ms
FROM v$asm_disk
WHERE reads > 0 OR writes > 0;
```

### Common Recovery Actions

```sql
-- Drop a failed disk (FORCE if necessary)
ALTER DISKGROUP data DROP DISK data_0001 FORCE;

-- Add a replacement disk
ALTER DISKGROUP data ADD DISK '/dev/oracleasm/new_disk' NAME data_0005;

-- Mount a disk group
ALTER DISKGROUP data MOUNT;

-- Dismount a disk group
ALTER DISKGROUP data DISMOUNT;

-- Check disk group for errors
ALTER DISKGROUP data CHECK ALL REPAIR;

-- Rebalance manually (power 1-11)
ALTER DISKGROUP data REBALANCE POWER 8;
```

### System-Level Diagnostics

```bash
# Check for kernel I/O errors
dmesg | grep -i "error\|fail" | tail -50

# Check multipath status
multipath -ll

# Check ASM disk labels
/usr/sbin/oracleasm listdisks

# Check ASM disk attributes
/usr/sbin/oracleasm querydisk -d /dev/oracleasm/disks/DISK1

# Monitor I/O in real-time
iostat -x 5

# Check for hardware errors
smartctl -a /dev/sdb
```

---

## Decision Tree

```
┌─────────────────────────────┐
│ ORA-15096 or ORA-15032?     │
└──────────┬──────────────────┘
           │
           ├─ ORA-15096 (Lost Write)
           │  │
           │  ├─ Check: v$asm_disk for write_errs > 0
           │  ├─ Check: System logs (/var/log/messages)
           │  ├─ Check: Storage array status
           │  ├─ Action: Identify failed disk
           │  └─ Action: Replace disk, then rebalance
           │
           └─ ORA-15032 (Alterations Failed)
              │
              ├─ Check: v$asm_disk for state != 'NORMAL'
              ├─ Check: v$asm_diskgroup for offline_disks
              ├─ Check: Sufficient space for operation
              └─ Action: Fix underlying issue, retry operation
```

---

## Troubleshooting Workflow

### Phase 1: Assess (5 minutes)
1. Run diagnostic tool: `python oracle_disk_diagnostics.py --connection ... --sysdba`
2. Review generated report
3. Identify failed disks and disk groups
4. Check alert log for patterns

### Phase 2: Isolate (10 minutes)
1. Check storage array status
2. Verify disk paths and multipathing
3. Check system logs for I/O errors
4. Test disk accessibility

### Phase 3: Remediate (30+ minutes)
1. Drop failed disk(s): `ALTER DISKGROUP ... DROP DISK ... FORCE`
2. Add replacement disk(s): `ALTER DISKGROUP ... ADD DISK ...`
3. Monitor rebalance: `SELECT * FROM v$asm_operation`
4. Verify completion: `SELECT state FROM v$asm_diskgroup`

### Phase 4: Verify (15 minutes)
1. Re-run diagnostic tool
2. Confirm no errors in v$asm_disk
3. Verify disk group redundancy restored
4. Check application connectivity

---

## Critical Metrics to Monitor

| Metric | Query | Warning Threshold | Critical Threshold |
|--------|-------|-------------------|-------------------|
| Write Errors | `SELECT SUM(write_errs) FROM v$asm_disk` | > 0 | > 10 |
| Offline Disks | `SELECT SUM(offline_disks) FROM v$asm_diskgroup` | > 0 | > 2 |
| Free Space | `SELECT free_mb/total_mb*100 FROM v$asm_diskgroup` | < 20% | < 10% |
| Rebalance Time | `SELECT est_minutes FROM v$asm_operation` | > 60 min | > 240 min |

---

## Emergency Contacts Checklist

- [ ] Storage Team: Contact for array issues
- [ ] DBA Team: For database recovery
- [ ] Oracle Support: SR# ____________
- [ ] Hardware Vendor: Case# ____________

---

## Prevention Best Practices

✅ **Monitor disk I/O errors daily**
✅ **Keep storage firmware updated**
✅ **Maintain proper redundancy (NORMAL/HIGH)**
✅ **Test backups regularly**
✅ **Document disk replacement procedures**
✅ **Set up automated alerts for ASM errors**
✅ **Perform regular storage health checks**
✅ **Keep adequate free space (>20%)**

---

## Additional Resources

- Oracle Doc: [Managing ASM Disk Groups](https://docs.oracle.com/en/database/oracle/oracle-database/19/ostmg/manage-asm-diskgroups.html)
- My Oracle Support: Doc ID 1088884.1 (ORA-15096)
- My Oracle Support: Doc ID 1507796.1 (ORA-15032)
