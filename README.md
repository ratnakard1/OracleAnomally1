# Oracle ASM Disk Write Error Diagnostics Tool

A comprehensive Python tool for diagnosing and monitoring Oracle ASM disk write errors, specifically targeting **ORA-15032** and **ORA-15096** errors.

## Error Descriptions

### ORA-15032: not all alterations performed
This error occurs when an `ALTER DISKGROUP` command cannot complete all requested operations. Common causes include:
- Insufficient disks to maintain redundancy
- Disks in FORCING state
- Disk path accessibility issues
- Insufficient space for rebalancing operations

### ORA-15096: lost disk write detected
This critical error indicates that Oracle ASM detected a lost write operation. This typically signals:
- Hardware disk failures
- Storage array controller issues
- I/O subsystem problems
- Firmware issues
- Multipathing configuration errors

## Features

- **Disk Group Status Monitoring**: Check the health and status of all ASM disk groups
- **Individual Disk Analysis**: Detailed status of each disk including I/O statistics and errors
- **Alert Log Scanning**: Search for recent ORA-15032 and ORA-15096 errors
- **Operation Tracking**: Monitor ongoing ASM operations and rebalancing
- **Remediation Recommendations**: Automated suggestions based on detected issues
- **Comprehensive Reporting**: Generate detailed diagnostics reports with timestamps
- **Simulation Mode**: Test error scenarios without requiring database access

## Installation

### Prerequisites

1. **Oracle Instant Client**: Required for cx_Oracle
   ```bash
   # For Linux (Oracle Linux/RHEL/CentOS)
   sudo yum install oracle-instantclient-basic
   
   # For Ubuntu/Debian
   # Download from Oracle website and install manually
   ```

2. **Python Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

### Manual Installation
```bash
pip install cx_Oracle>=8.3.0
```

## Usage

### With Database Connection

Run diagnostics against a live Oracle ASM instance:

```bash
# Connect as SYSDBA (typical for ASM)
python oracle_disk_diagnostics.py \
  --connection 'sys/password@localhost:1521/+ASM' \
  --sysdba

# Connect as regular user
python oracle_disk_diagnostics.py \
  --connection 'asmadmin/password@hostname:1521/+ASM'
```

### Simulation Mode (No Database Required)

View error scenarios and recommended queries without database access:

```bash
# Simulate ORA-15096 scenario
python oracle_disk_diagnostics.py --simulate 15096

# Simulate ORA-15032 scenario
python oracle_disk_diagnostics.py --simulate 15032

# Simulate both scenarios
python oracle_disk_diagnostics.py --simulate both
```

## Output

The tool generates:

1. **Console Output**: Real-time diagnostics and findings
2. **Log File**: `oracle_disk_diagnostics.log` with detailed execution logs
3. **Report File**: `asm_diagnostics_YYYYMMDD_HHMMSS.txt` with complete analysis

### Sample Report Structure

```
================================================================================
ORACLE ASM DISK WRITE ERROR DIAGNOSTICS REPORT
Generated: 2025-12-19 10:30:45
================================================================================

DISK GROUP STATUS
--------------------------------------------------------------------------------
Disk Group: DATA
  State: MOUNTED
  Type: EXTERN
  Total Space: 204800 MB
  Free Space: 102400 MB
  Offline Disks: 0
  Voting Files: N

INDIVIDUAL DISK STATUS
--------------------------------------------------------------------------------
Disk: DATA_0000 (Group: DATA)
  Path: /dev/oracleasm/disk1
  State: NORMAL
  Mount Status: CACHED
  Header Status: MEMBER
  Total Size: 102400 MB
  I/O Stats - Reads: 1523456, Writes: 987234
  Errors - Read: 0, Write: 0

RECENT ALERT LOG ERRORS (Last 24 hours)
--------------------------------------------------------------------------------
[2025-12-19 09:15:23] ORA-15096: lost disk write detected

REMEDIATION RECOMMENDATIONS
--------------------------------------------------------------------------------
[Specific recommendations based on findings]
```

## Diagnostic Queries

The tool executes several key diagnostic queries:

### Check Disk Status
```sql
SELECT name, path, state, mode_status, mount_status 
FROM v$asm_disk 
WHERE state != 'NORMAL' OR mount_status != 'CACHED';
```

### Check I/O Errors
```sql
SELECT name, path, reads, writes, read_errs, write_errs 
FROM v$asm_disk 
WHERE read_errs > 0 OR write_errs > 0;
```

### Check Disk Group Status
```sql
SELECT name, state, type, offline_disks 
FROM v$asm_diskgroup;
```

### Check Ongoing Operations
```sql
SELECT group_number, operation, state, power, sofar, est_work 
FROM v$asm_operation;
```

## Troubleshooting Steps

### For ORA-15096 (Lost Disk Write)

1. **Check Storage Array**:
   ```bash
   # Check system logs for I/O errors
   sudo grep -i "i/o error" /var/log/messages
   sudo dmesg | grep -i error
   ```

2. **Verify Disk Paths**:
   ```bash
   # List multipath devices
   multipath -ll
   
   # Check ASM disk discovery
   ls -la /dev/oracleasm/disks/
   ```

3. **Check ASM Instance**:
   ```sql
   -- Connect to ASM instance
   sqlplus / as sysasm
   
   -- Check disk errors
   SELECT path, read_errs, write_errs 
   FROM v$asm_disk 
   WHERE read_errs > 0 OR write_errs > 0;
   ```

4. **Hardware Diagnostics**:
   - Review storage array logs
   - Check HBA firmware versions
   - Verify cable connections
   - Run disk surface scans

### For ORA-15032 (Alterations Not Performed)

1. **Check Disk Group Redundancy**:
   ```sql
   SELECT name, type, total_mb, free_mb, required_mirror_free_mb 
   FROM v$asm_diskgroup;
   ```

2. **Identify Problematic Disks**:
   ```sql
   SELECT name, path, header_status, mode_status, state 
   FROM v$asm_disk 
   WHERE header_status != 'MEMBER' OR state = 'FORCING';
   ```

3. **Check Failed Operations**:
   ```sql
   SELECT group_number, operation, state, error_code 
   FROM v$asm_operation 
   WHERE state = 'ERROR';
   ```

4. **Review Alert Log**:
   ```bash
   # Find ASM alert log location
   adrci
   > show homes
   > set home <asm_home>
   > show alert -tail 100
   ```

## Common Resolution Steps

### Dropping a Failed Disk
```sql
ALTER DISKGROUP data DROP DISK data_0001 FORCE;
```

### Adding a Replacement Disk
```sql
ALTER DISKGROUP data ADD DISK '/dev/oracleasm/new_disk' NAME data_0005;
```

### Mounting a Disk Group
```sql
ALTER DISKGROUP data MOUNT;
```

### Checking Rebalance Progress
```sql
SELECT operation, state, power, sofar, est_work, 
       ROUND((sofar/est_work)*100, 2) as percent_complete
FROM v$asm_operation;
```

## Best Practices

1. **Regular Monitoring**: Run diagnostics daily or after any disk-related alerts
2. **Proactive Hardware Checks**: Monitor disk I/O errors before they become critical
3. **Maintain Redundancy**: Ensure disk groups have appropriate redundancy levels
4. **Storage Array Monitoring**: Keep storage array firmware updated and monitor health
5. **Alert Log Review**: Regularly check ASM alert logs for early warnings
6. **Backup Strategy**: Ensure proper backup strategy is in place for data protection

## Environment Variables

You can set these environment variables for easier usage:

```bash
export ORACLE_HOME=/u01/app/oracle/product/19c/dbhome_1
export PATH=$ORACLE_HOME/bin:$PATH
export LD_LIBRARY_PATH=$ORACLE_HOME/lib:$LD_LIBRARY_PATH
export ORACLE_SID=+ASM
```

## Security Considerations

- Store connection credentials securely (consider Oracle Wallet)
- Limit SYSDBA access to authorized personnel only
- Review generated reports before sharing (may contain sensitive paths/names)
- Rotate database passwords regularly
- Use encrypted connections when possible

## Troubleshooting the Tool

### cx_Oracle ImportError
```bash
# Verify Oracle Instant Client installation
echo $LD_LIBRARY_PATH

# Install cx_Oracle
pip install cx_Oracle

# If needed, set Oracle library path
export LD_LIBRARY_PATH=/usr/lib/oracle/19.3/client64/lib:$LD_LIBRARY_PATH
```

### Connection Refused
- Verify ASM instance is running: `ps -ef | grep asm_pmon`
- Check listener status: `lsnrctl status`
- Verify connection string format
- Ensure network connectivity to database host

### Permission Denied
- Ensure user has appropriate privileges (SYSDBA/SYSASM for ASM)
- Check Oracle user permissions
- Verify file system permissions for writing logs/reports

## Support and Documentation

- Oracle ASM Documentation: https://docs.oracle.com/en/database/oracle/oracle-database/
- Oracle Error Messages: https://docs.oracle.com/en/error-help/
- cx_Oracle Documentation: https://cx-oracle.readthedocs.io/

## License

This tool is provided as-is for diagnostic purposes. Always test in non-production environments first.

## Author

Created for diagnosing and resolving Oracle ASM disk write errors (ORA-15032, ORA-15096).
