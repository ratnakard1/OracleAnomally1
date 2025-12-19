# Solution Summary: Oracle ASM Disk Write Errors

## Problem Statement

You encountered critical Oracle ASM errors:
- **ORA-15032**: not all alterations performed
- **ORA-15096**: lost disk write detected (DBD ERROR: OCIStmtExecute)

These errors indicate serious storage layer issues that can lead to data corruption or database downtime if not addressed immediately.

## Solution Provided

A comprehensive Python-based diagnostic and monitoring tool that helps:

### 1. **Diagnose Issues** 
   - Query ASM disk group status
   - Check individual disk health and I/O errors
   - Scan alert logs for recent errors
   - Monitor ongoing ASM operations

### 2. **Provide Actionable Recommendations**
   - Automated analysis of disk and disk group health
   - Specific remediation steps based on detected issues
   - Best practices for both ORA-15096 and ORA-15032 errors

### 3. **Generate Comprehensive Reports**
   - Timestamped diagnostic reports
   - Detailed logging for audit trails
   - Easy-to-read formatted output

### 4. **Simulate and Learn**
   - No database required for learning mode
   - View error scenarios and SQL queries
   - Test tool functionality offline

## Files Created

| File | Purpose |
|------|---------|
| `oracle_disk_diagnostics.py` | Main diagnostic tool (500+ lines) |
| `test.py` | Comprehensive unit tests (11 test cases) |
| `requirements.txt` | Python dependencies |
| `README.md` | Full documentation with examples |
| `QUICK_REFERENCE.md` | Quick troubleshooting guide |
| `example_usage.sh` | Usage examples and quick start |
| `SOLUTION_SUMMARY.md` | This file |

## Quick Start

### Option 1: Try Simulation Mode (No Database Needed)
```bash
python3 oracle_disk_diagnostics.py --simulate both
```

### Option 2: Run Against Live Database
```bash
python3 oracle_disk_diagnostics.py \
  --connection 'sys/password@host:1521/+ASM' \
  --sysdba
```

### Option 3: Run Tests
```bash
python3 test.py
```

## Key Features

### ✅ Diagnostics Capabilities
- Check disk group status (mounted, space, redundancy)
- Analyze individual disk health (errors, state, I/O stats)
- Search alert logs for ORA-15032/ORA-15096 errors
- Monitor rebalancing and ASM operations
- Track disk read/write errors in real-time

### ✅ Smart Recommendations
- Automated issue detection
- Specific remediation steps for detected problems
- General best practices for both error types
- Hardware and storage array guidance
- SQL queries for deeper investigation

### ✅ Comprehensive Reporting
- Formatted text reports with timestamps
- Separate log files for debugging
- Export-friendly format
- Section-based organization

### ✅ No Database Required Mode
- Learn about errors through simulation
- View recommended SQL queries
- Understand error scenarios
- Test tool functionality

## Understanding the Errors

### ORA-15096: Lost Disk Write Detected

**Severity**: 🔴 CRITICAL

**What Happened**: Oracle ASM tried to write data to disk but couldn't confirm the write completed successfully. This is a serious data integrity issue.

**Common Causes**:
1. Physical disk failure
2. Storage array controller malfunction
3. I/O subsystem problems (cables, HBA)
4. Firmware bugs
5. Write cache issues

**Immediate Actions**:
```sql
-- Find disks with write errors
SELECT name, path, write_errs, state 
FROM v$asm_disk 
WHERE write_errs > 0;

-- Check disk group status
SELECT name, state, offline_disks 
FROM v$asm_diskgroup;
```

### ORA-15032: Not All Alterations Performed

**Severity**: 🟠 HIGH

**What Happened**: An `ALTER DISKGROUP` command couldn't complete all requested changes, usually during disk add/drop operations.

**Common Causes**:
1. Insufficient disks to maintain redundancy
2. Disks stuck in FORCING state
3. Path accessibility issues
4. Insufficient space for rebalancing
5. Disk header corruption

**Immediate Actions**:
```sql
-- Find problematic disks
SELECT name, path, state, header_status 
FROM v$asm_disk 
WHERE state != 'NORMAL';

-- Check for failed operations
SELECT operation, state, error_code 
FROM v$asm_operation 
WHERE state = 'ERROR';
```

## Typical Recovery Workflow

### Phase 1: Assessment (Use the diagnostic tool)
```bash
python3 oracle_disk_diagnostics.py \
  --connection 'sys/password@host:1521/+ASM' \
  --sysdba
```

Review the generated report to identify:
- Which disks have errors
- Which disk groups are affected
- Current rebalance status
- Space availability

### Phase 2: Isolation
Check storage layer:
```bash
# System logs
sudo tail -100 /var/log/messages | grep -i error

# Disk I/O stats
iostat -x 5

# Multipath status
multipath -ll

# Hardware errors
dmesg | grep -i error
```

### Phase 3: Remediation
Drop failed disk:
```sql
ALTER DISKGROUP data DROP DISK data_0001 FORCE;
```

Add replacement disk:
```sql
ALTER DISKGROUP data ADD DISK '/dev/oracleasm/new_disk';
```

Monitor rebalance:
```sql
SELECT operation, state, sofar, est_work 
FROM v$asm_operation;
```

### Phase 4: Verification
Re-run diagnostic tool to confirm:
- No more disk errors
- All disk groups mounted
- Rebalance completed
- Redundancy restored

## Installation Requirements

### Minimal (Simulation Mode)
- Python 3.x
- No other dependencies

### Full Functionality (Database Connection)
- Python 3.x
- cx_Oracle package
- Oracle Instant Client
- Network access to ASM instance

### Installation
```bash
# Install Python dependencies
pip install -r requirements.txt

# Or manually
pip install cx_Oracle
```

## Testing

The solution includes comprehensive unit tests:

```bash
$ python3 test.py
test_get_remediation_recommendations_includes_general_advice ... ok
test_get_remediation_recommendations_with_disk_errors ... ok
test_get_remediation_recommendations_with_offline_disks ... ok
test_get_remediation_recommendations_with_unmounted_diskgroups ... ok
test_initialization ... ok
test_simulate_ora_15032_scenario ... ok
test_simulate_ora_15096_scenario ... ok
test_generate_report_structure ... ok
test_detect_abnormal_disk_states ... ok
test_detect_disk_with_io_errors ... ok
test_detect_offline_diskgroups ... ok

----------------------------------------------------------------------
Ran 11 tests in 0.001s

OK ✅
```

## Sample Output

### Disk Group Status
```
Disk Group: DATA
  State: MOUNTED
  Type: EXTERN
  Total Space: 204800 MB
  Free Space: 102400 MB
  Offline Disks: 0
  Voting Files: N
```

### Individual Disk Status (with Issues)
```
Disk: DATA_0001 (Group: DATA)
  Path: /dev/oracleasm/disk1
  State: NORMAL
  Mount Status: CACHED
  Header Status: MEMBER
  Total Size: 102400 MB
  I/O Stats - Reads: 1523456, Writes: 987234
  Errors - Read: 0, Write: 5
  *** ERROR: I/O ERRORS DETECTED ***
```

### Recommendations
```
REMEDIATION RECOMMENDATIONS
--------------------------------------------------------------------------------
ERROR: 1 disk(s) with I/O errors detected. Check disk paths, hardware, 
and storage array status.
  - Disk: DATA_0001 (Path: /dev/oracleasm/disk1) - 
    Read Errors: 0, Write Errors: 5

General recommendations for ORA-15096 (lost disk write):
1. Check storage array logs for hardware failures
2. Verify disk path connectivity and multipathing
3. Check for firmware updates on storage controllers
4. Review system logs for I/O errors
5. Verify ASM disk discovery string
6. Consider running disk surface scans
```

## Support Resources

### Documentation
- `README.md` - Complete documentation
- `QUICK_REFERENCE.md` - Troubleshooting guide
- `example_usage.sh` - Usage examples

### Oracle Documentation
- [Managing ASM Disk Groups](https://docs.oracle.com/en/database/oracle/oracle-database/19/ostmg/)
- My Oracle Support: Doc ID 1088884.1 (ORA-15096)
- My Oracle Support: Doc ID 1507796.1 (ORA-15032)

### Tool Support
- Run tests: `python3 test.py`
- Simulation mode: `python3 oracle_disk_diagnostics.py --simulate both`
- Check logs: `oracle_disk_diagnostics.log`

## Next Steps

1. **Immediate**: Run simulation mode to understand the errors
   ```bash
   python3 oracle_disk_diagnostics.py --simulate both
   ```

2. **If you have database access**: Run diagnostics
   ```bash
   python3 oracle_disk_diagnostics.py \
     --connection 'your_connection_string' \
     --sysdba
   ```

3. **Review**: Check the generated report and logs

4. **Act**: Follow the remediation recommendations

5. **Monitor**: Re-run diagnostics after remediation

6. **Prevent**: Implement monitoring and alerting

## Prevention Best Practices

✅ Run diagnostics daily or after any disk-related alerts  
✅ Monitor disk I/O errors proactively  
✅ Keep storage firmware and drivers updated  
✅ Maintain proper disk group redundancy (NORMAL/HIGH)  
✅ Keep at least 20% free space in disk groups  
✅ Document disk replacement procedures  
✅ Set up automated alerts for ASM errors  
✅ Perform regular storage health checks  

## Summary

This solution provides enterprise-grade diagnostics and monitoring for Oracle ASM disk write errors. The tool:

- ✅ Identifies root causes quickly
- ✅ Provides specific remediation steps
- ✅ Generates audit-ready reports
- ✅ Works with or without database access
- ✅ Includes comprehensive testing
- ✅ Follows Oracle best practices

**The errors you encountered (ORA-15032, ORA-15096) are now diagnosable and addressable with this tool.**
